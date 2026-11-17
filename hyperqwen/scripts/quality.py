import json,re,time,decimal,sys
from stream_client import ROOT,label,request
CAP=int(sys.argv[4]) if len(sys.argv)>4 else 1024
samples=[json.loads(l) for l in (ROOT/'receipts/gsm8k-test.jsonl').read_text().splitlines()][:50]
rows=[]
def number(text):
    part=text.rsplit('####',1)[-1]
    values=re.findall(r'-?\d[\d,]*(?:\.\d+)?',part)
    if not values:return None
    try:return str(decimal.Decimal(values[-1].replace(',','')).normalize())
    except decimal.InvalidOperation:return None
for i,sample in enumerate(samples):
    prompt=sample['question']+'\nSolve carefully. End your answer with #### followed by the final numerical answer.'
    row,text=request('gsm-'+str(i),prompt,CAP,False)
    expected=number(sample['answer']);actual=number(text)
    row.update(index=i,expected=expected,actual=actual,passed=actual==expected and row['finish_reason']!='length')
    rows.append(row)
    (ROOT/'receipts'/f'{label}-quality.json').write_text(json.dumps({'protocol':'quality_protocol.json','output_cap':CAP,'passed':sum(r['passed'] for r in rows),'total':len(rows),'complete':len(rows)==50,'rows':rows},indent=2))
    print(label,i,row['passed'],flush=True)
