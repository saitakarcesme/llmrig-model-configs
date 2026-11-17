#!/bin/bash
# GPU1: container control vs production baseline, then in-process prefill profile.
. /home/isa/Projects/llmrig/candidates/elpis-plus-20261108/window/common.sh
cand_run ep-g1 1 18031 -- "${SERVE_ARGS[@]}"; wait_ready 18031 || { log g1 not ready; exit 1; }
log g1 ready
gate 18031 g1-control-short short --repeat 1
gate 18031 g1-control-long long --repeat 2 --prompt-file $W/long-prompt.txt
docker rm -f ep-g1 >/dev/null
cand_run ep-g1p 1 18031 -- -B /work/bench/gate/profile_prefill.py --text /work/long-prompt.txt --out /work/results/g1-profile --tokens 260000
docker wait ep-g1p; docker logs ep-g1p > $W/results/g1-profile.log 2>&1; docker rm ep-g1p >/dev/null
log g1 done
