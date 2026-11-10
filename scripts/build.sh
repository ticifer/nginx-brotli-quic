#!/bin/bash
set -euo pipefail
variant=${1:?boringssl or openssl}
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
read -r NGINX PCRE OPENSSL < <(python3 -c 'import json;d=json.load(open("locks/components.json"));print(d["nginx"]["version"],d["pcre2"]["version"],d["openssl"]["version"])')
cd work/src
cmake -S ngx_brotli/deps/brotli -B ngx_brotli/deps/brotli/out -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DBROTLI_DISABLE_TESTS=ON
cmake --build ngx_brotli/deps/brotli/out --target brotlienc brotlicommon -j2
if [[ $variant == boringssl ]]; then
 cmake -S boringssl -B boringssl/build -GNinja -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF
 cmake --build boringssl/build --target ssl crypto -j2
 TLS_ARGS=(--with-cc-opt="-O2 -fstack-protector-strong -D_FORTIFY_SOURCE=2 -I../boringssl/include" --with-ld-opt="-Wl,-z,relro,-z,now -L../boringssl/build -Wl,--no-as-needed -ljemalloc -lstdc++ -lpthread")
else
 TLS_ARGS=(--with-openssl=../openssl-${OPENSSL} --with-openssl-opt=no-shared)
fi
cd "nginx-$NGINX"
./configure --prefix=/etc/nginx --sbin-path=/usr/sbin/nginx --modules-path=/usr/lib/nginx/modules --conf-path=/etc/nginx/nginx.conf --error-log-path=/var/log/nginx/error.log --http-log-path=/var/log/nginx/access.log --pid-path=/var/run/nginx.pid --lock-path=/var/run/nginx.lock --http-client-body-temp-path=/var/cache/nginx/client_temp --http-proxy-temp-path=/var/cache/nginx/proxy_temp --http-fastcgi-temp-path=/var/cache/nginx/fastcgi_temp --http-uwsgi-temp-path=/var/cache/nginx/uwsgi_temp --http-scgi-temp-path=/var/cache/nginx/scgi_temp --user=nginx --group=nginx --with-compat --with-debug --with-http_stub_status_module --with-http_v2_module --with-http_v3_module --with-http_ssl_module --with-http_gzip_static_module --with-http_realip_module --with-http_addition_module --with-http_flv_module --with-http_mp4_module --with-pcre=../pcre2-${PCRE} --with-pcre-jit --add-module=../substitutions --add-module=../cache_purge --add-module=../slowfs_cache --add-module=../ngx_brotli --add-module=../fancyindex --with-cc-opt='-O2 -fstack-protector-strong -D_FORTIFY_SOURCE=2' --with-ld-opt='-Wl,-z,relro,-z,now -Wl,--no-as-needed -ljemalloc -lstdc++ -lpthread' "${TLS_ARGS[@]}"
# BoringSSL-specific options must be last so they override generic compiler options.
make -j2
mkdir -p "$root/work/output"
cp objs/nginx "$root/work/output/nginx"
strip --strip-unneeded "$root/work/output/nginx"
"$root/work/output/nginx" -V 2>"$root/work/output/nginx-version.txt"

cd "$root"
rm -f runtime/licenses/boringssl.LICENSE
if [[ $variant == boringssl ]]; then
 cp work/src/boringssl/LICENSE runtime/licenses/TLS.LICENSE
else
 cp "work/src/openssl-$OPENSSL/LICENSE.txt" runtime/licenses/TLS.LICENSE
fi
cp locks/components.json runtime/licenses/components.json
for component in nginx-${NGINX} pcre2-${PCRE} ngx_brotli fancyindex cache_purge slowfs_cache; do
 source="work/src/$component"
 if [[ -f "$source/LICENSE" ]]; then cp "$source/LICENSE" "runtime/licenses/$component.LICENSE"; elif [[ -f "$source/COPYING" ]]; then cp "$source/COPYING" "runtime/licenses/$component.LICENSE"; fi
done
cp work/src/ngx_brotli/deps/brotli/LICENSE runtime/licenses/brotli.LICENSE
