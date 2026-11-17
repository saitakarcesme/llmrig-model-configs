import hashlib,json,struct
from pathlib import Path
r=Path('/home/isa/Experiments/hyperqwen-fit');rows=[]
for d in sorted((r/'models').iterdir()):
 if not d.is_dir():continue
 files=[]
 for p in sorted(d.iterdir()):
  if not p.is_file() or p.suffix not in ['.json','.safetensors','.pt','.jinja']:continue
  h=hashlib.sha256()
  with p.open('rb') as f:
   for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
  if p.suffix=='.safetensors':
   with p.open('rb') as f:
    n=struct.unpack('<Q',f.read(8))[0];hdr=json.loads(f.read(n))
   end=max(v['data_offsets'][1] for k,v in hdr.items() if k!='__metadata__')
   assert 8+n+end==p.stat().st_size, str(p)
  files.append({'file':p.name,'bytes':p.stat().st_size,'sha256':h.hexdigest()})
 rows.append({'model':d.name,'files':files})
(r/'receipts/prepared_models.json').write_text(json.dumps(rows,indent=2))
print('Prepared snapshots hashed and safetensors byte ranges checked',flush=True)
