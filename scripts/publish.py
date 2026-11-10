#!/usr/bin/env python3
import datetime,json,os,pathlib,re,subprocess,urllib.request
root=pathlib.Path('.');lock=json.loads((root/'locks/components.json').read_text());repo='ticifer/nginx-brotli-quic';date=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y%m%d');release=os.environ['RELEASE_ID'];tags={};sizes={}
def run(*args):subprocess.run(args,check=True)
for variant in ['boringssl','openssl']:
 run('docker','load','-i',f'work/images/{variant}.tar')
 tls=variant if variant=='boringssl' else 'openssl'+lock['openssl']['version']
 tag=f'{lock["nginx"]["version"]}-{tls}-{date}-r{release}';tags[variant]=tag
 sizes[variant]=int(subprocess.check_output(['docker','image','inspect',f'nginx-ci:{variant}','--format','{{.Size}}']))
 run('docker','tag',f'nginx-ci:{variant}',f'{repo}:{tag}');run('docker','push',f'{repo}:{tag}')
# Advance rolling tags only after both immutable images were uploaded successfully.
for alias,variant in [('boringssl','boringssl'),('openssl','openssl'),('latest','boringssl')]:
 run('docker','tag',f'nginx-ci:{variant}',f'{repo}:{alias}');run('docker','push',f'{repo}:{alias}')
readme=(root/'README.md').read_text();table='| 标签 | TLS 实现 | Nginx | 镜像大小（未压缩） |\n|---|---|---|---|\n'
for tag,v in [('latest','boringssl'),('boringssl','boringssl'),('openssl','openssl'),(tags['boringssl'],'boringssl'),(tags['openssl'],'openssl')]:
 tls='BoringSSL' if v=='boringssl' else 'OpenSSL '+lock['openssl']['version'];table+=f'| {tag} | {tls} | {lock["nginx"]["version"]} | {sizes[v]/1e6:.1f} MB |\n'
readme=re.sub(r'\| 标签 \|.*?(?=\n\n)',lambda _:table.rstrip(),readme,count=1,flags=re.S)
# Keep the component summary synchronized with the lock file.
readme=re.sub(r'- Nginx .*?\n',f'- Nginx {lock["nginx"]["version"]} stable，PCRE2 {lock["pcre2"]["version"]}（JIT），Brotli 版本跟随 ngx_brotli 锁定子模块。\n',readme,count=1)
readme=re.sub(r'- BoringSSL 提交：.*?\n',f'- BoringSSL 提交：{lock["git"]["boringssl"]["commit"]}；另一版本使用 OpenSSL {lock["openssl"]["version"]}。\n',readme,count=1)
readme=readme.replace('- ngx_brotli、ngx-fancyindex 0.6.0、ngx_http_substitutions_filter_module、ngx_cache_purge 2.3、ngx_slowfs_cache 1.10。','- ngx_brotli、ngx-fancyindex、ngx_http_substitutions_filter_module、ngx_cache_purge、ngx_slowfs_cache：版本按仓库 locks/components.json 固定提交。')
(root/'README.md').write_text(readme)
req=urllib.request.Request('https://hub.docker.com/v2/auth/token',data=json.dumps({'identifier':os.environ['DOCKERHUB_USERNAME'],'secret':os.environ['DOCKERHUB_TOKEN']}).encode(),headers={'Content-Type':'application/json'},method='POST')
with urllib.request.urlopen(req,timeout=30) as r:auth=json.load(r)
token=auth.get('access_token') or auth.get('token');assert token
req=urllib.request.Request(f'https://hub.docker.com/v2/repositories/{repo}/',data=json.dumps({'full_description':readme,'description':f'Nginx {lock["nginx"]["version"]} + Brotli + HTTP/3; BoringSSL latest / OpenSSL {lock["openssl"]["version"]}; amd64'}).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'},method='PATCH')
with urllib.request.urlopen(req,timeout=30) as r:assert json.load(r)['full_description']==readme
results={}
for tag in [*tags.values(),'boringssl','openssl','latest']:
 with urllib.request.urlopen(f'https://hub.docker.com/v2/repositories/{repo}/tags/{tag}/',timeout=30) as r:results[tag]=json.load(r)['digest']
assert results['latest']==results['boringssl']==results[tags['boringssl']]
assert results['openssl']==results[tags['openssl']]
(root/'releases').mkdir(exist_ok=True);(root/'releases/latest.json').write_text(json.dumps({'tags':results,'components':lock},indent=2)+'\n')
