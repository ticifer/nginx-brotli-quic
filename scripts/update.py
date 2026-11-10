#!/usr/bin/env python3
"""Discover pinned updates; cross-series changes require review."""
import copy,hashlib,json,os,pathlib,re,urllib.request
p=pathlib.Path('locks/components.json');old=json.loads(p.read_text());new=copy.deepcopy(old);review=False;changes=[]
def get(url):
 req=urllib.request.Request(url,headers={'Accept':'application/vnd.github+json','User-Agent':'nginx-component-updater',**({'Authorization':'Bearer '+os.environ['GH_TOKEN']} if 'api.github.com' in url and os.getenv('GH_TOKEN') else {})})
 with urllib.request.urlopen(req,timeout=45) as r:return r.read()
def api(url):return json.loads(get('https://api.github.com/'+url))
def version(s):return tuple(map(int,re.findall(r'\d+',s)))
html=get('https://nginx.org/en/download.html').decode();stable=re.search(r'Stable version.*?nginx-(\d+\.\d+\.\d+)\.tar.gz',html,re.S).group(1)
if stable!=old['nginx']['version']:
 review|=version(stable)[:2]!=version(old['nginx']['version'])[:2]
 new['nginx']={'version':stable,'sha256':hashlib.sha256(get(f'https://nginx.org/download/nginx-{stable}.tar.gz')).hexdigest()}
for name,repo,prefix in [('pcre2','PCRE2Project/pcre2','pcre2-'),('openssl','openssl/openssl','openssl-')]:
 releases=api(f'repos/{repo}/releases?per_page=50');releases=[r for r in releases if not r['draft'] and not r['prerelease'] and re.fullmatch(re.escape(prefix)+r'\d+\.\d+(?:\.\d+)?',r['tag_name'])]
 if name=='openssl':releases=[r for r in releases if version(r['tag_name'])[:2]==version(old[name]['version'])[:2]]
 r=max(releases,key=lambda r:version(r['tag_name']));v=r['tag_name'].removeprefix(prefix)
 if v!=old[name]['version']:
  review|=version(v)[0]!=version(old[name]['version'])[0]
  a=next(a for a in r['assets'] if a['name']==prefix+v+'.tar.gz');digest=hashlib.sha256(get(a['browser_download_url'])).hexdigest()
  if a.get('digest'):assert a['digest']=='sha256:'+digest
  new[name]={'version':v,'sha256':digest}
for name,item in new['git'].items():item['commit']=api(f'repos/{item["repo"]}/commits/HEAD')['sha']
entry=api('repos/nginx/docker-nginx/commits/HEAD')['sha']
if entry!=new['entrypoint']:new['entrypoint']=entry;review=True
base=json.loads(get('https://hub.docker.com/v2/repositories/library/ubuntu/tags/24.04/'))
if base.get('digest'):new['base']='ubuntu:24.04@'+base['digest']
# Major distro changes remain manual; only the pinned Ubuntu 24.04 digest advances.
for key in new:
 if new[key]!=old[key]:changes.append(key)
p.write_text(json.dumps(new,indent=2)+'\n')
result={'changed':bool(changes),'review':review,'changes':changes}
pathlib.Path('update-result.json').write_text(json.dumps(result))
print(json.dumps(result))
if os.getenv('GITHUB_OUTPUT'):
 with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write(f'changed={str(bool(changes)).lower()}\nreview={str(review).lower()}\n')
