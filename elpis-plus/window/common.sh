# shared by window scripts
W=/home/isa/Projects/llmrig/candidates/elpis-plus-20261108
IMAGE=sha256:2446a45495af44611a5a3c4ee1986a1f79a6acb29d04619629484d6d4527486d
LEASE=/home/isa/Projects/llmrig/pdf-api/gpu-switch.lock
KEY=$(cat /home/isa/.local/share/llmrig-elpis/api-key)
log(){ echo "$(date +%FT%T) $*" | tee -a $W/window/events.log; }
# cand_run NAME GPU PORT [docker -e args...] -- [entrypoint args...]
cand_run(){
  local name=$1 gpu=$2 port=$3; shift 3
  local envs=(); while [ "$1" != "--" ]; do envs+=("$1"); shift; done; shift
  mkdir -p $W/cache-g$gpu; [ -d $W/cache-g$gpu/triton ] || cp -a /home/isa/.local/share/llmrig-elpis/cache/. $W/cache-g$gpu/
  docker rm -f $name >/dev/null 2>&1 || true
  docker run -d --name $name --label elpis-plus=1 --device nvidia.com/gpu=$gpu --user 1000:1000 \
    --read-only --tmpfs /run:rw,nosuid,size=64m --tmpfs /tmp:rw,nosuid,size=2g --shm-size 4g --memory 11g --cap-drop ALL \
    -p 127.0.0.1:$port:18020 \
    -v /home/isa/models/elpis-262k:/models:ro -v $W/cache-g$gpu:/cache:rw \
    -v /home/isa/.local/share/llmrig-elpis/api-key:/app/api_key.txt:ro -v $W:/work:rw \
    -e QWEN_PREFIX_PERSIST=0 "${envs[@]}" --entrypoint /opt/venv/bin/python $IMAGE "$@" >/dev/null
}
SERVE_ARGS=(-B /opt/qwen/serve/exl3_server.py --target /models/qwen38-27b-exl3 --draft /models/dflash2-exl3 --model-name qwen3.8-27b --max-model-len 262144 --cache-tokens 270336 --cq 3 --host 0.0.0.0 --port 18020 --cpu-cache-gib 0)
wait_ready(){ # port timeout
  local t=0; until curl -sf -m 5 -H "Authorization: Bearer $KEY" http://127.0.0.1:$1/v1/models >/dev/null; do sleep 5; t=$((t+5)); [ $t -gt ${2:-600} ] && return 1; done; return 0; }
gate(){ # port out suite [extra]
  local port=$1 out=$2 suite=$3; shift 3
  python3 $W/bench/gate/gate.py $suite --url http://127.0.0.1:$port/v1/chat/completions --busy-url "" --out $W/results/$out "$@"; }
