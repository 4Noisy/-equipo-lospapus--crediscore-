# Impact Map — CrediScore

## Goal (Objetivos)
**CrediScore:** Reducir el tiempo de evaluación y aprobación de microcréditos de **3 días a < 60 s**, con detección de fraude en tiempo real (**< 500 ms**) y equidad algorítmica bajo norma CMF.

---

## Actors
* Solicitante
* Analista de riesgo
* Oficial de fraude
* Partner API
* Compliance

---

## Impacts
* El solicitante obtiene respuesta inmediata sin acudir a sucursales.
* El analista deja de evaluar casos obvios y audita solo anomalías.
* El oficial de fraude bloquea ataques al instante.
* Partners integran créditos en sus plataformas.
* Compliance audita cada decisión sin pedir extracciones manuales de datos.

---

## Deliverables
* Módulo de Onboarding Digital KYC.
* Motor de Scoring supervisado (ML).
* Motor reactivo antifraude.
* Backoffice de re-evaluación CMF.
* API pública REST con idempotencia.

---

## Trazabilidad Goal → Historia

| Métrica del goal | Actor | Impacto esperado | Entregable | Historia |
| :--- | :--- | :--- | :--- | :--- |
| Tiempo de respuesta (< 60 s) | Solicitante | Respuesta inmediata sin acudir a sucursales. | Módulo de Onboarding Digital KYC. | **HU1** — valida la identidad digitalmente y elimina los tiempos muertos presenciales. |
| Tiempo de respuesta (< 60 s) | Analista de riesgo | Deja de evaluar casos obvios; solo audita anomalías. | Motor de Scoring supervisado (ML). | **HU2** — automatiza la decisión estándar dentro del SLA de 60 s. |
| Detección de fraude (< 500 ms) | Oficial de fraude | Bloquea ataques al instante. | Motor reactivo antifraude. | **HU3** — analiza cada solicitud en tiempo real y bloquea antes de la aprobación. |
| Cumplimiento y equidad (CMF) | Analista de riesgo, Compliance | Identifica anomalías, previene el sobreendeudamiento y audita decisiones. | Backoffice de re-evaluación CMF. | **HU4** — aplica las reglas normativas y deja las solicitudes límite en revisión humana. |
| Escalabilidad del objetivo | Partner API | Integra el crédito rápido en su propia plataforma. | API pública REST con idempotencia. | **HU5** — expone el motor a terceros sin duplicar solicitudes. |

La trazabilidad de cada historia hacia los contenedores del C4 L2 está en [trazabilidad-backlog-contenedor.md](../arch/trazabilidad-backlog-contenedor.md).

---
