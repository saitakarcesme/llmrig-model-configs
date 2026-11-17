"""Compare the complete offloaded MoE layer with a fully resident native layer."""
import json
import os
from pathlib import Path
import time
import torch
from exllamav3 import Config,Model
import native_disk

torch.set_grad_enabled(False)
torch.set_num_threads(8)
torch.manual_seed(19)
root='/work/models/flashnext-3.05bpw'
config=Config.from_directory(root)
config.infer_params.no_reconstruct=False
model=Model.from_config(config)
layer=model.find_module('model.language_model.layers.0.mlp')
if os.environ.get('FLASHNEXT_PARITY_ROUTED_ONLY')=='1':layer.shared_experts=None
layer.load(torch.device('cuda:0'))
print('Resident reference layer loaded', {k:getattr(layer,k,None) for k in ('fused_rows','mtile_ok','support_fused','act_limit','f_threshold','interm_dtype','is_quantized')},flush=True)
inputs=[]
expected=[]
reference_routes=[]
native_routing=layer.routing_fn
def record_routing(*args):
    ids,weights=native_routing(*args)
    reference_routes.append((ids.clone(),weights.clone()))
    return ids,weights
layer.routing_fn=record_routing
for rows in map(int,os.environ.get('FLASHNEXT_PARITY_ROWS','1,4,16,128').split(',')):
    x=(torch.randn((1,rows,2560),device='cuda:0',dtype=torch.float16)*float(os.environ.get('FLASHNEXT_PARITY_SCALE','0.1'))).contiguous()
    if os.environ.get('FLASHNEXT_PARITY_REPEAT_INPUT')=='1':
        x=x[:,:1].expand(1,rows,2560).contiguous()
    inputs.append(x)
    expected.append(layer.forward(x,{}).clone())

store=native_disk.install(root,gpu_gib=(0.02,0.02),host_gib=0.02)
config2=Config.from_directory(root)
config2.infer_params.no_reconstruct=False
model2=Model.from_config(config2)
offload=model2.find_module('model.language_model.layers.0.mlp')
if os.environ.get('FLASHNEXT_PARITY_ROUTED_ONLY')=='1':offload.shared_experts=None
offload.load(torch.device('cuda:0'))
checks=[]
offload_routing=offload.routing_fn
route_index=0
def compare_routing(*args):
    global route_index
    ids,weights=offload_routing(*args)
    ri,rw=reference_routes[route_index%len(reference_routes)]
    torch.testing.assert_close(ids,ri,atol=0,rtol=0)
    torch.testing.assert_close(weights,rw,atol=0,rtol=0)
    route_index+=1
    return ids,weights
offload.routing_fn=compare_routing
for repeat in range(2):
    for x,reference in zip(inputs,expected):
        start=time.perf_counter()
        before_gpu=[set(cache) for cache in store.gpu]
        before_host=set(store.host)
        actual=offload.forward(x,{}).clone()
        if x.shape[1]>8:
            assert all(keys<=set(store.gpu[d]) for d,keys in enumerate(before_gpu)), 'Prefill evicted a resident expert'
            assert all(k in store.host or k in store.gpu[store.owner(k)] for k in before_host), 'Prefill consumed a host entry'
        assert all(n<=cap for n,cap in zip(store.gpu_bytes,store.gpu_cap))
        assert store.host_bytes<=store.host_cap
        torch.cuda.synchronize()
        error=float((reference-actual).abs().max())
        print('MoE parity',repeat,x.shape[1],error,'reference RMS',float(reference.square().mean().sqrt()),flush=True)
        # Distinct native fused/shared/prefill FP16 kernels do not promise bitwise equality.
        # Bound aggregate numerical drift while requiring identical routes and weights above.
        nrmse=float((reference-actual).square().mean().sqrt()/reference.square().mean().sqrt().clamp_min(1e-12))
        cosine=float(torch.nn.functional.cosine_similarity(reference.flatten(),actual.flatten(),dim=0))
        assert nrmse<0.01 and cosine>0.9999,(nrmse,cosine)
        assert error<=float(reference.abs().max())*0.02+1e-4,error
        checks.append({'repeat':repeat,'rows':x.shape[1],'max_absolute_error':error,'normalized_rms_error':nrmse,'cosine_similarity':cosine,
                       'seconds':time.perf_counter()-start})
if os.environ.get('FLASHNEXT_PARITY_CACHEFILL')=='1':
    assert store.stats['prefill_cache_admissions']>0
receipt={'reference':'Native resident fused layer; exact routes and weights; FP16 kernel numerical tolerance 1% normalized RMS and cosine >0.9999','input_scale':float(os.environ.get('FLASHNEXT_PARITY_SCALE','0.1')),'status':'passed','checks':checks,'offload':store.metrics()}
Path('/work/receipts/'+os.environ.get('FLASHNEXT_PARITY_RECEIPT','moe-layer-parity.json')).write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2),flush=True)
