"""Contract tests (S18): la API real cumple api/openapi.yaml.

Valida cada respuesta contra el schema del contrato (JSON Schema 2020-12, que es el
dialecto de OpenAPI 3.1) y revisa que no haya endpoints sin documentar. Si alguien
cambia un campo en el código sin tocar el contrato (o al revés), este test falla.
"""

import uuid
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry
from referencing.jsonschema import DRAFT202012

from src import main

SPEC = yaml.safe_load((Path(__file__).resolve().parents[1] / "api" / "openapi.yaml").read_text(encoding="utf-8"))
REGISTRY = Registry().with_resource("urn:crediscore", DRAFT202012.create_resource(SPEC))
client = TestClient(main.app)

# Endpoints operativos que no son parte de la API pública
OPERACIONALES = {"/", "/health", "/ready", "/metrics", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}


def validar(instancia, schema_name: str):
    validator = Draft202012Validator(
        {"$ref": f"urn:crediscore#/components/schemas/{schema_name}"},
        registry=REGISTRY,
        format_checker=FormatChecker(),
    )
    errores = sorted(validator.iter_errors(instancia), key=lambda e: e.path)
    assert not errores, [f"{list(e.path)}: {e.message}" for e in errores]


def schema_de_respuesta(path: str, method: str, status: str) -> str:
    op = SPEC["paths"][path][method]["responses"][status]
    if "$ref" in op:
        op = SPEC["components"]["responses"][op["$ref"].split("/")[-1]]
    content = op["content"]
    schema = (content.get("application/json") or content.get("application/problem+json"))["schema"]
    return schema["$ref"].split("/")[-1]


@pytest.fixture(autouse=True)
def limpiar():
    main.APPLICATIONS.clear()
    main.DECISIONS.clear()
    main.IDEMPOTENCY.clear()


def crear(**cambios):
    body = {
        "rut": "12345678-5",
        "amount": 900_000,
        "term_months": 18,
        "identity_verification_id": str(uuid.uuid4()),
        "partner_reference": "ORD-77",
        **cambios,
    }
    return client.post("/v1/credit-applications", json=body, headers={"Idempotency-Key": str(uuid.uuid4())})


def test_post_credit_application_cumple_contrato():
    r = crear()
    assert r.status_code == 201
    validar(r.json(), schema_de_respuesta("/credit-applications", "post", "201"))


def test_get_credit_application_cumple_contrato():
    app_id = crear().json()["id"]
    r = client.get(f"/v1/credit-applications/{app_id}")
    validar(r.json(), schema_de_respuesta("/credit-applications/{applicationId}", "get", "200"))


@pytest.mark.parametrize("monto,plazo", [(100_000, 6), (2_500_000, 24), (5_000_000, 36)])
def test_decision_cumple_contrato(monto, plazo):
    app_id = crear(amount=monto, term_months=plazo).json()["id"]
    r = client.get(f"/v1/credit-applications/{app_id}/decision")
    validar(r.json(), schema_de_respuesta("/credit-applications/{applicationId}/decision", "get", "200"))


@pytest.mark.parametrize("monto,plazo", [(100_000, 6), (2_500_000, 24), (5_000_000, 36)])
def test_explicacion_cumple_contrato(monto, plazo):
    app_id = crear(amount=monto, term_months=plazo).json()["id"]
    r = client.get(f"/v1/credit-applications/{app_id}/explanation")
    validar(r.json(), schema_de_respuesta("/credit-applications/{applicationId}/explanation", "get", "200"))


def test_errores_son_problem_rfc7807():
    r404 = client.get(f"/v1/credit-applications/{uuid.uuid4()}/decision")
    assert r404.headers["content-type"].startswith("application/problem+json")
    validar(r404.json(), "Problem")
    r422 = crear(rut="malo")
    validar(r422.json(), "Problem")


def test_contrato_rechaza_atributos_protegidos():
    """Fairness por diseño: el contrato y la API no aceptan género ni comuna."""
    schema = SPEC["components"]["schemas"]["CreditApplicationInput"]
    assert schema["additionalProperties"] is False
    assert not {"gender", "genero", "comuna"} & set(schema["properties"])
    assert crear(gender="F").status_code == 422
    assert crear(comuna="La Pintana").status_code == 422


def test_limites_del_input_coinciden_con_el_contrato():
    s = SPEC["components"]["schemas"]["CreditApplicationInput"]["properties"]
    assert crear(amount=s["amount"]["minimum"] - 1).status_code == 422
    assert crear(amount=s["amount"]["maximum"] + 1).status_code == 422
    assert crear(term_months=s["term_months"]["maximum"] + 1).status_code == 422
    assert crear(amount=s["amount"]["maximum"], term_months=s["term_months"]["maximum"]).status_code == 201


def test_no_hay_endpoints_sin_documentar():
    documentados = {"/v1" + p for p in SPEC["paths"]}
    implementados = {
        r.path.replace("{application_id}", "{applicationId}")
        for r in main.app.routes
        if getattr(r, "path", None) and r.path not in OPERACIONALES
    }
    assert implementados <= documentados, implementados - documentados
