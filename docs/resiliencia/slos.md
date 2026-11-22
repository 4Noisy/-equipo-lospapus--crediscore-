# SLOs de scoring-api

Equipo lospapus · S18 · dueño: Martin Jara (DevSecOps) · revisión: mensual

Los SLIs salen de `/metrics` ([`src/metrics.py`](../../src/metrics.py)), que Prometheus raspa en cada Pod. Las reglas de grabación y las alertas están en [`observability/prometheus-rules.yaml`](../../observability/prometheus-rules.yaml).

## Objetivos

| # | SLO | SLI (PromQL resumido) | Objetivo | Ventana | Presupuesto de error | Medido (game day local, run 3) |
| :-: | :--- | :--- | :-: | :-: | :--- | :-: |
| 1 | **Disponibilidad de originación** | `POST /v1/credit-applications` sin 5xx / total | **99,5 %** | 30 días | 3 h 36 min al mes | 100 % (E0, 13.670 req) · 99,977 % con caída del proceso (E2) |
| 2 | **Latencia de aceptación** | p95 de `crediscore_http_request_duration_seconds{route="/v1/credit-applications"}` | **< 300 ms** | 30 días | 5 % de requests sobre 300 ms | p95 8,2 ms · p99 10,6 ms |
| 3 | **Decisión a tiempo** (charter) | solicitud → decisión disponible | **p95 < 60 s** | 30 días | — | Hoy es síncrona: igual al SLO 2. Se medirá extremo a extremo cuando la decisión pase por Kafka (ADR 0004) |
| 4 | **Explicación siempre disponible** | `GET .../explanation` con 200 en < 3,5 s / total | **99 %** | 30 días | 1 % | 100 % con el LLM caído (E1): p95 3,5 ms, 0 errores |
| 5 | **Calidad de la explicación** | `guardrail_violations_total{rule=~"pii\|protected_attribute"}` | **0** | siempre | ninguno: cada una es un incidente | 0 (eval y game day) |

**SLO que no podemos medir todavía:** la propagación de eventos de fraude < 500 ms (README) requiere el Event Bus, que no está implementado. Queda declarado y sin medición: no lo reportamos como cumplido.

## Por qué estos números

- **99,5 % y no 99,9 %:** con 3 réplicas en una sola región y estado en memoria (ADR 0009), 99,9 % (43 min/mes) sería una promesa que no podemos respaldar. 99,5 % es lo que la arquitectura actual sostiene con margen. Pasar a 99,9 % exige Aurora Multi-AZ y el outbox.
- **300 ms de aceptación:** el `POST` responde `received` y la decisión es asíncrona por diseño (contrato). El usuario ve la aceptación; 300 ms deja holgura sobre los ~8 ms medidos para el viaje por API Gateway, ALB y TLS.
- **3,5 s para la explicación:** el timeout del LLM es 3 s sin reintentos (hallazgo del game day E1). Peor caso = 3 s + la plantilla.

## Política de presupuesto de error

| Presupuesto consumido | Acción |
| :--- | :--- |
| < 50 % | Se despliega normal. |
| 50–100 % | Solo cambios con rollback probado; el Tech Lead aprueba cada PR a prod. |
| > 100 % | Congelamiento de features: el siguiente sprint es de confiabilidad, con post-mortem obligatorio. |

## Alertas (burn rate, multiventana)

| Alerta | Condición | Severidad | A quién |
| :--- | :--- | :--- | :--- |
| `OriginacionBurnRateRapido` | consumo del presupuesto 14,4× en 1 h **y** en 5 min | page | on-call (rotación semanal, ver [runbook](runbook.md)) |
| `OriginacionBurnRateLento` | 6× en 6 h **y** en 30 min | ticket | DevSecOps |
| `LatenciaAceptacionAlta` | p95 > 300 ms por 10 min | ticket | Tech Lead |
| `ExplicadorCircuitoAbierto` | `crediscore_circuit_state == 2` por 5 min | ticket | AI/Data |
| `GuardrailDatoSensible` | aumento de `pii` o `protected_attribute` | page | AI/Data + DPO |
