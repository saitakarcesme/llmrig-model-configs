"""One GPU job per disposable container. Models and request data stay local."""
import json,os,sys,time,fcntl
LEASE=open("/gpu.lock","a")
fcntl.flock(LEASE,fcntl.LOCK_SH)
from pathlib import Path
JOB=Path('/job'); MODELS=Path('/models')

def audio(req):
    from faster_whisper import WhisperModel
    name={'whisper-large-v3':'whisper-large-v3','BuzzASR/turkish':'buzz-turkish-ct2'}[req['model']]
    model=WhisperModel(str(MODELS/name),device='cuda',compute_type='int8_float16',cpu_threads=4,num_workers=1,local_files_only=True)
    segments,info=model.transcribe(str(JOB/'input'),language=req.get('language') or None,task='transcribe',beam_size=5,vad_filter=True,initial_prompt=req.get('prompt') or None)
    rows=[{'id':s.id,'start':s.start,'end':s.end,'text':s.text,'avg_logprob':s.avg_logprob,'no_speech_prob':s.no_speech_prob} for s in segments]
    return {'text':''.join(s['text'] for s in rows).strip(),'language':info.language,'duration':info.duration,'segments':rows,'model':req['model']}

def ocr(req):
    import torch
    from PIL import Image
    import pymupdf
    from transformers import AutoProcessor,AutoModelForImageTextToText
    torch.set_num_threads(4)
    model=AutoModelForImageTextToText.from_pretrained(str(MODELS/'paddleocr-vl-1.6'),dtype=torch.bfloat16,local_files_only=True).to('cuda').eval()
    processor=AutoProcessor.from_pretrained(str(MODELS/'paddleocr-vl-1.6'),local_files_only=True)
    prompts={'ocr':'OCR:','formula':'Formula Recognition:','table':'Table Recognition:','chart':'Chart Recognition:','spotting':'Spotting:'}
    pages=[]
    if req['is_pdf']:
        doc=pymupdf.open(JOB/'input')
        for i in req['page_indices']:
            page=doc[i];scale=min(2,2048/max(page.rect.width,page.rect.height));pix=page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False)
            pages.append((i+1,Image.frombytes('RGB',(pix.width,pix.height),pix.samples)))
    else:
        im=Image.open(JOB/'input');im.load();pages=[(1,im.convert('RGB'))]
    results=[]
    for number,im in pages:
        original=list(im.size);im.thumbnail((2048,2048))
        messages=[{'role':'user','content':[{'type':'image','image':im},{'type':'text','text':prompts[req['task']]}]}]
        inputs=processor.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,return_dict=True,return_tensors='pt',images_kwargs={'size':{'shortest_edge':112896,'longest_edge':2048*28*28 if req['task']=='spotting' else 1280*28*28}}).to('cuda')
        with torch.inference_mode():out=model.generate(**inputs,max_new_tokens=req['max_tokens'],do_sample=False)
        generated=out[0][inputs['input_ids'].shape[-1]:]
        results.append({'page':number,'text':processor.decode(generated,skip_special_tokens=True),'generated_tokens':len(generated),'hit_output_limit':len(generated)>=req['max_tokens'],'source_size':original,'submitted_image_size':list(im.size)})
    return {'model':'PaddleOCR-VL-1.6','task':req['task'],'pages':results,'pipeline':'transformers recognition; no layout detector','coordinates':'Spotting is raw model output; interpret coordinates against the submitted image and the model output format.'}

def main():
    req=json.loads((JOB/'request.json').read_text());start=time.monotonic()
    result=audio(req) if req['operation']=='audio' else ocr(req)
    result['processing_seconds']=time.monotonic()-start
    (JOB/'result.json').write_text(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
