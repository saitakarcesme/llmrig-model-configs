#!/bin/bash
set -euo pipefail
ROOT=/home/isa/Projects/llmrig/repos/homelab-exl3
export PYTHONPATH="$ROOT" CUDA_VISIBLE_DEVICES=0,1 AGENTIC_TP=1 RESEARCH_PROFILE=hyperqwen-baseline
export AGENTIC_ACTIVE=/home/isa/Experiments/hyperqwen-fit/receipts/baseline-active.json AGENTIC_REQUESTS=/dev/null RESEARCH_TIMINGS=/home/isa/Experiments/hyperqwen-fit/receipts/baseline-timings.jsonl
exec "$ROOT/.venv/bin/python" -u "$ROOT/tools/serve_openai.py" -m /home/isa/models/homelab-qwen38-3.5bpw -gs 21,21 -cs 262144 -cq 4 -dm mtp --host 127.0.0.1 --port 18019 --model_id qwen3.8:27b --vision off --ui off
