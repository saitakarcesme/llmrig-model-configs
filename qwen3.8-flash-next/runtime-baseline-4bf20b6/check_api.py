"""Exercise chat, sampling, streaming and tool-call contracts on the rig."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import time
import httpx

parser=argparse.ArgumentParser()
parser.add_argument('--endpoint',default='http://127.0.0.1:30260')
parser.add_argument('--output',default='/home/isa/Experiments/qwen38-flash-next-b70-fit/receipts/api-contract.json')
args=parser.parse_args()
client=httpx.Client(base_url=args.endpoint,timeout=httpx.Timeout(None,connect=10,write=60,pool=10))
health=client.get('/health').json()
assert health['status']=='ready' and health['vision_mrope'] and health['default_thinking']
assert client.get('/v1/models').json()['data'][0]['id']=='flashnext'
body={'model':'flashnext','messages':[{'role':'user','content':
      'Write only Python code defining sum_even_numbers(nums), returning the sum of even integers, including negative values. No explanation.'}],
      'temperature':0,'max_tokens':256,'enable_thinking':False}
records=[]
for label in ['first','repeat']:
    start=time.perf_counter()
    response=client.post('/v1/chat/completions',json=body)
    response.raise_for_status()
    data=response.json()
    code=data['choices'][0]['message']['content']
    code=re.sub(r'^```(?:python)?\s*|\s*```$','',code.strip())
    checker='import sys; code=sys.stdin.read(); ns={}; exec(compile(code,"model-output","exec"),ns); f=ns["sum_even_numbers"]; assert f([1,2,3,4,-2])==4; assert f([])==0; assert f([-4,-3,6])==2; print("PASS")'
    command=['bwrap','--unshare-all','--die-with-parent','--ro-bind','/usr','/usr',
             '--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--proc','/proc',
             '--dev','/dev','--tmpfs','/tmp','--clearenv','--setenv','PATH','/usr/bin',
             'python3','-I','-c',checker]
    checked=subprocess.run(command,input=code,text=True,capture_output=True,timeout=15)
    assert checked.returncode==0 and checked.stdout.strip()=='PASS',checked.stderr
    records.append({'label':label,'seconds':time.perf_counter()-start,'response':data,'code_verified':True})

def streaming(request):
    start=time.perf_counter();first=None;chunks=[]
    with client.stream('POST','/v1/chat/completions',json=dict(request,stream=True)) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line.startswith('data: '):continue
            if line=='data: [DONE]':break
            chunk=json.loads(line[6:]);chunks.append(chunk)
            delta=chunk['choices'][0]['delta']
            if first is None and (delta.get('content') or delta.get('tool_calls')):
                first=time.perf_counter()-start
    assert chunks[-1]['choices'][0]['finish_reason']
    return {'seconds':time.perf_counter()-start,'first_payload_seconds':first,'chunks':chunks}

plain=streaming(body)
assert ''.join(c['choices'][0]['delta'].get('content') or '' for c in plain['chunks'])
records.append({'label':'text_stream',**plain})
tool_body={'model':'flashnext','messages':[{'role':'user','content':'Call read_file with path package.json. Use the tool instead of answering.'}],
           'tools':[{'type':'function','function':{'name':'read_file','description':'Read a file.',
               'parameters':{'type':'object','properties':{'path':{'type':'string'}},'required':['path']}}}],
           'temperature':0,'max_tokens':128,'enable_thinking':False}
tool_stream=streaming(tool_body)
calls=[call for chunk in tool_stream['chunks'] for call in chunk['choices'][0]['delta'].get('tool_calls',[])]
assert len(calls)==1 and calls[0]['function']['name']=='read_file'
assert json.loads(calls[0]['function']['arguments'])=={'path':'package.json'}
records.append({'label':'tool_stream',**tool_stream})
sample=client.post('/v1/chat/completions',json=dict(body,temperature=0.2,top_k=1,max_tokens=128))
sample.raise_for_status()
records.append({'label':'nonzero_temperature','response':sample.json()})
limited=client.post('/v1/chat/completions',json={'model':'flashnext','messages':[{'role':'user','content':'Compute 17+25.'}],
                    'enable_thinking':True,'reasoning_effort':'low','temperature':0,'max_tokens':8})
limited.raise_for_status();limited=limited.json()
assert limited['choices'][0]['finish_reason']=='length'
assert limited['choices'][0]['message'].get('reasoning_content')
records.append({'label':'truncated_reasoning','response':limited})
invalid=client.post('/v1/chat/completions',json=dict(body,max_tokens=health['context']+1))
assert invalid.status_code==400
unknown=client.post('/v1/chat/completions',json=dict(body,model='missing-model'))
assert unknown.status_code==404
for thinking in (False,True):
    direct=dict(tool_body,enable_thinking=thinking,reasoning_effort='low')
    nested=dict(tool_body,chat_template_kwargs={'enable_thinking':thinking,'reasoning_effort':'low'})
    nested.pop('enable_thinking')
    direct_tokens=client.post('/tokenize',json=direct);direct_tokens.raise_for_status()
    nested_tokens=client.post('/tokenize',json=nested);nested_tokens.raise_for_status()
    assert direct_tokens.json()['tokens']==nested_tokens.json()['tokens']
default_body=dict(tool_body,max_tokens=1024)
default_body.pop('temperature')
default_body.pop('enable_thinking')
default_response=client.post('/v1/chat/completions',json=default_body)
default_response.raise_for_status();default_response=default_response.json()
default_message=default_response['choices'][0]['message']
assert default_message.get('reasoning_content')
assert default_message['tool_calls'][0]['function']['name']=='read_file'
assert json.loads(default_message['tool_calls'][0]['function']['arguments'])=={'path':'package.json'}
records.append({'label':'native_thinking_defaults','response':default_response})
receipt={'status':'passed','health':health,'checks':records,'context_overflow_status':invalid.status_code,
         'unknown_model_status':unknown.status_code}
Path(args.output).write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'status':'passed','checks':len(records),'health':health}))
