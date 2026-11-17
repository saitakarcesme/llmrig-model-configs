"""Local Clef decision endpoint; retains Cloudflare's joint schema head."""
import argparse, importlib.util, json, sys, time
from pathlib import Path
import torch
from fastapi import FastAPI, HTTPException
import uvicorn
from transformers import BitsAndBytesConfig

p=argparse.ArgumentParser();p.add_argument('--model',default='clef-flash');p.add_argument('--precision',choices=['bf16','nf4'],default='nf4');p.add_argument('--port',type=int,default=18031);a=p.parse_args()
path=Path('/models')/a.model
sys.path.insert(0,str(path))
from joint_schema_model import load_release_model, systemone
kw={}
if a.precision=='nf4':
    kw['quantization_config']=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16,llm_int8_skip_modules=['lm_head'])
started=time.perf_counter()
model,processor=load_release_model(path,device='cuda:0',**kw)
torch.cuda.synchronize()
load_s=time.perf_counter()-started
app=FastAPI()
@app.get('/health')
def health():
    return {'model':a.model,'precision':a.precision,'load_seconds':load_s,'vram_allocated_mb':torch.cuda.memory_allocated()/2**20}
@app.post('/v1/systemone')
def decide(body:dict):
    if body.get('model',a.model)!=a.model: raise HTTPException(400,'Model mismatch')
    body['model']=a.model
    if body.get('images') or body.get('videos'): raise HTTPException(400,'This local endpoint currently accepts text/JSON only')
    try:
        torch.cuda.synchronize();t=time.perf_counter()
        response=systemone(model,processor,body,max_length=4096)
        torch.cuda.synchronize()
        response['metrics']={'inference_ms':(time.perf_counter()-t)*1000,'precision':a.precision,'peak_vram_mb':torch.cuda.max_memory_allocated()/2**20}
        return response
    except (ValueError,KeyError,TypeError) as e: raise HTTPException(400,str(e))
uvicorn.run(app,host='0.0.0.0',port=a.port,workers=1)
