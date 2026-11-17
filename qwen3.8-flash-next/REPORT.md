# Flash-Next installation compatibility report

User-facing date: October 7, 2026 (Europe/Luxembourg). Remote receipts retain the rig's own UTC clock.

Status: source staged on LLMRig; runnable installation and model evaluation blocked.

## Verified installation state

Upstream source: https://github.com/0xSero/qwen38-flash-next-b70-offload

Pinned commit: `30d1b5b94d15f020ed926350d37341d7269d3692`.

Rig checkout: `/home/isa/Experiments/qwen38-flash-next-b70-fit/upstream`.

The rig has two NVIDIA RTX 3090 GPUs (24 GiB each), 31 GiB reported RAM, a Kingston NV3 SSD, and 163 GB available disk space. No Intel GPU is present. Published results use an Intel Arc Pro B70 and a four-drive NVMe array; those results are not measurements of this rig.

The launch script requires Intel XPU execution, xe SVM, a private local image ID `24c872759256`, `bench/xpu_run.sh`, a packed expert store, and `_moe_a8.so`. The image and required data are absent on this rig. The wrapper, compiled MoE library, its source/build recipe, and expert packing utility are not supplied in this checkout. The script also hardcodes upstream home paths and CPU affinity. It cannot be made runnable here by changing `--device xpu` to `cuda`.

The installed CUDA SGLang image contains Qwen4 architecture modules and EXL3 MoE support, but its plugin does not provide the published Intel NVMe/RAM/VRAM expert tier. The existing DeepSeek CUDA offload engine is architecture-specific. Neither is a verified Flash-Next offload runtime for these two GPUs and 32 GB RAM. A CUDA implementation and memory-layout validation are prerequisite work.

Hugging Face metadata and configuration were fetched without downloading weights. Model revision: `69e33439ae950f17bcbe95c98f117d80f759ab6d`; architecture `Qwen4ExpForConditionalGeneration`; model maximum position embeddings 262144. The upstream launcher defaults to a 65536-token context. Its 131072-token cache budget in the README is an aggregate budget, not evidence that a single 131072-token request works.

Read-only checks are saved in `preflight.json`. The expected endpoint on port 30260 refuses connections. No model generations were performed. The active `clef-pi-qwen` service remained running.

## Requested task evaluation

`task-matrix.json` prepares 32 task specifications: coding, multi-tool agent diagnosis, desktop computer use, and browser use at context capacities 2K, 4K, 8K, 16K, 32K, 64K, 128K, and 256K. The last two require separately validated server configurations. “Every context” is interpreted as a power-of-two sweep through the model's configured maximum.

Tasks cover a React stale-response bug with executable regressions; a broken frontend/API deployment with a real SQLite round trip; sorting/filtering/saving invoices through a desktop application; and filtering/paginating/updating issues through a browser with an injection decoy. Each specifies an isolated environment and artifact-based success criteria. These are prepared specifications, not implemented fixtures or executed benchmarks.

All 32 cells are blocked before generation. There are no measured speed, task-success, tool-use, screenshot-understanding, or long-context scores. Benchmarking the already installed smaller Qwen model would not answer the requested Flash-Next experiment.

Next prerequisite: obtain a reproducible complete Intel runtime plus suitable Intel hardware, or implement and validate a CUDA expert-offload runtime for Flash-Next. Then create the isolated fixtures, run a short smoke generation and tool test, and execute the matrix with exact tokenizer counts and saved tool/artifact traces.
