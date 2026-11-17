#!/bin/bash
set -euo pipefail
export PI_CODING_AGENT_DIR=/home/isa/Experiments/hyperqwen-fit/pi-live/agent
cd /home/isa/Experiments/hyperqwen-fit/live
exec /home/isa/.local/share/mise/installs/node/26.8.2/bin/node /home/isa/.local/share/mise/installs/node/26.8.2/lib/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js --offline --provider hyperqwen --model qwen3.8-27b --thinking high --no-context-files --no-extensions --no-skills --no-prompt-templates
