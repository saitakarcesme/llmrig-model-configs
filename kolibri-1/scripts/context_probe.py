import hashlib,json,pathlib,re,sys,time
from probe import ROOT,api,chat

def make_prompt(lines,seed):
    keys={p:hashlib.sha256(f'{seed}-{p}'.encode()).hexdigest()[:12] for p in ['start','middle','end']}
    records=[]
    for i in range(lines):
        value=hashlib.sha256(f'{seed}-record-{i}'.encode()).hexdigest()[:10]
        records.append(f'Record {i:07d}. Component cache worker. Status tested. Build label {value}. Retain this record for audit.\n')
    records.insert(0,f'Unique deployment marker start = {keys["start"]}.\n')
    records.insert(len(records)//2,f'Unique deployment marker middle = {keys["middle"]}.\n')
    records.append(f'Unique deployment marker end = {keys["end"]}.\n')
    prefix='Read the audit records below and find all three unique deployment markers. Their values are only in the records.\n'
    suffix='\nReturn ONLY a JSON object with keys start, middle, end and their exact marker values. No explanation.\n'
    return prefix+''.join(records)+suffix,keys

def run(context,seed='first'):
    target=context-4096;lines=max(1,target//28)
    for n in range(4):
        prompt,expected=make_prompt(lines,seed)
        rendered=api('/apply-template',{'messages':[{'role':'user','content':prompt}],'chat_template_kwargs':{'reasoning_effort':'none','enable_thinking':False}})['prompt']
        size=len(api('/tokenize',{'content':rendered,'add_special':False})['tokens'])
        if target-512<=size<=target:break
        lines=max(1,int(lines*(target-128)/size))
    assert size+1024<context,(size,context)
    label=f'context-{context}-{seed}'
    r=chat(label,prompt,'none',512)
    text=r['answer'].strip()
    if text.startswith('```'):text=re.sub(r'^```(?:json)?\s*|\s*```$','',text)
    try:got=json.loads(text);passed=got==expected
    except Exception:got=None;passed=False
    r.update(context_configured=context,prompt_tokens_estimated=size,marker_check_passed=passed,marker_expected=expected,marker_actual=got,prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),scope='Synthetic three-position retrieval. Not a general real-project quality benchmark.')
    (ROOT/'receipts'/f'{label}.json').write_text(json.dumps(r,indent=2)+'\n')
    print('CONTEXT_GATE',json.dumps({k:r[k] for k in ['context_configured','usage','marker_check_passed','timings','ttft_seconds','total_seconds']}),flush=True)
    return r
if __name__=='__main__':run(int(sys.argv[1]),sys.argv[2] if len(sys.argv)>2 else 'first')
