#!/usr/bin/env python3
"""Attach both validated docker-save archives to one GitHub Release."""
import hashlib
import json
import os
import pathlib
import subprocess
import sys

REPO = "ticifer/nginx-brotli-quic"

GIT_LABELS = {
    "boringssl": "BoringSSL",
    "ngx_brotli": "ngx_brotli",
    "substitutions": "substitutions",
    "fancyindex": "ngx-fancyindex",
    "cache_purge": "ngx_cache_purge",
    "slowfs_cache": "ngx_slowfs_cache",
}


def run(*args, **kw):
    return subprocess.run(args, check=True, **kw)


def short_base(base):
    if "@sha256:" in base:
        prefix, digest = base.split("@sha256:", 1)
        return f"{prefix}@sha256:{digest[:12]}"
    return base


def find_previous_release(repo, current_tag, work_dir):
    """Return (prev_tag, prev_components) from the most recent prior published Release."""
    try:
        raw = subprocess.check_output(
            ["gh", "api", f"repos/{repo}/releases?per_page=20"],
            stderr=subprocess.PIPE,
        )
        releases = json.loads(raw)
    except Exception as exc:
        print(f"Warning: failed to query previous releases: {exc}", file=sys.stderr)
        return None, None

    for rel in releases:
        if rel.get("draft"):
            continue
        tag = rel.get("tag_name")
        if not tag or tag == current_tag:
            continue
        asset_names = {a.get("name") for a in rel.get("assets", [])}
        if "components.json" not in asset_names:
            continue
        prev_path = work_dir / "prev-components.json"
        try:
            run(
                "gh",
                "release",
                "download",
                tag,
                "--repo",
                repo,
                "--pattern",
                "components.json",
                "--output",
                str(prev_path),
                "--clobber",
            )
            prev_record = json.loads(prev_path.read_text())
            prev_lock = prev_record.get("components")
            if isinstance(prev_lock, dict):
                return tag, prev_lock
        except Exception as exc:
            print(
                f"Warning: failed to load components.json from {tag}: {exc}",
                file=sys.stderr,
            )
            return None, None
    return None, None


def format_changes_section(repo, current_tag, lock, prev_tag, prev_lock):
    if not prev_tag or not prev_lock:
        return ""

    changes = []

    for key, label in (("nginx", "Nginx"), ("openssl", "OpenSSL"), ("pcre2", "PCRE2")):
        old_item = prev_lock.get(key) or {}
        new_item = lock.get(key) or {}
        old_ver = old_item.get("version")
        new_ver = new_item.get("version")
        if old_ver != new_ver:
            changes.append(f"- {label}：`{old_ver or '无'}` → `{new_ver or '无'}`")
        elif old_item.get("sha256") != new_item.get("sha256"):
            changes.append(f"- {label}：`{new_ver}`（源码包校验值变更）")

    old_base = prev_lock.get("base")
    new_base = lock.get("base")
    if old_base != new_base:
        changes.append(
            f"- 基础镜像：`{short_base(old_base or '无')}` → `{short_base(new_base or '无')}`"
        )

    old_git = prev_lock.get("git") or {}
    new_git = lock.get("git") or {}
    ordered_keys = list(new_git.keys()) + [k for k in old_git.keys() if k not in new_git]
    for key in ordered_keys:
        label = GIT_LABELS.get(key, key)
        old_item = old_git.get(key)
        new_item = new_git.get(key)
        if old_item == new_item:
            continue
        if old_item and not new_item:
            changes.append(f"- {label}：已移除（原 `{old_item['commit'][:7]}`）")
            continue
        if new_item and not old_item:
            changes.append(
                f"- {label}：新增 `{new_item['repo']}@{new_item['commit'][:7]}`"
            )
            continue
        old_repo, old_c = old_item["repo"], old_item["commit"]
        new_repo, new_c = new_item["repo"], new_item["commit"]
        if old_repo == new_repo:
            changes.append(
                f"- {label}：[`{old_c[:7]}` → `{new_c[:7]}`]"
                f"(https://github.com/{new_repo}/compare/{old_c}...{new_c})"
            )
        else:
            changes.append(
                f"- {label}：`{old_repo}@{old_c[:7]}` → `{new_repo}@{new_c[:7]}`"
            )

    old_ep = prev_lock.get("entrypoint")
    new_ep = lock.get("entrypoint")
    if old_ep != new_ep:
        if old_ep and new_ep:
            changes.append(
                f"- 入口脚本锁定提交（`nginx/docker-nginx`）："
                f"[`{old_ep[:7]}` → `{new_ep[:7]}`]"
                f"(https://github.com/nginx/docker-nginx/compare/{old_ep}...{new_ep})"
            )
        else:
            changes.append(
                f"- 入口脚本锁定提交：`{(old_ep or '无')[:7]}` → `{(new_ep or '无')[:7]}`"
            )

    if not changes:
        changes.append("- 锁定组件无版本或提交变更（本次为定期重建或仓库构建/测试/配置更新）。")

    changes.append(
        f"- 仓库完整对比：https://github.com/{repo}/compare/{prev_tag}...{current_tag}"
    )

    prev_link = f"[`{prev_tag}`](https://github.com/{repo}/releases/tag/{prev_tag})"
    return f"### 相比上一版本（{prev_link}）更新\n\n" + "\n".join(changes) + "\n\n"


def build_release_notes(repo, release_tag, runid, lock, tags, prev_tag=None, prev_lock=None):
    changes_section = format_changes_section(repo, release_tag, lock, prev_tag, prev_lock)
    return (
        f"Nginx {lock['nginx']['version']}，linux/amd64。包含同一轮测试通过的 BoringSSL 与 OpenSSL {lock['openssl']['version']} 两个镜像。\n\n"
        f"{changes_section}"
        f"### 镜像与使用说明\n\n"
        f"- BoringSSL：`{repo}:{tags['boringssl']}`\n"
        f"- OpenSSL：`{repo}:{tags['openssl']}`\n"
        f"- `latest` 发布时跟随 BoringSSL。固定版本 digest 见附带的 `components.json`。\n"
        f"- 校验：`sha256sum -c SHA256SUMS`（先下载两个镜像包和 components.json）。\n"
        f"- 导入：`gunzip -c <镜像文件.tar.gz> | docker load`，也可 `docker load -i <镜像文件.tar.gz>`。\n"
        f"- 默认 HTTP；HTTPS/QUIC 需挂载自己的证书并开放 TCP/UDP。\n\n"
        f"验证运行：https://github.com/{repo}/actions/runs/{runid}\n"
    )


def main():
    root = pathlib.Path(".")
    record = json.loads((root / "releases/latest.json").read_text())
    lock = record["components"]
    assets = root / "work/release"
    assets.mkdir(parents=True, exist_ok=True)

    tags = {}
    for variant in ["boringssl", "openssl"]:
        matches = [
            t
            for t in record["tags"]
            if t.startswith(lock["nginx"]["version"] + "-" + variant) and "-r" in t
        ]
        if len(matches) != 1:
            raise ValueError("Expected one fixed release tag for " + variant)
        tags[variant] = matches[0]

    runids = {t.rsplit("-r", 1)[1] for t in tags.values()}
    if len(runids) != 1:
        raise ValueError("Images must belong to the same validated run")
    runid = runids.pop()
    release_tag = "v" + lock["nginx"]["version"] + "-r" + runid

    archives = []
    for variant, tag in tags.items():
        archive = assets / ("nginx-brotli-quic-" + tag + ".tar.gz")
        with archive.open("wb") as f:
            proc = subprocess.Popen(
                ["docker", "save", REPO + ":" + tag], stdout=subprocess.PIPE
            )
            try:
                run("gzip", "-1", stdin=proc.stdout, stdout=f)
            finally:
                proc.stdout.close()
            if proc.wait() != 0:
                raise RuntimeError("docker save failed")
        run("gzip", "-t", str(archive))
        archives.append(archive)

    metadata = assets / "components.json"
    metadata.write_text(json.dumps(record, indent=2) + "\n")
    checks = assets / "SHA256SUMS"
    checks.write_text(
        "".join(
            hashlib.file_digest(p.open("rb"), "sha256").hexdigest() + "  " + p.name + "\n"
            for p in [*archives, metadata]
        )
    )

    prev_tag, prev_lock = find_previous_release(REPO, release_tag, assets)
    notes = assets / "release-notes.md"
    notes.write_text(
        build_release_notes(REPO, release_tag, runid, lock, tags, prev_tag, prev_lock)
    )

    existing = (
        subprocess.run(
            ["gh", "release", "view", release_tag, "--repo", REPO],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )
    if not existing:
        run(
            "gh",
            "release",
            "create",
            release_tag,
            "--repo",
            REPO,
            "--draft",
            "--target",
            os.environ.get("GITHUB_SHA", "main"),
            "--title",
            f"Nginx {lock['nginx']['version']} · BoringSSL + OpenSSL · run {runid}",
            "--notes-file",
            str(notes),
        )
    run(
        "gh",
        "release",
        "upload",
        release_tag,
        "--repo",
        REPO,
        "--clobber",
        *[str(p) for p in [*archives, metadata, checks]],
    )
    run(
        "gh",
        "release",
        "edit",
        release_tag,
        "--repo",
        REPO,
        "--draft=false",
        "--latest",
        "--notes-file",
        str(notes),
    )
    result = json.loads(
        subprocess.check_output(
            [
                "gh",
                "release",
                "view",
                release_tag,
                "--repo",
                REPO,
                "--json",
                "url,assets,isDraft",
            ]
        )
    )
    assert not result["isDraft"]
    assert {p.name for p in [*archives, metadata, checks]} <= {
        a["name"] for a in result["assets"]
    }
    print(result["url"])


if __name__ == "__main__":
    main()
