# ADR 0004: Persistencia, broker de eventos y patrones de datos

**Fecha:** 2026-10-01  
**Estado:** Aceptado  
**Relacionado con:** [ADR 0002](0002-estilo-arquitectonico.md), [ADR 0003](0003-cloud-style.md), [bounded contexts](../data/bounded-contexts.md), [catálogo de eventos](../data/event-catalog.md), [DER](../data/der.png)

## Contexto
Con los bounded contexts explícitos, falta decidir el motor de persistencia de cada uno, el broker de eventos y qué patrones de datos aplicar.

## Decisión

### Motor por contexto
| Contexto | Motores | Motivo |
| :--- | :--- | :--- |
| **Onboarding / Identidad** | Aurora PostgreSQL + Redis | El dominio requiere integridad referencial y joins. Redis guarda la sesión y el OTP. |
| **Scoring / Riesgo** | Aurora PostgreSQL (escritura) + OpenSearch (lectura) | Separa la escritura transaccional de las consultas complejas del dashboard de analistas. |
| **Antifraude** | Neo4j / Amazon Neptune + Redis | Necesita un motor de grafos: un modelo relacional no es apto para analizar redes de riesgo. Redis lleva los contadores de velocidad. |
| **Cumplimiento / Auditoría** | OpenSearch + S3 | Requiere búsqueda y un archivo inmutable para una trazabilidad real ante la CMF. |

### Broker
**Amazon MSK Serverless** (Kafka gestionado), entrega *at-least-once* y consumidores idempotentes por `event_id`. Gestiona el flujo de crédito que atraviesa los 4 contextos vía eventos.

### Patrones
| Patrón | ¿Se aplica? | Dónde y por qué |
| :--- | :-: | :--- |
| **Outbox** | Sí | Onboarding y Scoring publican a Kafka desde la misma transacción: evita perder eventos si el broker cae justo después del commit. |
| **CQRS** | Sí | Scoring separa físicamente la escritura (Aurora) de la lectura (OpenSearch) para el dashboard de analistas. |
| **Saga por coreografía** | Sí | El flujo de crédito cruza los 4 contextos sin 2PC, con compensaciones como `credit_decision.revoked`. |
| **Event Sourcing** | Solo en Cumplimiento | Es el único contexto que exige el historial completo; en los demás, la complejidad del *replay* no se justifica. |

## Consecuencias

### Positivas
* **Motor:** cada contexto usa el motor que calza con su patrón de acceso real.
* **Trazabilidad:** Compliance obtiene una auditoría inmutable real para la CMF.

### Negativas
* **Operación:** 5 motores que mantener; consistencia eventual entre Aurora y OpenSearch.
* **Debugging:** la saga por coreografía exige tracing distribuido con `trace_id`.

## Alternativas descartadas
* **Un único PostgreSQL para todo:** Antifraude necesita grafo y Cumplimiento necesita búsqueda.
* **Saga orquestada (Temporal):** un motor más que operar sin SRE 24/7.
* **Event Sourcing en todos los contextos:** *replay* y curva de aprendizaje injustificados.
* **MongoDB para Scoring:** el core de crédito necesita integridad referencial y joins.
