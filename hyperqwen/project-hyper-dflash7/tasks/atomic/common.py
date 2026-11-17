"""Dependency-free normalization and atomic evidence writes."""
import json,os,pathlib,tempfile,unicodedata
def norm(s):return ' '.join(unicodedata.normalize('NFKC',s).casefold().split())
def atomic_json(path,obj):
 # Unique per-call temp file in the destination directory, then atomic rename:
 # concurrent writers never share a fixed .tmp name, the destination is only
 # ever touched by the final replace, and this call's temp is removed on failure.
 p=pathlib.Path(path);data=json.dumps(obj,indent=2).encode('utf-8')+b'\n'
 tmp=None
 try:
  fd,name=tempfile.mkstemp(prefix=p.name+'.',suffix='.tmp',dir=str(p.parent))
  tmp=pathlib.Path(name)
  with os.fdopen(fd,'wb') as f:
   f.write(data);f.flush();os.fsync(f.fileno())
  tmp.replace(p)
 except BaseException:
  if tmp is not None:
   try:tmp.unlink()
   except OSError:pass
  raise

def file_sha256(path):
 import hashlib
 with pathlib.Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
