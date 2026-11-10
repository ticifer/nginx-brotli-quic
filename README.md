# Nginx + Brotli + HTTP/3 (QUIC)

基于 Nginx 源码编译，包含 HTTP/2、HTTP/3、Brotli 和多个扩展模块。提供 BoringSSL、OpenSSL 两个版本，linux/amd64。

## 标签

| 标签 | TLS 实现 | Nginx | 镜像大小（未压缩） |
|---|---|---|---|
| latest | BoringSSL | 1.30.6 | 94.1 MB |
| boringssl | BoringSSL | 1.30.6 | 94.1 MB |
| openssl | OpenSSL 3.5.9 | 1.30.6 | 98.4 MB |
| 1.30.6-boringssl-20261110-r42772081671 | BoringSSL | 1.30.6 | 94.1 MB |
| 1.30.6-openssl3.5.9-20261110-r42772081671 | OpenSSL 3.5.9 | 1.30.6 | 98.4 MB |

latest 当前指向 BoringSSL 版本。生产环境建议固定版本标签或 digest。旧历史标签保留；新版本不包含公共示例证书/私钥。

## 组件与构建

- Nginx 1.30.6 stable，PCRE2 10.49（JIT），Brotli 版本跟随 ngx_brotli 锁定子模块。
- BoringSSL 提交：98ffd075a2db87093a62ca46f9e6e66e5f2f9f23；另一版本使用 OpenSSL 3.5.9。
- ngx_brotli、ngx-fancyindex、ngx_http_substitutions_filter_module、ngx_cache_purge、ngx_slowfs_cache：版本按仓库 locks/components.json 固定提交。
- 修复 slowfs 主配置初始化和 cache-purge 私有结构与 Nginx 1.30.6 的兼容性问题。
- 保留 stub_status、realip、gzip_static、FLV、MP4、addition、debug 支持。
- 源码编译，TLS/Brotli/PCRE2 静态链接；独立 Ubuntu 24.04 运行环境，保留 shell、CA、curl、envsubst 与官方入口脚本。最终镜像不含源码、编译器和构建缓存。

## HTTP 快速启动

```sh
docker run -d --name nginx-quic --restart unless-stopped \
  --ulimit nofile=8192:8192 \
  -p 8080:80 \
  ticifer/nginx-brotli-quic:latest
```

访问 http://localhost:8080。默认只启用 HTTP。

配置目录：/etc/nginx/nginx.conf、/etc/nginx/conf.d/*.conf。
静态文件目录：/usr/share/nginx/html。
模板目录：/etc/nginx/templates/*.template，入口脚本生成到 /etc/nginx/conf.d。
保留 fastcgi_params、fastcgi.conf、uwsgi_params 和 scgi_params。

## HTTPS 与 HTTP/3

准备自己的有效证书和私钥，创建 sites/https.conf：

```nginx
server {
    listen 443 ssl;
    listen 443 quic reuseport;
    server_name example.com;
    http2 on;
    http3 on;
    http3_hq on;
    ssl_certificate /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;
    quic_retry on;
    add_header Alt-Svc 'h3=":443"; ma=86400' always;
    location / {
        root /usr/share/nginx/html;
        index index.html;
    }
}
```

```sh
docker run -d --name nginx-quic --restart unless-stopped \
  --ulimit nofile=8192:8192 \
  -p 80:80/tcp -p 443:443/tcp -p 443:443/udp \
  -v "$PWD/sites:/etc/nginx/conf.d:ro" \
  -v "$PWD/certs:/etc/nginx/certs:ro" \
  -v "$PWD/html:/usr/share/nginx/html:ro" \
  ticifer/nginx-brotli-quic:latest
```

必须同时放通 TCP 和 UDP 443。外部映射到 8443 时，TCP/UDP 都映射为 8443:443，并将 Alt-Svc 改为 h3=":8443"。不要使用旧文档的 listen 443 http3，正确写法是 listen 443 quic。同一地址端口的 reuseport 只需声明一次。
镜像内参考配置：/etc/nginx/examples/https-quic.conf.example。
切换 OpenSSL 版只需替换镜像标签，挂载路径和配置方式相同。

## 默认参数

worker_processes auto，worker_connections 4096，worker_rlimit_nofile 8192；容器应提供相应 nofile 限制。
Brotli/Gzip 压缩级别 5、最小长度 256 字节，主要压缩文本/JSON/JS/CSS/XML/SVG；brotli_static on，按客户端能力协商。
TLS 1.2/1.3，ssl_early_data off，ssl_session_tickets off，隐藏版本号。
与旧镜像相比，brotli_static always 改为 on；不再默认压缩 JPEG/PNG 等已压缩类型；HTTPS 必须自行配置证书。

## 已验证

配置检查、HTTP、Brotli/Gzip、Fancyindex、subs_filter、slowfs 文件读取、代理缓存命中与清理、TLS+HTTP/2、真实 QUIC HTTP/3 请求、BoringSSL 版入口模板生成。两版使用相同入口脚本。
HTTP/3 已在测试环境本机端到端验证，公网可用性仍取决于宿主机 UDP、防火墙与网络环境。

## 自动更新

构建源码与工作流：https://github.com/ticifer/nginx-brotli-quic 。每周一北京时间 09:00 检查并构建，双版本测试通过后发布；跨系列/入口脚本更新先提交审核 PR。详见仓库 AUTOMATION.md。
