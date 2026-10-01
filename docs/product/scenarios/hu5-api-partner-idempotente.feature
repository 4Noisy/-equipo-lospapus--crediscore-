Feature: HU5 — API Partner Idempotente
  Como partner
  Quiero enviar solicitudes mediante una API REST idempotente
  Para evitar solicitudes duplicadas

  Scenario: Registro de solicitud única vía API (Camino feliz)
    Given un partner autenticado con un token válido y un Idempotency-Key nuevo
    When envía una solicitud POST /v1/credit-applications
    Then el sistema responde con código 201 Created
    And retorna el identificador único de la solicitud generada

  Scenario: Envío repetido con la misma clave de idempotencia (Caso borde)
    Given una solicitud previamente procesada con un Idempotency-Key específico
    When el partner vuelve a enviar la misma petición por reintento de red
    Then el sistema responde con el resultado original sin crear un duplicado
    And retorna el mismo código 201 Created con el header Idempotent-Replayed: true

  Scenario: Misma clave de idempotencia con un cuerpo distinto (Caso borde)
    Given una solicitud previamente procesada con un Idempotency-Key específico
    When el partner envía un cuerpo distinto con esa misma clave
    Then el sistema rechaza la solicitud con código 409 Conflict
    And no crea ni modifica ninguna solicitud

  Scenario: Token de autenticación expirado o inválido (Caso de error)
    Given un partner enviando una solicitud con credenciales inválidas
    When se procesa la petición en el endpoint de la API
    Then el sistema rechaza la solicitud con código 401 Unauthorized
    And no se registra ninguna operación en la base de datos
