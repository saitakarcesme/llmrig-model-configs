#!/bin/bash
set -euo pipefail
export PI_CODING_AGENT_DIR=/home/isa/Experiments/clef-fit/pi-agent
export CLEF_URL=http://127.0.0.1:18031
cd /home/isa/Experiments/clef-fit
exec /home/isa/.local/share/mise/installs/node/26.8.2/bin/node /home/isa/.local/share/mise/installs/node/26.8.2/lib/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js --offline --provider hyperqwen --model qwen3.8-27b --thinking off --no-context-files --no-extensions --no-skills --no-prompt-templates -e /home/isa/Experiments/clef-fit/clef-tool.ts "$@"
