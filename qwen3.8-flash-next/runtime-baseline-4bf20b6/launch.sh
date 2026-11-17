#!/usr/bin/env bash
set -euo pipefail
ROOT=${FLASHNEXT_ROOT:-/home/isa/Experiments/qwen38-flash-next-b70-fit}
IMAGE=${FLASHNEXT_IMAGE:-ghcr.io/0xsero/sglang-exl3@sha256:84f75f3424c99a3d63392a4e0348292bdeba9cf7efba2ff1aa9b85c8fc0131e8}
NAME=${FLASHNEXT_CONTAINER:-flashnext-api}
if docker container inspect "$NAME" >/dev/null 2>&1; then
  docker stop "$NAME" >/dev/null
  docker rename "$NAME" "$NAME-previous-$(date -u +%Y%m%dT%H%M%S)"
fi
mkdir -p "$ROOT/receipts"
docker run -d --name "$NAME" --restart unless-stopped --gpus all --memory 20g --memory-swap 20g --shm-size 2g \
  -e FLASHNEXT_FUSED_DECODE=1 -e FLASHNEXT_FUSED_PREFILL=1 -e EXLLAMA_NO_P2P_COPY=1 \
  -e FLASHNEXT_CONTEXT="${FLASHNEXT_CONTEXT:-65536}" -e FLASHNEXT_CHUNK="${FLASHNEXT_CHUNK:-4096}" \
  -e FLASHNEXT_RECURRENT_CACHE_MB="${FLASHNEXT_RECURRENT_CACHE_MB:-4096}" \
  -e FLASHNEXT_VISION_DEVICE="${FLASHNEXT_VISION_DEVICE:-0}" \
  -e FLASHNEXT_GPU_CACHE="${FLASHNEXT_GPU_CACHE:-10,20}" -e FLASHNEXT_HOST_CACHE="${FLASHNEXT_HOST_CACHE:-1.5}" \
  -p 127.0.0.1:30260:30260 -v "$ROOT/models:/work/models:ro" \
  -v "$ROOT/runtime:/work/runtime:ro" -v "$ROOT/receipts:/work/receipts" \
  -w /work/runtime --entrypoint python3 "$IMAGE" server.py
for attempt in $(seq 1 120); do
  if curl -fsS http://127.0.0.1:30260/health >/dev/null 2>&1; then
    echo 'Ready: http://127.0.0.1:30260/v1 (model: flashnext)'
    exit 0
  fi
  if [ "$(docker inspect --format '{{.State.Running}}' "$NAME")" != true ]; then
    docker logs --tail 20 "$NAME"
    exit 1
  fi
  sleep 1
done
docker logs --tail 20 "$NAME"
echo 'Service did not become ready within 120 seconds.' >&2
exit 1
