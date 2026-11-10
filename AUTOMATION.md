# 自动迭代与发布

每周一北京时间 09:00（GitHub cron 01:00 UTC）检查更新，也可在 Actions 手动运行。GitHub 调度可能延迟。

- 锁定版本在 locks/components.json；源码下载校验 SHA256，Git 源码固定提交。
- 同一 Nginx 稳定系列、OpenSSL 3.5 LTS 补丁、PCRE2 同主系列、第三方模块提交及 Ubuntu 24.04 基础镜像更新：构建并验证两版，通过后自动发布。
- Nginx 跨稳定系列、PCRE2 跨主版本、入口脚本更新：创建审核 PR，保持线上标签。OpenSSL 跨 LTS 系列和 Ubuntu 跨发行版需手动修改锁文件。
- 第三方补丁无法应用、任一构建/测试失败：不进入发布步骤，创建失败 Issue。
- 每周即使源码未变也重建，获取运行库安全更新。
- 发布不可变版本标签带 Actions run id，避免覆盖历史；滚动标签 boringssl、openssl，latest 始终跟随 boringssl。
- 两版均验证后才进入发布。注册表逐个更新标签不具备跨标签事务；网络失败可能导致部分滚动标签更新，失败 Issue 提供记录，可重跑恢复。
- Hub 说明由 README.md 自动同步。源文件与已发布锁文件回写 GitHub。

Secrets：DOCKERHUB_USERNAME、DOCKERHUB_TOKEN（专用 read/write PAT，无删除权限）。在 Docker Hub 设置中撤销后请更新仓库 Secrets，不要把令牌提交到 Git。
现有凭据用于 Docker 登录和 Hub 说明更新；令牌不进入镜像和构建工件。

本地：Ubuntu 24.04 上运行 scripts/deps.sh、python3 scripts/fetch.py、bash scripts/build.sh boringssl（或 openssl）、bash scripts/image.sh boringssl、bash tests/verify.sh nginx-ci:boringssl。
验证覆盖 HTTP、Brotli/Gzip、Fancyindex、subs_filter、slowfs、缓存 HIT/PURGE、TLS/HTTP2、真实 HTTP3、模板。
slowfs/cache-purge 依赖 Nginx 私有结构；升级时保留补丁检查和实际功能验证。FastCGI/SCGI/UWSGI cache-purge 结构已同步，但这些协议尚无端到端后端测试。
当前仅 linux/amd64。
