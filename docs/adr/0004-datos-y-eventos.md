# ADR 0004: Persistencia, broker de eventos y patrones de datos

**Fecha:** 2026-10-01  
**Estado:** Aceptado  
**Relacionado con:** [ADR 0002](0002-estilo-arquitectonico.md), [ADR 0003](0003-cloud-style.md), [bounded contexts](../data/bounded-contexts.md), [catálogo de eventos](../data/event-catalog.md), [DER](../data/der.png)

## Contexto
Hay cuatro bounded contexts que se comunican por eventos. Falta decidir dónde guarda cada uno su estado, qué broker transporta los eventos y qué patrones se aplican. Tres requisitos mandan:

* **Idempotencia:** una solicitud reintentada no puede duplicarse, ni en la API ni al consumir eventos.
* **Auditoría CMF:** cada decisión debe poder reconstruirse y no puede alterarse.
* **Latencia:** una alerta de fraude llega a los contextos afectados en < 500 ms.

El ADR 0002 atribuyó la idempotencia a "colas transaccionales". Eso es impreciso y aquí se corrige: la entrega *exactly-once* de Kafka solo cubre casos acotados, así que el diseño asume *at-least-once*.

## Decisión

### Persistencia por contexto
| Contexto | Motor | Motivo |
| :--- | :--- | :--- |
| Identidad | PostgreSQL (schema `identity`) | Datos relacionales con integridad referencial. |
| Originación y Scoring | PostgreSQL (schema `origination`) | La solicitud, la clave de idempotencia y el evento de salida se confirman en una sola transacción ACID. |
| Fraude | Redis | Contadores por dispositivo con ventana de tiempo (TTL) y listas negras leídas en milisegundos. No guarda estado duradero: sus resultados son eventos. |
| Cumplimiento y Auditoría | PostgreSQL (schema `compliance`, solo `INSERT`) + S3 con Object Lock | Consultas del backoffice sobre PostgreSQL; el archivo en S3 no se puede borrar ni sobrescribir durante la retención. |

Una sola instancia de RDS con un schema y un usuario por servicio. Sigue la regla del taller: empezar con PostgreSQL y agregar un motor especializado solo cuando se mida que no alcanza.

### Broker
**Apache Kafka en Amazon MSK Serverless.** Un tópico por contexto productor, particionado por `aggregate_id`.

### Semántica de entrega e idempotencia
* Entrega **at-least-once**.
* **En la API:** restricción única `(partner_id, key)` en la tabla `idempotency_key`, insertada en la misma transacción que la solicitud. Guarda la respuesta 24 h. Misma clave con otro cuerpo (`request_hash` distinto) responde `409`.
* **En los consumidores:** cada servicio registra los `event_id` procesados y descarta los repetidos.

### Patrones
| Patrón | ¿Se aplica? | Criterio |
| :--- | :-: | :--- |
| **Outbox** | Sí | Guardar la solicitud y publicar su evento no es atómico. El evento se inserta en `outbox_event` dentro de la misma transacción y un proceso `outbox-relay` lo publica. Aplica a los tres servicios con PostgreSQL. |
| **Saga (coreografía)** | Sí | La decisión cruza tres contextos sin transacción distribuida. Cada paso reacciona al evento anterior; las compensaciones son `credit-application.blocked` ante una alerta y `review-requested` ante un tiempo de espera de 5 s. |
| **CQRS** | No | Lecturas y escrituras del MVP caben en PostgreSQL. Se revisa si el backoffice necesita búsquedas que degraden las escrituras. |
| **Event Sourcing** | No | La auditoría se cubre con el log de solo inserción, la retención de Kafka y el archivo en S3. No se necesita reconstruir el estado desde eventos. |
| **CDC (Debezium)** | No | El relay de outbox logra lo mismo sin exponer el schema físico ni operar otro componente. |

Fraud Detection no usa outbox porque no tiene base de datos: consume, evalúa, publica el resultado y recién entonces confirma el offset. Un reintento puede publicar dos veces el mismo resultado, y los consumidores lo deduplican por `event_id`, que se deriva del evento de entrada.

## Consecuencias

### Positivas
* Una solicitud y su evento se confirman juntos o no se confirman: no hay solicitudes "mudas" ni eventos huérfanos.
* Los reintentos son seguros en los dos extremos (API y consumidores).
* El *replay* de Kafka permite recalcular puntajes con un modelo nuevo o reconstruir el log de auditoría.
* El archivo de auditoría resiste incluso a un administrador con permisos.

### Negativas
* El relay de outbox agrega latencia a la publicación. Presupuesto para los 500 ms de fraude: sondeo del relay ≤ 100 ms, broker ≤ 50 ms, consumo ≤ 100 ms. **Es un objetivo de diseño, sin medir**; se verifica con pruebas de carga en S12 y S15.
* Consistencia eventual: el partner puede ver `received` durante unos segundos.
* La deduplicación obliga a cada consumidor a mantener una tabla de `event_id` procesados y a purgarla.
* Una instancia de RDS compartida es un punto único de falla. Se mitiga con Multi-AZ; separar instancias es una decisión posterior.

## Alternativas descartadas
* **SNS + SQS:** menos operación y entrega con baja latencia. Se descarta porque no tiene *replay* ni orden por clave, que son los que sirven a la auditoría y a la saga.
* **RabbitMQ:** bueno para colas de tareas, pero es autogestionado y sin log reproducible.
* **Kafka transaccional (*exactly-once*):** no elimina la necesidad de idempotencia en la API ni en los efectos fuera de Kafka, y agrega costo. Se prefiere at-least-once con consumidores idempotentes.
* **Clave de idempotencia en Redis:** más rápida, pero dejaría una ventana en la que la solicitud se guarda y la clave no. La restricción única en PostgreSQL es correcta en ese borde.
* **Una base de datos por servicio (instancias separadas):** aislamiento total, a cuatro veces el costo y la operación. El schema por servicio da el mismo aislamiento lógico.
* **Base de grafos (Neptune) para fraude:** útil para redes de fraude con varios saltos. Las reglas del MVP (IP, dispositivo, velocidad) no lo requieren.
* **DynamoDB o MongoDB para solicitudes:** se pierde la transacción que une solicitud, clave de idempotencia y outbox.
