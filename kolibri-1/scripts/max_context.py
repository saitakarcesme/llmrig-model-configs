import json,time,subprocess,pathlib,traceback
from start_server import ROOT,start
from context_probe import run
def state(**fields):
    p=ROOT/'LOOP_STATE.json';s=json.loads(p.read_text());s.update(fields);p.write_text(json.dumps(s,indent=2)+'\n')
    print('STATE',json.dumps(fields),flush=True)
    with (ROOT/'FINDINGS.md').open('a') as f:f.write('\n'+json.dumps(fields)+'\n')

deadline=time.monotonic()+900
while not (ROOT/'receipts/context-262144-first.json').exists():
    assert time.monotonic()<deadline,'262K prerequisite wait expired'
    time.sleep(3)
gate=json.loads((ROOT/'receipts/context-262144-first.json').read_text())
assert gate['marker_check_passed'],'262K prerequisite failed; leave original controller to diagnose'
subprocess.run(['systemctl','--user','stop','kolibri-context-campaign.service'],check=False,stderr=subprocess.DEVNULL)
selected=262144
results=[]
try:
    for context in [1048576,524288]:
        state(stage='maximum_context_server_starting',testing_context=context)
        cache='q4_0' if context==1048576 else 'q8_0'
        try:name=start(context,cache=cache,split='1,1.04')
        except Exception as exc:
            cache='q4_0';state(stage='maximum_context_q4_cache_fallback',error=str(exc),testing_context=context)
            name=start(context,cache=cache,split='1,1.04')
        state(stage='maximum_context_request_running',container=name,cache=cache,testing_context=context)
        r=run(context,'first');results.append(r)
        if r['marker_check_passed']:
            selected=context
            state(stage='maximum_context_gate_passed',largest_passed_configured_context=context,largest_passed_actual_prompt=r['usage']['prompt_tokens'],context_decode_tps=r['timings']['predicted_per_second'])
            break
        state(stage='maximum_context_quality_gate_failed',failed_context=context)
    current=json.loads((ROOT/'receipts/current-server.json').read_text())
    if current['context']!=selected:start(selected)
    (ROOT/'receipts/context-ladder-summary.json').write_text(json.dumps({'largest_passed_configured_context':selected,'maximum_trials':results,'earlier_runs':['context-32768-first.json','context-131072-first.json','context-262144-first.json'],'scope':'Single synthetic three-position retrieval per size. No general maximum-context quality claim.'},indent=2)+'\n')
    state(stage='maximum_context_campaign_complete',largest_passed_configured_context=selected)
except Exception as exc:
    (ROOT/'receipts/maximum-context-error.log').write_text(traceback.format_exc())
    state(stage='maximum_context_campaign_error',error=str(exc),largest_passed_configured_context=selected)
    start(selected)
    raise
