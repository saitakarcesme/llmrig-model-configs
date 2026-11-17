#!/bin/bash
# One GPU window: preflight idle, take lease, dead-man restore, stop lanes, run both jobs, restore.
. /home/isa/Projects/llmrig/candidates/elpis-plus-20261108/window/common.sh
set -e
python3 - <<P
import json,urllib.request
r=urllib.request.Request("http://127.0.0.1:11446/props",headers={"Authorization":"Bearer $KEY"})
s=json.load(urllib.request.urlopen(r,timeout=10))["slots"]
assert all(x["healthy"] and not x["busy"] and not x["gpu_lease_held"] for x in s), s
P
python3 -c "import fcntl,time;f=open('$LEASE','a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);time.sleep(7200)" & echo $! > $W/window/lease.pid; sleep 1
kill -0 $(cat $W/window/lease.pid) || { log lease busy; exit 1; }
systemd-run --user --unit elpis-plus-deadman --on-active=100min $W/window/restore.sh >/dev/null
docker inspect -f '{{.Name}} {{.State.StartedAt}}' llmrig-elpis-lane0 llmrig-elpis-lane1 > $W/window/lanes-before.txt
log window start; trap "$W/window/restore.sh" EXIT
docker stop --time 30 llmrig-elpis-lane0 llmrig-elpis-lane1 >/dev/null
log lanes stopped
$W/window/job_g1.sh > $W/results/job_g1.log 2>&1 & p1=$!
$W/window/job_g0.sh > $W/results/job_g0.log 2>&1 & p0=$!
wait $p1 $p0 || true
log jobs finished
