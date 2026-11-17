import requests,json,time,subprocess,threading,io,zipfile
from pathlib import Path
ROOT=Path('/home/isa/Experiments/rig-extensions-20261030')
BASE='http://127.0.0.1:11445'
def snap():
    mem={l.split(':')[0]:int(l.split()[1])//1024 for l in Path('/proc/meminfo').read_text().splitlines()}
    gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.used,memory.free','--format=csv,noheader,nounits'],text=True)
    names=subprocess.check_output(['docker','ps','--format','{{.Names}}'],text=True).splitlines()
    return {'time':time.time(),'available_ram_mib':mem['MemAvailable'],'swap_used_mib':mem['SwapTotal']-mem['SwapFree'],'gpus':[[int(v) for v in x.split(',')] for x in gpu.strip().splitlines()],'media_worker_active':'llmrig-media-task' in names,'secondary_running':'llmrig-elpis-lane1' in names}
def save(name,result):
    (ROOT/(name+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(name+' '+json.dumps({k:v for k,v in result.items() if k!='samples'},ensure_ascii=False),flush=True)
def call(name,path,**kwargs):
    samples=[];stop=threading.Event()
    def monitor():
        while not stop.is_set():samples.append(snap());stop.wait(.8)
    thread=threading.Thread(target=monitor);thread.start();start=time.monotonic()
    try:
        r=requests.post(BASE+path,timeout=900,**kwargs)
        try:body=r.json()
        except ValueError:
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                d=json.loads(z.read('objects.json'));body={'files':z.namelist(),'pages':[p['page'] for p in d['pages']]}
        result={'status':r.status_code,'elapsed_seconds':time.monotonic()-start,'body':body,'samples':samples}
        save(name,result);assert r.status_code==200
    finally:stop.set();thread.join()
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        c=subprocess.run(['docker','inspect','--format','{{.State.Health.Status}}','llmrig-elpis-lane1'],capture_output=True,text=True)
        if c.returncode==0 and c.stdout.strip()=='healthy':break
        time.sleep(2)
    else:raise AssertionError('Secondary recovery failed')
    save(name+'-after',snap())

save('public-before',{'memory':snap(),'props':requests.get(BASE+'/props').json(),'models':requests.get(BASE+'/v1/models').json(),'extensions':requests.get(BASE+'/extensions/health').json()})
for name,path,file,data in [
 ('public-ocr','/v1/ocr','/home/isa/Experiments/elpis-dual-262k-20261029/results/vision-fixture.png',{'task':'ocr','max_tokens':128}),
 ('public-whisper','/v1/audio/transcriptions',str(ROOT/'test-fr.aiff'),{'model':'whisper-large-v3','language':'fr','response_format':'verbose_json'}),
 ('public-buzz','/v1/audio/transcriptions',str(ROOT/'test-tr.aiff'),{'model':'BuzzASR/turkish','language':'tr','response_format':'verbose_json'}),
 ('public-native','/v1/pdf/objects','/home/isa/Projects/llmrig/pdf-api/attention.pdf',{'pages':'3-4'})]:
    with open(file,'rb') as f:call(name,path,files={'file':(Path(file).name,f)},data=data)
for penalty in (0,1.5):
    body={'model':'qwen3.8-27b-sampled','messages':[{'role':'user','content':'What is 2+2? Reply with just the answer.'}],'max_tokens':128,'presence_penalty':penalty,'reasoning_effort':'none','seed':42}
    if penalty:body.update(temperature=1.0,top_p=.95,top_k=20)
    call('sampled-'+str(penalty),'/v1/chat/completions',json=body)
bad=requests.post(BASE+'/v1/chat/completions',json={'model':'qwen3.8-27b-sampled','messages':[],'top_k':21},timeout=20)
save('sampled-bad-topk',{'status':bad.status_code,'body':bad.json()});assert bad.status_code==400
bad=requests.post(BASE+'/v1/chat/completions',json={'model':'qwen3.8-27b','messages':[{'role':'user','content':'Hi'}],'presence_penalty':1.5,'max_tokens':1},timeout=30)
save('main-presence-rejection',{'status':bad.status_code,'body':bad.json()});assert bad.status_code==400
save('public-final',{'memory':snap(),'props':requests.get(BASE+'/props').json(),'health':requests.get(BASE+'/health').json()})
