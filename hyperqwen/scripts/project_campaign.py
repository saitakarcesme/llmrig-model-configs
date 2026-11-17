"""Finite Pi project evaluation, with masked graders and per-request server timing."""
import pathlib,json,subprocess,hashlib,shutil,threading,time,datetime,urllib.request,http.server,traceback,statistics,os,sys
ROOT=pathlib.Path('/home/isa/Experiments/hyperqwen-fit');LABEL,PORT,MODEL=sys.argv[1:4];STUDY=ROOT/('project-'+LABEL)
NODE='/home/isa/.local/share/mise/installs/node/26.8.2/bin/node'
CLI='/home/isa/.local/share/mise/installs/node/26.8.2/lib/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js'
SOURCE=pathlib.Path('/home/isa/Projects/PocketLore');REV='e6287d0a1eccb716c4424803c85bcc5fc7356eb5'
FILES=['common.py','compact_search.py','search.py','enrich.py','catalog.py','osm_read.py']
TASKS={
 'paths':{'editable':['common.py','compact_search.py','search.py','enrich.py','catalog.py'],'prompt':'''Fix read-only SQLite access for database filenames containing spaces, Unicode, #, ?, & or literal %. Add common.readonly_sqlite(path) as the shared helper and use it in every read-only database connection in compact_search.py, search.py, enrich.py and catalog.py. Preserve existing public methods and their result semantics. Existing files must remain read-only; missing files must raise sqlite3.OperationalError without creating anything. Use Python's standard library. Add your own regression tests and run them.'''},
 'inflate':{'editable':['compact_search.py'],'prompt':'''Harden the production compressed-block decoder compact_search.inflate without changing valid results. Enforce a MAX_COMPRESSED constant of 1 MiB in addition to the existing 32 MiB inflated bound. Reject corrupt or truncated zlib, trailing garbage, concatenated streams, wrong SHA256, invalid JSON and either exceeded bound with ValueError. Check the compressed bound before decoding, and keep inflation bounded throughout. Unicode JSON must still round-trip. Do not relax existing validation. Add your own regression tests and run them.'''},
 'atomic':{'editable':['common.py'],'prompt':'''Repair common.atomic_json for concurrent writers. Its fixed .tmp name makes simultaneous evidence writes interfere. Use a unique temporary file in the destination directory and atomic replacement. Each successful write must publish complete valid JSON; failures before replacement must preserve any previous destination bytes. Remove only that call's temporary file after both success and failure. Leave unrelated files alone. Preserve the public API, JSON content and common.norm/file_sha256. Standard library only. Add tests for concurrency and failure cleanup and run them.'''},
 'filters':{'editable':['catalog.py'],'prompt':'''Extend the real Catalog.nearby facade with optional name and city keyword filters for Overture search, forwarding both to compact_search.search. Keep all existing positional arguments and default output contracts intact. Exact-name normalization and exact city matching already live in compact_search, so reuse them. If a nonempty diet is selected, any non-None name, city or category filter must raise ValueError rather than invent a cross-source join; this includes empty strings explicitly provided as filters. Diet-only calls must remain supported. Keep source-family attribution, enrichment candidates and unknown live status intact. Add your own regression tests and run them.'''},
}

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def state(stage,**fields):
 p=ROOT/'LOOP_STATE.json';s=json.loads(p.read_text());s.update(stage=stage,updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),**fields)
 t=p.with_suffix('.project.tmp');t.write_text(json.dumps(s,indent=2)+'\n');t.replace(p)
 with (ROOT/'FINDINGS.md').open('a') as f:f.write('\nProject evaluation: '+json.dumps({'stage':stage,**fields})+'\n')
 print(stage,json.dumps(fields),flush=True)

def grade(work,task,label):
 p=subprocess.run(['python3',str(STUDY/'graders/project_grader.py'),str(work),task],capture_output=True,text=True,timeout=120)
 (STUDY/'receipts'/f'{task}-{label}-grade.log').write_text(p.stdout+p.stderr)
 rows=[l[11:] for l in p.stdout.splitlines() if l.startswith('GRADE_JSON ')]
 assert rows,'Grader did not produce a receipt'
 result=json.loads(rows[-1]);result['return_code']=p.returncode
 return result

STUDY.mkdir(exist_ok=True);(STUDY/'receipts').mkdir(exist_ok=True);(STUDY/'graders').mkdir(exist_ok=True)
shutil.copy2(ROOT/'scripts/project_grader.py',STUDY/'graders/project_grader.py')
base=STUDY/'base';base.mkdir(exist_ok=True)
for name in FILES:
 p=base/name;assert not p.exists(),'Do not overwrite an existing frozen campaign'
 p.write_bytes(subprocess.check_output(['git','-C',str(SOURCE),'show',f'{REV}:tools/scale/places/{name}']))
(base/'LICENSE').write_bytes(subprocess.check_output(['git','-C',str(SOURCE),'show',f'{REV}:LICENSE']))
manifest={'project':'PocketLore','revision':REV,'files':{n:digest(base/n) for n in FILES},'grader_sha256':digest(STUDY/'graders/project_grader.py'),'tasks':TASKS,'context_profile':{'context':65536,'cache':'bf16 for HyperQwen; Q4 for EXL3','quant':'recorded separately','split':'recorded separately'},'effort':'high','scope':'Four selected project maintenance tasks, not local.ai Intelligence Index or official benchmark replication.'}
(STUDY/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
profile=STUDY/'pi-home';(profile/'.pi/agent').mkdir(parents=True,exist_ok=True)
provider={'baseUrl':'http://127.0.0.1:8013/v1','api':'openai-completions','apiKey':'none','models':[{'id':MODEL,'name':'Qwen matched project benchmark','reasoning':True,'input':['text'],'cost':{'input':0,'output':0,'cacheRead':0,'cacheWrite':0},'contextWindow':manifest['context_profile']['context'],'maxTokens':32768,'compat':{'supportsDeveloperRole':False,'supportsReasoningEffort':True,'thinkingLevelMap':{'off':'none','minimal':'low','low':'low','medium':'medium','high':'xhigh','xhigh':None,'max':None}}}]}
(profile/'.pi/agent/models.json').write_text(json.dumps({'providers':{'kolibri-project':provider}},indent=2))
(profile/'.pi/agent/settings.json').write_text(json.dumps({'defaultProvider':'kolibri-project','defaultModel':MODEL,'defaultThinkingLevel':'high'}))

active={'task':None};lock=threading.Lock();requests=[]
class Proxy(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  try:
   with urllib.request.urlopen(f'http://127.0.0.1:{PORT}'+self.path,timeout=30) as r:
    data=r.read();self.send_response(r.status);self.send_header('Content-Type',r.headers.get('Content-Type','application/json'));self.end_headers();self.wfile.write(data)
  except Exception:self.send_error(502)
 def do_POST(self):
  body=self.rfile.read(int(self.headers['Content-Length']));payload=json.loads(body)
  payload.setdefault('temperature',0.6);payload.setdefault('top_p',0.95);payload.setdefault('top_k',20)
  if payload.get('stream'):payload['stream_options']={'include_usage':True}
  context_count=None
  if str(PORT)=='18020':
   token_body={k:payload[k] for k in ['model','messages','tools','chat_template_kwargs'] if k in payload}
   token_body.setdefault('chat_template_kwargs',{})['reasoning_effort']=payload.get('reasoning_effort','xhigh')
   tokreq=urllib.request.Request(f'http://127.0.0.1:{PORT}/tokenize',data=json.dumps(token_body).encode(),headers={'Content-Type':'application/json'})
   with urllib.request.urlopen(tokreq,timeout=60) as tr:context_count=json.load(tr)['count']
   remaining=65536-context_count-8
   if remaining<=0:self.send_error(400,'Context limit reached');return
   for cap_field in ['max_tokens','max_completion_tokens']:
    if payload.get(cap_field):payload[cap_field]=min(payload[cap_field],remaining)
  record={'task':active['task'],'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'request_bytes':len(body),'tokenized_input_count':context_count,'temperature':payload.get('temperature'),'top_p':payload.get('top_p'),'top_k':payload.get('top_k'),'reasoning_effort':payload.get('reasoning_effort'),'max_tokens':payload.get('max_tokens') or payload.get('max_completion_tokens'),'stream':payload.get('stream'),'request_sha256':hashlib.sha256(body).hexdigest()}
  t=time.monotonic();first=None;last=None
  try:
   req=urllib.request.Request(f'http://127.0.0.1:{PORT}'+self.path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
   with urllib.request.urlopen(req,timeout=900) as r:
    self.send_response(r.status);self.send_header('Content-Type',r.headers.get('Content-Type','text/event-stream'));self.send_header('Connection','close');self.end_headers()
    for line in r:
     self.wfile.write(line);self.wfile.flush()
     if line.startswith(b'data: ') and line[6:].strip()!=b'[DONE]':
      j=json.loads(line[6:]);
      if j.get('timings'):record['timings']=j['timings']
      if j.get('usage'):record['usage']=j['usage']
      if j.get('metrics'):record['native_metrics']=j['metrics']
      for c in j.get('choices',[]):
       delta=c.get('delta',{})
       if any(delta.get(k) for k in ['content','reasoning_content','reasoning','tool_calls']):first=first or time.monotonic();last=time.monotonic()
      if j.get('error'):record['api_error']=str(j['error'])[:200]
  except Exception as exc:record['transport_error']=type(exc).__name__
  finally:
   self.close_connection=True;record['total_seconds']=time.monotonic()-t;record['ttft_seconds']=first-t if first else None;record['decode_seconds']=last-first if first and last else None;record['observed_decode_tps']=(record.get('usage',{}).get('completion_tokens',0)-1)/(last-first) if first and last and last>first else None
   with lock:
    requests.append(record)
    with (STUDY/'receipts/requests.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')

server=http.server.ThreadingHTTPServer(('127.0.0.1',8013),Proxy);threading.Thread(target=server.serve_forever,daemon=True).start()
results=[]
try:
 for task,spec in TASKS.items():
  work=STUDY/'tasks'/task;shutil.copytree(base,work)
  before=grade(work,task,'baseline');assert not before['passed'],'Task unexpectedly passes before changes'
  (work/'TASK.md').write_text(spec['prompt']+'\nEditable existing files: '+', '.join(spec['editable'])+'\n')
  state('project_task_running',project_task=task,completed_project_tasks=len(results))
  active['task']=task
  prompt='Complete TASK.md in the current working directory. Read the actual source, implement the requested change, add and run standard-library unittest regressions. Edit only the listed existing source files and new test files in this directory. Do not access parent directories, other projects, evaluation code or any network service. Do not install packages, use git, call another model or modify services. End with a concise summary of changes and test results.'
  command=['bwrap','--ro-bind','/','/','--dev','/dev','--proc','/proc','--tmpfs','/tmp','--tmpfs','/home/isa','--dir','/home/isa/.local/share/mise/installs/node','--ro-bind','/home/isa/.local/share/mise/installs/node/26.8.2','/home/isa/.local/share/mise/installs/node/26.8.2','--dir','/home/isa/Experiments','--dir',str(ROOT),'--dir',str(STUDY),'--bind',str(work),str(work),'--bind',str(profile),str(profile),'--setenv','HOME',str(profile),'--setenv','PI_CODING_AGENT_DIR',str(profile/'.pi/agent'),'--setenv','PI_OFFLINE','1','--setenv','PI_TELEMETRY','0','--chdir',str(work),NODE,CLI,'--offline','--provider','kolibri-project','--model',MODEL,'--thinking','high','--print','--mode','json','--no-session','--no-context-files','--no-extensions','--no-skills','--no-prompt-templates','--tools','read,write,edit,bash',prompt]
  t=time.monotonic();timeout=False
  with (STUDY/'receipts'/f'{task}-pi-output.jsonl').open('w') as out,(STUDY/'receipts'/f'{task}-pi-errors.log').open('w') as err:
   p=subprocess.Popen(command,stdout=out,stderr=err,start_new_session=True)
   try:rc=p.wait(timeout=900)
   except subprocess.TimeoutExpired:
    import signal
    os.killpg(p.pid,signal.SIGTERM);timeout=True
    try:rc=p.wait(timeout=15)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);rc=p.wait()
  wall=time.monotonic()-t
  after=grade(work,task,'final')
  changed=[n for n in FILES if digest(work/n)!=manifest['files'][n]]
  scope_ok=set(changed)<=set(spec['editable']) and (work/'LICENSE').read_bytes()==(base/'LICENSE').read_bytes()
  newtests=[x.name for x in work.iterdir() if x.is_file() and (x.name.startswith('test') or x.name.endswith('_test.py'))]
  events=[]
  for line in (STUDY/'receipts'/f'{task}-pi-output.jsonl').read_text().splitlines():
   try:events.append(json.loads(line))
   except Exception:pass
  calls=[e.get('toolName') for e in events if e.get('type')=='tool_execution_start']
  rows=[r for r in requests if r['task']==task];timings=[r['timings'] for r in rows if r.get('timings')]
  decoded=sum(max(0,r.get('predicted_n',0)-1) for r in timings);decode_s=sum(r.get('predicted_ms',0) for r in timings)/1000
  result={'task':task,'baseline':before,'acceptance':after,'scope_ok':scope_ok,'passed':after['passed'] and scope_ok and rc==0 and not timeout,'pi_return_code':rc,'timeout':timeout,'wall_seconds':wall,'changed_existing_files':changed,'new_test_files':newtests,'tool_calls':calls,'api_requests':len(rows),'timing_receipts':len(timings),'weighted_decode_tps':sum(max(0,r.get('usage',{}).get('completion_tokens',0)-1) for r in rows if r.get('decode_seconds'))/sum(r['decode_seconds'] for r in rows if r.get('decode_seconds')) if any(r.get('decode_seconds') for r in rows) else None,'per_request_decode_tps':[r.get('observed_decode_tps') for r in rows],'decode_seconds':sum(r.get('decode_seconds') or 0 for r in rows),'prompt_seconds':sum(r.get('prompt_ms',0) for r in timings)/1000,'generated_tokens':sum(r.get('usage',{}).get('completion_tokens',0) for r in rows),'prompt_tokens_evaluated':sum(r.get('prompt_n',0) for r in timings),'cached_prompt_tokens':sum(r.get('cache_n',0) for r in timings),'tokens_per_wall_second':sum(r.get('usage',{}).get('completion_tokens',0) for r in rows)/wall,'reasoning_effort':'high','scope':'One first attempt per task; test criteria fixed before generation. Not local.ai benchmark scores.'}
  results.append(result);(STUDY/'receipts'/f'{task}-summary.json').write_text(json.dumps(result,indent=2)+'\n')
  state('project_task_completed',project_task=task,project_result=result,completed_project_tasks=len(results))
 summary={'project':manifest['project'],'revision':REV,'model':LABEL,'context_profile':manifest['context_profile'],'effort':'high','tasks':results,'tasks_passed':sum(r['passed'] for r in results),'tasks_total':len(results),'median_task_seconds':statistics.median(r['wall_seconds'] for r in results),'total_task_seconds':sum(r['wall_seconds'] for r in results),'scope':'Selected real-source maintenance tasks with frozen functional tests. No official local.ai Intelligence Index, ranking or broad model-quality claim.'}
 (STUDY/'receipts/summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 state('project_evaluation_complete',project_tasks_passed=summary['tasks_passed'],project_tasks_total=len(results),project_study='project-study/receipts/summary.json')
except Exception as exc:
 (STUDY/'receipts/campaign-error.log').write_text(traceback.format_exc());state('project_evaluation_error',project_error=str(exc));raise
finally:server.shutdown();server.server_close()
