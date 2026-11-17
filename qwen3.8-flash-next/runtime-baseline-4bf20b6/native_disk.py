"""Exact selected-expert CUDA offload for native ExLlamaV3 Flash-Next.

Keeps checkpoint tensors on disk, uses bounded GPU and host LRUs, and
preserves native routing, shared experts, attention, hyperconnections and PLE.
The first version deliberately runs eagerly: disk misses never mask experts.
"""
import collections
import concurrent.futures
import json
import os
from pathlib import Path
import struct
import threading
import time

import torch
from exllamav3.modules.block_sparse_mlp import BlockSparseMLP
from exllamav3.modules.quant.exl3 import LinearEXL3
from exllamav3.util.device_copy import to_device
from exllamav3.ext import exllamav3_ext as ext

DTYPES = {'I16': torch.int16, 'I32': torch.int32, 'I64': torch.int64,
          'F16': torch.float16, 'BF16': torch.bfloat16, 'F32': torch.float32}
STORE = None


class DiskExperts:
    def __init__(self, root, gpu_gib=(12, 20), host_gib=2, workers=4):
        self.root = Path(root)
        self.index = json.loads((self.root / 'model.safetensors.index.json').read_text())['weight_map']
        self.expert_keys = collections.defaultdict(lambda: collections.defaultdict(list))
        for name in self.index:
            if '.mlp.experts.' in name:
                key, projection, suffix = name.rsplit('.', 2)
                self.expert_keys[key][projection].append(name)
        self.headers = {}
        self.lock = threading.Lock()
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
        self.gpu = [collections.OrderedDict(), collections.OrderedDict()]
        self.host = collections.OrderedDict()
        self.gpu_bytes = [0, 0]
        self.host_bytes = 0
        self.gpu_cap = [int(x * 1024**3) for x in gpu_gib]
        self.host_cap = int(host_gib * 1024**3)
        self.stats = collections.Counter()

    def header(self, filename):
        with self.lock:
            if filename not in self.headers:
                with (self.root / filename).open('rb') as f:
                    raw = f.read(8)
                    if len(raw) != 8:
                        raise RuntimeError('Incomplete checkpoint: ' + filename)
                    n = struct.unpack('<Q', raw)[0]
                    self.headers[filename] = (8 + n, json.loads(f.read(n)))
            return self.headers[filename]

    def read(self, key):
        start = time.perf_counter()
        keys = self.expert_keys[key]
        if set(keys) != {'gate_proj', 'up_proj', 'down_proj'}:
            raise KeyError('Incomplete expert: ' + key)
        # Header/index metadata only; reading a single expert never loads its shard.
        tensors = {proj: {} for proj in keys}
        files = collections.defaultdict(list)
        for proj, names in keys.items():
            if not names:
                raise KeyError('Missing expert projection: ' + key + '.' + proj)
            for name in names:
                base, head = self.header(self.index[name])
                files[self.index[name]].append((proj, name.rsplit('.', 1)[1], base, head[name]))
        size = 0
        for filename, entries in files.items():
            # Merge adjacent tensors to avoid one read syscall per sign/scaling tensor.
            entries.sort(key=lambda x: x[3]['data_offsets'][0])
            groups = []
            for entry in entries:
                if groups and groups[-1][-1][3]['data_offsets'][1] == entry[3]['data_offsets'][0]:
                    groups[-1].append(entry)
                else:
                    groups.append([entry])
            fd = os.open(self.root / filename, os.O_RDONLY)
            try:
                for group in groups:
                    lo = group[0][3]['data_offsets'][0]
                    hi = group[-1][3]['data_offsets'][1]
                    raw = bytearray(os.pread(fd, hi - lo, group[0][2] + lo))
                    if len(raw) != hi - lo:
                        raise RuntimeError('Short checkpoint read: ' + filename)
                    size += len(raw)
                    for proj, suffix, base, desc in group:
                        a, b = desc['data_offsets']
                        dtype = DTYPES[desc['dtype']]
                        itemsize = torch.empty((), dtype=dtype).element_size()
                        tensors[proj][suffix] = torch.frombuffer(
                            raw, dtype=dtype, count=(b-a)//itemsize, offset=a-lo).reshape(desc['shape'])
            finally:
                os.close(fd)
        return tensors, size, time.perf_counter() - start

    def owner(self, key):
        # Stable ownership spreads every layer's expert cache across the two cards.
        return int(key.rsplit('.', 1)[1]) % 2

    def cached(self, key):
        return key in self.gpu[self.owner(key)] or key in self.host

    def get(self, key, config, future=None, admit=True, fill_unused=False):
        device = self.owner(key)
        cache = self.gpu[device]
        self.stats['expert_requests'] += 1
        if key in cache:
            self.stats['gpu_hits'] += 1
            cache.move_to_end(key)
            return cache[key][0]
        if key in self.host:
            self.stats['host_hits'] += 1
            tensors, size = self.host[key]
        else:
            tensors, size, elapsed = future.result() if future else self.read(key)
            self.stats['disk_reads'] += 1
            self.stats['disk_bytes'] += size
            self.stats['io_seconds'] += elapsed
        # Cold prefill can use vacant slots without flushing hot decoder weights.
        if fill_unused and not admit and self.gpu_bytes[device] + size <= self.gpu_cap[device]:
            admit = True
            self.stats['prefill_cache_admissions'] += 1
        if key in self.host:
            if admit:
                self.host.pop(key)
                self.host_bytes -= size
            else:
                # A temporary prefill upload must not consume its reusable host entry.
                self.host.move_to_end(key)
        while admit and cache and self.gpu_bytes[device] + size > self.gpu_cap[device]:
            # Eviction must wait for all kernels that refer to the victim's tensors.
            torch.cuda.synchronize(device)
            old_key, (old_modules, old_size) = cache.popitem(last=False)
            self.gpu_bytes[device] -= old_size
            if old_size <= self.host_cap:
                old_tensors = {p: {s: t.cpu() for s, t in m.get_tensors(p).items()}
                               for p, m in old_modules.items()}
                old_tensors = {p: {s.rsplit('.', 1)[1]: t for s,t in ts.items()}
                               for p,ts in old_tensors.items()}
                while self.host and self.host_bytes + old_size > self.host_cap:
                    _, (_, n) = self.host.popitem(last=False)
                    self.host_bytes -= n
                self.host[old_key] = (old_tensors, old_size)
                self.host_bytes += old_size
            del old_modules
        modules = {}
        with torch.cuda.device(device):
            for proj, values in tensors.items():
                # Clone CPU scalar metadata so a tiny view cannot retain a full disk buffer.
                values = {s: t.to(device) if s not in ('mul1', 'mcg') else t.clone() for s,t in values.items()}
                shape = values['trellis'].shape
                modules[proj] = LinearEXL3(config, shape[0]*16, shape[1]*16,
                                           **values, key=key + '.' + proj)
        if admit and size <= self.gpu_cap[device]:
            cache[key] = (modules, size)
            self.gpu_bytes[device] += size
        return modules

    def apply(self, layer, shape, y, selected, weights, params):
        if os.environ.get('FLASHNEXT_FUSED_DECODE','0') == '1' and (y.shape[0] <= 8 or os.environ.get('FLASHNEXT_FUSED_PREFILL','0') == '1'):
            from fused_disk import apply
            return apply(self,layer,shape,y,selected,weights,params)
        started = time.perf_counter()
        ids = selected.cpu()
        chosen = sorted(torch.unique(ids).tolist())
        if any(e < 0 or e >= layer.num_experts for e in chosen):
            raise RuntimeError('Invalid routed expert ID')
        routes = {e: (ids == e).nonzero(as_tuple=True) for e in chosen}
        keys = {e: layer.key + '.experts.' + str(e) for e in chosen}
        pending = collections.deque(e for e in chosen if not self.cached(keys[e]))
        futures = {}
        def fill():
            while pending and len(futures) < 8:
                e = pending.popleft()
                futures[e] = self.pool.submit(self.read, keys[e])
        fill()
        sources = {}
        out = torch.zeros((y.shape[0], layer.expert_size), device=y.device, dtype=torch.float32)
        for e in chosen:
            key = keys[e]
            dev = self.owner(key)
            modules = self.get(key, layer.config, futures.pop(e, None))
            fill()
            rows, slots = routes[e]
            if dev not in sources:
                sources[dev] = to_device(y.contiguous().half(), torch.device('cuda', dev))
            with torch.cuda.device(dev):
                x = sources[dev].index_select(0, rows.to(dev)).contiguous()
                gate = modules['gate_proj'].forward(x, {}, out_dtype=torch.float16)
                up = modules['up_proj'].forward(x, {}, out_dtype=torch.float16)
                activation = torch.empty_like(up)
                ext.silu_mul(gate, up, activation, 0.0)
                result = modules['down_proj'].forward(activation, {}, out_dtype=torch.float32)
            result = to_device(result, y.device)
            result = result * weights[rows.to(weights.device), slots.to(weights.device)].float().unsqueeze(-1)
            out.index_add_(0, rows.to(y.device), result)
        self.stats['moe_calls'] += 1
        self.stats['moe_seconds'] += time.perf_counter() - started
        self.stats['masked_experts'] = 0
        return out.reshape(shape)

    def metrics(self):
        return {'counters': dict(self.stats), 'gpu_cache_bytes': self.gpu_bytes,
                'host_cache_bytes': self.host_bytes, 'gpu_caps': self.gpu_cap,
                'host_cap': self.host_cap}


def install(root, gpu_gib=(12,20), host_gib=2):
    global STORE
    STORE = DiskExperts(root, gpu_gib, host_gib)
    original_load = BlockSparseMLP.load
    original_forward = BlockSparseMLP.cpu_offload_forward
    def load(self, device, **kwargs):
        if not self.key.startswith('model.language_model.layers.'):
            return original_load(self, device, **kwargs)
        self.device = torch.device(device)
        expert_modules = set(self.gates + self.ups + self.downs)
        for module in self.modules:
            if module not in expert_modules:
                module.load(device, **kwargs)
        # Flash-Next uses standard routing without correction bias or per-expert scale.
        self.load_routing(**kwargs)
        self.cpu_offload = True  # reuse native dispatch hook; compute happens on CUDA
        print('Exact disk-backed CUDA experts:', self.key, flush=True)
    def forward(self, shape, y, selected_experts, routing_weights, params):
        if self.key.startswith('model.language_model.layers.'):
            return STORE.apply(self, shape, y, selected_experts, routing_weights, params)
        return original_forward(self, shape, y, selected_experts, routing_weights, params)
    BlockSparseMLP.load = load
    BlockSparseMLP.cpu_offload_forward = forward
    return STORE
