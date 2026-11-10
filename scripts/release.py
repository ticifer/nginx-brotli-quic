#!/usr/bin/env python3
"""Attach both validated docker-save archives to one GitHub Release."""
import hashlib,json,os,pathlib,subprocess
root=pathlib.Path('.');record=json.loads((root/'releases/latest.json').read_text());lock=record['components'];repo='ticifer/nginx-brotli-quic';assets=root/'work/release';assets.mkdir(parents=True,exist_ok=True)
def run(*args,**kw):return subprocess.run(args,check=True,**kw)
tags={}
for variant in ['boringssl','openssl']:
 matches=[t for t in record['tags'] if t.startswith(lock['nginx']['version']+'-'+variant) and '-r' in t]
 if len(matches)!=1:raise ValueError('Expected one fixed release tag for '+variant)
 tags[variant]=matches[0]
runids={t.rsplit('-r',1)[1] for t in tags.values()}
if len(runids)!=1:raise ValueError('Images must belong to the same validated run')
runid=runids.pop();release_tag='v'+lock['nginx']['version']+'-r'+runid
archives=[]
for variant,tag in tags.items():
 archive=assets/('nginx-brotli-quic-'+tag+'.tar.gz')
 with archive.open('wb') as f:
  proc=subprocess.Popen(['docker','save',repo+':'+tag],stdout=subprocess.PIPE)
  try:run('gzip','-1',stdin=proc.stdout,stdout=f)
  finally:proc.stdout.close()
  if proc.wait()!=0:raise RuntimeError('docker save failed')
 run('gzip','-t',str(archive));archives.append(archive)
metadata=assets/'components.json';metadata.write_text(json.dumps(record,indent=2)+'\n')
checks=assets/'SHA256SUMS';checks.write_text(''.join(hashlib.file_digest(p.open('rb'),'sha256').hexdigest()+'  '+p.name+'\n' for p in [*archives,metadata]))
notes=assets/'release-notes.md';notes.write_text(f'''Nginx {lock['nginx']['version']}，linux/amd64。包含同一轮测试通过的 BoringSSL 与 OpenSSL {lock['openssl']['version']} 两个镜像。

- BoringSSL：`{repo}:{tags['boringssl']}`
- OpenSSL：`{repo}:{tags['openssl']}`
- `latest` 发布时跟随 BoringSSL。固定版本 digest 见附带的 `components.json`。
- 校验：`sha256sum -c SHA256SUMS`（先下载两个镜像包和 components.json）。
- 导入：`gunzip -c <镜像文件.tar.gz> | docker load`，也可 `docker load -i <镜像文件.tar.gz>`。
- 默认 HTTP；HTTPS/QUIC 需挂载自己的证书并开放 TCP/UDP。

验证运行：https://github.com/{repo}/actions/runs/{runid}
''')
existing=subprocess.run(['gh','release','view',release_tag,'--repo',repo],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
if not existing:
 run('gh','release','create',release_tag,'--repo',repo,'--draft','--target',os.environ.get('GITHUB_SHA','main'),'--title',f'Nginx {lock["nginx"]["version"]} · BoringSSL + OpenSSL · run {runid}','--notes-file',str(notes))
run('gh','release','upload',release_tag,'--repo',repo,'--clobber',*[str(p) for p in [*archives,metadata,checks]])
run('gh','release','edit',release_tag,'--repo',repo,'--draft=false','--latest','--notes-file',str(notes))
result=json.loads(subprocess.check_output(['gh','release','view',release_tag,'--repo',repo,'--json','url,assets,isDraft']))
assert not result['isDraft'];assert {p.name for p in [*archives,metadata,checks]} <= {a['name'] for a in result['assets']}
print(result['url'])
