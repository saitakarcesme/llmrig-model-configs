# HyperQwen on LLMRig

Source: syv-ai/HyperQwen at 10bb488418064b50738c925b70c9510785c3c949.

Preparation in progress. Source SHA image tag missing because latest commit changes documentation only. Pulling published image, then freezing digest and revision. Three model components pinned in receipts/model_manifest.json. Existing baseline is Qwen3.8 EXL3 3.5bpw with MTP on two RTX 3090s. Kolibri remains running during CPU preparation. No measured HyperQwen results yet.

Project evaluation: {"stage": "project_task_running", "project_task": "paths", "completed_project_tasks": 0}

Project evaluation: {"stage": "project_task_completed", "project_task": "paths", "project_result": {"task": "paths", "baseline": {"tests": 4, "failures": 0, "errors": 4, "passed": false, "return_code": 1}, "acceptance": {"tests": 4, "failures": 0, "errors": 4, "passed": false, "return_code": 1}, "scope_ok": true, "passed": false, "pi_return_code": 0, "timeout": false, "wall_seconds": 78.95036825101124, "changed_existing_files": [], "new_test_files": [], "tool_calls": ["read", "bash", "read", "read", "read", "read", "read", "read"], "api_requests": 3, "timing_receipts": 0, "weighted_decode_tps": 123.05824229166086, "per_request_decode_tps": [141.37491986286037, 101.43270051940803, 123.77368966145399], "decode_seconds": 0.0, "prompt_seconds": 0.0, "generated_tokens": 8591, "prompt_tokens_evaluated": 0, "cached_prompt_tokens": 0, "tokens_per_wall_second": 108.81519859015935, "reasoning_effort": "high", "scope": "One first attempt per task; test criteria fixed before generation. Not local.ai benchmark scores."}, "completed_project_tasks": 1}

Project evaluation: {"stage": "project_task_running", "project_task": "inflate", "completed_project_tasks": 1}

All three pinned model snapshots downloaded and LFS SHA256 checked. Image fixed at sha256:00713ba1e04b68db1be9eba2b15b579250f9fb0c29ed61add40c750228fc0cf8, source bd6c5e2f11628483109031d99d1cc4a7d22b1a26, vLLM 0.30.0 / torch 2.13.0+cu130. Latest checkout differs only in documentation. Default full-matrix CPU quantizer exceeded isolated 22GiB memory limit and was OOM killed. Retrying the repository-provided row-streaming quant_heads_stream.py with an 18GiB limit, four CPU threads, identical group quantization math, followed by standard preparation. Originals remain preserved. Existing EXL3 speed matrix completed: normal median 107.4128 tok/s, copy 170.1586, xhigh 89.3623. Project baseline running.

Protocol preflight: EXL3 at xhigh exhausted the initial 8192-token per-call cap in reasoning before editing the first task. Stopped that campaign, retaining preliminary receipts. Both final project arms will use the same 32768-token cap, 64K client context, xhigh effort, one session per task. No grader feedback supplied to models.

Project evaluation: {"stage": "project_task_running", "project_task": "paths", "completed_project_tasks": 0}

Project evaluation: {"stage": "project_task_completed", "project_task": "paths", "project_result": {"task": "paths", "baseline": {"tests": 4, "failures": 0, "errors": 4, "passed": false, "return_code": 1}, "acceptance": {"tests": 4, "failures": 0, "errors": 0, "passed": true, "return_code": 0}, "scope_ok": true, "passed": true, "pi_return_code": 0, "timeout": false, "wall_seconds": 187.10101971396944, "changed_existing_files": ["common.py", "compact_search.py", "search.py", "enrich.py", "catalog.py"], "new_test_files": ["test_readonly_sqlite.py"], "tool_calls": ["read", "bash", "read", "read", "read", "read", "read", "read", "bash", "edit", "edit", "edit", "edit", "edit", "write", "bash", "edit", "bash", "edit", "bash", "bash", "bash"], "api_requests": 13, "timing_receipts": 0, "weighted_decode_tps": 126.64519476430878, "per_request_decode_tps": [177.3262337165975, 177.93633882543656, 119.39773517051296, 138.14266953125087, 144.7854390042996, 158.0935757258274, 132.0423401123017, 144.03549667990958, 141.40383435101026, 117.30798110881767, 110.844309853464, 102.2293535487533, 119.43739280981262], "decode_seconds": 0.0, "prompt_seconds": 0.0, "generated_tokens": 19902, "prompt_tokens_evaluated": 0, "cached_prompt_tokens": 0, "tokens_per_wall_second": 106.37034491006607, "reasoning_effort": "high", "scope": "One first attempt per task; test criteria fixed before generation. Not local.ai benchmark scores."}, "completed_project_tasks": 1}

Project evaluation: {"stage": "project_task_running", "project_task": "inflate", "completed_project_tasks": 1}

{"stage": "baseline_project_and_quality_running", "updated_at": "2026-10-04T23:36:29.240775+00:00", "started_epoch": 1791156989.2407713, "completed_arms": []}

Project evaluation: {"stage": "project_task_completed", "project_task": "inflate", "project_result": {"task": "inflate", "baseline": {"tests": 8, "failures": 0, "errors": 2, "passed": false, "return_code": 1}, "acceptance": {"tests": 8, "failures": 0, "errors": 0, "passed": true, "return_code": 0}, "scope_ok": true, "passed": true, "pi_return_code": 0, "timeout": false, "wall_seconds": 227.78645937598776, "changed_existing_files": ["compact_search.py"], "new_test_files": ["test_inflate.py"], "tool_calls": ["read", "bash", "read", "read", "read", "read", "read", "read", "bash", "bash", "edit", "write", "edit", "bash", "edit", "bash", "edit", "bash", "read", "bash"], "api_requests": 15, "timing_receipts": 0, "weighted_decode_tps": 115.59119468608245, "per_request_decode_tps": [168.79743820321193, 169.8239381239029, 167.94143224168081, 111.06077292833255, 113.84303226033886, 107.20342609315351, 138.94975348332386, 138.525417225624, 112.58122368087483, 144.4576968919515, 121.56571437308052, 131.5145489339496, 113.79590505145987, 112.5589073496228, 100.0948043108765], "decode_seconds": 0.0, "prompt_seconds": 0.0, "generated_tokens": 22299, "prompt_tokens_evaluated": 0, "cached_prompt_tokens": 0, "tokens_per_wall_second": 97.89431760380864, "reasoning_effort": "high", "scope": "One first attempt per task; test criteria fixed before generation. Not local.ai benchmark scores."}, "completed_project_tasks": 2}

Project evaluation: {"stage": "project_task_running", "project_task": "atomic", "completed_project_tasks": 2}

Project evaluation: {"stage": "project_task_completed", "project_task": "atomic", "project_result": {"task": "atomic", "baseline": {"tests": 5, "failures": 1, "errors": 1, "passed": false, "return_code": 1}, "acceptance": {"tests": 5, "failures": 0, "errors": 0, "passed": true, "return_code": 0}, "scope_ok": true, "passed": true, "pi_return_code": 0, "timeout": false, "wall_seconds": 192.31366187799722, "changed_existing_files": ["common.py"], "new_test_files": ["test_atomic_json.py"], "tool_calls": ["read", "bash", "read", "read", "read", "read", "read", "read", "bash", "write", "write", "bash", "bash", "bash", "read", "bash"], "api_requests": 10, "timing_receipts": 0, "weighted_decode_tps": 118.48227831401273, "per_request_decode_tps": [171.57646171737213, 181.15619104492322, 175.36063617250653, 111.48922823501084, 132.1392924741583, 153.02404290494488, 147.1904104895134, 110.7203325197802, 110.10601345982437, 106.45438881799602], "decode_seconds": 0.0, "prompt_seconds": 0.0, "generated_tokens": 19233, "prompt_tokens_evaluated": 0, "cached_prompt_tokens": 0, "tokens_per_wall_second": 100.00849555972427, "reasoning_effort": "high", "scope": "One first attempt per task; test criteria fixed before generation. Not local.ai benchmark scores."}, "completed_project_tasks": 3}

Project evaluation: {"stage": "project_task_running", "project_task": "filters", "completed_project_tasks": 3}

Sandbox refinement for the upcoming HyperQwen agent arm: mask the entire user home, rebind only the fixed Node runtime, isolated task and isolated Pi profile. Baseline only consumed the same frozen task files. No provider credentials copied. HyperQwen model access forced offline after preparation.

Project evaluation: {"stage": "project_task_completed", "project_task": "filters", "project_result": {"task": "filters", "baseline": {"tests": 6, "failures": 0, "errors": 7, "passed": false, "return_code": 1}, "acceptance": {"tests": 6, "failures": 0, "errors": 0, "passed": true, "return_code": 0}, "scope_ok": true, "passed": true, "pi_return_code": 0, "timeout": false, "wall_seconds": 234.32350916601717, "changed_existing_files": ["catalog.py"], "new_test_files": ["test_catalog_filters.py"], "tool_calls": ["read", "bash", "read", "read", "read", "read", "read", "read", "bash", "edit", "write", "bash", "edit", "bash", "bash", "bash", "edit", "bash", "read", "bash"], "api_requests": 14, "timing_receipts": 0, "weighted_decode_tps": 125.9449567291527, "per_request_decode_tps": [166.5461073819198, 166.05267632090812, 124.75602983165548, 145.55552008404712, 144.707577422237, 165.02098201162113, 130.68693511928828, 128.45388047868528, 105.58057777284986, 106.24891545453846, 111.96820112278193, 121.11574519070184, 122.91720471237599, 108.45557733152027], "decode_seconds": 0.0, "prompt_seconds": 0.0, "generated_tokens": 24500, "prompt_tokens_evaluated": 0, "cached_prompt_tokens": 0, "tokens_per_wall_second": 104.55630374945375, "reasoning_effort": "high", "scope": "One first attempt per task; test criteria fixed before generation. Not local.ai benchmark scores."}, "completed_project_tasks": 4}

Project evaluation: {"stage": "project_evaluation_complete", "project_tasks_passed": 4, "project_tasks_total": 4, "project_study": "project-study/receipts/summary.json"}

EXL3 project baseline completed all four tasks with all 23 holdout tests passing. Actual peak total context 37225 tokens. vLLM strictly checks requested output budget plus input against 64K; added a /tokenize preflight for the upcoming Pi arm to cap requested output to min(32768, 65536-input-8) without trimming history. Baseline observed request lengths remain within 64K.

{"stage": "arm_starting", "updated_at": "2026-10-04T23:49:55.396671+00:00", "started_epoch": 1791156989.2407713, "completed_arms": [], "arm": "hyper-off"}

{"stage": "campaign_failed", "updated_at": "2026-10-04T23:50:35.460196+00:00", "started_epoch": 1791156989.2407713, "completed_arms": [], "error": "Server startup failed hyperqwen-hyper-off"}

{"stage": "restoring_kolibri", "updated_at": "2026-10-04T23:50:35.479729+00:00", "started_epoch": 1791156989.2407713, "completed_arms": []}

{"stage": "incomplete", "updated_at": "2026-10-04T23:50:58.473080+00:00", "started_epoch": 1791156989.2407713, "completed_arms": [], "restore_return_code": 0}

HyperQwen off control startup rejected REQ_METRICS=1 because the launcher includes speculative-decoding metrics even with SPEC=off. Bounded configuration repair: REQ_METRICS=0 only for SPEC=off; all arms still use stream usage and API-arrival timing. No model-generated results from the failed startup. Server/container names made unique for resumable campaign repair. Baseline GSM8K result: 48/50.

{"stage": "baseline_project_and_quality_running", "updated_at": "2026-10-04T23:51:15.773642+00:00", "started_epoch": 1791157875.7735686, "completed_arms": []}

{"stage": "campaign_failed", "updated_at": "2026-10-04T23:51:15.792193+00:00", "started_epoch": 1791157875.7735686, "completed_arms": [], "error": "Command '['systemctl', '--user', 'stop', 'hyperqwen-baseline.service']' returned non-zero exit status 5."}

{"stage": "restoring_kolibri", "updated_at": "2026-10-04T23:51:15.794918+00:00", "started_epoch": 1791157875.7735686, "completed_arms": []}

{"stage": "incomplete", "updated_at": "2026-10-04T23:51:38.912067+00:00", "started_epoch": 1791157875.7735686, "completed_arms": [], "restore_return_code": 0}

{"stage": "baseline_project_and_quality_running", "updated_at": "2026-10-04T23:51:48.076510+00:00", "started_epoch": 1791157908.076437, "completed_arms": []}

{"stage": "arm_starting", "updated_at": "2026-10-04T23:51:48.094474+00:00", "started_epoch": 1791157908.076437, "completed_arms": [], "arm": "hyper-off"}

{"stage": "arm_ready", "updated_at": "2026-10-04T23:54:28.321200+00:00", "started_epoch": 1791157908.076437, "completed_arms": [], "arm": "hyper-off", "spec": "off", "draft_tokens": 7, "gpus": 1}

{"stage": "quality_running", "updated_at": "2026-10-04T23:57:55.949680+00:00", "started_epoch": 1791157908.076437, "completed_arms": [], "arm": "hyper-off"}

Sampling audit: the Pi OpenAI adapter passes temperature only when explicitly configured. Existing EXL3 server defaults are temperature 0.6, top_p 0.95, top_k 20; HyperQwen model generation_config defaults temperature 1.0. The upcoming Pi proxy explicitly fills omitted sampling fields with the existing EXL3 defaults, preserving any explicit Pi field. This prevents a backend-default sampling mismatch. Serial speed and GSM8K protocols already explicitly use greedy temperature zero and seed 123.

{"stage": "arm_complete", "updated_at": "2026-10-05T00:04:48.474278+00:00", "started_epoch": 1791157908.076437, "completed_arms": ["hyper-off"], "arm": "hyper-off"}

{"stage": "arm_starting", "updated_at": "2026-10-05T00:04:48.474585+00:00", "started_epoch": 1791157908.076437, "completed_arms": ["hyper-off"], "arm": "hyper-mtp"}

{"stage": "arm_ready", "updated_at": "2026-10-05T00:07:58.731793+00:00", "started_epoch": 1791157908.076437, "completed_arms": ["hyper-off"], "arm": "hyper-mtp", "spec": "mtp", "draft_tokens": 7, "gpus": 1}

{"stage": "arm_complete", "updated_at": "2026-10-05T00:09:18.454517+00:00", "started_epoch": 1791157908.076437, "completed_arms": ["hyper-off", "hyper-mtp"], "arm": "hyper-mtp"}

{"stage": "arm_starting", "updated_at": "2026-10-05T00:09:18.454735+00:00", "started_epoch": 1791157908.076437, "completed_arms": ["hyper-off", "hyper-mtp"], "arm": "hyper-dflash7"}

{"stage": "arm_ready", "updated_at": "2026-10-05T00:12:38.699710+00:00", "started_epoch": 1791157908.076437, "completed_arms": ["hyper-off", "hyper-mtp"], "arm": "hyper-dflash7", "spec": "dflash2", "draft_tokens": 7, "gpus": 1}

{"stage": "quality_running", "updated_at": "2026-10-05T00:13:47.964938+00:00", "started_epoch": 1791157908.076437, "completed_arms": ["hyper-off", "hyper-mtp"], "arm": "hyper-dflash7"}

{"stage": "project_running", "updated_at": "2026-10-05T00:15:24.136670+00:00", "started_epoch": 1791157908.076437, "completed_arms": ["hyper-off", "hyper-mtp"], "arm": "hyper-dflash7"}

Project evaluation: {"stage": "project_task_running", "project_task": "paths", "completed_project_tasks": 0}

Project evaluation: {"stage": "project_task_completed", "project_task": "paths", "project_result": {"task": "paths", "baseline": {"tests": 4, "failures": 0, "errors": 4, "passed": false, "return_code": 1}, "acceptance": {"tests": 4, "failures": 0, "errors": 0, "passed": true, "return_code": 0}, "scope_ok": true, "passed": true, "pi_return_code": 0, "timeout": false, "wall_seconds": 478.03486349398736, "changed_existing_files": ["common.py", "compact_search.py", "search.py", "enrich.py", "catalog.py"], "new_test_files": ["test_readonly_sqlite.py"], "tool_calls": ["read", "bash", "read", "read", "read", "read", "read", "read", "bash", "bash", "bash", "edit", "edit", "edit", "read", "edit", "edit", "edit", "bash", "bash", "write", "bash", "edit", "bash", "read", "bash", "edit", "bash", "read", "edit", "bash", "bash", "bash", "bash", "bash", "read", "edit", "bash", "read", "bash", "bash", "bash"], "api_requests": 39, "timing_receipts": 0, "weighted_decode_tps": 524.9422963747086, "per_request_decode_tps": [304.63856129640493, 326.9573356612711, 3208.0680164175396, 1074.942230972332, 475.81116363025154, 2005.81351064995, 308.0053948338205, 450.7150271531495, 2737.5707452306883, 629.38977443667, 610.5108427011753, 1001.8370297036561, 197.9966994473618, 1676.5397971990665, 419.669533993804, 223.73112314751242, 259.6592761970845, 640.4334771802517, 377.8289792052678, 1556.6643657094744, 877.5746823759, 276.7913828302732, 165.1077128746617, 2720.94863833317, 451.84992685026367, 259.8656867881663, 226.10872413066673, 265.4568065105392, 632.9578578964574, 378.4628272690725, 1092.6520398613163, 833.4260595607208, 238.35232409654668, 318.844133151022, 743.3914383176221, 243.5623699469594, 211.76002090219706, 376.88348909676824, 244.29801039796288], "decode_seconds": 105.05345136189135, "prompt_seconds": 0.0, "generated_tokens": 55186, "prompt_tokens_evaluated": 0, "cached_prompt_tokens": 0, "tokens_per_wall_second": 115.44346284001547, "reasoning_effort": "high", "scope": "One first attempt per task; test criteria fixed before generation. Not local.ai benchmark scores."}, "completed_project_tasks": 1}

Project evaluation: {"stage": "project_task_running", "project_task": "inflate", "completed_project_tasks": 1}

Project evaluation: {"stage": "project_task_completed", "project_task": "inflate", "project_result": {"task": "inflate", "baseline": {"tests": 8, "failures": 0, "errors": 2, "passed": false, "return_code": 1}, "acceptance": {"tests": 8, "failures": 0, "errors": 0, "passed": true, "return_code": 0}, "scope_ok": true, "passed": true, "pi_return_code": 0, "timeout": false, "wall_seconds": 164.38304281799356, "changed_existing_files": ["compact_search.py"], "new_test_files": ["test_inflate.py"], "tool_calls": ["read", "bash", "read", "read", "read", "read", "read", "read", "bash", "edit", "bash", "edit", "read", "write", "bash", "bash", "bash"], "api_requests": 13, "timing_receipts": 0, "weighted_decode_tps": 854.8867160288996, "per_request_decode_tps": [378.20680779039253, 396.57264732821255, 380.75580884404053, 3684.726234926898, 362.9223411036842, 267.5253902620902, 277.8605226035617, 272.79999579485406, 178.4055382328567, 432.4323707383325, 680.5037389919254, 397.8685296395073, 210.81861272952887], "decode_seconds": 26.88543355400907, "prompt_seconds": 0.0, "generated_tokens": 22997, "prompt_tokens_evaluated": 0, "cached_prompt_tokens": 0, "tokens_per_wall_second": 139.8988582141194, "reasoning_effort": "high", "scope": "One first attempt per task; test criteria fixed before generation. Not local.ai benchmark scores."}, "completed_project_tasks": 2}

Project evaluation: {"stage": "project_task_running", "project_task": "atomic", "completed_project_tasks": 2}

Measurement defect found in the reused Pi proxy: vLLM 0.30 emits reasoning in delta.reasoning, while the transferred Kolibri/EXL3 proxy only timed delta.reasoning_content. The missing reasoning interval inflated its Pi decode rates. These raw proxy rates are invalid for HyperQwen and will not be used as performance evidence. Standalone stream_client.py already handled both fields, so the short-prompt matrix is unaffected. Final project comparisons will use whole-request token/time and whole-task wall time; aggregate native decode will be reconstructed from server counters minus saved pre-project per-request timings, with the discarded warmup explicitly bounded. Proxy source fixed for future runs, also recording native metrics and supporting max_completion_tokens in the context-budget guard. The running first-session project campaign is retained rather than reset or fed hidden-test results.

Project evaluation: {"stage": "project_task_completed", "project_task": "atomic", "project_result": {"task": "atomic", "baseline": {"tests": 5, "failures": 1, "errors": 1, "passed": false, "return_code": 1}, "acceptance": {"tests": 5, "failures": 0, "errors": 0, "passed": true, "return_code": 0}, "scope_ok": true, "passed": true, "pi_return_code": 0, "timeout": false, "wall_seconds": 145.02798354200786, "changed_existing_files": ["common.py"], "new_test_files": ["test_atomic_json.py"], "tool_calls": ["read", "bash", "read", "read", "read", "read", "read", "read", "bash", "bash", "edit", "write", "read", "bash", "edit", "bash", "bash", "bash", "bash"], "api_requests": 13, "timing_receipts": 0, "weighted_decode_tps": 904.3577956127543, "per_request_decode_tps": [332.5441940680532, 346.24943948247903, 24295.860675117452, 7111.639660422171, 189.8466892240882, 254.9171240056965, 259.6225455557986, 235.87072287267824, 1212.6262848703086, 273.546080244999, 319.13244048879335, 695.7808362136104, 171.2410096487933], "decode_seconds": 20.647801224899013, "prompt_seconds": 0.0, "generated_tokens": 18686, "prompt_tokens_evaluated": 0, "cached_prompt_tokens": 0, "tokens_per_wall_second": 128.84409990150306, "reasoning_effort": "high", "scope": "One first attempt per task; test criteria fixed before generation. Not local.ai benchmark scores."}, "completed_project_tasks": 3}

Project evaluation: {"stage": "project_task_running", "project_task": "filters", "completed_project_tasks": 3}

The isolated HyperQwen Pi provider now explicitly uses max_tokens for subsequent task processes, so the already-running proxy context guard can bound the output reservation correctly. It does not alter the configured generation budget or sampling. The generic future proxy supports either token-field alias.

Project evaluation: {"stage": "project_task_completed", "project_task": "filters", "project_result": {"task": "filters", "baseline": {"tests": 6, "failures": 0, "errors": 7, "passed": false, "return_code": 1}, "acceptance": {"tests": 6, "failures": 0, "errors": 0, "passed": true, "return_code": 0}, "scope_ok": true, "passed": true, "pi_return_code": 0, "timeout": false, "wall_seconds": 221.8196791979717, "changed_existing_files": ["catalog.py"], "new_test_files": ["test_catalog_nearby_filters.py"], "tool_calls": ["read", "bash", "read", "read", "read", "read", "read", "read", "bash", "edit", "write", "bash", "edit", "bash", "read", "bash"], "api_requests": 10, "timing_receipts": 0, "weighted_decode_tps": 1206.2978859945556, "per_request_decode_tps": [332.355913182349, 351.722204221481, 29170.732310711348, 254.17659963104882, 243.29167943028477, 284.95531024446416, 277.2187970597161, 1557.6371631367747, 230.40962678639366, 141.00711529830883], "decode_seconds": 24.880255821102764, "prompt_seconds": 0.0, "generated_tokens": 30023, "prompt_tokens_evaluated": 0, "cached_prompt_tokens": 0, "tokens_per_wall_second": 135.3486764950408, "reasoning_effort": "high", "scope": "One first attempt per task; test criteria fixed before generation. Not local.ai benchmark scores."}, "completed_project_tasks": 4}

Project evaluation: {"stage": "project_evaluation_complete", "project_tasks_passed": 4, "project_tasks_total": 4, "project_study": "project-study/receipts/summary.json"}

{"stage": "arm_complete", "updated_at": "2026-10-05T00:32:15.014003+00:00", "started_epoch": 1791157908.076437, "completed_arms": ["hyper-off", "hyper-mtp", "hyper-dflash7"], "arm": "hyper-dflash7"}

{"stage": "arm_starting", "updated_at": "2026-10-05T00:32:15.014212+00:00", "started_epoch": 1791157908.076437, "completed_arms": ["hyper-off", "hyper-mtp", "hyper-dflash7"], "arm": "hyper-dflash15"}

{"stage": "arm_ready", "updated_at": "2026-10-05T00:35:30.261052+00:00", "started_epoch": 1791157908.076437, "completed_arms": ["hyper-off", "hyper-mtp", "hyper-dflash7"], "arm": "hyper-dflash15", "spec": "dflash2", "draft_tokens": 15, "gpus": 1}

{"stage": "arm_complete", "updated_at": "2026-10-05T00:36:36.472578+00:00", "started_epoch": 1791157908.076437, "completed_arms": ["hyper-off", "hyper-mtp", "hyper-dflash7", "hyper-dflash15"], "arm": "hyper-dflash15"}

{"stage": "arm_starting", "updated_at": "2026-10-05T00:36:36.472898+00:00", "started_epoch": 1791157908.076437, "completed_arms": ["hyper-off", "hyper-mtp", "hyper-dflash7", "hyper-dflash15"], "arm": "hyper-dflash7-tp2"}

{"stage": "arm_ready", "updated_at": "2026-10-05T00:40:11.764298+00:00", "started_epoch": 1791157908.076437, "completed_arms": ["hyper-off", "hyper-mtp", "hyper-dflash7", "hyper-dflash15"], "arm": "hyper-dflash7-tp2", "spec": "dflash2", "draft_tokens": 7, "gpus": 2}

Quality gate failure: adaptive DFLASH_TOKENS=15 measured 467.5 tok/s on the synthetic copy workload but failed all three exact-prefix checks. First mismatch at character 641 in run zero; lines and numbers become corrupted. Off and DFlash7 copied the same prefix correctly in all repeats. The 467.5 rate is invalid as a successful copy performance result. One bounded follow-up will use VLLM_DFLASH2_LOOKUP_ADAPTIVE=0 (constant verify block), the repository setting used to avoid related adaptive state corruption, and will also check full-source copy completion. No upstream issue or message sent.

{"stage": "arm_complete", "updated_at": "2026-10-05T00:41:27.130899+00:00", "started_epoch": 1791157908.076437, "completed_arms": ["hyper-off", "hyper-mtp", "hyper-dflash7", "hyper-dflash15", "hyper-dflash7-tp2"], "arm": "hyper-dflash7-tp2"}

{"stage": "measurement_complete", "updated_at": "2026-10-05T00:41:27.131117+00:00", "started_epoch": 1791157908.076437, "completed_arms": ["hyper-off", "hyper-mtp", "hyper-dflash7", "hyper-dflash15", "hyper-dflash7-tp2"]}

{"stage": "restoring_kolibri", "updated_at": "2026-10-05T00:41:27.134083+00:00", "started_epoch": 1791157908.076437, "completed_arms": ["hyper-off", "hyper-mtp", "hyper-dflash7", "hyper-dflash15", "hyper-dflash7-tp2"]}

{"stage": "complete", "updated_at": "2026-10-05T00:41:50.220336+00:00", "started_epoch": 1791157908.076437, "completed_arms": ["hyper-off", "hyper-mtp", "hyper-dflash7", "hyper-dflash15", "hyper-dflash7-tp2"], "restore_return_code": 0}

Extended budget check: {"stage": "extended_budget_preparing"}

Extended budget check: {"stage": "extended_budget_running", "extended_arm": "exl3-mtp"}

Extended budget check: {"stage": "extended_budget_starting", "extended_arm": "hyper-off"}

Extended budget check: {"stage": "extended_budget_running", "extended_arm": "hyper-off"}

Extended budget check: {"stage": "extended_budget_starting", "extended_arm": "hyper-dflash7"}

Extended budget check: {"stage": "extended_budget_running", "extended_arm": "hyper-dflash7"}

Extended budget check: {"stage": "restoring_kolibri"}

Extended budget check: {"stage": "complete", "restore_return_code": 0}

Copy control: {"stage": "copy_control_starting"}

Copy control: {"stage": "copy_control_running"}

Copy control: {"stage": "copy_control_complete", "copy_control_done": true}

Copy control: {"stage": "restoring_kolibri"}

Copy control: {"stage": "complete", "restore_return_code": 0}

MTP quality control: {"stage": "mtp_quality_starting"}

MTP quality control: {"stage": "mtp_quality_running"}

MTP quality control: {"stage": "mtp_quality_complete", "mtp_quality_done": true}

MTP quality control: {"stage": "restoring_kolibri"}

MTP quality control: {"stage": "complete", "restore_return_code": 0}

Final results: all five primary speed arms completed. DFlash7 passed all four Pi tasks and all 23 holdout methods, matching the existing EXL3 task acceptance. Corrected native DFlash7 Pi decode is 156.68-156.78 tok/s; its per-task proxy decode fields are invalid because of the missing reasoning-field timing. Full API output rate 126.57 tok/s versus EXL3 102.63. Whole-task total 1009.27s versus 841.52s: HyperQwen produced 126892 versus 85934 completion tokens. Single-card DFlash7 normal 181.75, xhigh 108.65; two-card 171.66 / 100.66. Default adaptive DFlash15 copy corrupted text in 3/3 repeats. VLLM_DFLASH2_LOOKUP_ADAPTIVE=0 restored 3/3 correct prefixes and 3/3 full 2310-token copies, median full-copy about 511.1 tok/s. Constant mode normal 166.23, xhigh 101.39. Greedy math, same frozen first 50 GSM8K test rows: initial 1024-token scores EXL3 48, Hyper off 47, DFlash7 47. Exploratory two-stage 4096-token budget check: EXL3 48, Hyper off 50, DFlash7 48. MTP separate full 4096-token run scored 48/50. Output identity and scores are not guaranteed by the acceleration on this runtime; this small sample is not a general model quality ranking. Prior Kolibri service restored; no change to normal Pi defaults, no user project edits or upstream messages/pushes.

## Live desktop Pi launch
User requested both GPUs and longest context. Native config maximum is 262144. Preparing TP2 DFlash7 with BF16 KV, max sequences 1, custom all-reduce disabled. Dedicated Pi configuration preserves global defaults.

Live launch succeeded. TP2 BF16 KV pool capacity 396701 tokens, server max_model_len 262144. Both GPU workers loaded 7.82 GiB weights each. /health returns 200. Highest-reasoning sanity returned READY, 43 output tokens (39 reasoning), 0.363 s end-to-end. Desktop foot terminal title became π - live, demonstrating interactive Pi startup. This is startup/small-request verification, not a fully populated 262K context performance benchmark. Kolibri stopped; live HyperQwen left running per user request.

2026-10-05 07:36 UTC: Pi website research duration requirement failure detected. Two consecutive sleep 930 tools after substantive project updates ceased ~07:14 UTC. Three hours of active research not verified. Completion heartbeat paused and user notified. Pi, GPU service and website project left untouched; no redesign or redeployment. Receipt: receipts/autoresearch-monitor-failure.json.
