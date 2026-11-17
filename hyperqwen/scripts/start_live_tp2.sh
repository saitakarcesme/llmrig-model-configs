#!/bin/bash
set -euo pipefail
ROOT=/home/isa/Experiments/hyperqwen-fit
SPEC=${1:?spec}; NAME=${2:?name}; TOKENS=${3:-7}
REQUEST_METRICS=1
if [ "$SPEC" = off ]; then REQUEST_METRICS=0; fi
exec docker run --name "$NAME" --gpus "${HYPER_GPUS:-all}" --memory 24g --memory-swap 24g --shm-size 4g -p 127.0.0.1:18020:18020 -v "$ROOT/models:/app/models:ro" -v "$ROOT/cache:/cache" -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 -e PREPARE=0 -e VERIFY=1 -e SPEC="$SPEC" -e DFLASH_TOKENS="$TOKENS" -e VLLM_DFLASH2_LOOKUP_ADAPTIVE -e CTX=fast -e MAX_LEN=262144 -e MAX_SEQS=1 -e MODEL=/app/models/Qwen3.8-27B-W4A16-AutoRound-fast -e DRAFT=/app/models/Qwen3.8-27B-DFlash2-W4A16 -e PORT=18020 -e PREFIX_CACHE=1 -e REQ_METRICS="$REQUEST_METRICS" -e VLLM_OFFLOAD_KEEP_SHM=1 -e OMP_NUM_THREADS=6 -e EXTRA_ARGS="${EXTRA_ARGS:---tensor-parallel-size 2 --disable-custom-all-reduce}" ghcr.io/syv-ai/hyperqwen@sha256:00713ba1e04b68db1be9eba2b15b579250f9fb0c29ed61add40c750228fc0cf8 single
