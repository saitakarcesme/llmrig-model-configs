import urllib.request,json,time,pathlib,statistics,sys,datetime
ROOT=pathlib.Path('/home/isa/Experiments/kolibri-fit')
URL='http://127.0.0.1:8012'
def api(path,body=None,timeout=2400):
    req=urllib.request.Request(URL+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as r:return json.load(r)
def chat(label,content,effort='none',max_tokens=256,tools=None):
    body={'model':'kolibri-1','messages':[{'role':'user','content':content}],
      'max_tokens':max_tokens,'temperature':1.0,'top_p':0.97,'top_k':128,'seed':1234,
      'reasoning_effort':effort,'chat_template_kwargs':{'reasoning_effort':effort,'enable_thinking':effort!='none'},
      'cache_prompt':False,'stream':True,'stream_options':{'include_usage':True}}
    if tools:body['tools']=tools
    started=time.monotonic();first=None;last=None;timings=None;usage=None;answer='';reasoning='';calls=[];finish=None
    req=urllib.request.Request(URL+'/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=5400) as r:
        for line in r:
            if not line.startswith(b'data: '):continue
            data=line[6:].strip()
            if data==b'[DONE]':break
            j=json.loads(data)
            if j.get('error'):raise RuntimeError(j['error'])
            timings=j.get('timings') or timings;usage=j.get('usage') or usage
            for c in j.get('choices',[]):
                d=c.get('delta',{})
                if d.get('content') or d.get('reasoning_content'):
                    first=first or time.monotonic();last=time.monotonic()
                answer+=d.get('content') or '';reasoning+=d.get('reasoning_content') or ''
                calls.extend(d.get('tool_calls') or []);finish=c.get('finish_reason') or finish
    result={'label':label,'reasoning_effort':effort,'usage':usage,'timings':timings,'ttft_seconds':first-started if first else None,
      'total_seconds':time.monotonic()-started,'finish_reason':finish,'answer':answer,'reasoning_characters':len(reasoning),'tool_deltas':calls}
    (ROOT/'receipts'/f'{label}.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['answer','tool_deltas']}),flush=True)
    return result
def run():
    tests=[('arithmetic','What is 17 times 23. Reply only the integer.',lambda s:s.strip()=='391'),
      ('json','Return only valid JSON with keys name and count. Set name to Kolibri and count to 7.',lambda s:json.loads(s)=={'name':'Kolibri','count':7}),
      ('german','Antworte nur mit dem Namen der Hauptstadt von Frankreich.',lambda s:'paris' in s.lower())]
    quality=[]
    for label,text,check in tests:
        r=chat('smoke-'+label,text)
        try:passed=check(r['answer'])
        except Exception:passed=False
        quality.append({'case':label,'passed':passed})
    (ROOT/'receipts/smoke-summary.json').write_text(json.dumps(quality,indent=2)+'\n');print('QUALITY',quality,flush=True)
    assert all(x['passed'] for x in quality),'Short smoke gate failed'
    prompt='Write a detailed tutorial on implementing an LRU cache in Python with examples and explanations. Continue until the output limit. Do not use tools.'
    for effort in ['none','high']:
        chat(f'warmup-{effort}',prompt,effort,64)
        for n in range(3):chat(f'speed-{effort}-{n+1}',prompt,effort,512)
    r=chat('tool-protocol','Use the lookup tool to get the deployment identifier for project demo. Do not guess the result.',tools=[{'type':'function','function':{'name':'lookup','description':'Look up a deployment identifier.','parameters':{'type':'object','properties':{'project':{'type':'string'}},'required':['project']}}}])
    assert r['tool_deltas'],'No structured tool call emitted'
if __name__=='__main__':run()
