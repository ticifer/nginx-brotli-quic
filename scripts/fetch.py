#!/usr/bin/env python3
import hashlib,json,pathlib,subprocess,urllib.request,tarfile
root=pathlib.Path(__file__).resolve().parents[1]; lock=json.loads((root/'locks/components.json').read_text());src=root/'work/src';src.mkdir(parents=True,exist_ok=True)
def run(*args):subprocess.run(args,check=True)
urls={'nginx':f'https://nginx.org/download/nginx-{lock["nginx"]["version"]}.tar.gz','pcre2':f'https://github.com/PCRE2Project/pcre2/releases/download/pcre2-{lock["pcre2"]["version"]}/pcre2-{lock["pcre2"]["version"]}.tar.gz','openssl':f'https://github.com/openssl/openssl/releases/download/openssl-{lock["openssl"]["version"]}/openssl-{lock["openssl"]["version"]}.tar.gz'}
for name,url in urls.items():
 target=src/(name+'.tar.gz');urllib.request.urlretrieve(url,target)
 assert hashlib.sha256(target.read_bytes()).hexdigest()==lock[name]['sha256'],name+' SHA256 mismatch'
 with tarfile.open(target) as t:t.extractall(src,filter='data')
for name,item in lock['git'].items():
 target=src/name
 run('git','init',str(target));run('git','-C',str(target),'remote','add','origin','https://github.com/'+item['repo']+'.git');run('git','-C',str(target),'fetch','--depth=1','origin',item['commit']);run('git','-C',str(target),'checkout','--detach','FETCH_HEAD')
 if name=='ngx_brotli':run('git','-C',str(target),'submodule','update','--init','--recursive','--depth=1')
for name in ['cache-purge-nginx-abi.patch','slowfs-nginx-cache-api.patch']:
 directory=src/('cache_purge' if name.startswith('cache-purge') else 'slowfs_cache')
 run('git','-C',str(directory),'apply','--check',str(root/'patches'/name));run('git','-C',str(directory),'apply',str(root/'patches'/name))
for name in ['docker-entrypoint.sh','10-listen-on-ipv6-by-default.sh','15-local-resolvers.envsh','20-envsubst-on-templates.sh','30-tune-worker-processes.sh']:
 p=root/'runtime'/name;urllib.request.urlretrieve(f'https://raw.githubusercontent.com/nginx/docker-nginx/{lock["entrypoint"]}/entrypoint/{name}',p);p.chmod(0o755)
