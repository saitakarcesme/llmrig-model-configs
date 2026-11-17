"""Dependency-free normalization and atomic evidence writes."""
import json,os,pathlib,tempfile,unicodedata
def norm(s):return ' '.join(unicodedata.normalize('NFKC',s).casefold().split())
def atomic_json(path,obj):
    p=pathlib.Path(path)
    tmp_path=None
    try:
        fd,tmp_path_str=tempfile.mkstemp(dir=p.parent,suffix='.tmp')
        tmp_path=pathlib.Path(tmp_path_str)
        with os.fdopen(fd,'w') as f:
            json.dump(obj,f,indent=2)
            f.write('\n')
        tmp_path.replace(p)
    except:
        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass
        raise

def file_sha256(path):
 import hashlib
 with pathlib.Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
