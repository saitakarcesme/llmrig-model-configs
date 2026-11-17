# Kolibri real-project evaluation on LLMRig

**2/4 selected project tasks passed.** Whole-study weighted server decode throughput was **90.26 tok/s**, including high-effort reasoning. Median task completion took **4.19 minutes**. These are different measurements: tok/s describes generation, while task time includes reading, thinking, tool calls, self-tests and repairs.

| Project task | Weighted decode tok/s | End-to-end time | Hidden test methods passed | Task accepted |
| --- | ---: | ---: | ---: | --- |
| Read-only SQLite filenames across five modules | 88.05 | 5.05 min | 4/4 | True |
| Bounded compressed-block decoding | 87.19 | 5.57 min | 7/8 | False |
| Concurrent atomic JSON evidence writes | 97.01 | 2.48 min | 5/5 | True |
| Catalog name/city filters with source separation | 93.74 | 3.34 min | 5/6 | False |

Two tasks were not accepted. The decoder still raised `zlib.error` instead of the required `ValueError` for corrupt input. The catalog added working filters but reordered existing positional parameters, breaking legacy calls. Both failed artifacts were preserved without a hidden-grader-guided retry.

## Exact setup

PocketLore revision `e6287d0a1eccb716c4424803c85bcc5fc7356eb5`, frozen tracked source from `tools/scale/places`. Six original Python modules and Apache-2.0 license were copied to four independent workspaces on LLMRig. The working PocketLore tree was not edited, no model-generated change was committed, pushed or applied to production, and its existing untracked file was preserved. Original source digests and task instructions are in the manifest.

Pi used `Kolibri-1 Q3_K_S`, high effort, read/write/edit/bash tools, one slot, fully GPU-offloaded on two RTX 3090s. Configured serving profile:

```json
{
  "context": 1048576,
  "cache": "q4_0",
  "quant": "q3",
  "split": "1,1.04",
  "ubatch": 256
}
```

A Bubblewrap sandbox exposed the task workspace as writable and hid the original Projects directory, grader directory and experiment scripts. Pi used a separate minimal configuration containing only the local benchmark provider. No original Pi credentials were copied. The transparent loopback proxy forwarded Pi requests to the existing server and collected timing/usage metadata; full source prompts and raw agent output stay on the rig.

## Grading and timing

The model got the task brief and source, then implemented and ran its own tests. The acceptance grader was frozen and hashed before model generation, masked during the Pi session and only run after the session ended. Each task had one independent agent session with at most 15 minutes; self-repairs inside that session are allowed, but no hidden-grader feedback was provided to the model. The original snapshot failed each requested-change gate. An independently written reference fixture passed all 23 test methods, confirming the grader is satisfiable; the model could not read this fixture.

Acceptance checks cover special URI characters/read-only behavior, decompression limits/corruption/hash validation, concurrent write races/failure cleanup, and correct filter forwarding/source separation. Grading also checks existing-file edit scope and exit status. This is functional coverage of four selected maintenance changes, not human acceptance, Android device validation or a representative coding leaderboard.

Decode TPS uses the server's measured inter-token generation rate. For aggregation, sum `(predicted_n - 1)` and divide by summed `predicted_ms`; do not average SSE chunks or equate task duration to decode time. Prompt prefix caching was retained as in normal multi-turn Pi use; cached tokens are included in receipts, so these are not cold-prompt throughput tests. Aggregate request count is 139. Peak actual prompt tokens by task: `{"paths": 50552, "inflate": 51273, "atomic": 24083, "filters": 33895}`. A configured 1M window does not mean each project task used a million tokens.

## local.ai comparison

[local.ai's published methodology](https://local.ai/about) combines three benchmark scores: 2% τ²-bench, 36% GAIA and 62% GDPval. All three must be completed for the exact model variation before an Intelligence Index is assigned; missing scores are not treated as zero. Its speed index uses weighted end-to-end evaluation task times.

**No defensible local.ai rank or Intelligence Index was produced.** The Models page redirected to an access screen requiring Hugging Face sign-in. More importantly, these four coding maintenance tasks do not provide the three required evaluation scores. Even access to the table would not turn our project pass rate into a comparable leaderboard score. Official-cohort evaluation and the same harness, quantization/configuration and grading methodology are prerequisites for a valid rank. No result was submitted to the site.

`receipts/local-ai-comparison.json` keeps unavailable official scores and rank explicitly null. Project task pass rate is never relabeled as the local.ai Intelligence Index.

## Evidence

Per-task baseline/final grader logs, source snapshots, edits, model-written tests and raw Pi transcripts remain under `/home/isa/Experiments/kolibri-fit/project-study` on LLMRig. Numeric request timings and sanitized summary JSON can be exported to the local experiment folder. The selected Kolibri server and user's normal Pi profile remain ready after this finite campaign; the benchmark proxy shuts down when the campaign ends.
