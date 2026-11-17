"""Local OpenAI-compatible Flash-Next chat API using native CUDA offload."""
import base64
import io
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import time
import uuid

import torch
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from PIL import Image
from transformers import AutoTokenizer
from exllamav3 import Config, Model, Tokenizer, Cache, Generator, Job, ArgmaxSampler, ComboSampler
import native_disk
import vision_positions

ROOT=Path('/work')
MODEL=ROOT/'models/flashnext-3.05bpw'
CONTEXT=int(os.environ.get('FLASHNEXT_CONTEXT','65536'))
CHUNK=int(os.environ.get('FLASHNEXT_CHUNK','512'))
VISION_DEVICE=int(os.environ.get('FLASHNEXT_VISION_DEVICE','0'))
RECURRENT_CACHE_MB=int(os.environ.get('FLASHNEXT_RECURRENT_CACHE_MB','4096'))
lock=threading.Lock()
torch.set_num_threads(8)
torch.set_grad_enabled(False)
store=native_disk.install(MODEL,tuple(map(float,os.environ.get('FLASHNEXT_GPU_CACHE','12,21').split(','))),
                          float(os.environ.get('FLASHNEXT_HOST_CACHE','2')))
config=Config.from_directory(str(MODEL))
model=Model.from_config(config)
vision_positions.install(model,config)
tokenizer=Tokenizer(config)
hf_tokenizer=AutoTokenizer.from_pretrained(str(MODEL),local_files_only=True)
cache=Cache(model,max_num_tokens=CONTEXT,max_batch_size=1)
started=time.perf_counter()
model.load(device='cuda:0',max_chunk_size=CHUNK)
generator=Generator(model,cache,tokenizer,max_batch_size=1,max_chunk_size=CHUNK,
                    recurrent_cache_size=RECURRENT_CACHE_MB*1024**2,
                    recurrent_checkpoint_interval_pp=CHUNK)
vision=None
image_cache={}
print('Flash-Next text model ready',time.perf_counter()-started,flush=True)
app=FastAPI()


def normalize_messages(messages):
    output=[]
    for message in messages:
        message=dict(message)
        if message.get('tool_calls'):
            calls=[]
            for call in message['tool_calls']:
                call=dict(call)
                function=dict(call['function'])
                if isinstance(function.get('arguments'),str):
                    function['arguments']=json.loads(function['arguments'])
                call['function']=function
                calls.append(call)
            message['tool_calls']=calls
        output.append(message)
    return output


def template_options(body):
    options=body.get('chat_template_kwargs',{})
    return {'enable_thinking':body.get('enable_thinking',options.get('enable_thinking',True)),
            'reasoning_effort':body.get('reasoning_effort',options.get('reasoning_effort','low'))}


def prepare(body):
    global vision
    messages=normalize_messages(body.get('messages',[]))
    if not messages:
        raise HTTPException(400,'messages must not be empty')
    embeddings=[]
    for message in messages:
        content=message.get('content')
        if isinstance(content,list):
            replacement=[]
            for item in content:
                if item.get('type')=='image_url':
                    url=item['image_url']['url']
                    if not url.startswith('data:image/') or ';base64,' not in url:
                        raise HTTPException(400,'Images must use base64 data URLs')
                    image_bytes=base64.b64decode(url.split(',',1)[1])
                    image=Image.open(io.BytesIO(image_bytes)).convert('RGB')
                    if vision is None:
                        vision=Model.from_config(config,component='vision')
                        # Bound screenshot preprocessing to control prefill memory and latency.
                        config.vision_pp.max_pixels=1024*768
                        vision.load(device=f'cuda:{VISION_DEVICE}')
                    alias=f'[flashnext_image_{len(embeddings)}]'
                    image_key=(hashlib.sha256(image_bytes).hexdigest(),alias)
                    if image_key not in image_cache:
                        if len(image_cache)>=8:
                            image_cache.pop(next(iter(image_cache)))
                        image_cache[image_key]=vision.get_image_embeddings(tokenizer,image,text_alias=alias)
                    embedding=image_cache[image_key]
                    embeddings.append(embedding)
                    replacement.append({'type':'text','text':alias})
                elif item.get('type')=='text':
                    replacement.append(item)
                else:
                    raise HTTPException(400,'Unsupported content type')
            message['content']=replacement
    options=template_options(body)
    thinking=options['enable_thinking']
    effort=options['reasoning_effort']
    try:
        prompt=hf_tokenizer.apply_chat_template(messages,tools=body.get('tools'),tokenize=False,
            add_generation_prompt=True,enable_thinking=thinking,reasoning_effort=effort)
        ids=tokenizer.encode(prompt,encode_special_tokens=True,add_bos=False,embeddings=embeddings)
    except Exception as e:
        raise HTTPException(400,str(e)) from e
    max_tokens=int(body.get('max_completion_tokens',body.get('max_tokens',2048)))
    if max_tokens<1 or max_tokens+ids.shape[-1]>CONTEXT:
        raise HTTPException(400,f'Input {ids.shape[-1]} + output {max_tokens} exceeds context {CONTEXT}')
    stop=body.get('stop',[])
    if isinstance(stop,str):
        stop=[stop]
    temperature=float(body.get('temperature',1.0 if thinking else 0.7))
    sampler=ArgmaxSampler() if temperature==0 else ComboSampler(temperature=temperature,
        top_p=float(body.get('top_p',0.95 if thinking else 0.8)),top_k=int(body.get('top_k',20)),
        min_p=float(body.get('min_p',0)),freq_p=float(body.get('frequency_penalty',0)),
        pres_p=float(body.get('presence_penalty',0 if thinking else 1.5)))
    job=Job(ids,max_new_tokens=max_tokens,sampler=sampler,embeddings=embeddings,
            stop_conditions=['<|im_end|>','<|endoftext|>']+stop,decode_special_tokens=True)
    return job,ids.shape[-1]


def parse_output(text,tools,thinking=False):
    reasoning=None
    if '</think>' in text:
        reasoning,text=text.split('</think>',1)
        reasoning=reasoning.replace('<think>','').strip()
    elif thinking:
        # A generation limit can interrupt an unfinished reasoning block.
        reasoning,text=text.replace('<think>','').strip(),''
    calls=[]
    schemas={tool['function']['name']:tool['function'].get('parameters',{}).get('properties',{}) for tool in tools or []}
    for match in re.finditer(r'<tool_call>\s*<function=([^>]+)>(.*?)</function>\s*</tool_call>',text,re.S):
        name=match.group(1)
        if name not in schemas:
            raise HTTPException(502,'Model emitted an undeclared tool: '+name)
        arguments={}
        for parameter in re.finditer(r'<parameter=([^>]+)>\s*(.*?)\s*</parameter>',match.group(2),re.S):
            key,value=parameter.groups()
            if schemas[name].get(key,{}).get('type')!='string':
                try:
                    value=json.loads(value)
                except json.JSONDecodeError:
                    raise HTTPException(502,'Malformed tool argument: '+key)
            arguments[key]=value
        calls.append({'id':'call_'+uuid.uuid4().hex[:16],'type':'function',
                      'function':{'name':name,'arguments':json.dumps(arguments)}})
    content=re.sub(r'<tool_call>.*?</tool_call>','',text,flags=re.S).strip()
    if '<tool_call>' in content:
        raise HTTPException(502,'Truncated or malformed model tool call')
    message={'role':'assistant','content':content or None}
    if reasoning:
        message['reasoning_content']=reasoning
    if calls:
        message['tool_calls']=calls
    return message,'tool_calls' if calls else 'stop'


def run(job):
    generator.enqueue(job)
    try:
        while generator.num_remaining_jobs():
            for result in generator.iterate():
                if result['stage']=='error':
                    raise result['error']
                yield result
    finally:
        generator.clear_queue()


@app.get('/health')
def health():
    return {'status':'ready','model':'flashnext','context':CONTEXT,'busy':lock.locked(),
            'vision_mrope':model.caps.get('mrope',False),'prefill_chunk_tokens':CHUNK,
            'vision_device':VISION_DEVICE,'recurrent_cache_mb':RECURRENT_CACHE_MB,'default_thinking':True}


@app.get('/v1/models')
def models():
    return {'object':'list','data':[{'id':'flashnext','object':'model','owned_by':'local',
                                   'context_length':CONTEXT}]}


@app.get('/metrics')
def metrics():
    result=store.metrics()
    recurrent=generator.recurrent_cache
    if recurrent is not None:
        result['recurrent_cache']={'bytes':recurrent.current_size,'capacity_bytes':recurrent.max_size,
            'checkpoints':len(recurrent),'metrics':dict(recurrent.metrics)}
    return result


@app.post('/tokenize')
def tokenize(body:dict):
    if any(isinstance(m.get('content'),list) and any(i.get('type')=='image_url' for i in m['content'])
           for m in body.get('messages',[])):
        with lock:
            _,count=prepare(dict(body,max_tokens=1))
        return {'tokens':count}
    if 'messages' in body:
        text=hf_tokenizer.apply_chat_template(normalize_messages(body['messages']),
            tools=body.get('tools'),tokenize=False,add_generation_prompt=True,
            **template_options(body))
    else:
        text=body.get('text','')
    ids=hf_tokenizer.encode(text,add_special_tokens=False)
    output={'tokens':len(ids)}
    if 'truncate_to' in body:
        output['text']=hf_tokenizer.decode(ids[:int(body['truncate_to'])],skip_special_tokens=False)
    return output


@app.post('/v1/chat/completions')
async def completions(request:Request):
    body=await request.json()
    if body.get('model','flashnext')!='flashnext':
        raise HTTPException(404,'Only flashnext is served')
    identifier='chatcmpl-'+uuid.uuid4().hex
    created=int(time.time())
    def response(message,finish,usage=None,chunk=False):
        value={'id':identifier,'object':'chat.completion.chunk' if chunk else 'chat.completion',
               'created':created,'model':'flashnext','choices':[{'index':0,
                'delta' if chunk else 'message':message,'finish_reason':finish}]}
        if usage is not None:
            value['usage']=usage
        return value
    def execute(stream):
        with lock:
            torch.set_grad_enabled(False)
            job,input_tokens=prepare(body)
            text=''
            last={}
            start=time.perf_counter()
            first=None
            progress_at=0
            buffered=bool(body.get('tools')) or body.get('enable_thinking',body.get('chat_template_kwargs',{}).get('enable_thinking',True))
            if stream:
                yield response({'role':'assistant'},None,chunk=True)
            for result in run(job):
                now=time.perf_counter()
                if now-progress_at>=15 or result.get('eos'):
                    progress={'id':identifier,'stage':result['stage'],'seconds':now-start,
                              'input_tokens':input_tokens,'current_tokens':result.get('curr_progress'),
                              'target_tokens':result.get('max_progress'),'output_characters':len(text)}
                    (ROOT/'receipts/current-request.json').write_text(json.dumps(progress)+'\n')
                    progress_at=now
                if result['stage']=='streaming':
                    piece=result.get('text','')
                    text+=piece
                    if first is None and piece:
                        first=time.perf_counter()-start
                    if stream and piece and not buffered:
                        yield response({'content':piece},None,chunk=True)
                if result.get('eos'):
                    last=result
            message,finish=parse_output(text,body.get('tools'),
                body.get('enable_thinking',body.get('chat_template_kwargs',{}).get('enable_thinking',True)))
            if last.get('eos_reason')=='max_new_tokens' and finish!='tool_calls':
                finish='length'
            output_tokens=int(last.get('new_tokens',tokenizer.encode(text,encode_special_tokens=True).shape[-1]))
            usage={'prompt_tokens':input_tokens,'completion_tokens':output_tokens,'total_tokens':input_tokens+output_tokens}
            receipt={'id':identifier,'time_to_first_text':first,'seconds':time.perf_counter()-start,
                     'usage':usage,'finish_reason':finish,'offload':store.metrics(),
                     'prefill_seconds':last.get('time_prefill'),
                     'decode_seconds':last.get('time_generate'),'cached_tokens':last.get('cached_tokens'),
                     'peak_gpu_allocated':[torch.cuda.max_memory_allocated(i) for i in range(2)]}
            with (ROOT/'receipts/requests.jsonl').open('a') as f:
                f.write(json.dumps(receipt)+'\n')
            if stream:
                if buffered:
                    if message.get('tool_calls'):
                        message['tool_calls']=[dict(call,index=i) for i,call in enumerate(message['tool_calls'])]
                    yield response(message,None,chunk=True)
                yield response({},finish,usage,chunk=True)
            else:
                yield response(message,finish,usage)
    if body.get('stream'):
        def events():
            for value in execute(True):
                yield 'data: '+json.dumps(value)+'\n\n'
            yield 'data: [DONE]\n\n'
        return StreamingResponse(events(),media_type='text/event-stream')
    # Avoid blocking the ASGI loop so health probes remain responsive during inference.
    from starlette.concurrency import run_in_threadpool
    return await run_in_threadpool(lambda:next(execute(False)))


if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='0.0.0.0',port=30260)
