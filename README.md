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
* **Emilio Santibáñez** — *Product Owner*
* **Martin Jara** — *DevSecOps*
* **Justin Navarro** — *QA Engineer*
