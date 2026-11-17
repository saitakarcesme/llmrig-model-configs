"""Validate disk tensors, both CUDA devices, and eviction/reload against safetensors."""
import json
from pathlib import Path
import torch
from safetensors import safe_open
from exllamav3.modules.quant.exl3 import LinearEXL3
from exllamav3.util.device_copy import to_device
from native_disk import DiskExperts

root = Path('/work/models/flashnext-3.05bpw')
torch.set_grad_enabled(False)
torch.manual_seed(42)
store = DiskExperts(root, gpu_gib=(0.002,0.002),host_gib=0.003)
checks=[]
for e in [0, 1, 2, 0, 1, 3, 1, 2]:
    key=f'model.language_model.layers.0.mlp.experts.{e}'
    modules=store.get(key, None)
    for projection,module in modules.items():
        names=store.expert_keys[key][projection]
        values={}
        for name in names:
            with safe_open(str(root/store.index[name]),framework='pt',device='cpu') as f:
                value=f.get_tensor(name)
            suffix=name.rsplit('.',1)[1]
            device=0 if suffix not in ('mul1','mcg') else 'cpu'
            values[suffix]=value.to(device)
        with torch.cuda.device(0):
            reference=LinearEXL3(None,module.in_features,module.out_features,**values)
        actual_tensors=module.get_tensors('p')
        for suffix,tensor in reference.get_tensors('p').items():
            assert torch.equal(actual_tensors[suffix].cpu(),tensor.cpu()), (e,projection,suffix)
        for rows in [1,16,160]:
            x=torch.randn((rows,module.in_features),device='cuda:0',dtype=torch.float16)
            with torch.cuda.device(0):
                expected=reference.forward(x,{},out_dtype=torch.float32).clone()
            with torch.cuda.device(store.owner(key)):
                actual=module.forward(to_device(x,module.trellis.device),{},out_dtype=torch.float32).clone()
            actual=to_device(actual,expected.device)
            print('checking',e,projection,rows,dict(store.stats),float((actual-expected).abs().max()),flush=True)
            torch.testing.assert_close(actual,expected,rtol=1e-4,atol=1e-4)
            checks.append({'expert':e,'projection':projection,'rows':rows,
                           'max_absolute_error':float((actual-expected).abs().max())})
receipt={'status':'passed','checks':checks,'cache':store.metrics()}
Path('/work/receipts/disk-expert-parity.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'status':'passed','checks':len(checks),'max_error':max(c['max_absolute_error'] for c in checks),'cache':store.metrics()},indent=2),flush=True)
