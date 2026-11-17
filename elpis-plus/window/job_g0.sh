#!/bin/bash
# GPU0: prefill knob sweep, each config = fresh server + 1 cold 262K request; control first and last.
. /home/isa/Projects/llmrig/candidates/elpis-plus-20261108/window/common.sh
for cfg in "c0-control" "c1-attn-triton:-e EXL3_PREFILL_ATTN=triton" "c2-twopass128:-e EXL3_QC_PF_TWO_PASS_MIN_Q=128" \
           "c3-twopass1024:-e EXL3_QC_PF_TWO_PASS_MIN_Q=1024" "c4-ns1:-e EXL3_QC_PREFILL_NS=1" "c5-ns2:-e EXL3_QC_PREFILL_NS=2" "c6-control"; do
  name=${cfg%%:*}; envs=(); [[ $cfg == *:* ]] && read -ra envs <<< "${cfg#*:}"
  cand_run ep-g0 0 18030 "${envs[@]}" -- "${SERVE_ARGS[@]}"
  wait_ready 18030 || { log g0 $name not ready; docker logs ep-g0 > $W/results/g0-$name.fail.log 2>&1; continue; }
  gate 18030 g0-$name long --repeat 1 --prompt-file $W/long-prompt.txt
  docker rm -f ep-g0 >/dev/null
done
log g0 done
