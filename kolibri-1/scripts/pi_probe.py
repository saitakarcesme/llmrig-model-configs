import pathlib,subprocess,json,time,os
ROOT=pathlib.Path('/home/isa/Experiments/kolibri-fit')
work=ROOT/'pi-probe';work.mkdir(exist_ok=True)
(work/'input.txt').write_text('Model name: Kolibri. Compute the integer product of 17 and 23.\n')
node='/home/isa/.local/share/mise/installs/node/26.8.2/bin/node'
cli='/home/isa/.local/share/mise/installs/node/26.8.2/lib/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js'
command=[node,cli,'--offline','--provider','kolibri','--model','kolibri-1','--thinking','high',
 '--print','--mode','json','--no-session','--no-context-files','--no-extensions','--no-skills','--no-prompt-templates','--tools','read,write',
 'Read input.txt with the read tool. Compute the product. Use the write tool to create result.json containing only a JSON object with keys model and product, using the model name from the file. Then reply DONE. Do not use any other tools.']
started=time.monotonic()
p=subprocess.run(command,cwd=work,capture_output=True,text=True,timeout=600,env=dict(os.environ,PI_OFFLINE='1',PI_TELEMETRY='0'))
(ROOT/'receipts/pi-probe-output.jsonl').write_text(p.stdout)
(ROOT/'receipts/pi-probe-errors.log').write_text(p.stderr)
events=[]
for line in p.stdout.splitlines():
 try:events.append(json.loads(line))
 except Exception:pass
calls=[e.get('toolName') for e in events if e.get('type')=='tool_execution_start']
result_path=work/'result.json'
try:result=json.loads(result_path.read_text())
except Exception:result=None
passed=p.returncode==0 and result=={'model':'Kolibri','product':391} and 'read' in calls and 'write' in calls
summary={'passed':passed,'return_code':p.returncode,'tools':calls,'result':result,'seconds':time.monotonic()-started,'reasoning_effort':'high','scope':'Actual Pi read and write tool round trip in isolated synthetic workspace.'}
(ROOT/'receipts/pi-probe-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)
assert passed,'Pi tool gate failed; inspect isolated receipts'
