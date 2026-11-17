import pathlib,json,urllib.request,subprocess,time
from start_server import ROOT,start
selected=json.loads((ROOT/'selected-profile.json').read_text())
try:
    with urllib.request.urlopen('http://127.0.0.1:8012/health',timeout=3) as r:
        healthy=r.status==200
    current=json.loads((ROOT/'receipts/current-server.json').read_text())
except Exception:
    healthy=False;current={}
keys=['context','cache','quant','split','ubatch']
if healthy and all(current.get(k)==selected.get(k) for k in keys):
    print('Kolibri is ready.')
else:
    subprocess.run(['systemctl','--user','stop','llmrig-homelab.service'],check=False)
    subprocess.run(['docker','stop','homelab-ollama'],check=False,stdout=subprocess.DEVNULL)
    print('Loading the selected Kolibri profile. Please wait.',flush=True)
    name=start(**{k:selected[k] for k in keys})
    print('Kolibri ready:',name)
