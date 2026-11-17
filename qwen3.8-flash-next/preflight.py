"""Read-only compatibility checks; never stops or starts an inference service."""
import json
import pathlib
import subprocess
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path('/home/isa/Experiments/qwen38-flash-next-b70-fit')

def command(args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=30)
        return {'exit_code': r.returncode, 'stdout': r.stdout.strip(), 'stderr': r.stderr.strip()}
    except Exception as e:
        return {'error': str(e)}

checks = {
    'pci': command(['lspci']),
    'gpu': command(['nvidia-smi', '--query-gpu=name,memory.total,memory.used', '--format=csv']),
    'memory': command(['free', '-h']),
    'disk': command(['df', '-h', str(ROOT)]),
    'required_image': command(['docker', 'image', 'inspect', '24c872759256', '--format', '{{.Id}}']),
    'source_commit': command(['git', '-C', str(ROOT / 'upstream'), 'rev-parse', 'HEAD']),
    'active_services': command(['docker', 'ps', '--format', '{{.Names}} {{.Image}} {{.Ports}}']),
}
checks['required_paths'] = {p: pathlib.Path(p).exists() for p in [
    '/home/isa/freetoken-exl3/bench/xpu_run.sh',
    '/mnt/nvx/n104/qwen_experts.bin',
    '/home/isa/models/turboderp-Qwen3.8-Flash-Next-exl3-3.05bpw_h5_ng5',
]}
try:
    with urllib.request.urlopen('http://127.0.0.1:30260/v1/models', timeout=5) as r:
        checks['endpoint'] = json.load(r)
except Exception as e:
    checks['endpoint'] = {'error': str(e)}

intel_gpu = any(('VGA' in line or 'Display' in line) and 'Intel' in line
                for line in checks['pci'].get('stdout', '').splitlines())
blockers = []
if not intel_gpu:
    blockers.append('No Intel GPU; upstream uses torch.xpu, Intel xe SVM, and B70 SYCL kernels.')
if checks['required_image'].get('exit_code') != 0:
    blockers.append('Required Intel image 24c872759256 is absent; no reproducible image build is supplied.')
for path, exists in checks['required_paths'].items():
    if not exists:
        blockers.append('Missing required path: ' + path)
for name in ['bench/xpu_run.sh', 'plugin/exl3xpu/_moe_a8.so']:
    if not (ROOT / 'upstream' / name).exists():
        blockers.append('Repository does not ship ' + name)

result = {'checked_at': datetime.now(timezone.utc).isoformat(),
          'status': 'blocked' if blockers else 'preflight_passed_generation_unverified',
          'blockers': blockers, 'checks': checks, 'measured_model_generations': 0}
(ROOT / 'preflight.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
