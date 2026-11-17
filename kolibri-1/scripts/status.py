import pathlib,json,subprocess,re,datetime
root=pathlib.Path('/home/isa/Experiments/kolibri-fit')
state=json.loads((root/'LOOP_STATE.json').read_text())
current=json.loads((root/'receipts/current-server.json').read_text())
log=subprocess.run(['docker','logs','--tail','1',current['container']],capture_output=True,text=True)
line=log.stdout+log.stderr
m=re.search(r'n_tokens\s*=\s*(\d+), progress\s*=\s*([0-9.]+), t\s*=\s*([0-9.]+)',line)
if m:
    progress={'tokens_processed':int(m[1]),'fraction':float(m[2]),'prefill_seconds':float(m[3]),'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    state['progress']=progress
    milestone=progress['tokens_processed']//100000
    if milestone!=state.get('progress_milestone'):
        state['progress_milestone']=milestone
        with (root/'FINDINGS.md').open('a') as f:f.write('\nExtended context progress: '+json.dumps(progress)+'\n')
    (root/'LOOP_STATE.json').write_text(json.dumps(state,indent=2)+'\n')
    print(json.dumps(progress))
else:print(line.strip())
print('stage',state['stage'])
print(subprocess.run(['systemctl','--user','show','kolibri-max-context-v3.service','-p','ActiveState','-p','Result'],capture_output=True,text=True).stdout.strip())
