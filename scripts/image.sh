#!/bin/bash
set -euo pipefail
variant=${1:?}
read -r BASE NGINX < <(python3 -c 'import json;d=json.load(open("locks/components.json"));print(d["base"],d["nginx"]["version"])')
docker build --build-arg BASE="$BASE" --build-arg NGINX_VERSION="$NGINX" -t "nginx-ci:$variant" .
