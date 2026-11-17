"""Record rig memory, GPU use and temperature during a validation run."""
import argparse
import json
from pathlib import Path
import subprocess
import time

parser=argparse.ArgumentParser()
parser.add_argument('output')
parser.add_argument('--interval',type=float,default=10)
args=parser.parse_args()
while True:
    try:
        gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.used,utilization.gpu,temperature.gpu,power.draw',
                                     '--format=csv,noheader,nounits'],text=True,timeout=10)
        memory={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines()
                if line.startswith(('MemAvailable:','MemTotal:','SwapFree:','SwapTotal:'))}
        container=subprocess.check_output(['docker','stats','--no-stream','--format','{{json .}}','flashnext-api'],text=True,timeout=10)
        record={'unix':time.time(),'gpu':gpu.strip().splitlines(),'host':memory,'container':json.loads(container)}
    except Exception as error:
        record={'unix':time.time(),'error':str(error)}
    with Path(args.output).open('a') as output:
        output.write(json.dumps(record)+'\n')
    time.sleep(args.interval)
