import json,pathlib,time,datetime,subprocess,traceback
from start_server import start,ROOT
from context_probe import run

def state(**fields):
    p=ROOT/'LOOP_STATE.json';s=json.loads(p.read_text());s.update(fields,updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat());p.write_text(json.dumps(s,indent=2)+'\n')
    print('STATE',json.dumps(fields),flush=True)
    with (ROOT/'FINDINGS.md').open('a') as f:f.write('\n'+json.dumps(fields)+'\n')

passed=32768;out=[]
try:
    for context in [131072,262144,524288,1048576]:
        state(stage='context_server_starting',testing_context=context)
        try:name=start(context)
        except Exception as exc:
            state(stage='q8_allocation_failed_trying_q4_kv',testing_context=context,error=str(exc))
            name=start(context,cache='q4_0')
        state(stage='context_request_running',testing_context=context,container=name)
        r=run(context,'first');out.append(r)
        if not r['marker_check_passed']:
            state(stage='context_quality_retry',testing_context=context)
            r=run(context,'retry');out.append(r)
            if not r['marker_check_passed']:
                state(stage='context_growth_stopped_at_quality_gate',failed_context=context,largest_passed_configured_context=passed)
                break
        passed=context
        state(stage='context_gate_passed',largest_passed_configured_context=passed,largest_passed_actual_prompt=r['usage']['prompt_tokens'],context_decode_tps=r['timings']['predicted_per_second'])
    else:state(stage='context_ladder_complete',largest_passed_configured_context=passed)
    current=json.loads((ROOT/'receipts/current-server.json').read_text())
    if current['context']!=passed:start(passed)
    (ROOT/'receipts/context-ladder-summary.json').write_text(json.dumps({'largest_passed_configured_context':passed,'runs':out,'scope':'Synthetic three-position retrieval only; no general maximum-context quality claim.'},indent=2)+'\n')
except Exception as exc:
    (ROOT/'receipts/context-campaign-error.log').write_text(traceback.format_exc())
    state(stage='context_campaign_error',error=str(exc),largest_passed_configured_context=passed)
    start(passed)
    raise
