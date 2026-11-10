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

## 镜像历史版本

以下按 Hub 标签更新时间排序，时间为 UTC+08:00，**不代表首次发布日期**。滚动标签 `latest` / `boringssl` / `openssl` 见上表，不作为历史固定版本重复列出。带 `-r` 的版本来自 GitHub Actions，`20261110` 无 `-r` 的两版为首次 box 构建；旧标签仍可拉取，历史镜像的组件与参数不能套用当前支持表。

<!-- IMAGE_HISTORY:BEGIN -->
| 历史标签 | Nginx | TLS 实现 | Hub 标签更新时间（东八区） | Digest 前缀 |
|---|---|---|---|---|
| `1.30.6-openssl3.5.9-20261110-r42772081671` | 1.30.6 | OpenSSL 3.5.9 | 2026-11-10 15:09 | `sha256:b906f31a2e91` |
| `1.30.6-boringssl-20261110-r42772081671` | 1.30.6 | BoringSSL | 2026-11-10 15:09 | `sha256:a4065be6a77d` |
| `1.30.6-openssl3.5.9-20261110` | 1.30.6 | OpenSSL 3.5.9 | 2026-11-10 14:37 | `sha256:253ca242c270` |
| `1.30.6-boringssl-20261110` | 1.30.6 | BoringSSL | 2026-11-10 14:37 | `sha256:701573d0df1b` |
| `1.27.2-min` | 1.27.2 | 历史构建，未逐版核验 | 2024-11-27 23:07 | `sha256:5a28beb6fc49` |
| `1.27.2` | 1.27.2 | 历史构建，未逐版核验 | 2024-11-27 22:59 | `sha256:fbb30b539b88` |
| `1.23.4` | 1.23.4 | 历史构建，未逐版核验 | 2024-11-27 16:37 | `sha256:be4271a4a91e` |
| `1.27.1` | 1.27.1 | 历史构建，未逐版核验 | 2024-08-24 11:45 | `sha256:765860debaf6` |
| `1.25.3` | 1.25.3 | 历史构建，未逐版核验 | 2023-10-09 17:15 | `sha256:5c5cbede6881` |
<!-- IMAGE_HISTORY:END -->

完整 digest 和标签记录见 [releases/history.json](https://github.com/ticifer/nginx-brotli-quic/blob/main/releases/history.json)。后续每次成功发布会自动刷新并保留历史记录；需要精确锁定内容时使用 digest。

## 组件与构建

- Nginx 1.30.6 stable，PCRE2 10.49（JIT），Brotli 版本跟随 ngx_brotli 锁定子模块。
- BoringSSL 提交：98ffd075a2db87093a62ca46f9e6e66e5f2f9f23；另一版本使用 OpenSSL 3.5.9。
- ngx_brotli、ngx-fancyindex、ngx_http_substitutions_filter_module、ngx_cache_purge、ngx_slowfs_cache：版本按仓库 locks/components.json 固定提交。
- 修复 slowfs 主配置初始化和 cache-purge 私有结构与 Nginx 1.30.6 的兼容性问题。
- 保留 stub_status、realip、gzip_static、FLV、MP4、addition、debug 支持。
- 源码编译，TLS/Brotli/PCRE2 静态链接；独立 Ubuntu 24.04 运行环境，保留 shell、CA、curl、envsubst 与官方入口脚本。最终镜像不含源码、编译器和构建缓存。

## 组件与扩展支持

本表适用于当前 **Nginx 1.30.6 两种 TLS 版本**。除 TLS 实现不同，其余组件及参数一致。“已编译”不表示默认站点已启用该功能，历史标签需单独检查 `nginx -V`。

| 组件 / 扩展 | BoringSSL 版 | OpenSSL 版 | 用途与启用方式 |
|---|---|---|---|
| TLS / SSL | BoringSSL（固定提交） | OpenSSL 3.5.9 LTS | `ssl_certificate` / `ssl_certificate_key`，挂载自己的证书 |
| HTTP/2 | 已编译 | 已编译 | `http2 on`；实际请求已验证 |
| HTTP/3 / QUIC | 已编译 | 已编译 | `listen 443 quic reuseport`、`http3 on`，需开放 UDP；真实 QUIC 请求已验证 |
| PCRE2 + JIT | 10.49 | 10.49 | 正则表达式引擎；已编译 JIT 支持 |
| ngx_brotli / Brotli | 随锁定子模块 | 同左 | 动态压缩与 `.br` 文件；`brotli on` / `brotli_static on` |
| Gzip / gzip_static | 已编译 | 已编译 | 动态 gzip 默认开启；预压缩文件需 `gzip_static on` |
| ngx-fancyindex | 已编译 | 同左 | 目录索引，按站点配置 `fancyindex on`；已验证 |
| substitutions filter | 已编译 | 已编译 | `subs_filter`、`subs_filter_types`，支持内容替换；已验证 |
| ngx_cache_purge | 已编译 + 兼容补丁 | 同左 | `proxy_cache_purge` 等；代理缓存 HIT/PURGE 已验证 |
| ngx_slowfs_cache | 已编译 + 兼容补丁 | 同左 | 慢速文件系统缓存；`slowfs_cache_path` / `slowfs_cache`，文件读取已验证 |
| Proxy / FastCGI / SCGI / uWSGI | 已编译 | 已编译 | 反向代理、应用网关及对应缓存；FastCGI/SCGI/uWSGI 清理尚未做后端端到端测试 |
| realip | 已编译 | 已编译 | `set_real_ip_from` / `real_ip_header`，仅信任自己的代理 |
| stub_status | 已编译 | 已编译 | 在受限 location 内开启 `stub_status` |
| FLV / MP4 | 已编译 | 已编译 | `flv` / `mp4` 指令，按站点启用 |
| addition | 已编译 | 已编译 | `add_before_body` / `add_after_body`，也供 Fancyindex 头尾模板使用 |
| Debug 日志能力 | 已编译 | 已编译 | `error_log ... debug`；默认日志级别为 warn |
| jemalloc | 已链接 | 已链接 | 内存分配运行库 |
| envsubst / 官方入口脚本 | 支持 | 支持 | `/etc/nginx/templates/*.template`，两版模板生成测试通过 |
| Lua / njs / ModSecurity | 未集成 | 未集成 | 当前构建未添加这些扩展 |
| Stream / Mail / image_filter / XSLT / GeoIP | 未启用 | 未启用 | 不应将这些指令视为当前镜像支持范围 |

模块来源和提交见 [locks/components.json](https://github.com/ticifer/nginx-brotli-quic/blob/main/locks/components.json)，编译选项见 [scripts/build.sh](https://github.com/ticifer/nginx-brotli-quic/blob/main/scripts/build.sh)，兼容补丁见 [patches](https://github.com/ticifer/nginx-brotli-quic/tree/main/patches)。升级后的精确版本以该发布记录与 `nginx -V` 为准。

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

配置检查、HTTP、Brotli/Gzip、Fancyindex、subs_filter、slowfs 文件读取、代理缓存命中与清理、TLS+HTTP/2、真实 QUIC HTTP/3 请求、两版入口模板生成。
HTTP/3 已在测试环境本机端到端验证，公网可用性仍取决于宿主机 UDP、防火墙与网络环境。

## 自动更新

构建源码与工作流：https://github.com/ticifer/nginx-brotli-quic 。每周一北京时间 09:00 检查并构建，双版本测试通过后发布；跨系列/入口脚本更新先提交审核 PR。详见仓库 AUTOMATION.md。
