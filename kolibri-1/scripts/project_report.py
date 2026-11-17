import pathlib,json,statistics,datetime
ROOT=pathlib.Path('/home/isa/Experiments/kolibri-fit');S=ROOT/'project-study'
summary=json.loads((S/'receipts/summary.json').read_text());manifest=json.loads((S/'manifest.json').read_text())
requests=[json.loads(l) for l in (S/'receipts/requests.jsonl').read_text().splitlines()]
names={'paths':'Read-only SQLite filenames across five modules','inflate':'Bounded compressed-block decoding','atomic':'Concurrent atomic JSON evidence writes','filters':'Catalog name/city filters with source separation'}
rows=[]
for r in summary['tasks']:
 a=r['acceptance'];count=a['tests']-a['failures']-a['errors']
 rows.append(f"| {names[r['task']]} | {r['weighted_decode_tps']:.2f} | {r['wall_seconds']/60:.2f} min | {count}/{a['tests']} | {r['passed']} |")
timings=[r['timings'] for r in requests if r.get('timings')]
rate=sum(max(0,r['predicted_n']-1) for r in timings)/(sum(r['predicted_ms'] for r in timings)/1000)
peaks={t:max((r.get('usage',{}).get('prompt_tokens',0) for r in requests if r['task']==t),default=0) for t in names}
comparison={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':'https://local.ai/about','model_table_url':'https://local.ai/models','observed_model_table':'Redirects to /access?next=%2Fmodels, Hugging Face sign-in required. No account created or profile submitted.','intelligence_formula':{'tau2_bench':0.02,'GAIA':0.36,'GDPval':0.62},'our_official_scores':{'tau2_bench':None,'GAIA':None,'GDPval':None},'our_local_ai_intelligence_index':None,'our_local_ai_rank':None,'reason':'Four PocketLore maintenance tasks are not the three benchmark cohorts, their scoring protocols, or local.ai model/quant/harness configurations. Missing benchmarks cannot be assigned zero or replaced by project test pass rates.'}
(S/'receipts/local-ai-comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
text=f'''# Kolibri real-project evaluation on LLMRig

**{summary['tasks_passed']}/{summary['tasks_total']} selected project tasks passed.** Whole-study weighted server decode throughput was **{rate:.2f} tok/s**, including high-effort reasoning. Median task completion took **{summary['median_task_seconds']/60:.2f} minutes**. These are different measurements: tok/s describes generation, while task time includes reading, thinking, tool calls, self-tests and repairs.

| Project task | Weighted decode tok/s | End-to-end time | Hidden test methods passed | Task accepted |
| --- | ---: | ---: | ---: | --- |
{chr(10).join(rows)}

Two tasks were not accepted. The decoder still raised `zlib.error` instead of the required `ValueError` for corrupt input. The catalog added working filters but reordered existing positional parameters, breaking legacy calls. Both failed artifacts were preserved without a hidden-grader-guided retry.

## Exact setup

PocketLore revision `{summary['revision']}`, frozen tracked source from `tools/scale/places`. Six original Python modules and Apache-2.0 license were copied to four independent workspaces on LLMRig. The working PocketLore tree was not edited, no model-generated change was committed, pushed or applied to production, and its existing untracked file was preserved. Original source digests and task instructions are in the manifest.

Pi used `Kolibri-1 Q3_K_S`, high effort, read/write/edit/bash tools, one slot, fully GPU-offloaded on two RTX 3090s. Configured serving profile:

```json
{json.dumps(summary['context_profile'],indent=2)}
```

A Bubblewrap sandbox exposed the task workspace as writable and hid the original Projects directory, grader directory and experiment scripts. Pi used a separate minimal configuration containing only the local benchmark provider. No original Pi credentials were copied. The transparent loopback proxy forwarded Pi requests to the existing server and collected timing/usage metadata; full source prompts and raw agent output stay on the rig.

## Grading and timing

The model got the task brief and source, then implemented and ran its own tests. The acceptance grader was frozen and hashed before model generation, masked during the Pi session and only run after the session ended. Each task had one independent agent session with at most 15 minutes; self-repairs inside that session are allowed, but no hidden-grader feedback was provided to the model. The original snapshot failed each requested-change gate. An independently written reference fixture passed all 23 test methods, confirming the grader is satisfiable; the model could not read this fixture.

Acceptance checks cover special URI characters/read-only behavior, decompression limits/corruption/hash validation, concurrent write races/failure cleanup, and correct filter forwarding/source separation. Grading also checks existing-file edit scope and exit status. This is functional coverage of four selected maintenance changes, not human acceptance, Android device validation or a representative coding leaderboard.

Decode TPS uses the server's measured inter-token generation rate. For aggregation, sum `(predicted_n - 1)` and divide by summed `predicted_ms`; do not average SSE chunks or equate task duration to decode time. Prompt prefix caching was retained as in normal multi-turn Pi use; cached tokens are included in receipts, so these are not cold-prompt throughput tests. Aggregate request count is {len(requests)}. Peak actual prompt tokens by task: `{json.dumps(peaks)}`. A configured 1M window does not mean each project task used a million tokens.

## local.ai comparison

[local.ai's published methodology](https://local.ai/about) combines three benchmark scores: 2% τ²-bench, 36% GAIA and 62% GDPval. All three must be completed for the exact model variation before an Intelligence Index is assigned; missing scores are not treated as zero. Its speed index uses weighted end-to-end evaluation task times.

**No defensible local.ai rank or Intelligence Index was produced.** The Models page redirected to an access screen requiring Hugging Face sign-in. More importantly, these four coding maintenance tasks do not provide the three required evaluation scores. Even access to the table would not turn our project pass rate into a comparable leaderboard score. Official-cohort evaluation and the same harness, quantization/configuration and grading methodology are prerequisites for a valid rank. No result was submitted to the site.

`receipts/local-ai-comparison.json` keeps unavailable official scores and rank explicitly null. Project task pass rate is never relabeled as the local.ai Intelligence Index.

## Evidence

Per-task baseline/final grader logs, source snapshots, edits, model-written tests and raw Pi transcripts remain under `/home/isa/Experiments/kolibri-fit/project-study` on LLMRig. Numeric request timings and sanitized summary JSON can be exported to the local experiment folder. The selected Kolibri server and user's normal Pi profile remain ready after this finite campaign; the benchmark proxy shuts down when the campaign ends.
'''
(S/'README.md').write_text(text)
print(json.dumps({'tasks_passed':summary['tasks_passed'],'tasks_total':summary['tasks_total'],'weighted_decode_tps':rate,'median_task_seconds':summary['median_task_seconds'],'peak_prompt_tokens':peaks,'local_ai_rank':None}))
