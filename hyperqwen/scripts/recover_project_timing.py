"""Recover aggregate native timing, excluding the prior benchmarks and bounding warmup."""
from pathlib import Path
import json,re,subprocess
r=Path('/home/isa/Experiments/hyperqwen-fit');label='hyper-dflash7'
metrics=(r/'receipts'/f'{label}-metrics.txt').read_text()
def value(name):
 rows=[float(l.rsplit(' ',1)[1]) for l in metrics.splitlines() if l.startswith('vllm:'+name+'{')]
 assert len(rows)==1,(name,len(rows));return rows[0]
prior=json.loads((r/'receipts'/f'{label}-speed.json').read_text())+json.loads((r/'receipts'/f'{label}-quality.json').read_text())['rows']
requests=[json.loads(l) for l in (r/'project-hyper-dflash7/receipts/requests.jsonl').read_text().splitlines()]
assert all(q.get('extra_metrics',{}).get('metrics',{}).get('generation_time_ms') is not None for q in prior)
known_decode=sum(q['extra_metrics']['metrics']['generation_time_ms']/1000 for q in prior)
known_tokens=sum(q['usage']['completion_tokens'] for q in prior)
project_tokens=sum(q.get('usage',{}).get('completion_tokens',0) for q in requests)
expected_count=1+len(prior)+len(requests)
assert value('request_generation_tokens_count')==expected_count,(expected_count,value('request_generation_tokens_count'))
assert value('request_generation_tokens_sum')==known_tokens+64+project_tokens
names=subprocess.check_output(['docker','ps','-a','--format','{{.Names}}']).decode().splitlines()
servers=[n for n in names if re.fullmatch(r'hyperqwen-hyper-dflash7-\d+',n)];assert len(servers)==1,servers
logs=subprocess.check_output(['docker','logs',servers[0]],stderr=subprocess.STDOUT).decode(errors='replace');(r/'receipts'/f'{label}-server-final.log').write_text(logs)
matches=re.findall(r'Request finished:.*?generated_tokens=(\d+).*?elapsed_s=([0-9.]+)',logs)
assert matches and int(matches[0][0])==64,matches[:1]
warmup_upper=float(matches[0][1]);residual=value('request_decode_time_seconds_sum')-known_decode
assert residual>warmup_upper>=0
transitions=sum(max(0,q.get('usage',{}).get('completion_tokens',0)-1) for q in requests)
result={'scope':'Aggregate across all four HyperQwen Pi project tasks. Native first-to-last-token decode timing, excluding all recorded speed and math runs. The discarded 64-token warmup is bounded between zero and its full native engine elapsed time.','project_completion_tokens':project_tokens,'project_api_requests':len(requests),'validated_total_request_count':expected_count,'prior_recorded_decode_seconds':known_decode,'native_total_decode_seconds':value('request_decode_time_seconds_sum'),'project_decode_seconds_range':[residual-warmup_upper,residual],'decode_tps_range':[transitions/residual,transitions/(residual-warmup_upper)],'warmup_elapsed_upper_bound_seconds':warmup_upper,'api_output_tps_including_ttft':project_tokens/sum(q['total_seconds'] for q in requests),'invalid_raw_proxy_fields':'The first project proxy missed delta.reasoning; its original observed_decode_tps and weighted_decode_tps fields are invalid for this arm. Standalone speed and quality clients handled both reasoning fields.'}
(r/'receipts'/f'{label}-native-project-timing.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
