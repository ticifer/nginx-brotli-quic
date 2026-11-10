ARG BASE
FROM ${BASE}
ARG NGINX_VERSION
ENV NGINX_VERSION=${NGINX_VERSION}
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG http_proxy
ARG https_proxy
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates libjemalloc2 libcrypt1 libstdc++6 zlib1g libpcre2-8-0 gettext-base curl && rm -rf /var/lib/apt/lists/* /var/cache/apt/* && groupadd --system --gid 101 nginx && useradd --system --uid 101 --gid nginx --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin nginx && mkdir -p /etc/nginx/conf.d /etc/nginx/modules /etc/nginx/templates /etc/nginx/certs /var/cache/nginx /var/log/nginx /docker-entrypoint.d /usr/share/nginx/html /usr/lib/nginx/modules && ln -sf /dev/stdout /var/log/nginx/access.log && ln -sf /dev/stderr /var/log/nginx/error.log
COPY work/output/nginx /usr/sbin/nginx
COPY runtime/nginx.conf runtime/mime.types /etc/nginx/
COPY runtime/fastcgi_params runtime/fastcgi.conf runtime/uwsgi_params runtime/scgi_params /etc/nginx/
COPY runtime/default.conf /etc/nginx/conf.d/default.conf
COPY runtime/https-quic.conf.example /etc/nginx/examples/https-quic.conf.example
COPY runtime/html/ /usr/share/nginx/html/
COPY runtime/docker-entrypoint.sh /docker-entrypoint.sh
COPY runtime/10-listen-on-ipv6-by-default.sh runtime/15-local-resolvers.envsh runtime/20-envsubst-on-templates.sh runtime/30-tune-worker-processes.sh /docker-entrypoint.d/
EXPOSE 80/tcp 443/tcp 443/udp
STOPSIGNAL SIGQUIT
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]

COPY runtime/licenses/ /usr/share/doc/nginx/licenses/
