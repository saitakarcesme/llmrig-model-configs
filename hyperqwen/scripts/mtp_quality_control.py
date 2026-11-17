import subprocess,time,json,pathlib,urllib.request,traceback
R=pathlib.Path('/home/isa/Experiments/hyperqwen-fit');name=None

def active(u):return subprocess.check_output(['systemctl','--user','show',u,'-p','ActiveState','--value']).decode().strip()
def state(stage,**kw):
 d=json.loads((R/'LOOP_STATE.json').read_text());d.update(stage=stage,**kw);(R/'LOOP_STATE.json').write_text(json.dumps(d,indent=2));print(stage,json.dumps(kw),flush=True)
 with (R/'FINDINGS.md').open('a') as f:f.write('\nMTP quality control: '+json.dumps({'stage':stage,**kw})+'\n')
t=time.time()
while active('hyperqwen-copy-control.service') in ['active','activating','deactivating']:
 if time.time()-t>14400:raise TimeoutError('Copy control wait')
 time.sleep(5)
s=json.loads((R/'LOOP_STATE.json').read_text());assert s.get('copy_control_done') and s.get('restore_return_code')==0,'Prior controls incomplete'
try:
 state('mtp_quality_starting')
 for c in subprocess.check_output(['docker','ps','--format','{{.Names}}']).decode().splitlines():
  if c.startswith('kolibri-serve-'):subprocess.run(['docker','stop',c],check=True,timeout=60)
 name='hyperqwen-mtp-quality-'+str(int(time.time()))
 subprocess.run(['systemd-run','--user','--unit='+name,'--property=RuntimeMaxSec=2400',str(R/'scripts/start_hyper.sh'),'mtp',name,'7'],check=True)
 t=time.time()
 while time.time()-t<1200:
  if active(name+'.service')=='failed':raise RuntimeError('MTP quality server failed')
  try:urllib.request.urlopen('http://127.0.0.1:18020/health',timeout=2);break
  except Exception:time.sleep(5)
 else:raise TimeoutError('MTP quality startup')
 state('mtp_quality_running')
 subprocess.run(['python3',str(R/'scripts/quality.py'),'hyper-mtp','18020','qwen3.8-27b','4096'],check=True,timeout=1800)
 subprocess.run(['docker','logs',name],stdout=(R/'receipts/hyper-mtp-quality-startup.log').open('w'),stderr=subprocess.STDOUT,check=True)
 state('mtp_quality_complete',mtp_quality_done=True)
except Exception as e:
 (R/'receipts/mtp-quality-error.log').write_text(traceback.format_exc());state('mtp_quality_failed',mtp_quality_error=str(e));raise
finally:
 if name:subprocess.run(['docker','stop','-t','30',name],check=False,timeout=60)
 state('restoring_kolibri')
 p=subprocess.run(['python3','/home/isa/Experiments/kolibri-fit/scripts/ensure_server.py'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=900)
 (R/'receipts/mtp-quality-restore.log').write_text(p.stdout)
 state('complete' if p.returncode==0 and json.loads((R/'LOOP_STATE.json').read_text()).get('mtp_quality_done') else 'incomplete',restore_return_code=p.returncode)
