import argparse
import json
from pathlib import Path
import time
import torch
from exllamav3 import Config, Model, Tokenizer, Cache, Generator, ArgmaxSampler
import native_disk

parser = argparse.ArgumentParser()
parser.add_argument('--model', default='/work/models/flashnext-3.05bpw')
parser.add_argument('--context', type=int, default=4096)
parser.add_argument('--chunk', type=int, default=256)
parser.add_argument('--gpu-cache', default='0.5,1')
parser.add_argument('--host-cache', type=float, default=0.25)
parser.add_argument('--tokens', type=int, default=64)
parser.add_argument('--prompt', default='Write a Python function add(a, b) that returns their sum. Return only the function.')
parser.add_argument('--receipt', default='/work/receipts/native-smoke.json')
args = parser.parse_args()
torch.set_num_threads(8)
torch.set_grad_enabled(False)
store = native_disk.install(args.model, tuple(map(float,args.gpu_cache.split(','))), args.host_cache)
started = time.perf_counter()
config = Config.from_directory(args.model)
model = Model.from_config(config)
tokenizer = Tokenizer(config)
cache = Cache(model, max_num_tokens=args.context, max_batch_size=1)
model.load(device='cuda:0', max_chunk_size=args.chunk, verbose=True)
print('Model loaded', time.perf_counter()-started, flush=True)
generator = Generator(model=model, cache=cache, tokenizer=tokenizer, max_batch_size=1,
                      max_chunk_size=args.chunk, recurrent_cache_size=256*1024**2)
prompt = model.default_chat_prompt(args.prompt) + '<think>\n\n</think>\n\n'
generation_start = time.perf_counter()
completion, result = generator.generate(prompt, max_new_tokens=args.tokens, sampler=ArgmaxSampler(),
    encode_special_tokens=True, completion_only=True, return_last_results=True,
    stop_conditions=['<|im_end|>', '<|endoftext|>'])
receipt = {'status':'generated', 'prompt': args.prompt, 'completion': completion,
           'generation_seconds': time.perf_counter()-generation_start,
           'load_seconds': generation_start-started, 'context_capacity':args.context,
           'model_revision':'69e33439ae950f17bcbe95c98f117d80f759ab6d',
           'result': result, 'offload':store.metrics(),
           'gpu_peak_allocated':[torch.cuda.max_memory_allocated(i) for i in range(2)]}
Path(args.receipt).write_text(json.dumps(receipt, indent=2, default=str)+'\n')
print(json.dumps(receipt, indent=2, default=str), flush=True)
