"""Dependency-free normalization and atomic evidence writes."""
import json,pathlib,unicodedata
def norm(s):return ' '.join(unicodedata.normalize('NFKC',s).casefold().split())
def atomic_json(path,obj):
 import tempfile,os
 p=pathlib.Path(path);data=json.dumps(obj,indent=2)+'\n';name=None
 try:
  with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=p.parent,prefix=p.name+'.',suffix='.tmp',delete=False) as f:
   name=f.name;f.write(data)
  os.replace(name,p)
 finally:
  if name is not None:
   try:os.unlink(name)
   except FileNotFoundError:pass

def file_sha256(path):
 import hashlib
 with pathlib.Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def readonly_sqlite(path):
 import sqlite3
 return sqlite3.connect(pathlib.Path(path).resolve().as_uri()+'?mode=ro',uri=True)
