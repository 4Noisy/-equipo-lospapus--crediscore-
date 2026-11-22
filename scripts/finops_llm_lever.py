"""FinOps · Palanca 1: medir llamadas al LLM y costo antes/después (S18).

  python scripts/finops_llm_lever.py     # escribe docs/finops/evidencia/llm-lever.json

Corre el Explainer REAL (src/explainer.py) sobre 4.000 solicitudes sintéticas, con un
cliente LLM falso que cuenta llamadas. Cada explicación se pide 2 veces (supuesto: la ve el
solicitante en la app y el partner por API). Tres configuraciones:

  A · antes      : LLM para todo, sin caché
  B · + caché    : caché por contenido de la decisión
  C · + filtro   : caché + LLM solo para "review" y "rejected" (lo aprobado sale de plantilla)

Lo MEDIDO es el número de llamadas al LLM. Los tokens por llamada son una ESTIMACIÓN
(caracteres / 3,5 para español + 200 tokens de razonamiento con effort low) hasta tener la
corrida real de .github/workflows/ai-eval-llm.yml, que cuenta los tokens que factura Anthropic.
"""

from __future__ import annotations

import json
import random
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import explainer as ex  # noqa: E402
from src import main, metrics  # noqa: E402

OUT = ROOT / "docs" / "finops" / "evidencia" / "llm-lever.json"
CHARS_PER_TOKEN = 3.5
THINKING_TOKENS_EST = 200
VIEWS_PER_APPLICATION = 2
MONTHLY_APPLICATIONS = 30_000  # supuesto de negocio del MVP (~1.000 al día), ver docs/finops/costos.md


class CountingLLM:
    def __init__(self):
        self.calls = 0
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.calls += 1
        payload = json.loads(kw["messages"][0]["content"])
        text = _good_text(payload)
        tin = round((len(kw["system"]) + len(kw["messages"][0]["content"])) / CHARS_PER_TOKEN)
        tout = round(len(text) / CHARS_PER_TOKEN) + THINKING_TOKENS_EST
        return SimpleNamespace(
            stop_reason="end_turn",
            content=[SimpleNamespace(type="text", text=text)],
            usage=SimpleNamespace(input_tokens=tin, output_tokens=tout),
        )


def _good_text(p: dict) -> str:
    verbo = {"approved": "fue aprobada", "review": "quedó en revisión", "rejected": "fue rechazada"}[p["outcome"]]
    return (
        f"Tu solicitud {verbo} porque {p['reasons'][0]}. Tu puntaje fue {p['score']} de 1000. "
        "Tienes derecho a pedir que una persona revise esta decisión."
    )


def population(n=4000, seed=21719):
    rng = random.Random(seed)
    for _ in range(n):
        zona = rng.choices(["RM", "regiones"], weights=[0.45, 0.55])[0]
        mu = 13.9 if zona == "RM" else 13.75
        # Los montos se piden en pasos de $10.000 (así los ofrece la UI del partner)
        amount = int(min(5_000_000, max(50_000, round(rng.lognormvariate(mu, 0.7), -4))))
        term = min(36, max(1, int(rng.gauss(20 if zona == "regiones" else 18, 8))))
        yield amount, term


def run(label: str, cache_size: int, outcomes: set[str]) -> dict:
    metrics.reset()
    fake = CountingLLM()
    e = ex.Explainer(mode="llm", client=fake, cache_size=cache_size, llm_outcomes=outcomes)
    n = 0
    for amount, term in population():
        body = main.CreditApplicationInput(
            rut="12345678-5", amount=amount, term_months=term, identity_verification_id=uuid.uuid4()
        )
        app_id = str(uuid.uuid4())
        decision = main.decide(app_id, body)
        application = {"id": app_id, **body.model_dump(mode="json")}
        for _ in range(VIEWS_PER_APPLICATION):
            e.explain(decision, application)
            n += 1
    cost = metrics.get("crediscore_llm_cost_usd_total")
    per_app = cost / 4000
    return {
        "config": label,
        "explanations_served": n,
        "llm_calls": fake.calls,
        "llm_calls_per_1000_explanations": round(fake.calls / n * 1000, 1),
        "input_tokens_est": metrics.get("crediscore_llm_tokens_total", {"kind": "input"}),
        "output_tokens_est": metrics.get("crediscore_llm_tokens_total", {"kind": "output"}),
        "cost_usd_4000_apps_est": round(cost, 4),
        "cost_usd_per_application_est": round(per_app, 6),
        "cost_usd_month_est": round(per_app * MONTHLY_APPLICATIONS, 2),
        "guardrail_violations": metrics.get("crediscore_guardrail_violations_total", {"rule": "outcome_mismatch"}),
    }


def main_() -> int:
    todos = {"approved", "review", "rejected"}
    results = [
        run("A_antes_sin_cache_todo_llm", 0, todos),
        run("B_cache", 1024, todos),
        run("C_cache_y_solo_review_rejected", 1024, {"review", "rejected"}),
    ]
    out = {
        "model": ex.DEFAULT_MODEL,
        "price_per_mtok_usd": ex.PRICES_PER_MTOK[ex.DEFAULT_MODEL],
        "assumptions": {
            "applications": 4000,
            "views_per_application": VIEWS_PER_APPLICATION,
            "monthly_applications": MONTHLY_APPLICATIONS,
            "chars_per_token": CHARS_PER_TOKEN,
            "thinking_tokens_est": THINKING_TOKENS_EST,
        },
        "results": results,
        "reduction_calls_A_to_C": round(1 - results[2]["llm_calls"] / results[0]["llm_calls"], 4),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    for r in results:
        print(json.dumps(r))
    print(f"Reducción de llamadas A -> C: {out['reduction_calls_A_to_C']:.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main_())
