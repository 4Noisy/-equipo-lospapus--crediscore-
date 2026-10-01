Feature: HU2 — Scoring Automático
  Como analista de riesgo
  Quiero obtener un puntaje de riesgo automático
  Para evaluar rápidamente una solicitud

  Scenario: Evaluación de bajo riesgo aprobada de inmediato (Camino feliz)
    Given una solicitud completa con historial crediticio favorable
    When el motor de scoring calcula el puntaje
    Then se asigna una calificación de riesgo "Bajo" en menos de 60 segundos
    And la solicitud pasa a estado pre-aprobada

  Scenario: Solicitante sin historial crediticio previo (Caso borde)
    Given un solicitante sin antecedentes financieros registrados
    When el motor de scoring calcula el puntaje
    Then se asigna una categoría de "Riesgo Medio - Sin historial"
    And se solicita un comprobante de ingresos adicional

  Scenario: Motor de reglas o modelo fuera de línea (Caso de error)
    Given el motor de scoring ML no responde en más de 5 segundos
    When se solicita la evaluación crediticia
    Then la solicitud se envía a la cola de revisión manual del analista
    And se registra el evento en el log del sistema
