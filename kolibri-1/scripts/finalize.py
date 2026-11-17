import json,pathlib,subprocess,time,statistics,datetime,shutil
import probe
from start_server import ROOT

def state(stage,**fields):
    p=ROOT/'LOOP_STATE.json';s=json.loads(p.read_text())
    s.update(stage=stage,updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),**fields)
    p.write_text(json.dumps(s,indent=2)+'\n')
    with (ROOT/'FINDINGS.md').open('a') as f:f.write('\n'+json.dumps({'stage':stage,**fields})+'\n')
    print(stage,json.dumps(fields),flush=True)

deadline=time.monotonic()+1800
while not (ROOT/'receipts/context-ladder-summary.json').exists():
    assert time.monotonic()<deadline,'Maximum-context prerequisite did not finish'
    time.sleep(10)
state('q4_comparison_running')
p=subprocess.run(['python3',str(ROOT/'scripts/q4_comparison.py')],timeout=1800)
state('final_profile_validation',q4_comparison_return_code=p.returncode)
current=json.loads((ROOT/'receipts/current-server.json').read_text())
assert current['quant']=='q3','Comparison did not restore Q3'
selected={k:current[k] for k in ['context','cache','quant','split','ubatch']}
(ROOT/'selected-profile.json').write_text(json.dumps(selected,indent=2)+'\n')
study=ROOT/'final-study';(study/'receipts').mkdir(parents=True,exist_ok=True)
probe.ROOT=study
prompt='Write a detailed tutorial on implementing an LRU cache in Python with examples and explanations. Continue until the output limit. Do not use tools.'
probe.chat('warmup-high',prompt,'high',64)
rates=[probe.chat(f'speed-high-{n}',prompt,'high',512)['timings']['predicted_per_second'] for n in range(1,4)]
(ROOT/'receipts/final-profile-speed.json').write_text(json.dumps({'profile':selected,'high_tps':rates,'high_median_tps':statistics.median(rates),'scope':'512 generated tokens including thought on a short prompt in the final configured context slot.'},indent=2)+'\n')
subprocess.run(['python3',str(ROOT/'scripts/pi_source_probe.py')],check=True,timeout=660)
config=pathlib.Path('/home/isa/.pi/agent')
p=config/'models.json';models=json.loads(p.read_text())
for model in models['providers']['kolibri']['models']:
    if model['id']=='kolibri-1':model['contextWindow']=selected['context']
p.write_text(json.dumps(models,indent=2)+'\n')
p=config/'settings.json';settings=json.loads(p.read_text())
settings.update(defaultProvider='kolibri',defaultModel='kolibri-1',defaultThinkingLevel='high')
p.write_text(json.dumps(settings,indent=2)+'\n')
launcher=pathlib.Path('/home/isa/.local/bin/llmrig-pi')
backup=ROOT/'private/pi-original-launcher'
if launcher.exists() and not backup.exists():
    shutil.copy2(launcher,backup);backup.chmod(0o600)
launcher.write_text('#!/bin/bash\nset -e\npython3 /home/isa/Experiments/kolibri-fit/scripts/ensure_server.py\ncd /home/isa/Projects/llmrig\nexec /home/isa/.local/share/mise/installs/node/26.8.2/bin/node /home/isa/.local/share/mise/installs/node/26.8.2/lib/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js --offline --provider kolibri --model kolibri-1 --thinking high "$@"\n')
launcher.chmod(0o755)
state('complete',maximum_context_verified=True,selected_profile=selected,final_short_high_tps=statistics.median(rates),pi_source_verified=True,pi_default='kolibri-1',error=None)
