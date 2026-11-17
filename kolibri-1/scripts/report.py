import json,pathlib
ROOT=pathlib.Path('/home/isa/Experiments/kolibri-fit')
load=lambda p:json.loads((ROOT/p).read_text())
state=load('LOOP_STATE.json')
assert state['stage']=='complete'
profile=load('selected-profile.json')
rows=[]
for cap in [32768,131072,262144,524288,1048576]:
    p=ROOT/'receipts'/f'context-{cap}-first.json'
    if p.exists():
        r=json.loads(p.read_text());rows.append(f"| {cap:,} | {r['usage']['prompt_tokens']:,} | {r['timings']['predicted_per_second']:.2f} | {r['ttft_seconds']:.2f} s | {r['marker_check_passed']} |")
q4p=ROOT/'q4-study/receipts/summary.json'
q4=json.loads(q4p.read_text()) if q4p.exists() else {'result':'Comparison did not complete; inspect q4 logs and failed startup receipts.'}
speed=load('receipts/final-profile-speed.json');pi=load('receipts/pi-source-summary.json')
text=f'''# Kolibri 1 on LLMRig

Completed finite experiment on two RTX 3090 24 GB GPUs, i5-14400F, 32 GiB RAM. Pi is configured for Kolibri with high effort. Existing Qwen gateway and Ollama were stopped with user authorization. No new repository push was requested.

## Selected serving profile

```json
{json.dumps(profile,indent=2)}
```

All model layers are on GPU, one interactive slot, flash attention, layer splitting, no context shifting. Invoke `/home/isa/.local/bin/llmrig-pi` on the rig. It checks/starts this profile and launches Pi directly without mise's automatic dependency update. Original Pi settings, provider definitions and launcher are backed up in the rig's private experiment folder; they are not exported.

Short-prompt high-effort decode in the final configured slot: **{speed['high_median_tps']:.2f} tok/s**, median of three 512-token runs. These include thinking tokens and stop at the output cap; they do not measure time to a complete answer.

## Measured context ladder

| Configured context | Actual input tokens | Decode tok/s | First output / cold prefill | Three markers correct |
| ---: | ---: | ---: | ---: | --- |
{chr(10).join(rows)}

The 32K, 128K and 262K trials use Q8 KV. The 1M trial uses Q4 KV. See individual receipts for any 524K fallback. All retrieval requests disable thinking and prompt reuse. Three-position retrieval is a narrow synthetic gate, not a general million-token project-quality benchmark. Long-context rates use 53-token answers and are single measurements.

Original short-prompt baseline in a 32K/Q8 slot: thinking off **117.12 tok/s**, high effort **116.84 tok/s**, both medians of three runs. At 257,933 input tokens Q3/Q8 delivered **29.41 tok/s**, with about **5 minutes** of first prompt reading. The upstream recommends at most 262,144 context for efficiency and complex tasks. This remains the practical project starting point even when a larger slot is available.

## Q4 weight comparison

```json
{json.dumps(q4,indent=2)}
```

Q4 at 128K failed CUDA allocation; its fallback 32K profile passed the three-marker gate. Its short high-effort median was 118.74 tok/s, a small difference from Q3 that does not demonstrate a substantial advantage. The larger quant is not certified better on real tasks. Selected Q3 preserves every routed/shared expert and provides room for the largest tested context; no expert pruning was applied.

## Actual Pi verification

Initial high-effort Pi tool round trip passed read + write, producing the correct arithmetic JSON in **6.61 seconds**. The final selected profile completed actual Pi read/write calls. Structured code comprehension gate result: **{pi['passed']}**, **{pi['seconds']:.2f} seconds**. The final comprehension gate failed: four of five fields were correct, but the model incorrectly marked the direct-API long-context test as using Pi. The initial attempt wrote correct content to the parent directory; an explicit output path fixed placement on the second attempt. No third retry was used to force a passing score. These are bounded fixtures; they do not certify arbitrary project editing.

## Reproducibility and limits

- [Original Kolibri 1](https://huggingface.co/Aleph-Alpha/Kolibri-1): 78.10B total / 3.46B active parameters. Native context 262,144, documented extension 1,048,576.
- Q3_K_S: `Eliasfpv28/Kolibri-1-Q3_K_S-GGUF`, revision `04f6e403e0db21f5ecb9d1c142f69204a43fe1e7`, 33,870,242,400 bytes. All 16 published package checksums passed. Main SHA256 `26ce4a2f618e3d55d401faaa78bb144057268b8303e645b6e3d552258d1d34aa`.
- Q4_K_XL: `InsidiousFiddler/Kolibri-1-GGUF`, revision `3526916afa56f68b5475e1d85389f052c1be3b52`, 47,442,951,904 bytes. SHA256 `8b45804b524440b7da9779bb2ee8877165fb56b1175233811a447742afa4c195` verified.
- llama.cpp `edd6e2bbdad5930899a93db8fa73c3b61c7b9bcc`, independent experimental Kolibri architecture patch bundled with the Q3 release, CUDA SM86 build. Runtime image `ghcr.io/0xsero/sglang-exl3@sha256:84f75f3424c99a3d63392a4e0348292bdeba9cf7efba2ff1aa9b85c8fc0131e8`.

Q8 KV at 1M failed CUDA buffer allocation. Q4 KV fit with roughly 0.4–0.6 GiB VRAM spare per GPU during prefill; this is tight. The pinned server initially capped extended requests at training metadata; `--override-kv kolibri1.context_length=int:1048576` removed that runtime cap. Original GGUF bytes and RoPE scaling are unchanged. Receipt correctness, rather than successful allocation alone, determined the chosen context. Host swap was already in use; no claim of zero system-wide swap is made. The serving container has a 24 GiB host memory limit with no additional container swap.

To switch to the measured practical 262K/Q8 profile on the rig: `python3 /home/isa/Experiments/kolibri-fit/scripts/select_profile.py practical`, then restart Pi. Use `maximum` instead to restore the 1M/Q4 profile. Switching stops only experiment serving containers.

Quantized outputs are not certified equivalent to original FP8/BF16. Rates are the best measured profiles in this finite study, not proof of a global optimum. Model weights, full runtime sources and private Pi logs/configurations stay on LLMRig. Local exports include experiment scripts and sanitized numeric evidence only.
'''
(ROOT/'README.md').write_text(text)
print('Report generated.')
