# Clef / DeepSeek Harness installation — 2026-10-05

Cloudflare sources: https://huggingface.co/Cloudflare/clef and https://huggingface.co/Cloudflare/clef-flash. Official Harness: https://github.com/deepseek-ai/deepseek-harness.

## Use

Mac: open `/Users/ibrahimsaitakarcesme/Applications/DeepSeekHarness/Open DeepSeek Harness.command`. The official web application runs on localhost:3080. Qwen is the chat provider; `mcp__clef__decide` calls Clef-flash for typed decisions. Both Mac services are LaunchAgents. Model requests pass through private SSH forwards; credentials and server access tokens remain outside this workspace. Session upload and feedback telemetry are disabled.

Rig: the **Pi — Qwen + Clef** desktop entry opens `/home/isa/Experiments/clef-fit/pi-clef.sh`. A dedicated Pi agent directory keeps previous Pi sessions/settings intact. Its `clef_decide` tool reaches the local decision endpoint.

Active services: `clef-pi-qwen.service` (Qwen 27B TP2 DFlash7, 32K context) and `clef-flash-live.service` (Clef-flash 9B NF4). The 262K Qwen container is retained. To restore 262K mode, run `/home/isa/Experiments/clef-fit/restore-qwen.sh` on the rig; this stops the dual services. After restoration, set Harness contextWindow back to 262144. To switch back to dual mode, run `start-dual.sh` when Qwen is idle.

Clef 27B NF4 and Clef-flash BF16 are also installed and have separate retained benchmark containers (`clef27-nf4`, `clef-flash-bf16`). Their weights and the original joint schema heads live in `/home/isa/Experiments/clef-fit/models`. They require freeing GPU memory from the dual profile before starting. The stock Cloudflare loader is used with a bitsandbytes quantization config; decision heads and output embeddings remain BF16. No GGUF/chat-generation substitute is used.

The private endpoint is `http://127.0.0.1:18031/v1/systemone` on the rig. It currently accepts text/JSON, choice/noul/score questions, with a 4096-token cap. Vision and video are not exposed by this wrapper.

## Evidence

`summary.json` collects results; the individual JSON files preserve every request, question, expected result, answer probability, token count, and timing. `pi-integration.jsonl` proves the real Qwen → Pi tool → Clef → Qwen flow. `harness-clef-proof.png` shows the real Harness result. `installation.json` pins model revisions and runtime versions.

Five unique synthetic short cases were repeated four times, with the first five requests excluded from warm summaries. p95 is a descriptive sample percentile, not a production tail-latency estimate. The small set is not a general-quality benchmark. NF4 Clef-flash missed one English outage example that BF16 classified correctly. Larger input latency is recorded separately. Loading times have different cache/download conditions and should not be compared as a controlled startup benchmark.
