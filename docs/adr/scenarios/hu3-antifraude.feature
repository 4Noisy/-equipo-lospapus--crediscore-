Feature: HU3 — Antifraude
  Como oficial de fraude
  Quiero recibir alertas de operaciones sospechosas
  Para bloquear fraudes en tiempo real

  Scenario: Detección y bloqueo en tiempo real de anomalía (Camino feliz)
    Given una solicitud ingresada desde una IP fuera del país con datos de un tercero
    When el motor antifraude analiza la transacción
    Then se bloquea la solicitud de inmediato
    And se envía una alerta prioritaria al oficial de fraude

  Scenario: Intentos repetidos desde el mismo dispositivo (Caso borde)
    Given un dispositivo que ha generado 3 solicitudes distintas en menos de 1 hora
    When se envía la cuarta solicitud
    Then se suspende la cuenta temporalmente
    And se exige validación biométrica reforzada

  Scenario: Falla de conexión con lista de fraude (Caso de error)
    Given la base de datos de listas negras está inaccesible
    When ingresa una nueva solicitud
    Then la transacción queda en estado "En pausa por seguridad"
    And se notifica al oficial de fraude para revisión manual
