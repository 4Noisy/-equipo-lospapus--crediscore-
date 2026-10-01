Feature: HU4 — Cumplimiento CMF
  Como analista de riesgo
  Quiero identificar solicitudes que requieren re-evaluación según la CMF
  Para mantener el cumplimiento normativo

  Scenario: Identificación automática de solicitud sujeta a re-evaluación (Camino feliz)
    Given una solicitud aprobada cuyo monto total de deuda supera el umbral fijado por la CMF
    When se ejecuta el control normativo diario
    Then la solicitud se marca con la etiqueta "Re-evaluación CMF"
    And aparece en el panel de cumplimiento del analista de riesgo

  Scenario: Solicitud en el límite exacto del ratio de endeudamiento (Caso borde)
    Given un cliente con una carga financiera exactamente igual al límite normativo
    When se evalúa el cumplimiento normativo
    Then el sistema asigna una alerta preventiva de riesgo de sobreendeudamiento
    And requiere confirmación manual del analista

  Scenario: Reglas normativas desactualizadas o no disponibles (Caso de error)
    Given el módulo de parámetros normativos no puede cargar las tasas de referencia
    When se valida la cartera de créditos
    Then se genera una alerta crítica de auditoría
    And se bloquea la emisión final hasta restaurar los parámetros
