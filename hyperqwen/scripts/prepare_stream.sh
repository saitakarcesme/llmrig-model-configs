#!/bin/bash
set -euo pipefail
ROOT=/home/isa/Experiments/hyperqwen-fit
docker run --name hyperqwen-cpu-prepare-v2 --network none --memory 18g --memory-swap 18g --shm-size 1g -e OMP_NUM_THREADS=4 -e MKL_NUM_THREADS=4 -v "$ROOT/models:/app/models" -v "$ROOT/cache:/cache" -v "$ROOT/pristine:/pinned:ro" -v "$ROOT/pinned-prepare:/app/prepare:ro" ghcr.io/syv-ai/hyperqwen@sha256:00713ba1e04b68db1be9eba2b15b579250f9fb0c29ed61add40c750228fc0cf8 bash -c 'export PATH=/app/venv/bin:$PATH; python prepare/quant_heads_stream.py /app/models/Qwen3.8-27B-W4A16-AutoRound && bash docker/prepare.sh'
