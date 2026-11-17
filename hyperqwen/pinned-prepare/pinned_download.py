from pathlib import Path
import shutil,fnmatch,json
def snapshot_download(repo_id,local_dir=None,allow_patterns=None,**kwargs):
    manifest=json.loads(Path('/pinned/manifest.json').read_text())
    match=next(m for m in manifest if m['repo']==repo_id)
    src=Path('/pinned')/repo_id.split('/')[-1]
    assert src.is_dir(), 'Pinned verified snapshot missing'
    if local_dir:
        dst=Path(local_dir);dst.mkdir(parents=True,exist_ok=True)
        for f in match['files']:
            if allow_patterns and not any(fnmatch.fnmatch(f['path'],p) for p in allow_patterns):continue
            target=dst/f['path'];target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(src/f['path'],target)
        return str(dst)
    return str(src)
