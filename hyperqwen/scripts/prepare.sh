#!/bin/bash
set -euo pipefail
ROOT=/home/isa/Experiments/hyperqwen-fit
while systemctl --user is-active --quiet hyperqwen-download-models.service; do sleep 5; done
"$ROOT/../dsv41-fit/tools/bin/python" -c 'import json; from pathlib import Path; r=Path("/home/isa/Experiments/hyperqwen-fit"); assert len(json.loads((r/"receipts/download_verification.json").read_text()))==3'
cp "$ROOT/receipts/model_manifest.json" "$ROOT/pristine/manifest.json"
cp -a --reflink=auto "$ROOT/pristine/Qwen3.8-27B-W4A16-AutoRound" "$ROOT/models/"
docker run --name hyperqwen-cpu-prepare --network none --memory 22g --memory-swap 22g --shm-size 1g -v "$ROOT/models:/app/models" -v "$ROOT/cache:/cache" -v "$ROOT/pristine:/pinned:ro" -v "$ROOT/pinned-prepare:/app/prepare:ro" ghcr.io/syv-ai/hyperqwen@sha256:00713ba1e04b68db1be9eba2b15b579250f9fb0c29ed61add40c750228fc0cf8 prepare
