"""CrediScore · antifraude simulado (MVP de demo).

Reglas determinísticas y explicables, sin ML: sirven para mostrar el flujo y el
objetivo de latencia (< 500 ms) del evento de fraude. Cada regla suma puntos; con
RISK_REVIEW_THRESHOLD o más, la decisión pasa a revisión humana.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from src import metrics
from src.explainer import detect_injection

TARGET_MS = 500  # objetivo de propagación del evento de fraude (README)
RISK_REVIEW_THRESHOLD = 70

RULES = {
    "HIGH_AMOUNT_SHORT_TERM": (45, "Monto muy alto para un plazo muy corto"),
    "RUT_VELOCITY": (40, "El mismo RUT envió varias solicitudes seguidas"),
    "PARTNER_REF_INJECTION": (40, "El campo de referencia intenta dar órdenes al sistema"),
}


def check(application: dict, previous_by_rut: int) -> dict:
    """Evalúa una solicitud. `previous_by_rut` = solicitudes anteriores del mismo RUT."""
    start = time.perf_counter()
    flags: list[str] = []
    if application["amount"] >= 2_000_000 and application["term_months"] <= 3:
        flags.append("HIGH_AMOUNT_SHORT_TERM")
    if previous_by_rut >= 3:
        flags.append("RUT_VELOCITY")
    if detect_injection(application.get("partner_reference")):
        flags.append("PARTNER_REF_INJECTION")

    risk = min(100, sum(RULES[f][0] for f in flags))
    level = "high" if risk >= RISK_REVIEW_THRESHOLD else "medium" if risk > 0 else "low"
    elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
    metrics.inc("crediscore_fraud_checks_total", {"level": level})
    return {
        "application_id": application["id"],
        "risk_score": risk,
        "risk_level": level,
        "flags": [{"code": f, "points": RULES[f][0], "description": RULES[f][1]} for f in flags],
        "action": "send_to_review" if level == "high" else "none",
        "processing_ms": elapsed_ms,
        "target_ms": TARGET_MS,
        "within_target": elapsed_ms <= TARGET_MS,
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "check_id": str(uuid.uuid4()),
    }
