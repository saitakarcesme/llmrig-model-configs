#!/bin/bash
set -euo pipefail
printf "HyperQwen. Two RTX 3090s. 262144 token context. DFlash7. Highest reasoning.\nWaiting for local model server...\n"
for ((i=0;i<120;i++)); do
 if curl -fsS --max-time 2 http://127.0.0.1:18020/health >/dev/null 2>&1; then exec /home/isa/Experiments/hyperqwen-fit/scripts/pi_live_tp2.sh; fi
 sleep 5
done
printf "Server startup timed out. Check hyperqwen-live-tp2.service.\n"
exec /bin/bash
