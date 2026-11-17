#!/usr/bin/env bash
set -euo pipefail
ROOT=${FLASHNEXT_ROOT:-/home/isa/Experiments/qwen38-flash-next-b70-fit}
IMAGE=${FLASHNEXT_IMAGE:-ghcr.io/0xsero/sglang-exl3@sha256:84f75f3424c99a3d63392a4e0348292bdeba9cf7efba2ff1aa9b85c8fc0131e8}
SOURCE=$(cd -- "$(dirname -- "$0")" && pwd)
REVISION=69e33439ae950f17bcbe95c98f117d80f759ab6d
mkdir -p "$ROOT/runtime" "$ROOT/models/flashnext-3.05bpw" "$ROOT/receipts"
if [ "$SOURCE" != "$ROOT/runtime" ]; then
  cp "$SOURCE"/*.py "$SOURCE"/launch.sh "$SOURCE"/install.sh "$SOURCE"/README.md "$ROOT/runtime/"
fi
if [ ! -d "$ROOT/upstream/.git" ]; then
  git clone https://github.com/0xSero/qwen38-flash-next-b70-offload "$ROOT/upstream"
  git -C "$ROOT/upstream" checkout --detach 30d1b5b94d15f020ed926350d37341d7269d3692
fi
docker pull "$IMAGE"
docker run --rm -v "$ROOT/models:/work/models" --entrypoint hf "$IMAGE" \
  download turboderp/Qwen3.8-Flash-Next-exl3 --revision "$REVISION" \
  --local-dir /work/models/flashnext-3.05bpw --max-workers 2
docker run --rm -v "$ROOT/models:/work/models:ro" --entrypoint hf "$IMAGE" \
  cache verify turboderp/Qwen3.8-Flash-Next-exl3 --revision "$REVISION" \
  --local-dir /work/models/flashnext-3.05bpw
echo "Checkpoint verified. Start the service with: bash $ROOT/runtime/launch.sh"
