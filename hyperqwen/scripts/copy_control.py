import pathlib,subprocess,time,json,urllib.request,traceback
R=pathlib.Path('/home/isa/Experiments/hyperqwen-fit');name=None

def active(unit):return subprocess.check_output(['systemctl','--user','show',unit,'-p','ActiveState','--value']).decode().strip()
def state(stage,**kw):
 d=json.loads((R/'LOOP_STATE.json').read_text());d.update(stage=stage,**kw);(R/'LOOP_STATE.json').write_text(json.dumps(d,indent=2));print(stage,json.dumps(kw),flush=True)
 with (R/'FINDINGS.md').open('a') as f:f.write('\nCopy control: '+json.dumps({'stage':stage,**kw})+'\n')
t=time.time()
while active('hyperqwen-extended-campaign.service') in ['active','activating','deactivating']:
 if time.time()-t>14400:raise TimeoutError('Extended campaign wait')
 time.sleep(5)
s=json.loads((R/'LOOP_STATE.json').read_text());assert len(s.get('extended_completed',[]))==3 and s.get('restore_return_code')==0,'Budget follow-up incomplete; copy control not started'
try:
 state('copy_control_starting')
 for c in subprocess.check_output(['docker','ps','--format','{{.Names}}']).decode().splitlines():
  if c.startswith('kolibri-serve-'):subprocess.run(['docker','stop',c],check=True,timeout=60)
 name='hyperqwen-copy-constant-'+str(int(time.time()))
 subprocess.run(['systemd-run','--user','--unit='+name,'--property=RuntimeMaxSec=2400','--setenv=VLLM_DFLASH2_LOOKUP_ADAPTIVE=0',str(R/'scripts/start_hyper.sh'),'dflash2',name,'15'],check=True)
 t=time.time()
 while time.time()-t<1200:
  if active(name+'.service')=='failed':raise RuntimeError('Copy control server failed')
  try:urllib.request.urlopen('http://127.0.0.1:18020/health',timeout=2);break
  except Exception:time.sleep(5)
 else:raise TimeoutError('Copy control startup')
 state('copy_control_running')
 subprocess.run(['python3',str(R/'scripts/measure.py'),'hyper-dflash15-constant','18020','qwen3.8-27b'],check=True,timeout=1800)
 # This child client writes only numeric receipts; generated text stays in private/.
 code="""import sys,json
sys.path.insert(0,'/home/isa/Experiments/hyperqwen-fit/scripts')
from stream_client import ROOT,request
src='\\n'.join(f'Entry {i:03d}. Copper lantern {i*7:04d} crosses the quiet harbor at dawn.' for i in range(110))
rows=[]
for i in range(3):
 row,text=request('copy-full-'+str(i),'Copy the following text verbatim. Do not add any commentary or formatting.\\n\\n'+src,4096)
 row['exact_copy']=text.strip()==src;row['complete']=row['finish_reason']!='length';rows.append(row)
(ROOT/'receipts/hyper-dflash15-constant-full-copy.json').write_text(json.dumps(rows,indent=2))
print('Full copy checks',[(r['exact_copy'],r['complete']) for r in rows],flush=True)
"""
 subprocess.run(['python3','-c',code,'hyper-dflash15-constant','18020','qwen3.8-27b'],check=True,timeout=600)
 subprocess.run(['docker','logs',name],stdout=(R/'receipts/hyper-dflash15-constant-startup.log').open('w'),stderr=subprocess.STDOUT,check=True)
 envrows=json.loads(subprocess.check_output(['docker','inspect',name,'--format','{{json .Config.Env}}']))
 allowed={'VLLM_DFLASH2_LOOKUP_ADAPTIVE','SPEC','DFLASH_TOKENS','CTX','MODEL','DRAFT','VLLM_OFFLOAD_KEEP_SHM','HF_HUB_OFFLINE'}
 (R/'receipts/hyper-dflash15-constant-environment.json').write_text(json.dumps({x.split('=',1)[0]:x.split('=',1)[1] for x in envrows if x.split('=',1)[0] in allowed},indent=2))
 state('copy_control_complete',copy_control_done=True)
except Exception as e:
 (R/'receipts/copy-control-error.log').write_text(traceback.format_exc());state('copy_control_failed',copy_control_error=str(e));raise
finally:
 if name:subprocess.run(['docker','stop','-t','30',name],check=False,timeout=60)
 state('restoring_kolibri')
 p=subprocess.run(['python3','/home/isa/Experiments/kolibri-fit/scripts/ensure_server.py'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=900)
 (R/'receipts/copy-control-restore.log').write_text(p.stdout)
 state('complete' if p.returncode==0 and json.loads((R/'LOOP_STATE.json').read_text()).get('copy_control_done') else 'incomplete',restore_return_code=p.returncode)
