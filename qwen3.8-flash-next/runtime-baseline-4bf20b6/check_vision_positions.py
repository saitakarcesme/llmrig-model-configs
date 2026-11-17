"""Independent QSA query/pool parity across an image span and decode suffix."""
import json
from pathlib import Path
from types import SimpleNamespace
import torch
from exllamav3 import Config,Model
from exllamav3.util.rope import RoPE
import vision_positions

torch.set_grad_enabled(False)
torch.manual_seed(71)
torch.set_num_threads(4)
config=Config.from_directory('/work/models/flashnext-3.05bpw')
model=Model.from_config(config)
indexer=model.find_module('model.language_model.layers.3.self_attn.indexer')
indexer.load(torch.device('cuda:1'))
rope=RoPE(torch.device('cuda:1'),config.rope_settings)
vision_positions.install(model,config)
device=torch.device('cuda:1')
length=2300
axes=torch.arange(length,device=device).expand(3,-1).clone()
start,end=1500,1760
axes[0,start:end]=start
axes[1,start:end]=start+torch.arange(260,device=device)//20
axes[2,start:end]=start+torch.arange(260,device=device)%20
offset=-240
axes[:,end:]+=offset
frequencies=axes[0,:,None].float()*rope.inv_freq
for dim,shift in ((1,1),(2,2)):
    selector=slice(shift,rope.mrope_section[dim]*3,3)
    frequencies[:,selector]=axes[dim,:,None].float()*rope.inv_freq[selector]
frequencies=frequencies.unsqueeze(0).contiguous()
pages=16;page_size=256;dk=indexer.head_dim;cr=indexer.compress_ratio
bt=torch.randperm(pages,device=device).unsqueeze(0).int()
layer=SimpleNamespace(raw_k=torch.zeros((pages,page_size,dk),device=device,dtype=torch.float16),
                      pooled=torch.zeros((pages,page_size//cr,dk),device=device,dtype=torch.float16))
history=[];cursor=0;checks=[]

def rotate(x,angles):
    # Transformers partial-rotary equation, evaluated independently of the adapter.
    cos=torch.cat((angles.cos(),angles.cos()),-1).half()
    sin=torch.cat((angles.sin(),angles.sin()),-1).half()
    r=cos.shape[-1]
    part=x[...,:r]
    rotated=torch.cat((-part[...,r//2:],part[...,:r//2]),-1)
    return torch.cat((part*cos+rotated*sin,x[...,r:]),-1)

def reference_angles(count):
    if count<=length:return frequencies[0,:count]
    suffix=torch.arange(length,count,device=device).float()+offset
    return torch.cat((frequencies[0],suffix[:,None]*rope.inv_freq),0)[:count]

for rows in [1000,777,523,1,1,4]:
    x=torch.randn((1,rows,config.hidden_size),device=device,dtype=torch.float16)*0.1
    qk=indexer.index_qk_proj.forward(x,{})
    q,raw=qk.split([indexer.n_heads*dk,dk],-1)
    q=indexer.q_layernorm.forward(q.reshape(1,rows,indexer.n_heads,dk).contiguous(),{})
    history.append(raw.clone())
    all_raw=torch.cat(history,1)
    angles=reference_angles(cursor+rows)
    expected_q=rotate(q,angles[cursor:cursor+rows].view(1,rows,1,-1))
    count=(cursor+rows)//cr
    pooled=all_raw[:,:count*cr].reshape(1,count,cr,dk).float().mean(2).half()
    pooled=indexer.k_layernorm.forward(pooled,{})
    expected_pool=rotate(pooled,angles[torch.arange(count,device=device)*cr].unsqueeze(0))
    params={'indexed_embeddings':[object()]}
    if cursor<length:params['inv_freq']=frequencies
    else:params['positions']=torch.tensor([cursor+offset],dtype=torch.int32)
    actual_q=indexer.update_planes(layer,x,rope,bt,torch.tensor([cursor],dtype=torch.int32),params)
    blocks=torch.arange(count,device=device)
    physical=bt.long()[0,blocks//(page_size//cr)]*(page_size//cr)+blocks%(page_size//cr)
    actual_pool=layer.pooled.reshape(-1,dk)[physical].unsqueeze(0)
    torch.testing.assert_close(actual_q,expected_q,atol=1e-3,rtol=1e-3)
    torch.testing.assert_close(actual_pool,expected_pool,atol=1e-3,rtol=1e-3)
    check={'position':cursor,'rows':rows,'query_max_error':float((actual_q-expected_q).abs().max()),
           'pooled_max_error':float((actual_pool-expected_pool).abs().max())}
    checks.append(check);print(check,flush=True)
    cursor+=rows
receipt={'status':'passed','checks':checks,'reference':'Independent Transformers partial rotary and pooled-key equations; permuted cache pages, image span and decode offset.'}
Path('/work/receipts/vision-position-parity.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2),flush=True)
