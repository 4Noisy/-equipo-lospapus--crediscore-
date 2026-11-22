"""Generador de carga mínimo (librería estándar) para game day y right-sizing.

  python scripts/loadgen.py http://localhost:8080 --seconds 60 --workers 8 [--explain]

Cada iteración: POST solicitud y GET de su decisión (y explicación si --explain).
Mide disponibilidad, latencia (p50/p95/p99) y consistencia lectura-después-de-escritura
(una decisión que no aparece porque el GET cayó en otra réplica cuenta como inconsistente:
el estado vive en memoria por réplica, ver ADR 0009).
Imprime una línea JSON al final; el game day la guarda como evidencia.
"""

from __future__ import annotations

import argparse
import http.client
import json
import sys
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from smoke_e2e import solicitud  # noqa: E402


class Conn:
    """Una conexión keep-alive por worker (como un cliente real; evita agotar puertos)."""

    def __init__(self, base: str):
        u = urlsplit(base)
        self.host, self.port = u.hostname, u.port or 80
        self.c = None

    def __call__(self, method, path, body=None, headers=None, timeout=5):
        if self.c is None:
            self.c = http.client.HTTPConnection(self.host, self.port, timeout=timeout)
        self.c.timeout = timeout
        if self.c.sock is not None:
            self.c.sock.settimeout(timeout)
        h = {"Content-Type": "application/json", **(headers or {})}
        try:
            self.c.request(method, path, body=json.dumps(body) if body is not None else None, headers=h)
            r = self.c.getresponse()
            return r.status, {}, r.read().decode()
        except Exception:
            self.c.close()
            self.c = None
            raise


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    return round(values[min(len(values) - 1, int(len(values) * p))] * 1000, 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("--seconds", type=float, default=30)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--explain", action="store_true")
    ap.add_argument("--label", default="load")
    a = ap.parse_args()
    base = a.base.rstrip("/")

    lock = threading.Lock()
    stats = {
        "post_ok": 0,
        "post_err": 0,
        "read_ok": 0,
        "read_missing": 0,
        "read_err": 0,
        "explain_template": 0,
        "explain_llm": 0,
        "explain_err": 0,
    }
    lat_post: list[float] = []
    lat_explain: list[float] = []
    errors: dict[str, int] = {}
    timeline: list[tuple[float, bool]] = []
    start = time.monotonic()
    deadline = start + a.seconds

    def worker():
        call = Conn(base)
        while time.monotonic() < deadline:
            t0 = time.perf_counter()
            try:
                st, _, raw = call(
                    "POST",
                    "/v1/credit-applications",
                    solicitud(),
                    {"Idempotency-Key": str(uuid.uuid4())},
                    timeout=5,
                )
            except Exception as e:  # conexión rechazada, timeout, reset
                st, raw = 0, type(e).__name__
            dt = time.perf_counter() - t0
            ok = st == 201
            with lock:
                timeline.append((time.monotonic() - start, ok))
                if ok:
                    stats["post_ok"] += 1
                    lat_post.append(dt)
                else:
                    stats["post_err"] += 1
                    errors[str(st or raw)] = errors.get(str(st or raw), 0) + 1
            if not ok:
                time.sleep(0.05)
                continue
            app_id = json.loads(raw)["id"]
            try:
                st, _, _ = call("GET", f"/v1/credit-applications/{app_id}/decision", timeout=5)
            except Exception:
                st = 0
            with lock:
                stats["read_ok" if st == 200 else "read_missing" if st == 404 else "read_err"] += 1
            if a.explain:
                t1 = time.perf_counter()
                try:
                    st, _, raw = call("GET", f"/v1/credit-applications/{app_id}/explanation", timeout=15)
                    src = json.loads(raw).get("source") if st == 200 else None
                except Exception:
                    st, src = 0, None
                with lock:
                    if st == 200:
                        lat_explain.append(time.perf_counter() - t1)
                        stats["explain_llm" if src in {"llm", "cache"} else "explain_template"] += 1
                    elif st != 404:
                        stats["explain_err"] += 1

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(a.workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Ventana más larga con errores (aproximación del tiempo de impacto)
    worst, cur, last_t = 0.0, None, None
    for t, ok in sorted(timeline):
        if not ok and cur is None:
            cur = t
        if ok and cur is not None:
            worst = max(worst, t - cur)
            cur = None
        last_t = t
    if cur is not None and last_t is not None:
        worst = max(worst, last_t - cur)

    total = stats["post_ok"] + stats["post_err"]
    reads = stats["read_ok"] + stats["read_missing"] + stats["read_err"]
    out = {
        "label": a.label,
        "seconds": a.seconds,
        "workers": a.workers,
        "requests_post": total,
        "rps_post": round(total / a.seconds, 1),
        "availability_post": round(stats["post_ok"] / total, 5) if total else 0,
        "post_p50_ms": pct(lat_post, 0.50),
        "post_p95_ms": pct(lat_post, 0.95),
        "post_p99_ms": pct(lat_post, 0.99),
        "read_after_write_consistency": round(stats["read_ok"] / reads, 5) if reads else 0,
        "longest_error_window_s": round(worst, 2),
        "errors": errors,
        **({"explain_p95_ms": pct(lat_explain, 0.95), "explain_p50_ms": pct(lat_explain, 0.50)} if a.explain else {}),
        **stats,
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
