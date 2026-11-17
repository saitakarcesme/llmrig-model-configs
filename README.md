# LLMRig model configurations

Launch scripts, serving profiles, patches and measured results for the models tried on one home rig: two RTX 3090 24 GB GPUs (PCIe x16/x4, no NVLink), an i5-14400F and 32 GB DDR4.

Weights, caches, build trees and upstream clones are not included. Each folder pins the model revision, runtime commit and image digest it used, so the setup can be rebuilt. Paths like `/home/isa/...` are the rig's own layout.

| Folder | Model / work | What is in it |
| --- | --- | --- |
| [`elpis-plus/`](elpis-plus/) | Qwen3.8-27B on Elpis, feature work (in progress) | Native sampling patch (greedy parity 8/8), GPU window scripts with lease/deadman/restore, gate results |
| [`qwen3.8-flash-next/`](qwen3.8-flash-next/) | Qwen3.8-Flash-Next EXL3 with expert offload | Runtime notes, vision MRoPE fix, evaluation matrix and receipts |
| [`kolibri-1/`](kolibri-1/) | Kolibri 1 (Q3_K_S / Q4_K_XL GGUF, llama.cpp) | Selected 1M-context profile, context ladder, scripts |
| [`hyperqwen/`](hyperqwen/) | HyperQwen DFlash / MTP arms | Comparison report, launch scripts, receipts |
| [`clef/`](clef/) | Clef (BF16 / NF4) | Server, launch scripts, length benchmark, receipts |
| [`rig-extensions/`](rig-extensions/) | Whisper, OCR, PDF and embedding extensions for the router | Worker, Dockerfile, live and public test results |

Models with their own repositories:

- Qwen3.8-27B Elpis production serving: [qwen3.8-27b-elpis-serving](https://github.com/saitakarcesme/qwen3.8-27b-elpis-serving)
- Qwen3.8-27B 1 vs 2 GPU recipe: [qwen38-27b-dual3090-recipe](https://github.com/saitakarcesme/qwen38-27b-dual3090-recipe)
- GLM-5.3-Flash: [glm5.3-flash-2x3090](https://github.com/saitakarcesme/glm5.3-flash-2x3090)
- Rig monitor: [large-language-model-monitor](https://github.com/saitakarcesme/large-language-model-monitor)

All numbers are measurements on this rig, not reproductions of upstream claims.
