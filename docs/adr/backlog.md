# Product Backlog — CrediScore

## Matriz de Priorización MoSCoW

| ID | Nombre | Prioridad | Estimación (SP) |
| **HU1** | Onboarding KYC | **Must Have** | 5 |
| **HU2** | Scoring | **Must Have** | 8 |
| **HU3** | Antifraude | **Must Have** | 8 |
| **HU4** | Cumplimiento CMF | **Should Have** | 5 |
| **HU5** | API | **Should Have** | 5 |

---

## Detalle de Historias de Usuario (INVEST)

### HU1 — Onboarding KYC
* **Historia:** Como solicitante, quiero validar mi identidad digitalmente para solicitar un microcrédito sin acudir a una sucursal.
* **Prioridad:** Must Have
* **Checklist INVEST:**
  * **I**ndependiente: No requiere que el motor de scoring esté activo para capturar y validar la identidad.
  * **N**egociable: Los métodos de validación de identidad y biometría pueden refinarse durante el sprint.
  * **V**aliosa: Permite a los usuarios enrolarse remotamente evitando suplantaciones de identidad.
  * **E**stimable: Alcance delimitado al flujo de captura y verificación de credenciales.
  * **S**mall: Puede completarse dentro de una iteración.
  * **T**esteable: Comprobable mediante pruebas automatizadas con documentos válidos, inválidos y casos de suplantación.

---

### HU2 — Scoring
* **Historia:** Como analista de riesgo, quiero obtener un puntaje de riesgo automático para evaluar rápidamente una solicitud.
* **Prioridad:** Must Have
* **Checklist INVEST:**
  * **I**ndependiente: Se ejecuta a partir de los datos consolidados de la solicitud de crédito.
  * **N**egociable: Los pesos de las variables y los umbrales de decisión del modelo son parametrizables.
  * **V**aliosa: Automatiza la decisión crediticia reduciendo los tiempos de respuesta a menos de 60 segundos.
  * **E**stimable: Requiere desarrollo e inferencia del modelo supervisado.
  * **S**mall: Enfocada estrictamente en el procesamiento y entrega del puntaje de riesgo.
  * **T**esteable: Evaluada con conjuntos de datos de prueba, matrices de confusión y métricas de equidad (*fairness*).

---

### HU3 — Antifraude
* **Historia:** Como oficial de fraude, quiero recibir alertas de operaciones sospechosas para bloquear fraudes en tiempo real.
* **Prioridad:** Must Have
* **Checklist INVEST:**
  * **I**ndependiente: Se suscribe a los eventos del sistema de forma asíncrona.
  * **N**egociable: Las reglas de detección y umbrales de alerta pueden incrementarse de forma modular.
  * **V**aliosa: Protege los fondos al frenar transacciones anómalas en menos de 500 ms.
  * **E**stimable: Medible en base al motor de reglas y consumidor de eventos.
  * **S**mall: Acotada a la evaluación de telemetría y emisión de alertas de riesgo.
  * **T**esteable: Comprobable con inyección de eventos sospechosos y pruebas de estrés de latencia.

---

### HU4 — Cumplimiento CMF
* **Historia:** Como analista de riesgo, quiero identificar solicitudes que requieren re-evaluación según la CMF para mantener el cumplimiento normativo.
* **Prioridad:** Should Have
* **Checklist INVEST:**
  * **I**ndependiente: Lee el estado de las solicitudes evaluadas sin bloquear el flujo principal.
  * **N**egociable: La interfaz del backoffice y los campos del reporte de auditoría admiten ajustes.
  * **V**aliosa: Garantiza trazabilidad legal ante reguladores y permite la intervención humana (*Human-in-the-Loop*).
  * **E**stimable: Alcance centrado en la vista de re-evaluación y logs inmutables.
  * **S**mall: Limitada a la persistencia del log de auditoría y la consola administrativa.
  * **T**esteable: Validable mediante pruebas de integridad sobre el registro de auditoría y cambios de estado manuales.

---

### HU5 — API
* **Historia:** Como partner, quiero enviar solicitudes mediante una API REST idempotente para evitar solicitudes duplicadas.
* **Prioridad:** Should Have
* **Checklist INVEST:**
  * **I**ndependiente: Capa de entrada que se integra desacoplada de la lógica de negocio interna.
  * **N**egociable: La convención del header de idempotencia y el contrato OpenAPI pueden consensuarse.
  * **V**aliosa: Permite a terceros integrar el sistema de forma segura ante reintentos de red.
  * **E**stimable: Definida por la especificación de la API y el middleware de idempotencia.
  * **S**mall: Se limita al endpoint receptor y a la validación de claves únicas.
  * **T**esteable: Verificable enviando múltiples peticiones idénticas concurrentes y analizando las respuestas.
