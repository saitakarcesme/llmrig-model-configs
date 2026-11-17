import subprocess,time,json,datetime,pathlib,urllib.request,traceback
R=pathlib.Path('/home/isa/Experiments/hyperqwen-fit');current=None;completed=[]
def active(unit):return subprocess.check_output(['systemctl','--user','show',unit,'-p','ActiveState','--value']).decode().strip()
def state(stage,**kwargs):
 d=json.loads((R/'LOOP_STATE.json').read_text());d.update(stage=stage,updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),extended_completed=completed,**kwargs);(R/'LOOP_STATE.json').write_text(json.dumps(d,indent=2));print(stage,json.dumps(kwargs),flush=True)
 with (R/'FINDINGS.md').open('a') as f:f.write('\nExtended budget check: '+json.dumps({'stage':stage,**kwargs})+'\n')
def wait_ready(port,unit,timeout=1200):
 t=time.time()
 while time.time()-t<timeout:
  if active(unit)=='failed':raise RuntimeError(unit+' failed startup')
  try:urllib.request.urlopen(f'http://127.0.0.1:{port}/v1/models',timeout=2);return
  except Exception:time.sleep(5)
 raise TimeoutError(unit)
def stop():
 global current
 if current:
  kind,name=current
  if kind=='docker':subprocess.run(['docker','stop','-t','30',name],check=False,timeout=60)
  else:subprocess.run(['systemctl','--user','stop',name+'.service'],check=False)
  current=None
# Wait only for this finite campaign, then validate that all main arms actually completed.
t=time.time()
while active('hyperqwen-campaign.service') in ['active','activating','deactivating']:
 if time.time()-t>10800:raise TimeoutError('Primary campaign wait')
 time.sleep(5)
prior=json.loads((R/'LOOP_STATE.json').read_text());assert len(prior.get('completed_arms',[]))==5 and prior.get('restore_return_code')==0,'Primary campaign incomplete; extended check not started'
(R/'receipts/primary_campaign_state.json').write_text(json.dumps(prior,indent=2))
try:
 state('extended_budget_preparing')
 for c in subprocess.check_output(['docker','ps','--format','{{.Names}}']).decode().splitlines():
  if c.startswith('kolibri-serve-'):subprocess.run(['docker','stop',c],check=True,timeout=60)
 name='hyperqwen-extended-baseline-'+str(int(time.time()));current=('unit',name)
 subprocess.run(['systemd-run','--user','--unit='+name,'--property=RuntimeMaxSec=1800',str(R/'scripts/start_baseline.sh')],check=True)
 wait_ready(18019,name+'.service')
 state('extended_budget_running',extended_arm='exl3-mtp')
 subprocess.run(['python3',str(R/'scripts/quality_extended.py'),'exl3-mtp','18019','qwen3.8:27b'],check=True,timeout=1200)
 stop();completed.append('exl3-mtp')
 for label,spec in [('hyper-off','off'),('hyper-dflash7','dflash2')]:
  name='hyperqwen-extended-'+label+'-'+str(int(time.time()));current=('docker',name)
  state('extended_budget_starting',extended_arm=label)
  subprocess.run(['systemd-run','--user','--unit='+name,'--property=RuntimeMaxSec=2400',str(R/'scripts/start_hyper.sh'),spec,name,'7'],check=True)
  wait_ready(18020,name+'.service')
  state('extended_budget_running',extended_arm=label)
  subprocess.run(['python3',str(R/'scripts/quality_extended.py'),label,'18020','qwen3.8-27b'],check=True,timeout=1200)
  subprocess.run(['docker','logs',name],stdout=(R/'receipts'/f'{label}-extended-startup.log').open('w'),stderr=subprocess.STDOUT,check=True)
  stop();completed.append(label)
except Exception as e:
 (R/'receipts/extended-error.log').write_text(traceback.format_exc());state('extended_budget_failed',extended_error=str(e));raise
finally:
 stop();state('restoring_kolibri')
 p=subprocess.run(['python3','/home/isa/Experiments/kolibri-fit/scripts/ensure_server.py'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=900)
 (R/'receipts/extended_restore.log').write_text(p.stdout)
 state('complete' if len(completed)==3 and p.returncode==0 else 'incomplete',restore_return_code=p.returncode)
