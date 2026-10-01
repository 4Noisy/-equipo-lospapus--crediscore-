Feature: HU1 — Onboarding KYC
  Como solicitante
  Quiero validar mi identidad digitalmente
  Para solicitar un microcrédito sin acudir a una sucursal

  Scenario: Validación biométrica exitosa (Camino feliz)
    Given un solicitante con documento de identidad chileno vigente
    When envía su fotografía y cédula para validación
    Then la identidad se confirma en menos de 10 segundos
    And el solicitante avanza a la etapa de solicitud de crédito

  Scenario: Documento de identidad vencido o ilegible (Caso borde)
    Given un solicitante con cédula de identidad no legible
    When sube la imagen del documento
    Then el sistema solicita capturar nuevamente la fotografía
    And no se valida la identidad

  Scenario: Servicio de verificación caído (Caso de error)
    Given el servicio del Registro Civil / proveedor KYC no está disponible
    When el solicitante intenta validar su identidad
    Then se muestra un mensaje de reintento posterior
    And el estado de la solicitud queda como "Pendiente de verificación"
