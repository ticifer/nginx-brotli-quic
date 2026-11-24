# 自动迭代与发布

每天北京时间 09:00（GitHub cron 01:00 UTC）检查更新，也可在 Actions 手动运行。GitHub 调度可能延迟。

- 锁定版本在 locks/components.json；源码下载校验 SHA256，Git 源码固定提交。
- 核心组件更新（同一 Nginx 稳定系列、OpenSSL 3.5 LTS 补丁、PCRE2 同主系列、非 BoringSSL 第三方模块提交及 Ubuntu 24.04 基础镜像 digest）：当天立即构建并验证两版（同时纳入最新 BoringSSL 提交），通过后自动发布。
- 仅 BoringSSL 有提交更新：于每周一（东八区）统一汇总构建并发布，周二至周日跳过，避免高频刷版。
- 无任何锁定组件变更：定时任务直接跳过构建；需要强制重建时可通过 Actions 手动触发 workflow_dispatch。
- Nginx 跨稳定系列、PCRE2 跨主版本、以及 `nginx/docker-nginx` 仓库 `entrypoint/` 目录实际有提交更新：创建审核 PR（自动指派并 `@ticifer`），保持线上标签，并通过 Bark 推送直达 PR 链接；若审核 PR 已存在且无新的非 BoringSSL 变更，不重复推送提醒。OpenSSL 跨 LTS 系列和 Ubuntu 跨发行版需手动修改锁文件。
- 第三方补丁无法应用、任一构建/测试失败：不进入发布步骤，创建失败 Issue（自动指派并 `@ticifer`）并发送 Bark 告警通知。
- 发布不可变版本标签带 Actions run id，避免覆盖历史；滚动标签 boringssl、openssl，latest 始终跟随 boringssl。
- 两版均验证后才进入发布。注册表逐个更新标签不具备跨标签事务；网络失败可能导致部分滚动标签更新，失败 Issue 提供记录，可重跑恢复。
- Hub 说明由 README.md 自动同步。源文件与已发布锁文件回写 GitHub。

Secrets：DOCKERHUB_USERNAME、DOCKERHUB_TOKEN（专用 PAT；Docker Hub 要求包含 repo:admin 才可更新仓库说明，此外含 repo:read / repo:write。工作流不执行镜像删除）；BARK_URL（可选，用于 `scripts/notify.py` 在需要人工审核 PR 或构建失败时发送 Bark 推送）。在对应平台撤销或更换后请更新仓库 Secrets，不要把令牌或推送地址提交到 Git。
现有凭据用于 Docker 登录、Hub 说明更新和告警通知；凭据不进入镜像、代码和构建工件。

本地：Ubuntu 24.04 上运行 scripts/deps.sh、python3 scripts/fetch.py、bash scripts/build.sh boringssl（或 openssl）、bash scripts/image.sh boringssl、bash tests/verify.sh nginx-ci:boringssl。
验证覆盖 HTTP、Brotli/Gzip、Fancyindex、subs_filter、slowfs、缓存 HIT/PURGE、TLS/HTTP2、真实 HTTP3、模板。
slowfs/cache-purge 依赖 Nginx 私有结构；升级时保留补丁检查和实际功能验证。FastCGI/SCGI/UWSGI cache-purge 结构已同步，但这些协议尚无端到端后端测试。
当前仅 linux/amd64。

GitHub Release：两版通过测试与 Hub 发布后，scripts/release.py 将两版固定标签保存为压缩 docker-save 包，生成 SHA256SUMS 与 components.json，对比上一已发布版本自动生成更新说明，以草稿方式上传附件，验证齐全后公开。Release tag 为 v<Nginx>-r<run-id>。
