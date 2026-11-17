import json,pathlib,subprocess,time,statistics,datetime,shutil
import probe
from start_server import ROOT

def state(stage,**fields):
    p=ROOT/'LOOP_STATE.json';s=json.loads(p.read_text())
    s.update(stage=stage,updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),**fields)
    p.write_text(json.dumps(s,indent=2)+'\n')
    with (ROOT/'FINDINGS.md').open('a') as f:f.write('\n'+json.dumps({'stage':stage,**fields})+'\n')
    print(stage,json.dumps(fields),flush=True)

source_gate=json.loads((ROOT/'receipts/pi-source-summary.json').read_text())
assert 'write' in source_gate['tools'] and source_gate['tools'].count('read')>=3, 'Final Pi tool round trip did not complete'
selected=json.loads((ROOT/'selected-profile.json').read_text())
rates=json.loads((ROOT/'receipts/final-profile-speed.json').read_text())['high_tps']
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
state('complete',maximum_context_verified=True,selected_profile=selected,final_short_high_tps=statistics.median(rates),pi_source_verified=source_gate['passed'],pi_tools_verified=True,pi_default='kolibri-1',error=None)
