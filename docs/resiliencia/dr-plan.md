# Plan de recuperación ante desastres (DR)

Equipo lospapus · S18 · dueño: Martin Jara · probado en el game day del 22-nov-2026 ([game-day.md](game-day.md))

## Objetivos por componente

| Componente | Estado hoy | RTO objetivo | RPO objetivo | Estrategia | ¿Probado? |
| :--- | :--- | :-: | :-: | :--- | :-: |
| `scoring-api` (cómputo) | Implementado | 15 min | — (stateless cuando haya Aurora) | Redespliegue desde Git (GitOps): Argo CD reconcilia el overlay | ✅ E4 en kind ([workflow](../../.github/workflows/gameday.yml)) · ✅ E2 local: 1,25 s |
| Estado de solicitudes | **En memoria por réplica** | — | **Hoy: pérdida total** | Ninguna hoy. Ver brecha abajo | ✅ E2: 20/20 solicitudes perdidas tras la caída |
| Aurora PostgreSQL | Diseñado (ADR 0004) | 30 min | 5 min | Multi-AZ + backups automáticos con PITR (35 días) + snapshot diario copiado a us-east-1 | ❌ no existe aún |
| Auditoría (S3) | Diseñado | 4 h | 0 | S3 Object Lock (cumplimiento CMF, 5 años) + replicación entre regiones | ❌ |
| Imágenes | Implementado (GHCR) | 15 min | 0 | Imagen inmutable por SHA y firmada; reconstruible desde el commit | ✅ cada CI |
| Configuración y manifiestos | Implementado | 15 min | 0 | Todo en Git (app + gitops-repo); secretos en Secrets Manager | ✅ E4 |
| Región AWS completa (sa-east-1) | Diseñado | 4 h | 15 min | Recrear con Terraform en us-east-1 + restaurar snapshot copiado | ❌ |

## Escenarios y respuesta

| # | Escenario | Detección | Respuesta | Procedimiento |
| :-: | :--- | :--- | :--- | :--- |
| D1 | Cae un Pod | Probes + alerta de burn rate | Automática: el Deployment lo repone, el PDB mantiene 2 | [Runbook R1](runbook.md#r1) |
| D2 | Despliegue malo | Burn rate tras un promote | `git revert` en gitops-repo | [Runbook R1](runbook.md#r1) |
| D3 | Proveedor LLM caído | `ExplicadorCircuitoAbierto` | Automática: plantilla + circuit breaker | [Runbook R3](runbook.md#r3) |
| D4 | Namespace o clúster perdido | Argo CD Missing / smoke rojo | Sync desde Git | [Runbook R5](runbook.md#r5) |
| D5 | Base de datos corrupta (futuro) | Alertas de Aurora | PITR a 5 min antes del evento | por escribir cuando exista Aurora |
| D6 | Región caída (futuro) | Health checks de Route 53 | Terraform en región secundaria | por escribir |

## La brecha principal, dicha sin adornos

Mientras el estado viva en memoria (ADR 0009):

- Si un Pod muere, las solicitudes que guardaba **se pierden** (medido: 100 %).
- Con 3 réplicas, un reintento idempotente o un `GET` puede caer en otra réplica y no encontrar la solicitud (ya advertido en el ADR 0006; el smoke en kind lo deja registrado).

**Mitigación hoy:** el contrato obliga a los partners a reintentar con la misma `Idempotency-Key`, y el runbook R5 incluye avisarles. **Arreglo:** Aurora + outbox (ADR 0004). Es el trabajo de mayor valor si tuviéramos 2 semanas más (ver [roadmap](../defensa/roadmap.md)).

## Cómo se prueba

- `python scripts/gameday_local.py` (2 min, sin clúster): E0 línea base, E1 LLM caído, E2 caída del proceso.
- Workflow [`gameday`](../../.github/workflows/gameday.yml) en kind, manual y cada lunes: E3 matar un Pod bajo carga y E4 borrar el namespace y restaurar desde Git. Falla si disponibilidad < 99,5 %, réplicas > 60 s o RTO > 5 min.
- Cada game day deja un registro en [game-day.md](game-day.md) y, si algo salió distinto a la hipótesis, un post-mortem.
