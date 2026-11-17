import pathlib,json,traceback,subprocess,statistics
import probe,context_probe
from start_server import ROOT,start

# Run only after the extended-context campaign has finished.
assert (ROOT/'receipts/context-ladder-summary.json').exists()
selected=json.loads((ROOT/'receipts/current-server.json').read_text())
study=ROOT/'q4-study';(study/'receipts').mkdir(parents=True,exist_ok=True)
probe.ROOT=study
context_probe.ROOT=study
try:
    context=131072
    try:name=start(context,quant='q4',split='1,1.04',ubatch=128)
    except Exception:
        context=32768;name=start(context,quant='q4',split='1,1.04',ubatch=128)
    probe.run()
    r=context_probe.run(context,'q4')
    rows=[]
    for effort in ['none','high']:
        vals=[json.loads((study/'receipts'/f'speed-{effort}-{n}.json').read_text())['timings']['predicted_per_second'] for n in range(1,4)]
        rows.append({'effort':effort,'tps':vals,'median_tps':statistics.median(vals)})
    (study/'receipts/summary.json').write_text(json.dumps({'speed':rows,'context':context,'marker_check_passed':r['marker_check_passed'],'container':name},indent=2)+'\n')
finally:
    start(selected['context'],cache=selected['cache'],quant=selected['quant'],split=selected['split'],ubatch=selected['ubatch'])
