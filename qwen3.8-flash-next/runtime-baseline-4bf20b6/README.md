# Flash-Next on two RTX 3090 GPUs

This CUDA runtime uses the Intel B70 offload repository as its starting design, while reusing native ExLlamaV3 Flash-Next attention, routing, hyperconnections, shared experts, PLE disk lookup and vision support. Selected routed experts are loaded exactly from the original EXL3 checkpoint. Cache misses wait for weights; no selected experts are discarded.

`vision_positions.py` fixes missing image MRoPE wiring and applies image frequencies to QSA query and pooled-key rotations. The pinned native indexer used flat cache positions. Text requests retain its fused path; image requests use the checked native reference plane update and bypass the incompatible attention graph.

Upstream: https://github.com/0xSero/qwen38-flash-next-b70-offload, commit `30d1b5b94d15f020ed926350d37341d7269d3692`.

Model: `turboderp/Qwen3.8-Flash-Next-exl3`, revision `69e33439ae950f17bcbe95c98f117d80f759ab6d` (variant `3.05bpw_h5_ng5`; higher-bit head/ngram). Original files occupy 85.14 GB; all 25 downloaded file checksums verified.

## Runtime

Rig root: `/home/isa/Experiments/qwen38-flash-next-b70-fit`.

Base image: `ghcr.io/0xsero/sglang-exl3@sha256:84f75f3424c99a3d63392a4e0348292bdeba9cf7efba2ff1aa9b85c8fc0131e8`. It contains PyTorch 2.13.0/CUDA 13.0, ExLlamaV3 1.5.1 and Transformers 5.12.1. This runtime directly uses ExLlamaV3 rather than the SGLang server.

```sh
bash /home/isa/Experiments/qwen38-flash-next-b70-fit/runtime/install.sh
bash /home/isa/Experiments/qwen38-flash-next-b70-fit/runtime/launch.sh
curl http://127.0.0.1:30260/health
```

The launcher preserves any existing Flash-Next container under a timestamped name. The earlier `clef-pi-qwen` container is preserved, stopped to release both GPUs. To restore it, stop `flashnext-api` and run `docker start clef-pi-qwen`.

Local API base: `http://127.0.0.1:30260/v1`; model: `flashnext`. Chat completions accept standard messages, tools, streaming, sampling parameters and base64 image URLs. `enable_thinking` defaults to true; `reasoning_effort` supports low, medium and xhigh. Vision currently handles images, not video. Thinking responses and tool calls are buffered until completion and parsing; nonthinking plain text streams incrementally. One model request executes at a time.

```sh
curl http://127.0.0.1:30260/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"flashnext","messages":[{"role":"user","content":"Fix this race condition..."}],"max_tokens":1024,"temperature":0,"enable_thinking":false,"stream":true}'
```

## Validation

The host evaluation runner requires Python, Node.js, `/usr/bin/chromium`, and bubblewrap. Create its isolated environment with `python3 -m venv eval-venv`, then install `httpx==0.28.1` and `playwright==1.63.0` using `eval-venv/bin/pip`. It uses the installed Chromium executable.

`check_disk_experts.py` compares disk-loaded CUDA tensors/kernels on both GPUs with independently loaded safetensors, including cache reloads. `check_moe_layer.py` compares a complete offloaded layer against the resident native layer. Eager and fused implementations have separate saved receipts.

`agent_eval.py` performs real tool loops against disposable coding, HTTP/API/SQLite, DOM browser and screenshot-driven invoice fixtures. Coding execution runs inside a bubblewrap sandbox. The computer-use fixture is Chromium with actual screenshot, mouse, keyboard and download actions; it does not establish OS-desktop application control. Context filler consists of explicitly synthetic repository excerpts, and the test directory records all tool calls and artifacts.

```sh
./eval-venv/bin/python runtime/agent_eval.py --contexts 2048,4096,8192,16384,32768,65536 --coordinates normalized
```

Each context capacity includes input, tool schemas, screenshots, tool observations and generation. Initial background input reserves space for subsequent actions. A single passing trial is diagnostic evidence, not a broad accuracy benchmark.

The 262144-position profile has completed occupied-context coding, API, browser and screenshot trials, including a request with 256211 input tokens. Use the following profile for 128K/256K; switching profiles restarts the service.

```sh
FLASHNEXT_CONTEXT=262144 FLASHNEXT_CHUNK=8192 FLASHNEXT_GPU_CACHE=4,19 FLASHNEXT_VISION_DEVICE=1 \
  bash /home/isa/Experiments/qwen38-flash-next-b70-fit/runtime/launch.sh
```

Return to the 64K profile with `bash runtime/launch.sh` from the rig root. Thinking defaults use temperature 1.0, top_p 0.95, top_k 20 and presence penalty 0. Nonthinking defaults use 0.7, 0.8, 20 and 1.5. Explicit temperature zero selects greedy decoding. These follow the [official model guidance](https://huggingface.co/Qwen/Qwen3.8-Flash-Next#best-practices). Both direct options and `chat_template_kwargs` are accepted.

## Files

- `native_disk.py`: bounded disk/RAM/GPU caches and native model integration.
- `fused_disk.py`: dynamic expert pointer tables for existing fused CUDA decode/prefill kernels.
- `server.py`: chat API, tool parser, vision encoder and request metrics.
- `vision_positions.py`: image-position corrections for generation and the QSA indexer.
- `eval_fixtures.py`, `agent_eval.py`: executable fixture tasks and context evaluation.
- `launch.sh`: repeatable model launch.

See [RESULTS.md](RESULTS.md) for the task matrix, performance, limitations and saved evidence.

From this Mac, an SSH tunnel is currently available at `http://127.0.0.1:18060/v1`. To recreate it: `ssh -N -L 18060:127.0.0.1:30260 isa@<rig-tailscale-ip>`. Configure an OpenAI chat client with that base URL and model `flashnext`; the local service does not require an API key. Tool execution belongs to the client; the included evaluation runner demonstrates a complete tool loop.
