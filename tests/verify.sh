#!/bin/bash
set -euo pipefail
image=${1:?image}
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
name=nginx-ci-test
trap 'docker logs "$name" 2>&1 || true; docker rm -f "$name" >/dev/null 2>&1 || true' EXIT
python3 -m venv work/test-venv
work/test-venv/bin/pip install -r tests/requirements.txt
openssl req -x509 -newkey rsa:2048 -nodes -subj /CN=localhost -days 1 -keyout work/test.key -out work/test.crt >/dev/null 2>&1
docker run -d --name "$name" --network host --ulimit nofile=8192:8192 "$image"
for i in $(seq 1 15); do if curl --noproxy '*' -fsS http://127.0.0.1/ >/dev/null; then break; fi; sleep 1; done
docker exec "$name" nginx -t
docker exec "$name" nginx -V
for f in test-modules.conf test-tls.conf; do docker cp "tests/$f" "$name:/tmp/$f"; done
for f in test.key test.crt; do docker cp "work/$f" "$name:/tmp/$f"; done
for f in test-modules.conf test-tls.conf; do docker exec "$name" nginx -t -c "/tmp/$f"; docker exec "$name" nginx -c "/tmp/$f"; done
work/test-venv/bin/python tests/verify-http.py
work/test-venv/bin/python tests/test-http3.py
docker exec "$name" sh -c 'test ! -e /root/ssl.key; test ! -e /usr/bin/gcc; command -v envsubst; command -v curl'
printf 'server { listen ${TEST_PORT}; location / { return 200 "template-ok"; } }\n' >work/test.conf.template
docker cp work/test.conf.template "$name:/etc/nginx/templates/test.conf.template"
docker exec -e TEST_PORT=18083 "$name" /docker-entrypoint.d/20-envsubst-on-templates.sh
docker exec "$name" nginx -s reload
for i in $(seq 1 10); do if [[ $(curl --noproxy '*' -fsS http://127.0.0.1:18083/ || true) == template-ok ]]; then break; fi; sleep 1; done
[[ $(curl --noproxy '*' -fsS http://127.0.0.1:18083/) == template-ok ]]
