# ADR 0009 — Resiliencia: degradar con elegancia y decir dónde perdemos datos

- **Estado:** Aceptada
- **Fecha:** 2026-11-22
- **Equipo:** lospapus

## Contexto

La S18 pide SLOs, patrones de resiliencia aplicados, un plan de DR probado con game day y un runbook ejecutable. `scoring-api` tiene hoy dos tipos de dependencia:

- **Con respaldo:** el LLM del explicador (ADR 0008). Si falla, existe la plantilla.
- **Sin respaldo:** el propio estado de las solicitudes, que vive en memoria por réplica (ADR 0006 ya lo advertía).

El game day del 22-nov-2026 ([registro](../resiliencia/game-day.md)) mostró dos bugs en el primer diseño de resiliencia del explicador y midió la pérdida de datos.

## Decisión

1. **Dependencias con respaldo: timeout corto, sin reintentos, circuit breaker y fallback.**
   - Timeout de 3 s y `max_retries=0`. El reintento no aumenta la probabilidad de éxito cuando el proveedor está caído y duplica la espera, teniendo ya el respaldo (game day, run 2).
   - Circuit breaker: abre con 3 fallas seguidas, prueba después de 30 s y en semiabierto deja pasar **una sola** llamada (game day, run 1).
2. **Dependencias sin respaldo: reintento del lado del cliente, con idempotencia.** El contrato obliga a `Idempotency-Key`; los partners reintentan con la misma clave.
3. **SLOs que la arquitectura puede sostener:** 99,5 % de disponibilidad, no 99,9 % ([SLOs](../resiliencia/slos.md)).
4. **Estado en memoria aceptado para el MVP, de forma explícita y medida.** No agregamos parches intermedios (sesiones pegajosas, Redis como almacén principal): el arreglo es Aurora + outbox (ADR 0004) y entra primero en el roadmap.
5. **El game day se repite:** `gameday.yml` corre cada lunes en kind (pod kill y DR desde Git) y falla si no se cumplen los criterios.

## Alternativas descartadas

| Alternativa | Por qué no |
| :--- | :--- |
| **Reintentos con backoff hacia el LLM** (el default del SDK) | Medido: hasta 7 s de espera antes de caer a la plantilla, que estaba disponible desde el inicio. |
| **Librería de resiliencia (tenacity, pybreaker)** | El breaker propio tiene unas 40 líneas, está probado (incluido el caso de concurrencia que el game day encontró) y no suma dependencias a la imagen ni al SCA. Si aparecen más dependencias con breaker, se reevalúa. |
| **Service mesh (Istio/Linkerd) para retries y breakers** | No corre en Fargate (sin DaemonSets ni sidecars privilegiados fáciles) y es una pieza enorme para un servicio. Fuera de proporción. |
| **Sesiones pegajosas en el Service** para que el `GET` caiga en la réplica que guardó la solicitud | Esconde el problema: si esa réplica muere, se pierde igual. Y rompe el balanceo del HPA. |
| **Redis como almacén principal** | Agrega otra pieza con persistencia propia y su propio DR, para algo que Aurora resuelve con ACID (requisito de idempotencia). |
| **SLO de 99,9 %** | No lo podemos respaldar con 1 región y estado en memoria. Prometer un número que no se puede medir es peor que no tenerlo. |

## Consecuencias

- **Positivas:** con el LLM caído, 0 errores y p95 de 3,5 ms (E1); recuperación de un proceso en 1,25 s (E2); el breaker deja de golpear al proveedor caído (de 12 a 6 llamadas en 40 s).
- **Negativas:** **RPO total** mientras no exista Aurora (medido: 20 de 20 solicitudes perdidas en E2). Con 3 réplicas, una lectura puede caer en otra réplica y no encontrar la solicitud.
- **Riesgo técnico número 1 del producto.** Es la respuesta honesta a "¿dónde está el mayor riesgo técnico hoy?".
