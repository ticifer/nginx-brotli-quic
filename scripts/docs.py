#!/usr/bin/env python3
"""Maintain repository/Hub release history from public registry evidence."""
import datetime,json,pathlib,re,urllib.request
REPO='ticifer/nginx-brotli-quic'
def update_history(readme):
 lock=json.loads(pathlib.Path('locks/components.json').read_text())
 readme=re.sub(r'本表适用于当前 \*\*Nginx [\d.]+ 两种 TLS 版本\*\*',f'本表适用于当前 **Nginx {lock["nginx"]["version"]} 两种 TLS 版本**',readme)
 readme=re.sub(r'\| PCRE2 \+ JIT \|[^\n]+',f'| PCRE2 + JIT | {lock["pcre2"]["version"]} | {lock["pcre2"]["version"]} | 正则表达式引擎；已编译 JIT 支持 |',readme)
 readme=re.sub(r'(\| TLS / SSL \| BoringSSL（固定提交） \| )OpenSSL [\d.]+ LTS',lambda m:m.group(1)+'OpenSSL '+lock['openssl']['version']+' LTS',readme)
 path=pathlib.Path('releases/history.json');records={x['name']:x for x in json.loads(path.read_text())} if path.exists() else {}
 url=f'https://hub.docker.com/v2/repositories/{REPO}/tags?page_size=100'
 while url:
  with urllib.request.urlopen(url,timeout=30) as r:page=json.load(r)
  for item in page['results']:
   name=item['name']
   if name in ('latest','boringssl','openssl'):continue
   records[name]={'name':name,'digest':item['digest'],'last_updated':item['last_updated'],'compressed_bytes':item['full_size']}
  url=page.get('next')
 records=sorted(records.values(),key=lambda x:x['last_updated'],reverse=True);path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(records,indent=2,ensure_ascii=False)+'\n')
 lines=['| 历史标签 | Nginx | TLS 实现 | Hub 标签更新时间（东八区） | Digest 前缀 |','|---|---|---|---|---|']
 for item in records:
  name=item['name'];match=re.match(r'(\d+\.\d+\.\d+)',name);nginx=match.group(1) if match else '未确认'
  tls='BoringSSL' if '-boringssl-' in name else ('OpenSSL '+re.search(r'openssl([\d.]+)',name).group(1) if '-openssl' in name else '历史构建，未逐版核验')
  stamp=datetime.datetime.fromisoformat(item['last_updated'].replace('Z','+00:00')).astimezone(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')
  lines.append(f'| `{name}` | {nginx} | {tls} | {stamp} | `{item["digest"][:19]}` |')
 block='<!-- IMAGE_HISTORY:BEGIN -->\n'+'\n'.join(lines)+'\n<!-- IMAGE_HISTORY:END -->'
 if '<!-- IMAGE_HISTORY:BEGIN -->' not in readme:raise ValueError('README missing history marker')
 return re.sub(r'<!-- IMAGE_HISTORY:BEGIN -->.*?<!-- IMAGE_HISTORY:END -->',lambda _:block,readme,flags=re.S)
if __name__=='__main__':
 p=pathlib.Path('README.md');p.write_text(update_history(p.read_text()))
