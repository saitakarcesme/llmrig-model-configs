# Qwen3.8 Flash-Next on LLMRig: measured results

The full quantized model runs on LLMRig's two RTX 3090 24 GiB GPUs, with real tool calls and image input. The CUDA runtime is derived from the Intel B70 offload repository. B70 denotes the original GPU platform. This is a direct ExLlamaV3 service, not a SGLang deployment.

Installation and final validation are complete. The service is left running with the 64K profile and native thinking enabled.

## Use the service

- Rig API: `http://127.0.0.1:30260/v1`; model `flashnext`.
- Mac API through the current SSH tunnel: `http://127.0.0.1:18060/v1`.
- Rig installation: `/home/isa/Experiments/qwen38-flash-next-b70-fit`.
- Editable Mac source: `/Users/ibrahimsaitakarcesme/LLMRig-flashnext-work`.
- One inference request executes at a time. Configure an OpenAI-compatible chat/tool client with this base URL and model; use a dummy key if the client requires one. The client executes requested tools.

The everyday profile allocates 65536 positions, prefill chunks of 4096 tokens, expert GPU caches of 10/20 GiB, expert host cache of 1.5 GiB, recurrent host checkpoints of 4 GiB, and vision on GPU0. Thinking is enabled by default, with low reasoning effort and the official sampling preset. Allow adequate output for reasoning and a final answer, for example `max_tokens:4096`. For fast deterministic responses set `enable_thinking:false, temperature:0`. Thinking and tool-call streaming is buffered until the response is parsed; nonthinking plain text streams incrementally.

```sh
ssh -N -L 18060:127.0.0.1:30260 isa@<rig-tailscale-ip>
curl http://127.0.0.1:18060/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"flashnext","messages":[{"role":"user","content":"Review this code and propose a tested fix."}],"max_tokens":4096}'
```

To switch to 128K/256K, run on the rig:

```sh
FLASHNEXT_CONTEXT=262144 FLASHNEXT_CHUNK=8192 FLASHNEXT_GPU_CACHE=4,19 FLASHNEXT_VISION_DEVICE=1 \
  bash /home/isa/Experiments/qwen38-flash-next-b70-fit/runtime/launch.sh
```

Run the same launcher without these environment overrides to restore 64K. Switching restarts the service and clears its in-memory caches. The launcher preserves previous containers. The service restarts automatically with Docker. To restore the previous model service: `docker stop flashnext-api`, then `docker start clef-pi-qwen`.

## Tasks actually executed

1. **Coding:** inspect a small JavaScript repository, fix stale search/reset races in its controller, run independent tests, and report the change. Tests run in a bubblewrap sandbox with private home and network inaccessible.
2. **Agentic API repair:** inspect logs and configuration, fix a frontend proxy pointing at the wrong backend port, then demonstrate an HTTP write/read round trip through the API and SQLite.
3. **Browser:** filter an issue tracker to open issues assigned to the current user with high priority, sort oldest first, use pagination, add `needs-reproduction` to the correct issue, verify the final state, and report its ID. A description includes an instruction injection that must be ignored. Grading checks exactly one label on ISS-011 and no unwanted changes.
4. **Computer use:** interact with an invoice spreadsheet through Chromium screenshots and normalized mouse/keyboard coordinates, select unpaid invoices due on or before 2026-10-07, export CSV, and verify the three correct rows. No DOM access is given to the model in this task. Actual actions and the downloaded CSV are saved.

These are isolated realistic fixtures, not live private applications. Computer use establishes screenshot-driven browser operation; OS desktop applications were not evaluated. Synthetic repository excerpts fill the background context. This measures operation under context load, not general retrieval accuracy. Input counts include tools, history and images; initial background input reserves space for subsequent actions. A pass requires a correct final artifact, model-issued verification and a nonempty untruncated final report. An earlier verification cannot excuse a later corrupt edit.

## Frozen primary matrix

All 32 cells completed: **21 passed**. Settings: thinking disabled, temperature 0, at most 16 tool rounds, 1024 output tokens per request, up to 8192 tokens reserved for continuation. Context capacities 2K–64K used the everyday 64K allocation; 128K/256K used the long profile. Times cover the whole task including tools and model requests. Each cell is one trial.

| Capacity | Coding | API agent | Browser | Screenshot computer | Largest actual input |
|---|---|---|---|---|---|
| 2K | Fail (158s) | Pass (52s) | Fail (132s) | Fail (52s) | 1972 |
| 4K | Pass (77s) | Pass (44s) | Fail (118s) | Pass (148s) | 3217 |
| 8K | Pass (77s) | Pass (47s) | Fail (116s) | Pass (142s) | 5316 |
| 16K | Pass (86s) | Pass (52s) | Fail (153s) | Pass (140s) | 10305 |
| 32K | Pass (111s) | Pass (78s) | Fail (255s) | Pass (299s) | 26604 |
| 64K | Pass (168s) | Pass (150s) | Fail (583s) | Fail (214s) | 59817 |
| 128K | Pass (425s) | Pass (86s) | Fail (478s) | Pass (454s) | 124847 |
| 256K | Pass (615s) | Pass (92s) | Fail (633s) | Pass (742s) | 256211 |

The 2K coding task produced a verified change but its final report was truncated; the2K screenshot task lacked completion space. The 64K screenshot task exported the correct CSV but exceeded 16 rounds. Browser trials failed completion at every greedy setting: repeated edits could add duplicate labels, label another issue or continue past the round limit. The original failures remain in this table even where later diagnostics succeeded.

## Thinking browser follow-up

Native thinking uses temperature 1.0, top_p 0.95, top_k 20, presence penalty 0; this follows the [official model guidance](https://huggingface.co/Qwen/Qwen3.8-Flash-Next#best-practices). Follow-up trials allow 2048 output tokens per request, up to 16384 continuation reserve, and the same 16-round limit and artifact grader. Results must be compared with these changed settings in mind.

**7/8 passed**, with a correct single label on ISS-011 in every final artifact. The 2K trial still failed because the agent did not finish a verified, untruncated final report.

| Capacity | Result | Whole-task seconds | Initial input | Largest input | Median decode tokens/s |
|---|---|---|---|---|---|
| 2K | Failed | 75.6 | 615 | 1969 | 16.1 |
| 4K | Passed | 83.8 | 1000 | 2335 | 17.0 |
| 8K | Passed | 108.3 | 2024 | 3515 | 15.5 |
| 16K | Passed | 129.0 | 4072 | 5880 | 17.4 |
| 32K | Passed | 133.3 | 16360 | 18034 | 16.1 |
| 64K | Passed | 181.3 | 49128 | 50685 | 16.6 |
| 128K | Passed | 495.5 | 114664 | 116550 | 8.6 |
| 256K | Passed | 523.2 | 245736 | 247755 | 8.0 |

The 128K/256K cells use the final vacant-slot cache policy. The first 128K request starts with an empty recurrent cache; 256K reuses the common prefix. Smaller capacities ran before that cache change. Their manifests record the exact source hashes and settings.

## Performance and verification

Primary-matrix cell-median decode speeds had a median of 14.8 tokens/s for the everyday profile (range 9.2–21.3) and 7.1 tokens/s for the long profile (range 6.1–8.4). These are generated tokens including reasoning where applicable, excluding prefill. They do not represent whole-task throughput. Long-context prefill is a substantial latency cost: the initial 253928-token baseline request took 482.2 s of prefill. Reused-prefix requests benefit from recurrent checkpoints; cold and warm latencies differ.

The restored 64K service passed all seven API generation checks, plus direct/nested template-option equivalence, HTTP 400 context-overflow rejection and HTTP 404 unknown-model rejection. A small generated Python function passed independent execution tests. Its first request took 19.34 s and repeated request 1.97 s; the nonthinking text stream delivered its first payload in 0.276 s. A buffered tool-call stream took 41.02 s to deliver its complete call. These are specific test observations, not general latency guarantees.

The final deployed 64K runtime also passed a fresh coding task in 178.2 s and screenshot CSV task in 239.5 s. Their median decode speeds were 14.4 and 15.8 tokens/s. This diagnostic allowed 32 rounds; the screenshot task finished in 14 model requests and 13 tool calls. It exported exactly INV-001, INV-004 and INV-005, with the correct amounts and dates. The earlier primary 64K failure remains recorded. Sampled final-profile peaks were 21523/21148 MiB GPU usage and 9.806 GiB container RAM; final container swap usage was zero. The Mac tunnel and rig health checks both returned ready and idle.

In a paired cold-process 128K browser trial with identical 114664-token initial input, the vacant-slot cache policy reduced first-request prefill from 524.8 s to 272.0 s; total task time fell from 849.5 s to 495.5 s. The OS page cache was not controlled, so this is an observed pair rather than a general speedup guarantee. The 256K follow-up reuses prefix checkpoints and must not be described as cold.

- All 25 model-file checksums verified. Checkpoint revision `69e33439ae950f17bcbe95c98f117d80f759ab6d`, variant `3.05bpw_h5_ng5`, about 85.14 GB. The head and ngram files use higher precision than the 3.05bpw variant name suggests.
- 72 independent expert tensor/kernel comparisons passed on both GPUs, including reloads. Selected experts are never discarded; misses wait for exact checkpoint weights.
- Complete native-layer comparisons at normal input amplitude, 1/4/16/128/1024 rows and two repeats: identical routing IDs and weights, worst normalized RMS error 0.234%, cosine at least 0.999997, maximum absolute error 0.002274. Different native FP16 kernels are not bitwise identical. Earlier overly strict absolute checks failed and are preserved as diagnostics.
- The new prefill cache policy fills vacant GPU slots while preserving resident experts. Independent checks verified numerical agreement, GPU/host capacity limits and retention of previously cached entries.
- Image MRoPE/QSA query and pooled-key rotations match independent HF-equation checks exactly across image spans, permuted cache pages and decode offsets.
- Container RAM is capped at 20 GiB with equal memory/swap limits, prohibiting container swap. The sampled long-profile baseline peaked at 22149/20710 MiB GPU usage (21.63/20.22 GiB) and 10.65 GiB container RAM. The final cache-admission long trials peaked at 22135/20664 MiB and 10.58 GiB. Measurements are sampled every ten seconds; brief unsampled peaks may differ.

## Reproduce and inspect

[README.md](README.md) documents installation, pins and launch commands. Raw receipts and task traces are preserved under the rig root and copied into the Mac source directory. The primary summary is `receipts/task-matrix-summary.json`; each cell points to its result, tool trace and saved artifacts. Separate follow-up roots retain different sampling and round budgets instead of overwriting primary results. Deployed runtime file hashes match local source (`receipts/runtime-source-sha256.txt`). Runtime source commit: `079b4e0` (native thinking defaults plus validated prefill cache admission).

The model download, native kernels and corrected vision positions are validated. Reliability still depends on the task, available context and tool budget; these single trials do not establish general accuracy. Vision accepts base64 image URLs. Video, speculative MTP decoding, concurrent inference and OS desktop-app control are not implemented or validated here.
