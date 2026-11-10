#!/bin/bash
set -euo pipefail
sudo apt-get update
sudo apt-get install -y --no-install-recommends build-essential cmake ninja-build zlib1g-dev libcrypt-dev libjemalloc-dev libpcre2-dev curl git ca-certificates pkg-config gettext-base python3-venv
