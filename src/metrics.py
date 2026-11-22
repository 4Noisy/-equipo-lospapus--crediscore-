"""Métricas en memoria con formato Prometheus (sin dependencias).

Las usan los SLOs (docs/resiliencia/slos.md), el game day y FinOps:
  crediscore_http_requests_total{route,method,status}
  crediscore_http_request_duration_seconds (histograma por ruta)
  crediscore_explanations_total{source}          llm | template | cache
  crediscore_guardrail_violations_total{rule}
  crediscore_prompt_injection_flags_total
  crediscore_llm_calls_total{result}             ok | error | refusal | circuit_open
  crediscore_llm_tokens_total{kind}              input | output
  crediscore_llm_cost_usd_total
  crediscore_circuit_state                        0 cerrado · 1 semiabierto · 2 abierto

Es por réplica (cada Pod expone las suyas y Prometheus las suma).
"""

import threading
from collections import defaultdict

BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

_lock = threading.Lock()
_counters: dict[tuple[str, tuple], float] = defaultdict(float)
_gauges: dict[str, float] = {}
_hist: dict[str, dict] = {}


def _key(name: str, labels: dict | None) -> tuple[str, tuple]:
    return name, tuple(sorted((labels or {}).items()))


def inc(name: str, labels: dict | None = None, value: float = 1.0) -> None:
    with _lock:
        _counters[_key(name, labels)] += value


def set_gauge(name: str, value: float) -> None:
    with _lock:
        _gauges[name] = value


def observe(route: str, seconds: float) -> None:
    with _lock:
        h = _hist.setdefault(route, {"buckets": [0] * len(BUCKETS), "sum": 0.0, "count": 0})
        for i, b in enumerate(BUCKETS):
            if seconds <= b:
                h["buckets"][i] += 1
        h["sum"] += seconds
        h["count"] += 1


def get(name: str, labels: dict | None = None) -> float:
    with _lock:
        return _counters.get(_key(name, labels), 0.0)


def reset() -> None:
    with _lock:
        _counters.clear()
        _gauges.clear()
        _hist.clear()


def _fmt_labels(labels: tuple) -> str:
    if not labels:
        return ""
    inner = ",".join(f'{k}="{v}"' for k, v in labels)
    return "{" + inner + "}"


def render() -> str:
    lines: list[str] = []
    with _lock:
        for (name, labels), value in sorted(_counters.items()):
            lines.append(f"{name}{_fmt_labels(labels)} {value:g}")
        for name, value in sorted(_gauges.items()):
            lines.append(f"{name} {value:g}")
        for route, h in sorted(_hist.items()):
            base = "crediscore_http_request_duration_seconds"
            for b, c in zip(BUCKETS, h["buckets"]):
                lines.append(f'{base}_bucket{{route="{route}",le="{b}"}} {c}')
            lines.append(f'{base}_bucket{{route="{route}",le="+Inf"}} {h["count"]}')
            lines.append(f'{base}_sum{{route="{route}"}} {h["sum"]:.6f}')
            lines.append(f'{base}_count{{route="{route}"}} {h["count"]}')
    return "\n".join(lines) + "\n"
