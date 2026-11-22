"""CrediScore · scoring-api (servicio mínimo para el lab S07).

Implementa un subconjunto del contrato api/openapi.yaml (S05):
  POST /v1/credit-applications                         (idempotente por Idempotency-Key)
  GET  /v1/credit-applications/{applicationId}
  GET  /v1/credit-applications/{applicationId}/decision
  GET  /v1/credit-applications/{applicationId}/explanation   (feature IA, S18 · src/explainer.py)
y expone /health y /ready para las probes de Kubernetes y /metrics para Prometheus (SLOs).

Limitaciones conocidas (placeholder del lab):
- El almacenamiento es en memoria, por réplica. Persistencia real: Aurora PostgreSQL (ADR 0004).
- El puntaje es una regla fija, no el modelo de ML.
- No valida el token OAuth2 del contrato.
"""

import hashlib
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Literal

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field

from src import metrics
from src.explainer import Explainer

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "info").upper(),
    format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
)
log = logging.getLogger("scoring-api")

app = FastAPI(title="CrediScore Scoring API", version="0.2.0")

MODEL_VERSION = "placeholder-0.1.0"


# ---------- Modelos (api/openapi.yaml · components.schemas) ----------


class CreditApplicationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rut: str = Field(pattern=r"^\d{7,8}-[0-9K]$")
    amount: int = Field(ge=50_000, le=5_000_000)
    term_months: int = Field(ge=1, le=36)
    identity_verification_id: uuid.UUID
    partner_reference: str | None = Field(default=None, max_length=64)


class Decision(BaseModel):
    application_id: uuid.UUID
    outcome: Literal["approved", "rejected", "review"]
    score: int | None
    risk_category: Literal["low", "medium", "medium_no_history", "high"] | None
    reasons: list[str]
    model_version: str | None
    decided_by: Literal["model", "analyst"]
    decided_at: str


class Explanation(BaseModel):
    application_id: uuid.UUID
    outcome: Literal["approved", "rejected", "review"]
    text: str
    source: Literal["llm", "template", "cache"]
    model: str | None
    prompt_version: str
    guardrails: dict
    human_review: dict
    generated_at: str


# ---------- Estado en memoria (placeholder) ----------

APPLICATIONS: dict[str, dict] = {}
DECISIONS: dict[str, dict] = {}
IDEMPOTENCY: dict[str, tuple[str, dict]] = {}  # key -> (hash del cuerpo, respuesta)
EXPLAINER = Explainer()


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def problem(status: int, title: str, detail: str, trace_id: str) -> JSONResponse:
    """Error en formato RFC 7807, como define el contrato."""
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        headers={"X-Trace-Id": trace_id},
        content={
            "type": f"https://api.crediscore.cl/problems/{status}",
            "title": title,
            "status": status,
            "detail": detail,
            "trace_id": trace_id,
        },
    )


@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    request.state.trace_id = request.headers.get("X-Trace-Id") or uuid.uuid4().hex
    start = time.perf_counter()
    response = await call_next(request)
    # Métricas por plantilla de ruta (no por ID, para no explotar la cardinalidad)
    route = getattr(request.scope.get("route"), "path", "unmatched")
    metrics.observe(route, time.perf_counter() - start)
    metrics.inc(
        "crediscore_http_requests_total",
        {"route": route, "method": request.method, "status": str(response.status_code)},
    )
    response.headers.setdefault("X-Trace-Id", request.state.trace_id)
    # Headers de seguridad (S10, los revisa el DAST con ZAP):
    # no adivinar el tipo de contenido, no cachear datos financieros, no embeber en iframes.
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Cache-Control", "no-store")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return problem(422, "Solicitud inválida", str(exc.errors()), request.state.trace_id)


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return problem(exc.status_code, "Error", str(exc.detail), request.state.trace_id)


# ---------- Scoring placeholder ----------


def decide(app_id: str, data: CreditApplicationInput) -> dict:
    """Regla fija 0–1000: penaliza montos altos y plazos largos. La reemplaza el modelo real."""
    carga = data.amount / 5_000_000
    plazo = data.term_months / 36
    score = round(1000 * (1 - 0.6 * carga - 0.3 * plazo))
    if score >= 650:
        outcome, risk, reasons = "approved", "low", ["LOW_DEBT_RATIO"]
    elif score >= 450:
        outcome, risk, reasons = "review", "medium", ["INCOME_PROOF_REQUIRED"]
    else:
        outcome, risk, reasons = "rejected", "high", ["AMOUNT_TOO_HIGH_FOR_TERM"]
    return Decision(
        application_id=app_id,
        outcome=outcome,
        score=score,
        risk_category=risk,
        reasons=reasons,
        model_version=MODEL_VERSION,
        decided_by="model",
        decided_at=now(),
    ).model_dump(mode="json")


# ---------- Endpoints ----------


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    return {"status": "ready"}


@app.get("/metrics", include_in_schema=False)
def prometheus_metrics():
    return PlainTextResponse(metrics.render(), media_type="text/plain; version=0.0.4")


@app.post("/v1/credit-applications", status_code=201)
def create_credit_application(
    body: CreditApplicationInput,
    request: Request,
    idempotency_key: uuid.UUID = Header(alias="Idempotency-Key"),
):
    trace_id = request.state.trace_id
    key = str(idempotency_key)
    body_hash = hashlib.sha256(json.dumps(body.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()

    if key in IDEMPOTENCY:
        saved_hash, saved_response = IDEMPOTENCY[key]
        if saved_hash != body_hash:
            return problem(
                409, "Conflicto de idempotencia", "La misma Idempotency-Key se usó con otro cuerpo.", trace_id
            )
        return JSONResponse(
            status_code=201,
            content=saved_response,
            headers={"Idempotent-Replayed": "true", "Location": f"/v1/credit-applications/{saved_response['id']}"},
        )

    app_id = str(uuid.uuid4())
    ts = now()
    application = {
        "id": app_id,
        "status": "received",
        **body.model_dump(mode="json", exclude_none=True),
        "created_at": ts,
        "updated_at": ts,
    }
    APPLICATIONS[app_id] = application
    IDEMPOTENCY[key] = (body_hash, application)

    # En producción la decisión es asíncrona (Kafka). Aquí se calcula al tiro para el demo.
    DECISIONS[app_id] = decide(app_id, body)
    log.info("solicitud creada id=%s trace_id=%s", app_id, trace_id)

    return JSONResponse(
        status_code=201,
        content=application,
        headers={"Idempotent-Replayed": "false", "Location": f"/v1/credit-applications/{app_id}"},
    )


@app.get("/v1/credit-applications/{application_id}")
def get_credit_application(application_id: uuid.UUID):
    application = APPLICATIONS.get(str(application_id))
    if application is None:
        raise HTTPException(404, "Solicitud inexistente.")
    return application


@app.get("/v1/credit-applications/{application_id}/decision")
def get_credit_application_decision(application_id: uuid.UUID):
    decision = DECISIONS.get(str(application_id))
    if decision is None:
        raise HTTPException(404, "La solicitud no existe o aún no tiene decisión.")
    return decision


@app.get("/v1/credit-applications/{application_id}/explanation", response_model=Explanation)
def get_credit_application_explanation(application_id: uuid.UUID):
    """Explicación en lenguaje claro de la decisión (feature IA, ver docs/ia/model-card.md)."""
    decision = DECISIONS.get(str(application_id))
    application = APPLICATIONS.get(str(application_id))
    if decision is None or application is None:
        raise HTTPException(404, "La solicitud no existe o aún no tiene decisión.")
    exp = EXPLAINER.explain(decision, application)
    return Explanation(
        application_id=application_id,
        outcome=decision["outcome"],
        text=exp.text,
        source=exp.source,
        model=exp.model,
        prompt_version=exp.prompt_version,
        guardrails={
            "passed": not exp.violations,
            "output_violations": exp.violations,
            "input_flags": exp.input_flags,
            "fallback_reason": exp.fallback_reason,
        },
        human_review={
            "available": True,
            "legal_basis": "Ley 21.719, art. 8 bis (decisiones individuales automatizadas)",
        },
        generated_at=now(),
    ).model_dump(mode="json")


if __name__ == "__main__":
    uvicorn.run(
        app,
        # Escucha en todas las interfaces porque corre dentro de un contenedor.
        host="0.0.0.0",  # nosec B104
        port=int(os.getenv("APP_PORT", "8080")),
        timeout_graceful_shutdown=25,
        server_header=False,  # no anunciar "uvicorn" en cada respuesta
    )
