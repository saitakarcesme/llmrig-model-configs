#!/bin/bash
# Idempotent: stop candidates, start production lanes, wait for router health, release the GPU lease.
. /home/isa/Projects/llmrig/candidates/elpis-plus-20261108/window/common.sh
log restore begin
pkill -f "$W/window/job_" 2>/dev/null
for c in $(docker ps -aq --filter label=elpis-plus=1); do docker rm -f $c >/dev/null; done
docker start llmrig-elpis-lane0 llmrig-elpis-lane1 >/dev/null
for i in $(seq 1 120); do
  ok=$(curl -s -m 5 -H "Authorization: Bearer $KEY" http://127.0.0.1:11446/props | python3 -c 'import json,sys;s=json.load(sys.stdin)["slots"];print(sum(x["healthy"] for x in s))' 2>/dev/null)
  [ "$ok" = "2" ] && break; sleep 5
done
log restore lanes_healthy=$ok
[ -f $W/window/lease.pid ] && kill $(cat $W/window/lease.pid) 2>/dev/null; rm -f $W/window/lease.pid
systemctl --user stop elpis-plus-deadman.timer 2>/dev/null
log restore done
