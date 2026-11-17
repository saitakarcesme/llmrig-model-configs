"""Switch between the measured maximum and practical context profiles."""
import json,pathlib,sys
from start_server import ROOT,start
choice=sys.argv[1] if len(sys.argv)>1 else 'maximum'
assert choice in ['maximum','practical'],'Choose maximum or practical'
cap=1048576 if choice=='maximum' else 262144
receipt=json.loads((ROOT/'receipts'/f'context-{cap}-first.json').read_text())
assert receipt['marker_check_passed'],'This context did not pass the experiment gate'
selected={'context':cap,'cache':'q4_0' if choice=='maximum' else 'q8_0','quant':'q3','split':'1,1.04','ubatch':256}
start(**selected)
(ROOT/'selected-profile.json').write_text(json.dumps(selected,indent=2)+'\n')
p=pathlib.Path('/home/isa/.pi/agent/models.json');models=json.loads(p.read_text())
for model in models['providers']['kolibri']['models']:
    if model['id']=='kolibri-1':model['contextWindow']=cap
p.write_text(json.dumps(models,indent=2)+'\n')
p=ROOT/'LOOP_STATE.json';state=json.loads(p.read_text());state['selected_profile']=selected;p.write_text(json.dumps(state,indent=2)+'\n')
with (ROOT/'FINDINGS.md').open('a') as f:f.write(f'\nSelected {choice} profile: '+json.dumps(selected)+'\n')
print('Profile selected. Restart Pi to refresh its context window:',choice)
