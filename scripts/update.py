#!/usr/bin/env python3
"""Discover pinned updates; cross-series/entrypoint changes require review."""
import copy
import datetime
import hashlib
import json
import os
import pathlib
import re
import urllib.request

CST = datetime.timezone(datetime.timedelta(hours=8))


def get(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "nginx-component-updater",
    }
    if "api.github.com" in url and os.getenv("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()


def api(url):
    return json.loads(get("https://api.github.com/" + url))


def version(s):
    return tuple(map(int, re.findall(r"\d+", s)))


def diff_components(old, new):
    """Return granular list of changed component keys (e.g. 'nginx', 'git.boringssl')."""
    changes = []
    for key in new:
        if key == "git":
            old_git = old.get("git") or {}
            new_git = new.get("git") or {}
            ordered = list(new_git.keys()) + [k for k in old_git if k not in new_git]
            for name in ordered:
                if new_git.get(name) != old_git.get(name):
                    changes.append(f"git.{name}")
        elif new.get(key) != old.get(key):
            changes.append(key)
    for key in old:
        if key not in new and key != "git":
            changes.append(key)
    return changes


def plan_update(old, new, review, now_cst=None):
    """Decide whether a scheduled run should build/publish today.

    Policy:
    - review=True (cross-series Nginx/PCRE2 or real entrypoint/ change) -> PR only.
    - No changes -> skip build.
    - Any core component updated (Nginx, OpenSSL, PCRE2, Ubuntu base, non-BoringSSL
      third-party modules) -> build & publish immediately (including latest BoringSSL).
    - Only BoringSSL updated -> build & publish on Monday (UTC+8); defer Tue-Sun.
    """
    if now_cst is None:
        now_cst = datetime.datetime.now(CST)
    changes = diff_components(old, new)
    changed = bool(changes)
    core_changes = [c for c in changes if c not in ("git.boringssl", "entrypoint")]

    if review:
        should_build = False
        reason = "review_required"
    elif not changed:
        should_build = False
        reason = "no_changes"
    elif core_changes:
        should_build = True
        reason = "core_update"
    elif changes == ["git.boringssl"]:
        if now_cst.weekday() == 0:
            should_build = True
            reason = "boringssl_weekly_monday"
        else:
            should_build = False
            reason = "boringssl_deferred_until_monday"
    else:
        should_build = True
        reason = "component_update"

    return {
        "changed": changed,
        "review": review,
        "should_build": should_build,
        "reason": reason,
        "changes": changes,
        "core_changes": core_changes,
    }


def main():
    p = pathlib.Path("locks/components.json")
    old = json.loads(p.read_text())
    new = copy.deepcopy(old)
    review = False

    html = get("https://nginx.org/en/download.html").decode()
    stable = re.search(
        r"Stable version.*?nginx-(\d+\.\d+\.\d+)\.tar.gz", html, re.S
    ).group(1)
    if stable != old["nginx"]["version"]:
        review |= version(stable)[:2] != version(old["nginx"]["version"])[:2]
        new["nginx"] = {
            "version": stable,
            "sha256": hashlib.sha256(
                get(f"https://nginx.org/download/nginx-{stable}.tar.gz")
            ).hexdigest(),
        }

    for name, repo, prefix in [
        ("pcre2", "PCRE2Project/pcre2", "pcre2-"),
        ("openssl", "openssl/openssl", "openssl-"),
    ]:
        releases = api(f"repos/{repo}/releases?per_page=50")
        releases = [
            r
            for r in releases
            if not r["draft"]
            and not r["prerelease"]
            and re.fullmatch(
                re.escape(prefix) + r"\d+\.\d+(?:\.\d+)?", r["tag_name"]
            )
        ]
        if name == "openssl":
            releases = [
                r
                for r in releases
                if version(r["tag_name"])[:2] == version(old[name]["version"])[:2]
            ]
        r = max(releases, key=lambda r: version(r["tag_name"]))
        v = r["tag_name"].removeprefix(prefix)
        if v != old[name]["version"]:
            review |= version(v)[0] != version(old[name]["version"])[0]
            a = next(
                a for a in r["assets"] if a["name"] == prefix + v + ".tar.gz"
            )
            digest = hashlib.sha256(get(a["browser_download_url"])).hexdigest()
            if a.get("digest"):
                assert a["digest"] == "sha256:" + digest
            new[name] = {"version": v, "sha256": digest}

    for name, item in new["git"].items():
        item["commit"] = api(f'repos/{item["repo"]}/commits/HEAD')["sha"]

    # Track only commits touching entrypoint/ to avoid false review PRs on unrelated Dockerfiles.
    entry_commits = api("repos/nginx/docker-nginx/commits?path=entrypoint&per_page=1")
    entry = entry_commits[0]["sha"]
    if entry != new["entrypoint"]:
        new["entrypoint"] = entry
        review = True

    base = json.loads(
        get("https://hub.docker.com/v2/repositories/library/ubuntu/tags/24.04/")
    )
    if base.get("digest"):
        new["base"] = "ubuntu:24.04@" + base["digest"]
    # Major distro changes remain manual; only the pinned Ubuntu 24.04 digest advances.

    result = plan_update(old, new, review)
    p.write_text(json.dumps(new, indent=2) + "\n")
    pathlib.Path("update-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))

    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"changed={str(result['changed']).lower()}\n")
            f.write(f"review={str(result['review']).lower()}\n")
            f.write(f"should_build={str(result['should_build']).lower()}\n")
            f.write(f"reason={result['reason']}\n")


if __name__ == "__main__":
    main()
