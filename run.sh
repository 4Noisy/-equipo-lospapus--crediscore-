#!/usr/bin/env sh
# Arranca el MVP en Linux/macOS: ./run.sh   (opcional: PORT=9000 ./run.sh)
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-python3}; command -v "$PY" >/dev/null || PY=python
[ -d .venv ] || "$PY" -m venv .venv
. .venv/bin/activate
pip install -q -r requirements.txt
export APP_PORT=${PORT:-8080}
URL="http://localhost:$APP_PORT"
(sleep 2; (command -v xdg-open >/dev/null && xdg-open "$URL") || (command -v open >/dev/null && open "$URL") || true) &
echo "CrediScore en $URL  (Ctrl+C para salir)"
exec python -m src.main
