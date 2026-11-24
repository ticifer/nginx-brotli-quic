#!/usr/bin/env python3
"""Send Bark push notification using BARK_URL environment variable."""
import argparse
import json
import os
import sys
import urllib.request


def send_bark(bark_url, title, body, url="", group="nginx-brotli-quic", level="active"):
    endpoint = bark_url.strip().rstrip("/")
    if not endpoint:
        print("BARK_URL not configured; skipping notification.")
        return True
    payload = {
        "title": title,
        "body": body,
        "group": group,
        "level": level,
    }
    if url:
        payload["url"] = url
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "nginx-brotli-quic-notifier",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        status = resp.status
        raw = resp.read().decode("utf-8", errors="replace")
    if status != 200:
        raise RuntimeError(f"Bark HTTP {status}: {raw[:200]}")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {}
    if parsed.get("code") not in (None, 200):
        raise RuntimeError(f"Bark error: {parsed}")
    print("Bark notification sent successfully.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Send Bark push notification.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--body", required=True)
    parser.add_argument("--url", default="")
    parser.add_argument("--group", default="nginx-brotli-quic")
    parser.add_argument("--level", default="active")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    bark_url = os.environ.get("BARK_URL", "").strip()
    if not bark_url:
        print("BARK_URL not configured; skipping notification.")
        return

    try:
        send_bark(
            bark_url,
            title=args.title,
            body=args.body,
            url=args.url,
            group=args.group,
            level=args.level,
        )
    except Exception as exc:
        print(f"Warning: Bark notification failed: {exc}", file=sys.stderr)
        if args.strict:
            sys.exit(1)


if __name__ == "__main__":
    main()
