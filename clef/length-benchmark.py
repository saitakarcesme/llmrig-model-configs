import argparse,json,time,statistics,urllib.request
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--model',default='clef-flash');p.add_argument('--output',required=True);a=p.parse_args()
rows=[]
for repeats in [0,40,180]:
 state=('Routine log: all background workers are healthy. '*repeats)+' Checkout returns HTTP 500 and nobody can place orders.'
 for trial in range(4):
  body={'model':a.model,'state':state,'questions':{'department':{'type':'choice','criteria':{'billing':'Invoices and payments','technical':'Outages and software bugs'}},'outage':{'type':'noul','instructions':'Is ordering down?'}}}
  t=time.perf_counter()
  with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18031/v1/systemone',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'}),timeout=180) as r:x=json.load(r)
  rows.append({'repeats':repeats,'trial':trial,'wall_ms':1000*(time.perf_counter()-t),'response':x})
summary=[]
for r in [0,40,180]:
 group=[x for x in rows if x['repeats']==r and x['trial']>0]
 summary.append({'input_tokens':group[0]['response']['usage']['input_tokens'],'median_ms':statistics.median(x['wall_ms'] for x in group)})
Path(a.output).write_text(json.dumps({'model':a.model,'summary':summary,'rows':rows},indent=2));print(json.dumps(summary))
