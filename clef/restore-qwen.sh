#!/bin/bash
set -euo pipefail
for name in clef-flash-live clef-pi-qwen; do
 if docker inspect "$name" --format '{{.State.Running}}' 2>/dev/null | grep -q true; then docker stop --time 30 "$name"; fi
done
if [ "$(docker inspect hyperqwen-live-tp2-262k --format '{{.State.Running}}' 2>/dev/null || true)" = true ]; then
 echo 'Original 262K profile is already running.'
else
 systemd-run --user --unit=hyperqwen-restored-262k /usr/bin/docker start -a hyperqwen-live-tp2-262k
fi
