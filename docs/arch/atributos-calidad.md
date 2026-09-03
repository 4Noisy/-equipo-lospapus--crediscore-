# Top 3 Atributos de Calidad (NFRs) Priorizados

1. **Rendimiento (Latencia y Event-driven):** El sistema debe garantizar una latencia extrema, emitiendo decisiones de crédito en menos de 60 segundos (p95) y propagando eventos de fraude en menos de 500 ms.

2. **Confiabilidad (Idempotencia):** El sistema debe garantizar que los pagos y solicitudes sean reintentables sin generar duplicidad en las transacciones o evaluaciones.

3. **Trazabilidad y Cumplimiento (Compliance):** Toda decisión (scoring y fraude) debe registrarse de manera inmutable para permitir auditorías de la CMF y asegurar que el modelo cumpla con la restricción de *fairness* (no discriminación por género o comuna).
