"""Test de integración (S18): levanta la API real con uvicorn en otro proceso y corre
el flujo crítico por HTTP (scripts/smoke_e2e.py), igual que la demo y el game day.
"""

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import smoke_e2e  # noqa: E402


def puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def api():
    port = puerto_libre()
    env = {**os.environ, "APP_PORT": str(port), "EXPLAINER_MODE": "template", "LOG_LEVEL": "warning"}
    proc = subprocess.Popen([sys.executable, "-m", "src.main"], cwd=ROOT, env=env)  # nosec B603
    base = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            urllib.request.urlopen(base + "/ready", timeout=1)  # nosec B310
            break
        except Exception:
            time.sleep(0.2)
    else:
        proc.kill()
        pytest.fail("la API no levantó")
    yield base
    proc.terminate()
    proc.wait(timeout=30)


def test_flujo_critico_end_to_end(api):
    pasos = smoke_e2e.run(api)
    fallidos = [p for p in pasos if not p["ok"]]
    assert not fallidos, fallidos
    assert len(pasos) == 9
