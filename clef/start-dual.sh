#!/bin/bash
set -euo pipefail
ROOT=/home/isa/Experiments/clef-fit
if [ "$(docker inspect clef-pi-qwen --format '{{.State.Running}}' 2>/dev/null || true)" = true ] && [ "$(docker inspect clef-flash-live --format '{{.State.Running}}' 2>/dev/null || true)" = true ]; then
 echo 'Dual profile is already running.'; exit 0
fi
if curl -fsS http://127.0.0.1:18020/metrics | grep -Eq '^vllm:num_requests_(running|waiting)\{.*\} [1-9]'; then
 echo 'Qwen has active requests; try again after completion.' >&2; exit 1
fi
if docker inspect hyperqwen-live-tp2-262k --format '{{.State.Running}}' 2>/dev/null | grep -q true; then docker stop --time 30 hyperqwen-live-tp2-262k; fi
if docker inspect clef-pi-qwen >/dev/null 2>&1; then
 systemd-run --user --unit=clef-pi-qwen /usr/bin/docker start -a clef-pi-qwen
else
 EXTRA_ARGS='--tensor-parallel-size 2 --disable-custom-all-reduce --gpu-memory-utilization 0.60 --max-model-len 32768' systemd-run --user --unit=clef-pi-qwen --setenv=EXTRA_ARGS='--tensor-parallel-size 2 --disable-custom-all-reduce --gpu-memory-utilization 0.60 --max-model-len 32768' /home/isa/Experiments/hyperqwen-fit/scripts/start_live_tp2.sh dflash2 clef-pi-qwen 7
fi
if docker inspect clef-flash-live >/dev/null 2>&1; then
 systemd-run --user --unit=clef-flash-live /usr/bin/docker start -a clef-flash-live
else
 systemd-run --user --unit=clef-flash-live "$ROOT/run-server.sh" clef-flash nf4 clef-flash-live
fi
