import json,hashlib,time
from pathlib import Path
from huggingface_hub import snapshot_download
r=Path('/home/isa/Experiments/hyperqwen-fit')
manifest=json.loads((r/'receipts/model_manifest.json').read_text())
receipts=[]
for m in manifest:
 dest=r/'pristine'/m['repo'].split('/')[-1]
 print('Downloading pinned',m['repo'],m['revision'],flush=True)
 snapshot_download(m['repo'],revision=m['revision'],local_dir=dest,max_workers=4)
 checks=[]
 for f in m['files']:
  p=dest/f['path']
  if not p.is_file():raise RuntimeError('Missing '+str(p))
  h=hashlib.sha256()
  with p.open('rb') as stream:
   for b in iter(lambda:stream.read(8*1024*1024),b''):h.update(b)
  sha=h.hexdigest()
  if f['sha256'] and sha!=f['sha256']:raise RuntimeError('Checksum mismatch '+str(p))
  checks.append({'file':f['path'],'bytes':p.stat().st_size,'sha256':sha,'hub_lfs_verified':bool(f['sha256'])})
 receipts.append({'repo':m['repo'],'revision':m['revision'],'files':checks})
 (r/'receipts/download_verification.json').write_text(json.dumps(receipts,indent=2))
 print('Verified',m['repo'],flush=True)
print('All pinned model files downloaded and verified',flush=True)
