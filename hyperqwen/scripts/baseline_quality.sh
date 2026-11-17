#!/bin/bash
set -euo pipefail
while systemctl --user is-active --quiet hyperqwen-project-baseline-v2.service; do sleep 5; done
python3 -c 'import json; from pathlib import Path; p=Path("/home/isa/Experiments/hyperqwen-fit/project-exl3-mtp-v2/receipts/summary.json"); assert len(json.loads(p.read_text())["tasks"])==4'
exec python3 /home/isa/Experiments/hyperqwen-fit/scripts/quality.py exl3-mtp 18019 qwen3.8:27b
