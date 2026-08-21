# Team Charter — Equipo CrediScore

## Propósito y Misión
Desarrollar una solución fintech robusta, escalable y segura para la evaluación automatizada de microcréditos y detección de fraude en tiempo real, garantizando alta disponibilidad, estricto cumplimiento normativo (CMF / Finanzas Abiertas) y principios de equidad (fairness) algorítmica.

## Integrantes y Roles
* **Benjamín Garrido — Tech Lead:** Responsable de la arquitectura técnica general, estándares de código, resolución de bloqueos técnicos y revisión de Pull Requests clave.
* **Abdiel Ortiz — AI / Data Engineer:** Responsable del diseño, entrenamiento, evaluación y despliegue del motor de scoring crediticio y modelos de detección de fraude, asegurando métricas de *fairness*.
* **Nelson Arevalo — AI / Data Engineer:** Responsable del diseño, entrenamiento, evaluación y despliegue del motor de scoring crediticio y modelos de detección de fraude, asegurando métricas de *fairness*.
* **Emilio Santibáñez — Product Owner (PO):** Responsable de la priorización del backlog, refinamiento de historias de usuario, cumplimiento del alcance MVP y alineación con los requerimientos de negocio/CMF.
* **Martin Jara — DevSecOps:** Responsable del pipeline CI/CD, infraestructura como código, seguridad en el ciclo de vida del desarrollo y monitoreo de latencia/disponibilidad.
* **Justin Navarro — QA Engineer:** Responsable de la estrategia de pruebas automatizadas (unitarias, integración, idempotencia, carga y auditoría de datos) y control de calidad general.

## Valores y Reglas de Trabajo
* **Comunicación continua:** Canal oficial en Slack `#equipo-crediscore` para dudas y avisos diarios; decisiones críticas deben quedar documentadas en issues o ADRs.
* **Cadencia de reuniones:** Standup semanal (15 min) al inicio de cada iteración y revisión previa a cada entrega/deadline de sesión.
* **Responsabilidad y entrega:** Todo cambio debe pasar por PR con al menos una aprobación antes de mergear a la rama principal.

## Política de Uso de Inteligencia Artificial (IA)
* **Permitido y fomentado:** Asistencia en generación de boilerplate, documentación, optimización de algoritmos, refactorización y creación de casos de prueba unitarios.
* **Restricción y control:** Todo código o configuración generada por IA debe ser completamente comprendido, validado y probado por el autor del PR antes de ser subido. Queda prohibido el copiado directo sin análisis de seguridad o cumplimiento de requisitos.

## Definition of Done (DoD) Preliminar
Una tarea o historia de usuario se considera terminada si:
1. El código cumple con los requerimientos funcionales y pasa los linters definidos.
2. Posee pruebas unitarias y de integración pasando con éxito en el pipeline de CI.
3. No introduce vulnerabilidades de seguridad conocidas.
4. Ha sido revisada y aprobada mediante Pull Request por al menos un par (incluyendo Tech Lead o QA según corresponda).
5. La documentación técnica o Swagger/OpenAPI asociada se encuentra actualizada.
