"""Exploratory two-stage budget check, same rule for every arm; no answer feedback."""
import json,re,decimal
from stream_client import ROOT,label,request
initial=json.loads((ROOT/'receipts'/f'{label}-quality.json').read_text());rows=initial['rows'].copy();reruns=[]
def number(text):
 values=re.findall(r'-?\d[\d,]*(?:\.\d+)?',text.rsplit('####',1)[-1])
 if not values:return None
 try:return str(decimal.Decimal(values[-1].replace(',','')).normalize())
 except decimal.InvalidOperation:return None
for pos,old in enumerate(rows):
 if old['finish_reason']!='length':continue
 prev=json.loads((ROOT/'private'/label/f"gsm-{old['index']}.json").read_text())
 prompt=prev['request']['messages'][0]['content']
 row,text=request('gsm-extended-'+str(old['index']),prompt,4096,False)
 row.update(index=old['index'],expected=old['expected'],actual=number(text),passed=number(text)==old['expected'] and row['finish_reason']!='length',initial_content_prefix_preserved=text.startswith(prev['content']),output_cap=4096)
 rows[pos]=row;reruns.append(row)
 d={'protocol':'Exploratory two-stage budget check. Initial 1024-token greedy run; every truncated response is rerun with identical prompt and 4096-token cap. Completed wrong responses are not rerun. No expected answer supplied to model.','initial_passed':initial['passed'],'passed':sum(x['passed'] for x in rows),'total':len(rows),'rerun_count':len(reruns),'complete':False,'reruns':reruns,'rows':rows}
 (ROOT/'receipts'/f'{label}-extended.json').write_text(json.dumps(d,indent=2));print(label,'extended',old['index'],row['passed'],row['finish_reason'],flush=True)
d={'protocol':'Exploratory two-stage budget check. Initial 1024-token greedy run; every truncated response is rerun with identical prompt and 4096-token cap. Completed wrong responses are not rerun. No expected answer supplied to model.','initial_passed':initial['passed'],'passed':sum(x['passed'] for x in rows),'total':len(rows),'rerun_count':len(reruns),'complete':True,'reruns':reruns,'rows':rows}
(ROOT/'receipts'/f'{label}-extended.json').write_text(json.dumps(d,indent=2))
print(label,d['passed'],d['total'],flush=True)
