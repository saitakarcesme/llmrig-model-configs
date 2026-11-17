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
for i in range(180):
 try:
  urllib.request.urlopen(f'http://127.0.0.1:{port}/v1/models',timeout=3);break
 except Exception:time.sleep(5)
else:raise RuntimeError('Server did not become ready within 15 minutes')
request('warmup','Describe a robust SQLite migration strategy in detail.',64)
prompts={'design':'Design a Python service that accepts concurrent file uploads, deduplicates by SHA256 and writes a SQLite catalog. Explain concrete concurrency, crash recovery, API and testing decisions in detail. Do not stop early. Give implementation details and examples.','code':'Write a complete Python standard-library implementation of an LRU cache with TTL expiry, a monotonic clock, locking, eviction and thorough unittest coverage. Explain the implementation.','reason':'Explain how to diagnose inconsistent latency in a two-GPU local language-model server. Work through compute, memory, PCIe, batching, prompt processing and decoding, with measurable hypotheses and a detailed experiment matrix.'}
for repeat in range(3):
 for name,prompt in prompts.items():
  row,_=request(f'{name}-{repeat}',prompt,512);row['workload']='normal';rows.append(row)
  (ROOT/'receipts'/f'{label}-speed.json').write_text(json.dumps(rows,indent=2));print(label,row['name'],row['observed_decode_tps'],flush=True)
copy='\n'.join(f'Entry {i:03d}. Copper lantern {i*7:04d} crosses the quiet harbor at dawn.' for i in range(110))
for repeat in range(3):
 row,text=request(f'copy-{repeat}','Copy the following text verbatim. Do not add any commentary or formatting.\n\n'+copy,1024)
 row['workload']='copy';row['copy_prefix_correct']=bool(text.strip()) and copy.startswith(text.strip());rows.append(row)
 (ROOT/'receipts'/f'{label}-speed.json').write_text(json.dumps(rows,indent=2));print(label,row['name'],row['observed_decode_tps'],flush=True)
for name,prompt in prompts.items():
 row,_=request('xhigh-'+name,prompt,1024,True);row['workload']='normal_xhigh';rows.append(row)
 (ROOT/'receipts'/f'{label}-speed.json').write_text(json.dumps(rows,indent=2));print(label,row['name'],row['observed_decode_tps'],flush=True)
summary={w:{'samples':len(rr:=[r for r in rows if r['workload']==w]),'median_decode_tps':statistics.median([r['observed_decode_tps'] for r in rr if r['observed_decode_tps']]),'median_ttft_seconds':statistics.median([r['ttft_seconds'] for r in rr]),'total_completion_tokens':sum(r['usage'].get('completion_tokens',0) for r in rr)} for w in ['normal','copy','normal_xhigh']}
(ROOT/'receipts'/f'{label}-speed-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
