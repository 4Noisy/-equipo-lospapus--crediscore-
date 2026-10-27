import uuid

import pytest
from fastapi.testclient import TestClient

from src import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def limpiar_estado():
    main.APPLICATIONS.clear()
    main.DECISIONS.clear()
    main.IDEMPOTENCY.clear()


def payload(**cambios):
    base = {
        "rut": "12345678-5",
        "amount": 500_000,
        "term_months": 12,
        "identity_verification_id": str(uuid.uuid4()),
    }
    base.update(cambios)
    return base


def crear(body=None, key=None):
    return client.post(
        "/v1/credit-applications",
        json=body or payload(),
        headers={"Idempotency-Key": key or str(uuid.uuid4())},
    )


def test_health_y_ready():
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").json() == {"status": "ready"}


def test_crear_solicitud_devuelve_201_y_trace_id():
    r = crear()
    assert r.status_code == 201
    assert r.headers["Idempotent-Replayed"] == "false"
    assert "X-Trace-Id" in r.headers
    assert r.json()["status"] == "received"


def test_trace_id_se_propaga():
    r = client.get("/health", headers={"X-Trace-Id": "abc123"})
    assert r.headers["X-Trace-Id"] == "abc123"


def test_idempotencia_misma_key_mismo_cuerpo():
    key = str(uuid.uuid4())
    body = payload()
    r1 = crear(body, key)
    r2 = crear(body, key)
    assert r2.status_code == 201
    assert r2.headers["Idempotent-Replayed"] == "true"
    assert r1.json()["id"] == r2.json()["id"]


def test_idempotencia_misma_key_otro_cuerpo_da_409():
    key = str(uuid.uuid4())
    crear(payload(), key)
    r = crear(payload(amount=900_000), key)
    assert r.status_code == 409


def test_validacion_devuelve_422():
    r = crear(payload(rut="no-es-rut"))
    assert r.status_code == 422


def test_consultar_solicitud_y_decision():
    app_id = crear().json()["id"]
    assert client.get(f"/v1/credit-applications/{app_id}").status_code == 200
    d = client.get(f"/v1/credit-applications/{app_id}/decision")
    assert d.status_code == 200
    assert d.json()["decided_by"] == "model"


def test_solicitud_inexistente_da_404():
    falso = uuid.uuid4()
    assert client.get(f"/v1/credit-applications/{falso}").status_code == 404
    assert client.get(f"/v1/credit-applications/{falso}/decision").status_code == 404


@pytest.mark.parametrize(
    "monto,plazo,esperado",
    [(100_000, 6, "approved"), (2_500_000, 24, "review"), (5_000_000, 36, "rejected")],
)
def test_reglas_de_scoring(monto, plazo, esperado):
    app_id = crear(payload(amount=monto, term_months=plazo)).json()["id"]
    d = client.get(f"/v1/credit-applications/{app_id}/decision").json()
    assert d["outcome"] == esperado
