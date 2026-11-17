import json,subprocess,threading,time,requests,sys,io,zipfile
from pathlib import Path
ROOT=Path('/home/isa/Experiments/rig-extensions-20261030')
BASE=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:11450'
def snapshot():
    m={l.split(':')[0]:int(l.split()[1])//1024 for l in Path('/proc/meminfo').read_text().splitlines()}
    g=subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.used,memory.free','--format=csv,noheader,nounits'],text=True)
    return {'time':time.time(),'available_ram_mib':m['MemAvailable'],'swap_used_mib':m['SwapTotal']-m['SwapFree'],'gpus':[[int(v) for v in row.split(',')] for row in g.strip().splitlines()]}
def run(name,path,file,data):
    samples=[];done=threading.Event()
    def monitor():
        while not done.is_set():
            samples.append(snapshot());done.wait(2)
    t=threading.Thread(target=monitor);t.start();start=time.monotonic()
    try:
        with open(file,'rb') as f:r=requests.post(BASE+path,files={'file':(Path(file).name,f)},data=data,timeout=1000)
        try:body=r.json()
        except ValueError:body=r.text[:500]
        result={'name':name,'status':r.status_code,'elapsed_seconds':time.monotonic()-start,'body':body,'memory_samples':samples}
        if r.status_code==200 and path.endswith('/objects'):
            (ROOT/(name+'.zip')).write_bytes(r.content)
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                d=json.loads(z.read('objects.json'));result['body']={'entries':z.namelist(),'pages':[p['page'] for p in d['pages']],'text_spans':sum(len(line['spans']) for p in d['pages'] for b in p['text']['blocks'] for line in b.get('lines',[]))}
        (ROOT/(name+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
        print(json.dumps({k:v for k,v in result.items() if k!='memory_samples'},ensure_ascii=False),flush=True)
        if r.status_code!=200:sys.exit(1)
    finally:done.set();t.join()
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        h=requests.get('http://127.0.0.1:11446/health',timeout=5).json()
        if all(l['healthy'] for l in h['lanes']):break
        time.sleep(3)
    else:raise RuntimeError('Secondary lane not restored')
    print('RESTORED '+json.dumps(snapshot()),flush=True)

selection=sys.argv[2] if len(sys.argv)>2 else 'all'
fixture='/home/isa/Experiments/elpis-dual-262k-20261029/results/vision-fixture.png'
if selection in ('all','ocr'):
    run('ocr-live','/v1/ocr',fixture,{'task':'ocr','max_tokens':256})
    run('spotting-live','/v1/ocr',fixture,{'task':'spotting','max_tokens':512})
if selection in ('all','audio'):
    for name,model,lang in [('whisper-tr','whisper-large-v3','tr'),('whisper-fr','whisper-large-v3','fr'),('buzz-tr','BuzzASR/turkish','tr')]:
        run(name,'/v1/audio/transcriptions',ROOT/('test-'+lang+'.aiff'),{'model':model,'language':lang,'response_format':'verbose_json'})
