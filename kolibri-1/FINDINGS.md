# Kolibri on LLMRig

User authorized stopping current rig work and testing maximum usable context and performance through Pi. Separate installation at /home/isa/Experiments/kolibri-fit. Two RTX3090 24GB, i5-14400F, 32GiB RAM. Native FP8 ~78GB does not fit VRAM. Starting full-pool Q3_K_S quant, 33,870,242,400 bytes, pinned source Eliasfpv28/Kolibri-1-Q3_K_S-GGUF 04f6e403e0db21f5ecb9d1c142f69204a43fe1e7. Experimental runtime patch on llama.cpp edd6e2bbdad5930899a93db8fa73c3b61c7b9bcc. Need local CUDA correctness, Pi tool flow and context gates. Upstream 262144 native / 1048576 reported extension are not rig-validated limits. No push authorized for new experiment.

Q3 package SHA256SUMS all passed. Q4_K_XL independent BF16-derived imatrix quant pinned at 3526916afa56f68b5475e1d85389f052c1be3b52, 47442951904 bytes, SHA256 8b45804b524440b7da9779bb2ee8877165fb56b1175233811a447742afa4c195. Download started for bounded quality/memory comparison. Existing Qwen gateway and Ollama stopped for this authorized experiment. CUDA build uses existing image 84f75f3424c9, compute capability86.

Q3 CUDA short gate passed arithmetic, JSON and German. Server reported median decode none117.117/high116.840 tok/s over three512-token tutorial runs each; high512 limit includes reasoning tokens and does not measure complete answer latency. Actual Pi high effort read+write tool roundtrip passed product391 in6.61s. Short context32768 configured, actual prompt65/78 tokens. Proceeding synthetic long retrieval gates; no general quant quality claim.

{"stage": "context_server_starting", "testing_context": 131072}

{"stage": "context_request_running", "testing_context": 131072, "container": "kolibri-serve-kolibri-q3-131072-q80-1791149702"}

{"stage": "context_gate_passed", "largest_passed_configured_context": 131072, "largest_passed_actual_prompt": 126856, "context_decode_tps": 47.91350506639245}

{"stage": "context_server_starting", "testing_context": 262144}

{"stage": "context_request_running", "testing_context": 262144, "container": "kolibri-serve-kolibri-q3-262144-q80-1791149882"}

{"stage": "context_gate_passed", "largest_passed_configured_context": 262144, "largest_passed_actual_prompt": 257933, "context_decode_tps": 29.41129891608051}

{"stage": "context_server_starting", "testing_context": 524288}

{"stage": "maximum_context_server_starting", "testing_context": 1048576}

{"stage": "maximum_context_q4_cache_fallback", "error": "kolibri-serve-kolibri-q3-1048576-q80-1791150225 exited; saved log", "testing_context": 1048576}

{"stage": "maximum_context_request_running", "container": "kolibri-serve-kolibri-q3-1048576-q40-1791150256", "cache": "q4_0", "testing_context": 1048576}

{"stage": "maximum_context_campaign_error", "error": "HTTP Error 400: Bad Request", "largest_passed_configured_context": 262144}

{"stage": "maximum_context_server_starting", "testing_context": 1048576}

{"stage": "maximum_context_request_running", "container": "kolibri-serve-kolibri-q3-1048576-q40-1791150451", "cache": "q4_0", "testing_context": 1048576}

Extended context progress: {"tokens_processed": 366617, "fraction": 0.35, "prefill_seconds": 527.43, "checked_at": "2026-10-04T21:56:45.005619+00:00"}

Extended context progress: {"tokens_processed": 431129, "fraction": 0.41, "prefill_seconds": 693.22, "checked_at": "2026-10-04T21:59:33.145263+00:00"}

Extended context progress: {"tokens_processed": 528409, "fraction": 0.51, "prefill_seconds": 985.02, "checked_at": "2026-10-04T22:04:23.043066+00:00"}

Extended context progress: {"tokens_processed": 605209, "fraction": 0.58, "prefill_seconds": 1251.19, "checked_at": "2026-10-04T22:08:50.995156+00:00"}

Extended context progress: {"tokens_processed": 708633, "fraction": 0.68, "prefill_seconds": 1659.0, "checked_at": "2026-10-04T22:15:38.899112+00:00"}

Extended context progress: {"tokens_processed": 810009, "fraction": 0.78, "prefill_seconds": 2113.4, "checked_at": "2026-10-04T22:23:11.282092+00:00"}

Extended context progress: {"tokens_processed": 900121, "fraction": 0.86, "prefill_seconds": 2563.32, "checked_at": "2026-10-04T22:30:44.494115+00:00"}

Extended context progress: {"tokens_processed": 1001497, "fraction": 0.96, "prefill_seconds": 3120.68, "checked_at": "2026-10-04T22:40:03.383829+00:00"}

{"stage": "maximum_context_gate_passed", "largest_passed_configured_context": 1048576, "largest_passed_actual_prompt": 1044399, "context_decode_tps": 8.344073653779994}

{"stage": "maximum_context_campaign_complete", "largest_passed_configured_context": 1048576}

{"stage": "q4_comparison_running"}

Extended context progress: {"tokens_processed": 16409, "fraction": 0.57, "prefill_seconds": 12.23, "checked_at": "2026-10-04T22:46:05.393631+00:00"}

{"stage": "final_profile_validation", "q4_comparison_return_code": 0}

{"stage": "complete", "maximum_context_verified": true, "selected_profile": {"context": 1048576, "cache": "q4_0", "quant": "q3", "split": "1,1.04", "ubatch": 256}, "final_short_high_tps": 116.62944110532757, "pi_source_verified": false, "pi_tools_verified": true, "pi_default": "kolibri-1", "error": null}

Project evaluation: {"stage": "project_task_running", "project_task": "paths", "completed_project_tasks": 0}

Project evaluation: {"stage": "project_task_completed", "project_task": "paths", "project_result": {"task": "paths", "baseline": {"tests": 4, "failures": 0, "errors": 4, "passed": false, "return_code": 1}, "acceptance": {"tests": 4, "failures": 0, "errors": 0, "passed": true, "return_code": 0}, "scope_ok": true, "passed": true, "pi_return_code": 0, "timeout": false, "wall_seconds": 303.0719348490238, "changed_existing_files": ["common.py", "compact_search.py", "search.py", "enrich.py", "catalog.py"], "new_test_files": ["test_readonly_sqlite.py"], "tool_calls": ["read", "bash", "read", "read", "read", "read", "read", "read", "read", "read", "read", "read", "read", "edit", "edit", "edit", "read", "edit", "edit", "edit", "read", "edit", "read", "edit", "read", "read", "edit", "read", "edit", "read", "edit", "read", "edit", "write", "bash", "bash", "write", "bash", "bash", "bash", "bash", "bash", "bash", "bash", "read", "read", "read", "read", "bash", "read"], "api_requests": 36, "timing_receipts": 36, "weighted_decode_tps": 88.05116194428996, "per_request_decode_tps": [111.82460068285936, 110.65696531540098, 101.99510657752808, 92.9082474827875, 91.53678152137157, 91.01972039763544, 90.76879973790342, 89.05815617866065, 88.16926011382228, 87.71808967452456, 87.25631345997263, 85.81253649434271, 85.36434202802289, 84.63273975220945, 84.31929703076685, 83.36764697353694, 82.76995107202704, 81.8482105447778, 81.51794409899293, 80.77707546598275, 79.96021525462834, 79.32286271545489, 78.32394196395998, 77.93057981506979, 77.30755394306796, 77.33857472938935, 76.93562003853233, 75.79300032372603, 76.46607067459698, 76.2372954896174, 76.0691240914837, 76.21626532088074, 75.977362759796, 73.18299344169289, 72.7733509095871, 72.55410050247745], "decode_seconds": 278.962815, "prompt_seconds": 21.307502, "generated_tokens": 24599, "prompt_tokens_evaluated": 26533, "cached_prompt_tokens": 1157514, "tokens_per_wall_second": 81.16554907089653, "reasoning_effort": "high", "scope": "One first attempt per task; test criteria fixed before generation. Not local.ai benchmark scores."}, "completed_project_tasks": 1}

Project evaluation: {"stage": "project_task_running", "project_task": "inflate", "completed_project_tasks": 1}

Project evaluation: {"stage": "project_task_completed", "project_task": "inflate", "project_result": {"task": "inflate", "baseline": {"tests": 8, "failures": 0, "errors": 2, "passed": false, "return_code": 1}, "acceptance": {"tests": 8, "failures": 0, "errors": 1, "passed": false, "return_code": 1}, "scope_ok": true, "passed": false, "pi_return_code": 0, "timeout": false, "wall_seconds": 334.0766330490005, "changed_existing_files": ["compact_search.py"], "new_test_files": ["test_compact_search.py"], "tool_calls": ["read", "bash", "read", "bash", "read", "read", "read", "bash", "bash", "bash", "read", "bash", "bash", "read", "bash", "bash", "bash", "bash", "bash", "read", "edit", "read", "write", "read", "read", "read", "edit", "bash", "read", "write", "bash", "bash", "read", "read", "edit", "read", "bash", "bash"], "api_requests": 39, "timing_receipts": 39, "weighted_decode_tps": 87.18760377368936, "per_request_decode_tps": [108.07084774277969, 107.86132995221082, 109.11356712350793, 107.74946102967705, 105.33427920800263, 100.948308409196, 103.4445255221768, 100.83808915220094, 100.17848125333502, 100.80272415909893, 98.72515774563249, 98.27072725248495, 96.16758049438621, 95.99161781669507, 95.15466038248198, 93.14039610747656, 91.04172068776765, 89.7583639166512, 89.26551092049348, 85.98936000990874, 84.75173045930374, 84.01275466366256, 82.10086367709697, 80.82568937846985, 79.68787725370996, 78.98176908883137, 77.778956083643, 76.87328046609484, 76.64813343923748, 75.6612273759491, 74.64419599907109, 74.66629907873275, 75.05982802191706, 74.69597649759993, 73.68530812276249, 72.39352213714726, 72.17170203080066, 72.28478232834213, 72.20649917295454], "decode_seconds": 310.65196000000003, "prompt_seconds": 20.288769, "generated_tokens": 27124, "prompt_tokens_evaluated": 25031, "cached_prompt_tokens": 1039881, "tokens_per_wall_second": 81.19095236457798, "reasoning_effort": "high", "scope": "One first attempt per task; test criteria fixed before generation. Not local.ai benchmark scores."}, "completed_project_tasks": 2}

Project evaluation: {"stage": "project_task_running", "project_task": "atomic", "completed_project_tasks": 2}

Project evaluation: {"stage": "project_task_completed", "project_task": "atomic", "project_result": {"task": "atomic", "baseline": {"tests": 5, "failures": 1, "errors": 1, "passed": false, "return_code": 1}, "acceptance": {"tests": 5, "failures": 0, "errors": 0, "passed": true, "return_code": 0}, "scope_ok": true, "passed": true, "pi_return_code": 0, "timeout": false, "wall_seconds": 148.67182688601315, "changed_existing_files": ["common.py"], "new_test_files": ["test_common.py"], "tool_calls": ["read", "bash", "read", "read", "bash", "read", "read", "read", "read", "read", "read", "bash", "bash", "bash", "bash", "bash", "bash", "read", "edit", "read", "edit", "read", "bash", "read", "bash", "bash", "write", "read", "bash", "edit", "bash", "bash", "bash", "read", "bash"], "api_requests": 27, "timing_receipts": 27, "weighted_decode_tps": 97.00572597739506, "per_request_decode_tps": [110.63873862421906, 111.08799226968637, 109.74848782262136, 110.24168192059385, 110.6965544112577, 109.45280438607237, 103.24770828805492, 103.37152336835553, 102.16565972528788, 102.7125568655807, 101.97932600936355, 101.61895938798288, 99.22404415659426, 96.99256370138171, 97.17675676709472, 96.33948198413457, 96.15160742456537, 95.22934512388869, 93.94753693861178, 92.36549686864471, 92.2671808747758, 92.19505384974687, 90.6742430034154, 90.81999898619536, 90.64828732883055, 89.90773916449585, 89.57892330594548], "decode_seconds": 138.280497, "prompt_seconds": 8.664278, "generated_tokens": 13441, "prompt_tokens_evaluated": 10916, "cached_prompt_tokens": 338243, "tokens_per_wall_second": 90.4071758686683, "reasoning_effort": "high", "scope": "One first attempt per task; test criteria fixed before generation. Not local.ai benchmark scores."}, "completed_project_tasks": 3}

Project evaluation: {"stage": "project_task_running", "project_task": "filters", "completed_project_tasks": 3}

Project evaluation: {"stage": "project_task_completed", "project_task": "filters", "project_result": {"task": "filters", "baseline": {"tests": 6, "failures": 0, "errors": 7, "passed": false, "return_code": 1}, "acceptance": {"tests": 6, "failures": 1, "errors": 0, "passed": false, "return_code": 1}, "scope_ok": true, "passed": false, "pi_return_code": 0, "timeout": false, "wall_seconds": 200.11667577701155, "changed_existing_files": ["catalog.py"], "new_test_files": ["test_catalog.py"], "tool_calls": ["read", "bash", "read", "read", "bash", "bash", "bash", "read", "read", "read", "read", "bash", "bash", "bash", "bash", "edit", "read", "write", "bash", "read", "edit", "write", "bash", "read", "edit", "bash", "read", "edit", "bash", "bash", "bash", "bash", "read", "bash", "bash", "bash"], "api_requests": 37, "timing_receipts": 37, "weighted_decode_tps": 93.73910312090823, "per_request_decode_tps": [109.40864626692725, 108.34914428253605, 109.40520039385873, 108.07013751924998, 106.8077384832951, 105.02381414985848, 105.61083090172912, 104.219707053292, 104.0571524939629, 103.94561334519527, 102.12522595206241, 102.17862693108779, 100.80103220256976, 101.4283574165561, 100.4474635743705, 98.33300398416398, 97.7601603678252, 95.72996820054273, 94.47810716637595, 94.12546158782003, 92.16966854369197, 90.92573918147643, 89.83268662116807, 89.50041556496372, 88.2638835673143, 87.07139446198721, 85.8874284530084, 85.23825383435397, 84.94915569481255, 84.60722255929893, 83.65259660253733, 84.07050713198136, 84.19353152406879, 82.83346484160992, 82.79819054547447, 82.2221917695586, 82.43197772787278], "decode_seconds": 184.298755, "prompt_seconds": 13.396172, "generated_tokens": 17313, "prompt_tokens_evaluated": 17038, "cached_prompt_tokens": 648581, "tokens_per_wall_second": 86.51452925038461, "reasoning_effort": "high", "scope": "One first attempt per task; test criteria fixed before generation. Not local.ai benchmark scores."}, "completed_project_tasks": 4}

Project evaluation: {"stage": "project_evaluation_complete", "project_tasks_passed": 2, "project_tasks_total": 4, "project_study": "project-study/receipts/summary.json"}

Real-project study complete: 2/4 tasks accepted, 21/23 frozen test methods passed, weighted decode 90.26 tok/s including high reasoning, median task 251.59 seconds. Failures: exception-contract mismatch and positional API regression. No local.ai rank can be derived. Original project unchanged; benchmark proxy closed.
