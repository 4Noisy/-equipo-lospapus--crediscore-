# Catálogo de eventos de dominio — CrediScore

Los 15 eventos del ciclo de vida de una solicitud de crédito, más 1 de compensación de la saga. Las decisiones de broker, entrega y patrones están en el [ADR 0004](../adr/0004-datos-y-eventos.md).

## Formato

* **Nombre:** `recurso.acción` en pasado.
* **Sobre:** todo evento lleva `event_id`, versión y `trace_id`.
* **Entrega at-least-once:** los consumidores son idempotentes por `event_id`.

## Sobre común

Todos los eventos comparten este sobre; la tabla de cada evento describe solo `data`.

```json
{
  "event_id": "3d6f0a52-8c1b-4f7e-a2d9-0e1f2a3b4c5d",
  "event_type": "credit_application.submitted",
  "event_version": "1.0",
  "occurred_at": "2026-10-01T14:22:31Z",
  "aggregate_id": "7f3b6c1e-2a4d-4e8b-9c0f-1d2e3f4a5b6c",
  "trace_id": "c8f2b1a09d3e4f5a",
  "data": {
    "application_id": "7f3b6c1e-2a4d-4e8b-9c0f-1d2e3f4a5b6c",
    "applicant_id": "5a1c9e7d-3b2f-4d6a-8c0e-9f8a7b6c5d4e",
    "requested_amount": 250000,
    "term_months": 12,
    "channel": "partner_api",
    "submitted_at": "2026-10-01T14:22:31Z"
  }
}
```

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `event_id` | uuid | Identificador único; clave de deduplicación del consumidor. |
| `event_type` | string | Nombre del evento. |
| `event_version` | string | Versión del schema de `data`. |
| `occurred_at` | date-time (UTC) | Momento en que ocurrió el hecho. |
| `aggregate_id` | uuid | Agregado al que pertenece; clave de partición en Kafka. |
| `trace_id` | string | Traza que une la petición HTTP, los logs y los eventos. |
| `data` | object | Carga específica del evento. |

## Mapa de eventos

| # | Evento | Versión | Productor | Consumidores |
| :-: | :--- | :-: | :--- | :--- |
| 1 | `applicant.registered` | 1.0 | Onboarding | Scoring, Cumplimiento |
| 2 | `applicant.kyc_verified` | 1.0 | Onboarding | Scoring, Antifraude, Cumplimiento |
| 3 | `credit_application.submitted` | 1.0 | Scoring | Antifraude, Cumplimiento |
| 4 | `financial_profile.captured` | 1.0 | Onboarding | Scoring |
| 5 | `scoring.requested` | 1.0 | Scoring | Scoring (interno), Cumplimiento |
| 6 | `scoring.completed` | 1.0 | Scoring | Antifraude, Cumplimiento, Dashboard |
| 7 | `fraud_check.requested` | 1.0 | Scoring | Antifraude |
| 8 | `fraud_check.completed` | 1.0 | Antifraude | Scoring, Cumplimiento, Dashboard |
| 9 | `fraud_alert.raised` | 1.0 | Antifraude | Antifraude (backoffice), Cumplimiento |
| 10 | `manual_review.requested` | 1.0 | Scoring | Scoring (backoffice), Cumplimiento |
| 11 | `manual_review.completed` | 1.0 | Scoring | Scoring (interno), Cumplimiento |
| 12 | `credit_decision.approved` | 1.0 | Scoring | Onboarding, Cumplimiento, Partner, Dashboard |
| 13 | `credit_decision.rejected` | 1.0 | Scoring | Onboarding, Cumplimiento, Dashboard |
| 14 | `credit_decision.revoked` | 1.0 | Scoring | Onboarding, Cumplimiento, Partner, Dashboard |
| 15 | `audit_record.logged` | 1.0 | Cumplimiento | Dashboard (solo lectura) |
| 16 | `partner.notified` | 1.0 | Scoring | Partner comercial (externo) |

Productor y consumidores se nombran por [bounded context](bounded-contexts.md), no por contenedor.

`credit_decision.revoked` es el evento de compensación de la saga por coreografía ([ADR 0004](../adr/0004-datos-y-eventos.md)): revierte un `credit_decision.approved`. Los otros 15 son el ciclo de vida de la solicitud.

## Schema de `data` por evento

Los campos se derivan del [DER](der.png) del contexto Scoring & Riesgo.

| # | Evento | Campos de `data` |
| :-: | :--- | :--- |
| 1 | `applicant.registered` | `applicant_id` uuid · `channel` string · `registered_at` date-time |
| 2 | `applicant.kyc_verified` | `applicant_id` uuid · `verification_id` uuid · `kyc_status` string (`verified`) · `verified_at` date-time |
| 3 | `credit_application.submitted` | `application_id` uuid · `applicant_id` uuid · `requested_amount` integer · `term_months` integer · `channel` string · `submitted_at` date-time |
| 4 | `financial_profile.captured` | `profile_id` uuid · `application_id` uuid · `monthly_income` integer · `existing_debt` integer · `employment_type` string |
| 5 | `scoring.requested` | `application_id` uuid · `model_version` string |
| 6 | `scoring.completed` | `scoring_id` uuid · `application_id` uuid · `score` integer (0–1000) · `risk_category` string · `model_version` string · `computed_at` date-time |
| 7 | `fraud_check.requested` | `application_id` uuid · `applicant_id` uuid · `ip_country` string · `device_id` string |
| 8 | `fraud_check.completed` | `fraud_case_id` uuid · `application_id` uuid · `result` string (`clear`, `suspicious`) · `fraud_risk_index` number |
| 9 | `fraud_alert.raised` | `fraud_case_id` uuid · `application_id` uuid · `severity` string · `rule_codes` string[] |
| 10 | `manual_review.requested` | `decision_id` uuid · `application_id` uuid · `reason` string |
| 11 | `manual_review.completed` | `review_id` uuid · `decision_id` uuid · `analyst_id` uuid · `outcome` string · `notes` string |
| 12 | `credit_decision.approved` | `decision_id` uuid · `application_id` uuid · `decided_by` string (`model`, `analyst`) · `decided_at` date-time |
| 13 | `credit_decision.rejected` | `decision_id` uuid · `application_id` uuid · `decided_by` string · `reasons` string[] · `decided_at` date-time |
| 14 | `credit_decision.revoked` | `decision_id` uuid · `application_id` uuid · `reason` string · `revoked_at` date-time |
| 15 | `audit_record.logged` | `audit_record_id` uuid · `source_event_id` uuid · `application_id` uuid · `logged_at` date-time |
| 16 | `partner.notified` | `application_id` uuid · `decision` string · `notified_at` date-time |

`partner.notified` es el aviso que el partner recibe por el webhook `creditApplicationDecided` de [`api/openapi.yaml`](../../api/openapi.yaml).
