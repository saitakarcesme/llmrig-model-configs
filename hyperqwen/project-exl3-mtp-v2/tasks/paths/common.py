"""Dependency-free normalization and atomic evidence writes."""
import json,pathlib,unicodedata
def norm(s):return ' '.join(unicodedata.normalize('NFKC',s).casefold().split())
def atomic_json(path,obj):
 p=pathlib.Path(path);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(obj,indent=2)+'\n');t.replace(p)

def file_sha256(path):
 import hashlib
 with pathlib.Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def readonly_sqlite(path):
 """Open a SQLite database strictly read-only, safe for names with spaces, Unicode, #, ?, & or %."""
 import sqlite3
 from urllib.parse import quote
 return sqlite3.connect('file:'+quote(str(pathlib.Path(path).resolve()),safe='/')+'?mode=ro',uri=True)
