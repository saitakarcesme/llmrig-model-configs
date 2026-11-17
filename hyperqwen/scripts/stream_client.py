"""Finite matched stream benchmarks. Numeric receipts separate from model outputs."""
import urllib.request,json,time,pathlib,sys,statistics,hashlib,re,subprocess
ROOT=pathlib.Path('/home/isa/Experiments/hyperqwen-fit')
label,port,model=sys.argv[1:4]
url=f'http://127.0.0.1:{port}/v1/chat/completions'
outputs=ROOT/'private'/label;outputs.mkdir(parents=True,exist_ok=True)
rows=[]
def request(name,prompt,n=512,thinking=False,seed=123):
 body={'model':model,'messages':[{'role':'user','content':prompt}],'temperature':0,'seed':seed,'max_tokens':n,'stream':True,'stream_options':{'include_usage':True},'chat_template_kwargs':{'enable_thinking':thinking},'reasoning_effort':'xhigh' if thinking else 'none'}
 t=time.monotonic();first=None;last=None;content='';reasoning='';usage={};timings={};extra={};chunks=0;finish=None
 with urllib.request.urlopen(urllib.request.Request(url,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'}),timeout=900) as stream:
  for line in stream:
   if not line.startswith(b'data: '):continue
   data=line[6:].strip()
   if data==b'[DONE]':continue
   j=json.loads(data)
   if j.get('error'):raise RuntimeError(str(j['error']))
   if j.get('usage'):usage=j['usage']
   if j.get('timings'):timings=j['timings']
   for key in j:
    if 'metric' in key:extra[key]=j[key]
   for c in j.get('choices',[]):
    d=c.get('delta',{});text=d.get('content') or '';thought=d.get('reasoning_content') or d.get('reasoning') or ''
    if text or thought:
     now=time.monotonic();first=first or now;last=now;chunks+=1
     content+=text;reasoning+=thought
    finish=c.get('finish_reason') or finish
 wall=time.monotonic()-t;tokens=usage.get('completion_tokens')
 row={'name':name,'thinking':thinking,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'usage':usage,'ttft_seconds':first-t if first else None,'wall_seconds':wall,'decode_interval_seconds':last-first if last and first else None,'observed_decode_tps':(tokens-1)/(last-first) if tokens and last and first and last>first else None,'completion_tokens_per_wall_second':tokens/wall if tokens else None,'chunks':chunks,'finish_reason':finish,'content_sha256':hashlib.sha256(content.encode()).hexdigest(),'native_timings':timings,'extra_metrics':extra}
 (outputs/(name+'.json')).write_text(json.dumps({'content':content,'reasoning':reasoning,'request':body},indent=2))
 return row,content
