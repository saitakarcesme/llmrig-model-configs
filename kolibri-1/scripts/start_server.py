import json, subprocess, time, urllib.request, pathlib, sys
ROOT=pathlib.Path('/home/isa/Experiments/kolibri-fit')
IMAGE='84f75f3424c9'
def start(context=32768, cache='q8_0', quant='q3', split='1,1', ubatch=256):
    name=f'kolibri-{quant}-{context}-{cache.replace("_", "")}-{int(time.time())}'
    for line in subprocess.check_output(['docker','ps','--format','{{.Names}}'],text=True).splitlines():
        if line.startswith('kolibri-serve-'):
            subprocess.run(['docker','stop',line],check=True,stdout=subprocess.DEVNULL)
    name='kolibri-serve-'+name
    file='Kolibri-1-Q3_K_S.gguf' if quant=='q3' else 'Kolibri-1-Q4_K_XL.gguf'
    command=['docker','run','-d','--name',name,'--gpus','all','--memory','24g','--memory-swap','24g',
      '-p','127.0.0.1:8012:8080','-v',f'{ROOT}:/work:ro','--entrypoint','/work/build/bin/llama-server',IMAGE,
      '-m',f'/work/models/{quant}/{file}','--alias','kolibri-1','-ngl','99','--split-mode','layer',
      '--tensor-split',split,'-c',str(context),'-b','1024','-ub',str(ubatch),'-fa','on',
      '--cache-type-k',cache,'--cache-type-v',cache,'--parallel','1','-t','6','-tb','12',
      '--jinja','--host','0.0.0.0','--port','8080','--temp','1.0','--top-p','0.97','--top-k','128',
      '--no-context-shift','--metrics']
    if context>262144:
        # The server caps slots at model metadata. Kolibri's full attention has
        # no RoPE; upstream documents this runtime extension beyond native 262K.
        # Override metadata in memory, leaving the GGUF and RoPE scaling intact.
        command+=['--override-kv',f'kolibri1.context_length=int:{context}']
    subprocess.run(command,check=True,stdout=subprocess.DEVNULL)
    (ROOT/'receipts/current-server.json').write_text(json.dumps({'container':name,'context':context,'cache':cache,'quant':quant,'split':split,'ubatch':ubatch,'command':command},indent=2)+'\n')
    until=time.monotonic()+300
    while time.monotonic()<until:
        status=subprocess.check_output(['docker','inspect',name,'--format','{{.State.Status}}'],text=True).strip()
        if status!='running':
            log=subprocess.check_output(['docker','logs',name],stderr=subprocess.STDOUT,text=True)
            (ROOT/'receipts'/f'{name}-failed.log').write_text(log)
            raise RuntimeError(f'{name} exited; saved log')
        try:
            with urllib.request.urlopen('http://127.0.0.1:8012/health',timeout=2) as r:
                if r.status==200:return name
        except Exception:pass
        time.sleep(2)
    raise TimeoutError('Kolibri server health deadline exceeded')
if __name__=='__main__':print(start(int(sys.argv[1]) if len(sys.argv)>1 else 32768))
