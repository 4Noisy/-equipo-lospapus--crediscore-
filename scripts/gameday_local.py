"""Game day local de CrediScore (S18). Ejecuta 3 experimentos de caos sobre la API real.

  python scripts/gameday_local.py            # ~2 min, escribe docs/resiliencia/evidencia/gameday-local.json

  E0 · Línea base: carga sin fallas (referencia para SLOs y right-sizing: CPU y RAM medidas).
  E1 · Proveedor LLM caído: EXPLAINER_MODE=llm apuntando a una IP que no responde.
       Hipótesis: 0 errores 5xx, el circuit breaker se abre tras 3 fallas y la explicación
       sigue saliendo desde la plantilla con p95 < 500 ms una vez abierto.
  E2 · Caída del proceso (equivalente local a matar el único Pod): kill -9 a los 10 s y
       reinicio automático. Hipótesis: recupera en < 10 s. Se mide además cuántas
       solicitudes creadas antes de la caída siguen existiendo después (RPO).

Cada experimento corre la API en un proceso aparte con uvicorn y la carga con
scripts/loadgen.py. Los números que se reportan en docs/resiliencia/game-day.md salen de acá.
"""

from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from smoke_e2e import call, solicitud  # noqa: E402

OUT = ROOT / "docs" / "resiliencia" / "evidencia" / "gameday-local.json"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_api(port: int, extra_env: dict | None = None) -> subprocess.Popen:
    env = {**os.environ, "APP_PORT": str(port), "LOG_LEVEL": "error", **(extra_env or {})}
    proc = subprocess.Popen(  # nosec B603
        [sys.executable, "-m", "src.main"], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    wait_ready(port)
    return proc


def kill_tree(proc: subprocess.Popen) -> None:
    """kill -9 al proceso y a sus hijos (en Windows el python.exe del venv es un lanzador)."""
    import psutil

    try:
        parent = psutil.Process(proc.pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except psutil.NoSuchProcess:
        pass
    proc.wait()


def wait_ready(port: int, timeout: float = 20) -> float:
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/ready", timeout=0.5)  # nosec B310  # nosemgrep
            return time.monotonic() - t0
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("la API no levantó")


def loadgen(port: int, seconds: float, workers: int, label: str, explain: bool = False) -> dict:
    args = [
        sys.executable,
        str(ROOT / "scripts" / "loadgen.py"),
        f"http://127.0.0.1:{port}",
        "--seconds",
        str(seconds),
        "--workers",
        str(workers),
        "--label",
        label,
    ]
    if explain:
        args.append("--explain")
    out = subprocess.run(args, capture_output=True, text=True, timeout=seconds + 120)  # nosec B603
    return json.loads(out.stdout.strip().splitlines()[-1])


def metrics_text(port: int) -> str:
    return call(f"http://127.0.0.1:{port}", "GET", "/metrics")[2]


def metric(text: str, prefix: str) -> float:
    return sum(float(line.rsplit(" ", 1)[1]) for line in text.splitlines() if line.startswith(prefix))


def sample_resources(pid: int, stop: threading.Event, samples: list) -> None:
    try:
        import psutil
    except ImportError:
        return
    root = psutil.Process(pid)
    procs = [root, *root.children(recursive=True)]
    for p in procs:
        p.cpu_percent(None)
    while not stop.is_set():
        time.sleep(0.5)
        try:
            cpu = sum(p.cpu_percent(None) for p in procs)
            rss = max(p.memory_info().rss for p in procs) / 2**20  # el servidor real (no el lanzador)
            samples.append((cpu, rss))
        except psutil.NoSuchProcess:
            return


def e0_baseline() -> dict:
    port = free_port()
    proc = start_api(port)
    stop, samples = threading.Event(), []
    t = threading.Thread(target=sample_resources, args=(proc.pid, stop, samples), daemon=True)
    t.start()
    try:
        r = loadgen(port, 30, 8, "E0-baseline", explain=True)
    finally:
        stop.set()
        kill_tree(proc)
    if samples:
        cpus = sorted(s[0] for s in samples)
        mems = sorted(s[1] for s in samples)
        r["cpu_percent_p95"] = round(cpus[int(len(cpus) * 0.95) - 1], 1)
        r["cpu_millicores_p95"] = round(cpus[int(len(cpus) * 0.95) - 1] * 10)
        r["rss_mib_max"] = round(mems[-1], 1)
        r["rss_mib_p50"] = round(mems[len(mems) // 2], 1)
    return r


def e1_llm_down() -> dict:
    port = free_port()
    env = {
        "EXPLAINER_MODE": "llm",
        "ANTHROPIC_API_KEY": "gameday-valor-falso",  # no es una credencial: el destino no existe
        "ANTHROPIC_BASE_URL": "http://10.255.255.1:81",  # IP no enrutable: simula proveedor caído
        "EXPLAINER_TIMEOUT_S": "2",
        "EXPLAINER_CB_FAILURES": "3",
        "EXPLAINER_CB_RESET_S": "15",
    }
    proc = start_api(port, env)
    try:
        r = loadgen(port, 40, 4, "E1-llm-down", explain=True)
        m = metrics_text(port)
    finally:
        kill_tree(proc)
    r["llm_calls_error"] = metric(m, 'crediscore_llm_calls_total{result="error"}')
    r["llm_calls_short_circuited"] = metric(m, 'crediscore_llm_calls_total{result="circuit_open"}')
    r["explanations_template"] = metric(m, 'crediscore_explanations_total{source="template"}')
    r["http_5xx"] = sum(
        float(line.rsplit(" ", 1)[1])
        for line in m.splitlines()
        if line.startswith("crediscore_http_requests_total") and 'status="5' in line
    )
    return r


def e2_process_kill() -> dict:
    port = free_port()
    env = {"EXPLAINER_MODE": "template"}
    proc = start_api(port, env)
    base = f"http://127.0.0.1:{port}"
    before = []
    for _ in range(20):
        st, _, raw = call(base, "POST", "/v1/credit-applications", solicitud(), {"Idempotency-Key": str(uuid.uuid4())})
        before.append(json.loads(raw)["id"])

    result: dict = {}

    def chaos():
        time.sleep(10)
        kill_tree(proc)  # equivalente a kill -9 / OOMKilled
        t_kill = time.monotonic()
        # El "kubelet": reinicia el proceso
        newp = start_api(port, env)
        result["restart_s"] = round(time.monotonic() - t_kill, 2)
        result["proc"] = newp

    th = threading.Thread(target=chaos)
    th.start()
    r = loadgen(port, 25, 4, "E2-process-kill")
    th.join()
    survived = sum(call(base, "GET", f"/v1/credit-applications/{i}")[0] == 200 for i in before)
    kill_tree(result["proc"])
    r["restart_s"] = result["restart_s"]
    r["applications_before_kill"] = len(before)
    r["applications_after_restart"] = survived
    r["data_loss_ratio"] = round(1 - survived / len(before), 3)
    return r


def main() -> int:
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print("E0 · línea base...", flush=True)
    e0 = e0_baseline()
    print(json.dumps(e0), flush=True)
    print("E1 · proveedor LLM caído...", flush=True)
    e1 = e1_llm_down()
    print(json.dumps(e1), flush=True)
    print("E2 · caída del proceso...", flush=True)
    e2 = e2_process_kill()
    print(json.dumps(e2), flush=True)
    out = {
        "started_at": started,
        "host": {"os": platform.platform(), "python": platform.python_version(), "cpus": os.cpu_count()},
        "E0_baseline": e0,
        "E1_llm_down": e1,
        "E2_process_kill": e2,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Evidencia: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
