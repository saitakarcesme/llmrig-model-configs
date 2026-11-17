# HyperQwen comparison on LLMRig

Experiment date: 2026-10-05. Hardware: i5-14400F, 32 GiB system RAM, two RTX 3090 24 GiB. No NVLink / GPU peer-to-peer; second slot is PCIe x4. GPU power limits 350 W and 420 W. These are measurements on this rig, not power-normalized reproductions of the repository claims.

Repository: https://github.com/syv-ai/HyperQwen
Runtime image: ghcr.io/syv-ai/hyperqwen@sha256:00713ba1e04b68db1be9eba2b15b579250f9fb0c29ed61add40c750228fc0cf8
Runtime source: bd6c5e2f11628483109031d99d1cc4a7d22b1a26

## Speed

Serial requests. Normal prompts: architecture, code generation and diagnostic reasoning, three repeats each. Warm-up excluded. Copy prompt: three repeats. xhigh: one run per normal prompt. Output limits 512 / 1024 tokens. Numbers are API-observed decode rates from completion-token usage and first/last generated-text arrival, including reasoning where enabled. Speculative chunks can emit several tokens at once, so short-output timing has small boundary bias. Prompt processing is excluded from decode rate; TTFT and total time are retained in raw numeric receipts. Prefix caching enabled. No concurrent benchmark requests.

| Arm | Cards | Normal median tok/s | xhigh median tok/s | Copy median tok/s | Exact copy prefixes |
|---|---:|---:|---:|---:|---|
| exl3-mtp | 2 | 107.41 | 89.36 | 170.16 | 3/3 PASS |
| hyper-dflash15-constant | 1 | 166.23 | 101.39 | 505.48 | 3/3 PASS |
| hyper-dflash15 | 1 | 181.13 | 106.71 | 467.50 | 0/3 FAIL |
| hyper-dflash7 | 1 | 181.75 | 108.65 | 252.93 | 3/3 PASS |
| hyper-dflash7-tp2 | 2 | 171.66 | 100.66 | 240.01 | 3/3 PASS |
| hyper-mtp | 1 | 151.49 | 108.34 | 224.25 | 3/3 PASS |
| hyper-off | 1 | 53.11 | 52.99 | 52.23 | 3/3 PASS |

EXL3 baseline uses the existing 3.5 bpw weights with a 6-bit output head, MTP, Q4 KV and 262144 server context. HyperQwen controls use the same fast W4A16 target, int8 embeddings and calibrated low-bit output head, bf16 KV and 65536 context (57344 for DFlash15). SPEC=off is the same-target control, not stock upstream vLLM. Differences versus EXL3 include quantization, runtime, GPU topology and kernels. A true stock-vLLM comparison and full bf16 quality baseline were not run.

Adaptive DFlash15 failed all three copy-prefix correctness checks. Its high copy throughput is not a successful performance result. The constant-block follow-up is listed separately when present, and also checks full-source copy completion.

## Quality

Initial quality matrix: first 50 fixed GSM8K test rows, temperature zero, thinking disabled, maximum 1024 output tokens. The later MTP run used 4096 tokens, as identified in the table. Answer equality uses the last numerical answer; output truncations count as failures. This small sample does not establish broad quality equivalence or a leaderboard rank.

| Arm | Correct | Samples | Output cap | Complete |
|---|---:|---:|---:|---|
| exl3-mtp | 48 | 50 | 1024 | True |
| hyper-dflash7 | 47 | 50 | 1024 | True |
| hyper-mtp | 48 | 50 | 4096 | True |
| hyper-off | 47 | 50 | 1024 | True |

Same-target speculation comparison: {"paired_samples": 50, "same_numerical_answer": 47, "same_content_hash": 23, "off_only_correct": [37], "fast_only_correct": [20]}

Normal prompt greedy output hashes: {"hyper-mtp": {"samples": 9, "same_content_hash": 0, "same_prompt_hash": 9}, "hyper-dflash7": {"samples": 9, "same_content_hash": 3, "same_prompt_hash": 9}, "hyper-dflash15": {"samples": 9, "same_content_hash": 3, "same_prompt_hash": 9}, "hyper-dflash7-tp2": {"samples": 9, "same_content_hash": 0, "same_prompt_hash": 9}}

Extended budget follow-up: {"exl3-mtp": {"initial_passed": 48, "passed": 48, "total": 50, "rerun_count": 1, "complete": true}, "hyper-off": {"initial_passed": 47, "passed": 50, "total": 50, "rerun_count": 3, "complete": true}, "hyper-dflash7": {"initial_passed": 47, "passed": 48, "total": 50, "rerun_count": 3, "complete": true}}

MTP quality was an additional later run of all 50 fixed questions at a 4096-token budget; it was not part of the initial 1024-token matrix. All question selections and sampling were preserved.

This is an exploratory two-stage check: every output truncated at 1024 tokens is rerun with the identical prompt and a 4096-token budget. Completed wrong outputs are not rerun and no grading feedback is supplied. Original fixed-budget scores remain visible. This evaluates sensitivity to response budget; it does not replace the initial frozen protocol.

Copy output prefix checks: {"exl3-mtp": {"correct_prefixes": 3, "total": 3}, "hyper-off": {"correct_prefixes": 3, "total": 3}, "hyper-mtp": {"correct_prefixes": 3, "total": 3}, "hyper-dflash7": {"correct_prefixes": 3, "total": 3}, "hyper-dflash15": {"correct_prefixes": 0, "total": 3}, "hyper-dflash7-tp2": {"correct_prefixes": 3, "total": 3}, "hyper-dflash15-constant": {"correct_prefixes": 3, "total": 3}}

Constant-block full-copy checks: [{"exact_copy": true, "complete": true, "tokens": 2310, "observed_decode_tps": 511.67435204684887}, {"exact_copy": true, "complete": true, "tokens": 2310, "observed_decode_tps": 511.10713159979787}, {"exact_copy": true, "complete": true, "tokens": 2310, "observed_decode_tps": 510.90322544880877}]

## Real project tasks through Pi

Four fixed PocketLore source maintenance tasks. Frozen revision e6287d0a1eccb716c4424803c85bcc5fc7356eb5. Graders hidden from model and preserved unchanged. Each final arm uses one first session per task, xhigh effort, 64K client context and 32768-token per-call generation cap, additionally bounded by actual remaining context on vLLM via /tokenize without trimming history. All observed requests stayed within 64K; peak actual total context was 37225 tokens for EXL3 and 50589 for HyperQwen. Omitted Pi sampling fields resolved consistently to temperature 0.6, top_p 0.95, top_k 20 (the existing EXL3 defaults). Self-tests and repairs allowed; no hidden test feedback supplied. Editable scope checked. Preliminary EXL3 preflight at an 8192-token cap exhausted reasoning before editing and is retained separately, not pooled into the final campaign.

| Arm | Task | Passed | Hidden tests | Wall seconds | API output tok/s including TTFT |
|---|---|---|---|---:|---:|
| exl3-mtp-v2 | paths | True | 4/4 | 187.10 | 106.84 |
| exl3-mtp-v2 | inflate | True | 8/8 | 227.79 | 98.72 |
| exl3-mtp-v2 | atomic | True | 5/5 | 192.31 | 100.46 |
| exl3-mtp-v2 | filters | True | 6/6 | 234.32 | 104.85 |
| hyper-dflash7 | paths | True | 4/4 | 478.03 | 116.12 |
| hyper-dflash7 | inflate | True | 8/8 | 164.38 | 141.29 |
| hyper-dflash7 | atomic | True | 5/5 | 145.03 | 130.17 |
| hyper-dflash7 | filters | True | 6/6 | 221.82 | 135.86 |

Aggregate native HyperQwen Pi timing recovery: {"scope": "Aggregate across all four HyperQwen Pi project tasks. Native first-to-last-token decode timing, excluding all recorded speed and math runs. The discarded 64-token warmup is bounded between zero and its full native engine elapsed time.", "project_completion_tokens": 126892, "project_api_requests": 75, "validated_total_request_count": 141, "prior_recorded_decode_seconds": 155.75702082522912, "native_total_decode_seconds": 965.1478372755228, "project_decode_seconds_range": [808.8908164502936, 809.3908164502936], "decode_tps_range": [156.6820347136816, 156.778884641711], "warmup_elapsed_upper_bound_seconds": 0.5, "api_output_tps_including_ttft": 126.56883555734673, "invalid_raw_proxy_fields": "The first project proxy missed delta.reasoning; its original observed_decode_tps and weighted_decode_tps fields are invalid for this arm. Standalone speed and quality clients handled both reasoning fields."}

Pi timing correction: the transferred proxy missed vLLM delta.reasoning and consequently overestimated HyperQwen per-task decode rates. Those raw proxy decode fields are invalid and excluded. This table uses all completion tokens divided by full API request time including TTFT, consistently for both backends. The standalone speed benchmark already supported both reasoning fields and remains valid. Whole-task time additionally includes tools and model-side self-repair.

## Preparation and scope

All three Hub components pinned by commit and downloaded with LFS SHA256 verification. Pristine files preserved separately. The default whole-matrix CPU quantizer exceeded the isolated 22 GiB memory limit. The repository row-streaming quantizer completed within an 18 GiB limit; generated tensor files were range-checked and hashed. Runtime patch verification passed. Serving binds localhost only, uses a private shared-memory namespace and isolated model/cache directories. No user project was modified. Native public sample model responses stay on LLMRig; numeric receipts and reports are exported locally.

No claim of 1000 tok/s for one user, no 10x claim versus an already optimized EXL3+MTP baseline, and no long-context/max-context claim from these short-context measurements. Aggregate 64-client throughput is outside this serial test.

Final state: {"stage": "complete", "updated_at": "2026-10-05T01:02:21.400412+00:00", "started_epoch": 1791157908.076437, "completed_arms": ["hyper-off", "hyper-mtp", "hyper-dflash7", "hyper-dflash15", "hyper-dflash7-tp2"], "restore_return_code": 0, "extended_completed": ["exl3-mtp", "hyper-off", "hyper-dflash7"], "extended_arm": "hyper-dflash7", "copy_control_done": true, "mtp_quality_done": true, "report": "REPORT.md", "native_project_timing": "receipts/hyper-dflash7-native-project-timing.json", "final_health": "receipts/final_service_health.json", "all_finite_jobs_finished": true, "pi_defaults_changed": false, "user_projects_modified": false}
