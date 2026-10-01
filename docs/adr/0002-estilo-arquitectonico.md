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

## Alternativas descartadas
> Enmienda del 2026-10-01: se agrega esta sección, exigida por la estructura mínima de ADR del taller. La decisión no cambia.

* **Monolito modular:** es la opción natural para un equipo de 6 personas y un MVP (deploy único, transacciones ACID). Se descarta porque acopla el escalado del camino de fraude (< 500 ms) con la inferencia de ML, que tienen perfiles de carga y cadencias de release distintos. Queda como plan de repliegue: ver [ADR 0003](0003-cloud-style.md).
* **Serverless puro (FaaS):** se descarta porque los *cold starts* y la carga del modelo en cada arranque son incompatibles con la propagación de fraude en < 500 ms.

El costo operacional de esta decisión se acota en el [ADR 0003](0003-cloud-style.md) (4 servicios sobre servicios gestionados) y la semántica de entrega e idempotencia se precisa en el [ADR 0004](0004-datos-y-eventos.md).
