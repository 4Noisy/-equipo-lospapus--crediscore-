# ADR 0002: Elección de Estilo Arquitectónico para CrediScore

**Fecha:** 2026-09-02  
**Estado:** Aceptado  

## Contexto
CrediScore es una plataforma fintech que combina onboarding, scoring con ML y detección de fraude en tiempo real. Las restricciones de ingeniería exigen latencia extrema (< 60s p95 para crédito, < 500ms para propagación de fraude) e idempotencia estricta. Discutimos dos estilos candidatos: Monolito Modular vs. Arquitectura de Microservicios Orientada a Eventos (EDA).

## Decisión
Hemos elegido una **Arquitectura de Microservicios Orientada a Eventos (EDA)**.

## Justificación
* La separación en microservicios permite escalar independientemente el motor de fraude (reglas en tiempo real) del motor de scoring (ML supervisado).
* El uso de un *Message Broker* (ej. Apache Kafka) facilita el cumplimiento de la restricción *event-driven* de propagar alertas de fraude en menos de 500 ms a todos los dominios afectados.
* Garantiza mejor las propiedades de idempotencia mediante colas de mensajes transaccionales.

## Consecuencias

### Positivas
* Alta escalabilidad.
* Desacoplamiento de componentes de ML.
* Cumplimiento de los NFRs de latencia.

### Negativas
* Mayor complejidad operativa.
* Necesidad de manejar consistencia eventual.
* Monitoreo distribuido.
