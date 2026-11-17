"""Summarize saved task artifacts and their matching server measurements."""
import argparse
import json
from pathlib import Path
import statistics

parser=argparse.ArgumentParser()
parser.add_argument('root',nargs='+')
parser.add_argument('--output')
parser.add_argument('--receipts',required=True)
args=parser.parse_args()
roots=[Path(r) for r in args.root]
requests={}
for line in Path(args.receipts).read_text().splitlines():
    record=json.loads(line)
    requests[record['id']]=record
cells=[]
for path in sorted(p for root in roots for p in root.glob('*/result.json')):
    result=json.loads(path.read_text())
    if result.get('excluded_from_benchmark'):continue
    records=[requests[t['response']['id']] for t in result['trace']
             if 'response' in t and t['response']['id'] in requests]
    speeds=[r['usage']['completion_tokens']/r['decode_seconds'] for r in records
            if r.get('decode_seconds') and r['usage']['completion_tokens']>=10]
    cells.append({k:result[k] for k in ('task','context_capacity_tokens','status','seconds','error',
                                       'initial_text_prompt_tokens','agent_verified','enable_thinking')}
        | {'requests':len(records),'tool_calls':sum('tool' in t for t in result['trace']),
           'maximum_prompt_tokens':max((r['usage']['prompt_tokens'] for r in records),default=None),
           'median_decode_tokens_per_second':statistics.median(speeds) if speeds else None,
           'prefill_seconds':sum(r.get('prefill_seconds') or 0 for r in records),
           'maximum_request_seconds':max((r['seconds'] for r in records),default=None),
           'maximum_internal_ttft_seconds':max((r.get('time_to_first_text') or 0 for r in records),default=None),
           'receipt':str(path)})
summary={'cells':cells,'passed':sum(c['status']=='passed' for c in cells),'total':len(cells),
         'context_material':'synthetic repository excerpts',
         'computer_use_surface':'isolated screenshot-driven Chromium fixture, not OS desktop apps'}
destination=Path(args.output) if args.output else roots[0]/'summary.json'
destination.write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
