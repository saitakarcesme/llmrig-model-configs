#!/bin/bash
# GPU1 after the profile: elpis-plus 0001 sampling patch — greedy parity/speed vs production, sampled speed, functional.
. /home/isa/Projects/llmrig/candidates/elpis-plus-20261108/window/common.sh
P=("${SERVE_ARGS[@]}"); P[1]=/work/serve/exl3_server.py
cand_run ep-g1s 1 18031 -- "${P[@]}"; wait_ready 18031 || { log g1b not ready; docker logs ep-g1s > $W/results/g1b.fail.log 2>&1; exit 1; }
log g1b ready
gate 18031 g1s-greedy-short short --repeat 1
gate 18031 g1s-sampled-short short --repeat 1 --sampling '{"temperature":1.0,"top_p":0.95,"top_k":20}'
python3 $W/bench/gate/sample_test.py 18031 $W/results/g1s-functional.json
docker logs ep-g1s > $W/results/g1s-server.log 2>&1; docker rm -f ep-g1s >/dev/null
log g1b done
