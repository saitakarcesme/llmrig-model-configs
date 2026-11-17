"""Reuse ExLlamaV3's two-launch CUDA MoE decode kernel with dynamic disk caches."""
import torch
from exllamav3.ext import exllamav3_ext as ext
from exllamav3.util.device_copy import to_device


class FusedDecode:
    def __init__(self, device, exemplar, hidden=2560, intermediate=640, topk=10, experts=256):
        self.device=torch.device('cuda',device)
        self.experts=experts
        self.topk=topk
        slots=8*topk
        H,I=hidden,intermediate
        def empty(shape,dtype=torch.float16):
            return torch.empty(shape,device=self.device,dtype=dtype)
        with torch.cuda.device(device):
            yh2=empty((max(64,slots),H))
            igu=empty((max(64,2*slots),I))
            ia2=empty((max(32,slots),I))
            od2=empty((max(32,slots),H),torch.float32)
            ctr=torch.zeros(slots*(I//128)+8*(H//128)+2*slots+3,device=self.device,dtype=torch.int32)
            hadu=empty((slots,H))
            dq=empty((H,I))
            self.output=empty((8,H),torch.float32)
            self.tables=torch.zeros(15*experts,device=self.device,dtype=torch.int64)
            ptr=[self.tables[i*experts:(i+1)*experts] for i in range(9)]
            gu=[self.tables[(9+2*i)*experts:(11+2*i)*experts].view(experts,2) for i in range(3)]
            self.bc=ext.BC_BlockSparseMLP(
                yh2,yh2[:slots].view(slots,1,H),igu,
                igu[:slots].view(slots,1,I),igu[slots:2*slots].view(slots,1,I),
                ia2[:slots].view(slots,1,I),ia2,od2[:slots].view(slots,1,H),od2,
                None,ctr,hadu,dq,dq.view(I,H),0,experts,
                *ptr[0:3],3,False,True,*ptr[3:6],3,False,True,*ptr[6:9],3,False,True,
                True,False,False,None,None,0.0,
                [exemplar['gate_proj'].bc],[exemplar['up_proj'].bc],[exemplar['down_proj'].bc],*gu,self.output,
            )

    def update_tables(self,loaded):
        indices=[]
        values=[]
        for expert,modules in loaded.items():
            local=expert//2
            for p,projection in enumerate(('gate_proj','up_proj','down_proj')):
                m=modules[projection]
                if m.K != 3 or not m.mul1 or m.mcg:
                    raise RuntimeError('Fused disk decode requires the validated K=3 mul1 experts')
                for s,suffix in enumerate(('trellis','suh','svh')):
                    indices.append((p*3+s)*self.experts+local)
                    values.append(getattr(m,suffix).data_ptr())
                    if p<2:
                        indices.append((9+2*s)*self.experts+2*local+p)
                        values.append(getattr(m,suffix).data_ptr())
        with torch.cuda.device(self.device):
            self.tables.index_copy_(0,torch.tensor(indices,device=self.device,dtype=torch.long),
                                    torch.tensor(values,device=self.device,dtype=torch.long))
        return [self.tables[i*self.experts:(i+1)*self.experts] for i in range(9)]

    def run(self,y,ids,weights,loaded):
        self.update_tables(loaded)
        with torch.cuda.device(self.device):
            local=torch.where(ids%2==self.device.index,ids//2,self.experts)
            local=local.to(self.device).contiguous()
            weights=to_device(weights,self.device).contiguous()
            source=to_device(y.contiguous().half(),self.device)
            self.bc.run_bszN(source,local,weights)
            return self.output[:y.shape[0]].clone()

    def prefill(self,y,ids,weights,loaded):
        ptr=self.update_tables(loaded)
        H,I=2560,640
        R=256
        with torch.cuda.device(self.device):
            source=to_device(y.contiguous().half(),self.device)
            local=torch.where(ids%2==self.device.index,ids//2,self.experts).to(self.device)
            w=to_device(weights,self.device)
            flat=local.reshape(-1)
            order=flat.argsort()
            tokens=torch.arange(y.shape[0],device=self.device).unsqueeze(1).expand_as(local).reshape(-1)[order].contiguous()
            sorted_weights=w.reshape(-1)[order].contiguous()
            counts=torch.bincount(flat,minlength=self.experts+1)
            cpu_counts=counts.cpu().tolist()
            if not hasattr(self,'prefill_buffers'):
                C=ext.exl3_moe_max_concurrency(self.device.index)
                self.prefill_buffers=[torch.empty((C,R,n),device=self.device,dtype=torch.float16) for n in (H,H,I,I)]
            out=torch.zeros((y.shape[0],H),device=self.device,dtype=torch.float32)
            active=sum(0<c<=R for c in cpu_counts[:self.experts])
            if active:
                ext.exl3_moe(source,out,counts,tokens,sorted_weights,*self.prefill_buffers,
                    0,3,3,3,*ptr,False,True,False,True,False,True,0.0,active,
                    None,None,1,R,16)
            # Heavy experts use the native reconstructed GEMM path; none are discarded.
            start=0
            for local_expert,count in enumerate(cpu_counts[:self.experts]):
                if count>R:
                    rows=tokens[start:start+count]
                    x=source.index_select(0,rows).contiguous()
                    modules=loaded[local_expert*2+self.device.index]
                    gate=modules['gate_proj'].forward(x,{},out_dtype=torch.float16)
                    up=modules['up_proj'].forward(x,{},out_dtype=torch.float16)
                    activation=torch.empty_like(up)
                    ext.silu_mul(gate,up,activation,0.0)
                    result=modules['down_proj'].forward(activation,{},out_dtype=torch.float32)
                    result*=sorted_weights[start:start+count].float().unsqueeze(-1)
                    out.index_add_(0,rows,result)
                start+=count
            return out


def apply(store,layer,shape,y,selected,weights,params):
    ids=selected.cpu()
    chosen=sorted(torch.unique(ids).tolist())
    if any(e<0 or e>=512 for e in chosen):
        raise RuntimeError('Invalid routed expert ID')
    keys={e:layer.key+'.experts.'+str(e) for e in chosen}
    futures={e:store.pool.submit(store.read,keys[e]) for e in chosen if not store.cached(keys[e])}
    loaded=[{},{}]
    # Keep strong references through BOTH launches; a small LRU may evict an expert
    # selected by the same batch while later experts are being loaded.
    for e in chosen:
        loaded[e%2][e]=store.get(keys[e],layer.config,futures.get(e),admit=y.shape[0]<=8,fill_unused=y.shape[0]>8)
    if not hasattr(store,'fused_decode'):
        store.fused_decode=[None,None]
    result=torch.zeros_like(y,dtype=torch.float32)
    for device in range(2):
        if loaded[device]:
            if store.fused_decode[device] is None:
                store.fused_decode[device]=FusedDecode(device,next(iter(loaded[device].values())))
            kernel=store.fused_decode[device]
            partial=(kernel.run(y,selected,weights,loaded[device]) if y.shape[0]<=8
                     else kernel.prefill(y,selected,weights,loaded[device]))
            result+=to_device(partial,y.device)
    store.stats['fused_moe_calls']+=1
    store.stats['masked_experts']=0
    return result.reshape(shape)
