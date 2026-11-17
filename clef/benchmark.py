import argparse,json,time,statistics,urllib.request
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:18031');p.add_argument('--model',default='clef-flash');p.add_argument('--output',required=True);a=p.parse_args()
cases=[('outage','Checkout returns HTTP 500 and customers cannot complete orders.','technical',True),('invoice','Please send a copy of my paid invoice for September.','billing',False),('bug','The app crashes on launch after the update.','technical',False),('refund','I was charged twice and need the duplicate payment refunded.','billing',False),('turkish','Odeme sayfasi hata veriyor, hicbir musteri siparis veremiyor.','technical',True)]
rows=[]
for repeat in range(4):
 for name,state,team,outage in cases:
  body={'model':a.model,'state':state,'questions':{'department':{'type':'choice','instructions':'Which team should handle this?','criteria':{'billing':'Payments, invoices, refunds','technical':'Bugs, crashes, outages'}},'outage':{'type':'noul','instructions':'Is a service-wide outage preventing customers from ordering?'},'urgency':{'type':'score','instructions':'How urgently should this be handled?','criteria':['Can wait','This week','Today']}}}
  t=time.perf_counter()
  with urllib.request.urlopen(urllib.request.Request(a.url+'/v1/systemone',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'}),timeout=180) as r: response=json.load(r)
  rows.append({'case':name,'repeat':repeat,'cold_request':repeat==0 and name=='outage','wall_ms':(time.perf_counter()-t)*1000,'expected_department':team,'expected_outage':outage,'response':response})
warm=[r['wall_ms'] for r in rows[5:]]
out={'model':a.model,'health':json.load(urllib.request.urlopen(a.url+'/health')),'summary':{'warm_requests':len(warm),'warm_median_ms':statistics.median(warm),'warm_p95_ms':sorted(warm)[int(.95*(len(warm)-1))],'department_correct':sum(r['response']['answers']['department']['choice']==r['expected_department'] for r in rows),'requests':len(rows),'outage_correct':sum((r['response']['answers']['outage']['noul']>=.5)==r['expected_outage'] for r in rows)},'rows':rows}
Path(a.output).write_text(json.dumps(out,indent=2));print(json.dumps(out['summary']))
