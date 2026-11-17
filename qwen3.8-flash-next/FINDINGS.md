# Flash-Next CUDA port findings

Installation and validation are complete. The full quantized model runs on two RTX 3090 24 GiB GPUs with 31 GiB host RAM. The CUDA adapter stages selected EXL3 experts through bounded disk/RAM/GPU caches; no selected experts are discarded. Native attention, routing, shared experts, hyperconnections, PLE and image encoding are preserved.

Pinned upstream: `30d1b5b94d15f020ed926350d37341d7269d3692`. Model: `turboderp/Qwen3.8-Flash-Next-exl3`, revision `69e33439ae950f17bcbe95c98f117d80f759ab6d`, variant `3.05bpw_h5_ng5`. All 25 checkpoint checksums verified; 85.14 GB total. Runtime source commit: `079b4e0`; deployed file hashes match local source.

Independent expert checks: 72 passed across both GPUs and cache reloads. Whole native MoE layer comparisons at normal amplitude, 1/4/16/128/1024 rows, two repeats: identical routes and weights, worst normalized RMS error 0.234%, minimum cosine 0.999997, maximum absolute error 0.002274. Native FP16 kernels differ numerically; earlier strict 1e-4 absolute checks failed and remain as diagnostics. Vacant-slot prefill cache admission passed the numerical comparison, capacity assertions and preservation of GPU/host resident entries.

Image MRoPE and QSA query/pooled-key rotations fixed. Independent HF-equation checks across image spans, permuted pages and decode offsets matched exactly.

The frozen greedy/nonthinking matrix completed all 32 cells: 21 passed. Capacities: 2K/4K/8K/16K/32K/64K/128K/256K. Largest actual input: 256211 tokens. Browser greedy completion: 0/8; repeated edits could corrupt earlier verified artifacts. Separate native-thinking follow-up: 7/8 passed, from 4K through 256K; 2K failed to finish. Final 128K/256K browser tasks took 495.5/523.2 s. Paired cold-process 128K prefill improved from 524.8 to 272.0 s; OS page cache was uncontrolled.

Final everyday profile: 65536 positions, chunk4096, GPU expert caches10/20 GiB, host expert cache1.5 GiB, recurrent checkpoints4 GiB, visionGPU0, native thinking enabled. Long profile: 262144 positions, chunk8192, GPU expert caches4/19 GiB, visionGPU1. No container swap. Final seven API generation checks, nested template equivalence and error handling passed. Fresh final64K coding and screenshot tasks passed in178.2/239.5 s. Final screenshot task used14 model requests and13 tool calls within a32-round allowance; original primary grading and failures remain unchanged.

Fixtures execute real coding tests, HTTP/API/SQLite repairs, DOM browser edits, and screenshot-only Chromium mouse/keyboard/CSV export. OS desktop-app control was not evaluated. Context filler is synthetic repository excerpts; single trials are diagnostic evidence, not broad task accuracy.

Rig root: `/home/isa/Experiments/qwen38-flash-next-b70-fit`. API: `http://127.0.0.1:30260/v1`, model `flashnext`. Mac tunnel: `http://127.0.0.1:18060/v1`. Final health is ready and idle. Docker starts on boot and the container uses restart-unless-stopped. Previous model and Flash-Next containers are preserved and stopped. Editable source is outside the iCloud dataless workspace at `/Users/ibrahimsaitakarcesme/LLMRig-flashnext-work`.

See RESULTS.md for all task rows, latency and memory measurements, settings, limits and receipt locations. Hardware monitoring was stopped after final verification. No files were deleted and no commits pushed.
