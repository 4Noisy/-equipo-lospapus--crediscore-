# Trazabilidad backlog → contenedor

Cada historia del [backlog](../product/backlog.md) se mapea al atributo de calidad que la condiciona ([atributos-calidad.md](atributos-calidad.md)) y a los contenedores del [C4 L2](../c4/l2-container.png) que la implementan.

| Historia | Atributo que la condiciona | Contenedores | Sistemas externos | Por qué ahí |
| :--- | :--- | :--- | :--- | :--- |
| **HU1** — Onboarding KYC | Rendimiento: identidad confirmada en < 10 s. | Web App, Mobile App, API Gateway, Onboarding Service, PostgreSQL (schema `identity`), Event Bus. | Proveedor de identidad (KYC). | La identidad es un contexto propio: guarda datos personales y depende de un tercero que puede caer sin detener el resto. |
| **HU2** — Scoring | Rendimiento: decisión en < 60 s p95. Fairness: sin género ni comuna como variables. | Scoring Service, PostgreSQL (schema `origination`), Object Storage (modelo versionado), Event Bus. | Bureau de crédito. | La inferencia de ML escala y se libera con una cadencia distinta al resto (reentrenamientos). |
| **HU3** — Antifraude | Rendimiento: alerta propagada en < 500 ms. | Fraud Detection Service, Redis, Event Bus, Backoffice Web (vía Compliance & Audit Service). | — | El camino de fraude es asíncrono y se aísla para que la carga de scoring no lo degrade. |
| **HU4** — Cumplimiento CMF | Trazabilidad: registro inmutable de cada decisión. | Compliance & Audit Service, Backoffice Web, PostgreSQL (schema `compliance`), Object Storage (Object Lock), Event Bus. | Servicios CMF. | Consume todos los eventos de dominio y los archiva; la re-evaluación humana vive junto al log de auditoría. |
| **HU5** — API partner idempotente | Confiabilidad: reintentos sin duplicados. | API Gateway, Scoring Service, PostgreSQL (tabla `idempotency_key`). | Partner comercial. | El gateway autentica y limita por partner; la clave de idempotencia se guarda en la misma transacción que la solicitud. |

## Cobertura inversa

| Contenedor | Historias |
| :--- | :--- |
| Web App / Mobile App | HU1, HU2 |
| Backoffice Web | HU3, HU4 |
| API Gateway | HU1, HU2, HU4, HU5 |
| Onboarding Service | HU1 |
| Scoring Service | HU2, HU5 |
| Fraud Detection Service | HU3 |
| Compliance & Audit Service | HU3, HU4 |
| PostgreSQL | HU1, HU2, HU4, HU5 |
| Redis | HU3 |
| Object Storage | HU2, HU4 |
| Event Bus | HU1, HU2, HU3, HU4 |

Ningún contenedor queda sin historia y ninguna historia queda sin contenedor.
