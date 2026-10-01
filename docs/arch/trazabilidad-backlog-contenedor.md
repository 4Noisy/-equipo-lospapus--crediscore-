# Trazabilidad backlog → contenedor

Cada historia del [backlog](../product/backlog.md) se mapea al atributo de calidad que la condiciona ([atributos-calidad.md](atributos-calidad.md)) y a los contenedores del [C4 L2](../c4/l2-container.png) que la implementan.

| Historia | Atributo que la condiciona | Contenedores | Sistemas externos | Por qué ahí |
| :--- | :--- | :--- | :--- | :--- |
| **HU1** — Onboarding KYC | Rendimiento: identidad confirmada en < 10 s. | Web App, Mobile App, API Gateway, Onboarding Microservice, Core relations DB (Aurora), Redis, Event Bus. | Proveedor de identidad (KYC). | La identidad es un contexto propio: guarda datos personales y depende de un tercero que puede caer sin detener el resto. |
| **HU2** — Scoring | Rendimiento: decisión en < 60 s p95. Fairness: sin género ni comuna como variables. | Scoring Engine Microservice, Core relations DB (Aurora), Proyección de lectura (OpenSearch), Event Bus. | Bureau de crédito. | El motor de scoring escala de forma independiente del motor de fraude (ADR 0002). |
| **HU3** — Antifraude | Rendimiento: alerta propagada en < 500 ms. | Fraud Detection Microservice, Base de grafos, Redis, Event Bus, Backoffice Web. | — | El camino de fraude se aísla para que la carga de scoring no lo degrade. |
| **HU4** — Cumplimiento CMF | Trazabilidad: registro inmutable de cada decisión. | Compliance Microservice, Backoffice Web, Proyección de lectura (OpenSearch), Archivo de auditoría (S3), Event Bus. | Servicios CMF. | Consume todos los eventos de dominio y los archiva; la re-evaluación humana vive junto al registro de auditoría. |
| **HU5** — API partner idempotente | Confiabilidad: reintentos sin duplicados. | API Gateway, Scoring Engine Microservice, Core relations DB (Aurora). | Partner comercial. | El gateway autentica y limita por partner; la clave de idempotencia se guarda en la misma transacción que la solicitud. |

## Cobertura inversa

| Contenedor | Historias |
| :--- | :--- |
| Web App / Mobile App | HU1, HU2 |
| Backoffice Web | HU3, HU4 |
| API Gateway | HU1, HU2, HU4, HU5 |
| Onboarding Microservice | HU1 |
| Scoring Engine Microservice | HU2, HU5 |
| Fraud Detection Microservice | HU3 |
| Compliance Microservice | HU4 |
| Core relations DB (Aurora PostgreSQL) | HU1, HU2, HU5 |
| Redis | HU1, HU3 |
| Base de grafos (Neo4j / Neptune) | HU3 |
| Proyección de lectura (OpenSearch) | HU2, HU4 |
| Archivo de auditoría (S3) | HU4 |
| Event Bus (MSK) | HU1, HU2, HU3, HU4 |

Ningún contenedor queda sin historia y ninguna historia queda sin contenedor.
