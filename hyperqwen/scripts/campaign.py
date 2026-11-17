"""Finite sequential benchmark; restores the prior model after completion or failure."""
import subprocess,time,json,pathlib,urllib.request,datetime,traceback,os
R=pathlib.Path('/home/isa/Experiments/hyperqwen-fit')
started=time.time();results=json.loads((R/'LOOP_STATE.json').read_text()).get('completed_arms',[]);current=None

def state(stage,**more):
 d={'stage':stage,'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'started_epoch':started,'completed_arms':results,**more}
 (R/'LOOP_STATE.json').write_text(json.dumps(d,indent=2))
 with (R/'FINDINGS.md').open('a') as f:f.write('\n'+json.dumps(d)+'\n')
 print(stage,json.dumps(more),flush=True)

def unit_status(name):
 return dict(line.split('=',1) for line in subprocess.check_output(['systemctl','--user','show',name,'-p','ActiveState','-p','ExecMainStatus']).decode().splitlines())
def wait_unit(name,timeout):
 t=time.time()
 while time.time()-t<timeout:
  s=unit_status(name)
  if s.get('ActiveState') not in ['active','activating','deactivating']:
   if s.get('ExecMainStatus')!='0':raise RuntimeError(name+' failed '+str(s))
   return
  time.sleep(5)
 raise TimeoutError(name)
def run(script,*args,timeout=3600):
 subprocess.run(['python3',str(R/'scripts'/script),*map(str,args)],check=True,timeout=timeout)
def metrics(label):
 try:(R/'receipts'/f'{label}-metrics.txt').write_bytes(urllib.request.urlopen('http://127.0.0.1:18020/metrics',timeout=10).read())
 except Exception as e:print('Metrics unavailable',type(e).__name__,flush=True)
def start(spec,label,tokens=7,tp=1):
 global current
 current='hyperqwen-'+label+'-'+str(int(time.time()))
 env=os.environ.copy()
 if tp==2:env.update(HYPER_GPUS='all',EXTRA_ARGS='--tensor-parallel-size 2 --disable-custom-all-reduce')
 subprocess.run(['systemd-run','--user','--unit='+current,'--property=RuntimeMaxSec=7200',*(['--setenv=HYPER_GPUS=all','--setenv=EXTRA_ARGS=--tensor-parallel-size 2 --disable-custom-all-reduce'] if tp==2 else []),str(R/'scripts/start_hyper.sh'),spec,current,str(tokens)],check=True)
 t=time.time()
 while time.time()-t<1800:
  s=unit_status(current+'.service')
  if s.get('ActiveState')=='failed':raise RuntimeError('Server startup failed '+current)
  try:
   urllib.request.urlopen('http://127.0.0.1:18020/health',timeout=2);break
  except Exception:time.sleep(5)
 else:raise TimeoutError('Server startup '+current)
 subprocess.run(['docker','logs',current],stdout=(R/'receipts'/f'{label}-startup.log').open('w'),stderr=subprocess.STDOUT,check=True)
 state('arm_ready',arm=label,spec=spec,draft_tokens=tokens,gpus=tp)
def stop():
 global current
 if current:
  subprocess.run(['docker','stop','-t','30',current],check=False,timeout=60)
  current=None
try:
 state('baseline_project_and_quality_running')
 wait_unit('hyperqwen-project-baseline-v2.service',4200)
 wait_unit('hyperqwen-quality-baseline.service',5400)
 wait_unit('hyperqwen-hash-prepared.service',600)
 assert json.loads((R/'receipts/exl3-mtp-quality.json').read_text())['complete']
 subprocess.run(['systemctl','--user','stop','hyperqwen-baseline.service'],check=False)
 for spec,label,tokens,tp in [('off','hyper-off',7,1),('mtp','hyper-mtp',7,1),('dflash2','hyper-dflash7',7,1),('dflash2','hyper-dflash15',15,1),('dflash2','hyper-dflash7-tp2',7,2)]:
  if label in results:continue
  state('arm_starting',arm=label);start(spec,label,tokens,tp)
  run('measure.py',label,18020,'qwen3.8-27b',timeout=3600)
  if label in ['hyper-off','hyper-dflash7']:
   state('quality_running',arm=label);run('quality.py',label,18020,'qwen3.8-27b',timeout=3600)
  if label=='hyper-dflash7':
   state('project_running',arm=label);run('project_campaign.py',label,18020,'qwen3.8-27b',timeout=4200)
  metrics(label);stop();results.append(label);state('arm_complete',arm=label)
 state('measurement_complete')
except Exception as e:
 (R/'receipts/campaign-error.log').write_text(traceback.format_exc());state('campaign_failed',error=str(e));raise
finally:
 stop()
 subprocess.run(['systemctl','--user','stop','hyperqwen-baseline.service'],check=False)
 state('restoring_kolibri')
 p=subprocess.run(['python3','/home/isa/Experiments/kolibri-fit/scripts/ensure_server.py'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=900)
 (R/'receipts/restore.log').write_text(p.stdout)
 state('complete' if len(results)==5 and p.returncode==0 else 'incomplete',restore_return_code=p.returncode)
