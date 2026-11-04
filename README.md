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
| **S07** — Contenedores, K8s e IaC | [Dockerfile](Dockerfile) · [Manifiestos K8s](k8s/) · [Terraform](terraform/main.tf) · [ADR 0006](docs/adr/0006-plataforma-k8s.md) |
| **S08** — CI/CD y GitOps | [Pipeline CI](.github/workflows/ci.yml) · [Repo GitOps](https://github.com/4Noisy/gitops-repo) · [ADR 0005](docs/adr/0005-gitops-strategy.md) · [Evidencia](docs/s08/evidencia.md) |
| **S09** — DevSecOps I | [Workflow de seguridad](.github/workflows/security.yml) · [Reglas Semgrep](.semgrep/) · [Threat model STRIDE](docs/threat-model.md) · [Secret scanning](docs/security/secret-scanning.md) · [Triage y excepciones](#seguridad-triage-y-excepciones-vex) |

Los diagramas C4 se editan en draw.io (`docs/c4/*.xml`) y el DER en PlantUML (`docs/data/der.puml`).

---

### Seguridad: triage y excepciones (VEX)
Cada PR corre `security.yml`: **sast** (Semgrep), **sca** (Trivy + SBOM CycloneDX) y **secrets** (gitleaks). Si un check falla, el PR no se mergea.

**1. Re-triar un hallazgo.** No se decide solo por CVSS. Se pregunta:
- ¿Es alcanzable? ¿Se llama a la función vulnerable o se llega desde la red pública?
- ¿Qué dato expone? En CrediScore, RUT, datos financieros y KYC son críticos.
- ¿Hay parche? Trivy ya ignora los CVE sin versión corregida (`ignore-unfixed`).

**2. Plazos de remediación (SLA).** Critical < 7 días · High < 30 días · Medium < 90 días.

**3. Pedir una excepción.** Siempre por PR, con la justificación escrita y las 2 aprobaciones de la rama protegida. Nada de excepciones silenciosas.

| Herramienta | Dónde se declara | Qué debe decir |
| :--- | :--- | :--- |
| Trivy (SCA) | `.trivyignore` en la raíz (Trivy lo lee solo) | CVE, por qué no aplica (estado VEX: `not_affected` + motivo), fecha de revisión |
| Semgrep (SAST) | Regla propia: PR que corrige la regla en `.semgrep/` y su test en `tests/semgrep/`. Regla pública: `# nosemgrep: <id>` en la línea | Por qué es falso positivo |
| gitleaks | `[[allowlists]]` en `.gitleaks.toml` | Por qué el valor no es un secreto. Si era real: **rotarlo primero** ([guía](docs/security/secret-scanning.md)) |
| Bandit | `# nosec <id>` en la línea | Motivo en el mismo comentario. Ej.: `src/main.py` escucha en `0.0.0.0` (`B104`) porque corre en un contenedor |

**4. VEX formal.** Si el cliente o un auditor pide la declaración en formato estándar, la excepción de Trivy se escribe como documento OpenVEX y se pasa a Trivy con `--vex`. El SBOM CycloneDX del run (artefacto `sbom-cyclonedx`) sirve para revisar si un CVE nuevo nos afecta, incluso en dependencias transitivas.

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
