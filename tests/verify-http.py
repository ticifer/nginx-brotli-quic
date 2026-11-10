import httpx, brotli, gzip
base='http://127.0.0.1:18081'
with httpx.Client(trust_env=False) as c:
    for encoding in ['identity','br','gzip']:
        with c.stream('GET',base+'/',headers={'Accept-Encoding':encoding}) as r:
            raw=b''.join(r.iter_raw()); assert r.status_code==200
            actual=r.headers.get('content-encoding','identity'); assert actual==encoding,(actual,encoding)
            decoded=brotli.decompress(raw) if encoding=='br' else gzip.decompress(raw) if encoding=='gzip' else raw
            assert b'Welcome to nginx' in decoded
            print('HTTP compression',encoding,'OK',len(raw),'bytes')
    r=c.get(base+'/listing/'); assert r.status_code==200 and 'index.html' in r.text; print('fancyindex OK')
    r=c.get(base+'/subs'); assert r.text=='replaced',r.text; print('substitutions OK')
    for _ in range(2):
        r=c.get(base+'/slow/index.html'); assert r.status_code==200 and 'Welcome to nginx' in r.text,(r.status_code,r.text)
    print('slowfs cache reads OK')
    c.get(base+'/cached/item'); r=c.get(base+'/cached/item'); assert r.headers.get('x-cache')=='HIT',r.headers
    r=c.get(base+'/purge/cached/item'); assert r.status_code==200,r.status_code
    print('proxy cache + purge directive OK')
with httpx.Client(http2=True,verify=False,trust_env=False) as c:
    r=c.get('https://127.0.0.1:18443/'); assert r.status_code==200 and r.http_version=='HTTP/2'; print('TLS + HTTP/2 OK')
