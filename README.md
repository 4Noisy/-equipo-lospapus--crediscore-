# CrediScore — Scoring Crediticio y Detección de Fraude

## Resumen Ejecutivo

**CrediScore** es una plataforma fintech diseñada para automatizar la evaluación de solicitudes de microcréditos en tiempo real mediante modelos de Machine Learning y motores de reglas antifraude. El sistema permite procesar decisiones crediticias seguras en menos de 60 segundos, operando bajo una arquitectura orientada a eventos (*event-driven*), alta concurrencia y estricto cumplimiento normativo de la CMF y principios de Finanzas Abiertas.

---

###  Objetivos Principales
* **Decisiones en Tiempo Real:** Automatizar el ciclo de evaluación de riesgo crediticio reduciendo los tiempos de respuesta a menos de 60 segundos ($p95$).
* **Prevención y Detección de Fraude:** Implementar una arquitectura reactiva capaz de propagar y evaluar eventos de sospecha en menos de 500 ms.
* **Equidad Algorítmica (*Fairness*):** Garantizar modelos de scoring crediticio libres de sesgos discriminatorios por género, ubicación geográfica o comuna.
* **Transparencia y Cumplimiento:** Asegurar trazabilidad completa e inmutable para auditorías regulatorias (CMF) y mecanismos de re-evaluación humana (Human-in-the-Loop).

---

###  Alcance del Producto (MVP)
1. **Onboarding Digital & KYC:** Registro y verificación automatizada de identidad del solicitante.
2. **Motor de Scoring Supervisado:** Pipeline de inferencia para evaluación de capacidad crediticia.
3. **Módulo Antifraude Híbrido:** Combinación de reglas de negocio en tiempo real y detección basada en anomalías.
4. **Backoffice para Analistas:** Panel administrativo para inspección de casos borde y re-evaluación manual.
5. **API Pública Versionada:** Integración segura, idempotente y documentada para partners comerciales.

---

###  Restricciones de Ingeniería Clave
| Dimensión | Requerimiento / Restricción |
| :--- | :--- |
| **Latencia de Decisión** | $< 60\text{ s}$ en percentil 95 ($p95$). |
| **Propagación de Eventos** | $< 500\text{ ms}$ para alertas y eventos de fraude. |
| **Idempotencia** | Garantía de no duplicación en solicitudes y transacciones reintentables. |
| **Auditoría** | Trazabilidad integral de decisiones para cumplimiento normativo CMF. |

---

###  Equipo de Trabajo
* **Benjamín Garrido** — *Tech Lead*
* **Abdiel Ortiz** — *AI / Data Engineer*
* **Nelson Arevalo** — *AI / Data Engineer*
* **Emilio Santibáñez** — *Product Owner*
* **Martin Jara** — *DevSecOps*
* **Justin Navarro** — *QA Engineer*

Reglas de trabajo, Definition of Done y política de IA: [CHARTER.md](CHARTER.md).

---

###  Documentación por sesión
| Sesión | Entregables |
| :--- | :--- |
| **S01** — Charter | [CHARTER.md](CHARTER.md) · [ADR 0001](docs/adr/0001-eleccion-iniciativa.md) |
| **S02** — Requisitos | [Backlog](docs/product/backlog.md) · [Impact map](docs/product/impact-map.md) · [Escenarios Gherkin](docs/product/scenarios/) |
| **S03** — Arquitectura y C4 | [C4 L1](docs/c4/l1-context.png) · [C4 L2](docs/c4/l2-container.png) · [ADR 0002](docs/adr/0002-estilo-arquitectonico.md) · [Atributos de calidad](docs/arch/atributos-calidad.md) · [Trazabilidad backlog → contenedor](docs/arch/trazabilidad-backlog-contenedor.md) |
| **S04** — Cloud y 12-Factor | [Checklist 12-Factor](docs/12-factor-checklist.md) · [ADR 0003](docs/adr/0003-cloud-style.md) · [Servicios gestionados](docs/arch/managed-services.md) |
| **S05** — APIs y OpenAPI | [Contrato OpenAPI 3.1](api/openapi.yaml) · [Reglas Spectral](.spectral.yaml) · [Ejemplos](api/examples/) · [Política de versionado](docs/api/versioning-policy.md) · [Cliente TypeScript](packages/api-client/) |
| **S06** — Datos y eventos | [DER](docs/data/der.png) · [Catálogo de eventos](docs/data/event-catalog.md) · [Bounded contexts](docs/data/bounded-contexts.md) · [ADR 0004](docs/adr/0004-datos-y-eventos.md) |

Los diagramas C4 se editan en draw.io (`docs/c4/*.xml`) y el DER en PlantUML (`docs/data/der.puml`).

---

###  Validar el contrato de la API
```bash
# Lint del contrato con las reglas del equipo
npx @stoplight/spectral-cli lint api/openapi.yaml

# Mock local para ejecutar los ejemplos de api/examples/
npx @stoplight/prism-cli mock api/openapi.yaml

# Regenerar el cliente TypeScript tras cambiar el contrato
npx openapi-typescript api/openapi.yaml -o packages/api-client/src/schema.d.ts
```
