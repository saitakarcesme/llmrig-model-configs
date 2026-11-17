"""Dependency-free normalization and atomic evidence writes."""
import json,os,pathlib,tempfile,unicodedata
def norm(s):return ' '.join(unicodedata.normalize('NFKC',s).casefold().split())
def atomic_json(path,obj):
 p=pathlib.Path(path);payload=json.dumps(obj,indent=2)+'\n'
 try:prev=p.stat().st_mode
 except OSError:prev=None
 fd,tmp=tempfile.mkstemp(prefix=p.name+'.',suffix='.tmp',dir=str(p.parent))
 try:
  try:stream=os.fdopen(fd,'w',encoding='utf-8')
  except BaseException:
   os.close(fd);raise
  try:
   stream.write(payload);stream.flush();os.fsync(stream.fileno())
  finally:stream.close()
  os.replace(tmp,p)
  if prev is not None:os.chmod(p,prev)
 except BaseException:
  try:os.unlink(tmp)
  except OSError:pass
  raise

def file_sha256(path):
 import hashlib
 with pathlib.Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
