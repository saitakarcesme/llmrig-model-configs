import pathlib,json,subprocess,os,time
ROOT=pathlib.Path('/home/isa/Experiments/kolibri-fit')
work=ROOT/'pi-source-probe';work.mkdir(exist_ok=True)
node='/home/isa/.local/share/mise/installs/node/26.8.2/bin/node'
cli='/home/isa/.local/share/mise/installs/node/26.8.2/lib/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js'
prompt='Read ONLY these three source files: ../scripts/start_server.py, ../scripts/probe.py, ../scripts/context_probe.py. Use the read tool for each. Then use write to create /home/isa/Experiments/kolibri-fit/pi-source-probe/review.json with exactly these keys: listening_port as the host port used by API clients (not the container port), as an integer, context_shift_enabled as a boolean, short_speed_efforts as an array, long_gate_uses_pi as a boolean, long_gate_compares_all_three_markers as a boolean. Infer all values from the source. The question about Pi concerns context_probe.py specifically. Do not edit any source file. After writing review.json, reply DONE.'
cmd=[node,cli,'--offline','--provider','kolibri','--model','kolibri-1','--thinking','high','--print','--mode','json','--no-session','--no-context-files','--no-extensions','--no-skills','--no-prompt-templates','--tools','read,write',prompt]
t=time.monotonic();p=subprocess.run(cmd,cwd=work,capture_output=True,text=True,timeout=600,env=dict(os.environ,PI_OFFLINE='1',PI_TELEMETRY='0'))
(ROOT/'receipts/pi-source-output.jsonl').write_text(p.stdout);(ROOT/'receipts/pi-source-errors.log').write_text(p.stderr)
events=[]
for line in p.stdout.splitlines():
 try:events.append(json.loads(line))
 except Exception:pass
calls=[e.get('toolName') for e in events if e.get('type')=='tool_execution_start']
try:result=json.loads((work/'review.json').read_text())
except Exception:result=None
expected={'listening_port':8012,'context_shift_enabled':False,'short_speed_efforts':['none','high'],'long_gate_uses_pi':False,'long_gate_compares_all_three_markers':True}
summary={'passed':p.returncode==0 and result==expected and calls.count('read')>=3 and 'write' in calls,'result':result,'expected':expected,'tools':calls,'seconds':time.monotonic()-t,'reasoning_effort':'high','scope':'Actual Pi source reading and structured code comprehension in isolated workspace.'}
(ROOT/'receipts/pi-source-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)
assert summary['passed'],'Pi source review gate failed'
