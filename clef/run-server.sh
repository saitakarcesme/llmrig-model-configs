#!/bin/bash
set -euo pipefail
ROOT=/home/isa/Experiments/clef-fit
MODEL=${1:-clef-flash}; PRECISION=${2:-nf4}; NAME=${3:-clef-server}
exec docker run --name "$NAME" --gpus device=0 --memory 24g --memory-swap 28g -p 127.0.0.1:18031:18031 --entrypoint /app/venv/bin/python -e PYTHONPATH=/deps -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 -e OMP_NUM_THREADS=6 -v "$ROOT/models:/models:ro" -v "$ROOT/deps:/deps:ro" -v "$ROOT:/work" ghcr.io/syv-ai/hyperqwen@sha256:00713ba1e04b68db1be9eba2b15b579250f9fb0c29ed61add40c750228fc0cf8 /work/server.py --model "$MODEL" --precision "$PRECISION"
