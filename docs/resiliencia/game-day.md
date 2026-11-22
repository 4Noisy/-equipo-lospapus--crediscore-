# Game day · 22 de noviembre de 2026

Ejecutado por: Benjamín Garrido (Tech Lead), con asistencia de IA declarada según el [CHARTER](../../CHARTER.md) · dueño del proceso: DevSecOps
Script: [`scripts/gameday_local.py`](../../scripts/gameday_local.py) · datos crudos: [`evidencia/`](evidencia/)
Ambiente: API real (`src.main` con uvicorn) en una laptop Windows 11, Python 3.13, 12 CPU. La carga sale de [`scripts/loadgen.py`](../../scripts/loadgen.py).

La parte en Kubernetes (E3 y E4) está en el workflow [`gameday.yml`](../../.github/workflows/gameday.yml). Corre en kind dentro de GitHub Actions; sus resultados se agregan abajo cuando corre sobre `main`.

## Experimentos

| # | Experimento | Hipótesis | Resultado (run 3, final) | ¿Se cumplió? |
| :-: | :--- | :--- | :--- | :-: |
| E0 | Línea base: 8 workers, 30 s, con explicación | Disponibilidad 100 %, p95 < 300 ms | 13.670 solicitudes, **100 %**, p95 **8,2 ms**, p99 10,6 ms · CPU p95 **1,09 núcleos**, RSS máx. **70,6 MiB** | ✅ |
| E1 | Proveedor LLM caído: `EXPLAINER_MODE=llm` con el SDK apuntando a una IP que no responde | 0 errores, el breaker abre tras 3 fallas, la explicación sigue saliendo | 16.560 explicaciones, **0 errores**, **0 respuestas 5xx**, p95 **3,5 ms**. Solo **6** llamadas llegaron al proveedor caído; 16.554 se cortaron en el breaker | ✅ (tras 2 arreglos) |
| E2 | Caída del proceso (kill -9) a los 10 s y reinicio | Recupera en < 10 s | Reinicio en **1,25 s**, ventana de error 1,1 s, disponibilidad **99,977 %** (4 conexiones reseteadas). **20 de 20 solicitudes previas perdidas** | ✅ recuperación · ❌ datos |
| E3 | Matar 1 de 3 Pods bajo carga (kind) | Disponibilidad ≥ 99,5 %, 3/3 en < 60 s | Pendiente del primer run de `gameday.yml` en `main` | — |
| E4 | Borrar el namespace y restaurar desde Git (kind) | RTO < 5 min | Pendiente del primer run de `gameday.yml` en `main` | — |

## Qué salió distinto a la hipótesis (y lo arreglamos)

El game day se corrió tres veces. Los JSON de cada corrida están en `evidencia/`.

| Corrida | Qué vimos | Causa | Arreglo |
| :--- | :--- | :--- | :--- |
| [run 1](evidencia/gameday-local-run1.json) | CPU 0 y RAM 4 MiB; el "kill" no cortaba el servicio | **Del harness, no de la app:** en Windows el `python.exe` del venv es un lanzador; medíamos y matábamos al lanzador, no al servidor | `kill_tree()` y medición sobre el árbol de procesos |
| [run 1](evidencia/gameday-local-run1.json) | E1: **12** llamadas al proveedor caído en vez de 3, y 4 explicaciones con error | **Bug real:** el breaker semiabierto dejaba pasar todas las requests concurrentes, no una prueba | Semiabierto = una sola prueba (rama `feat/s18-defensa-final`, test `test_semiabierto_deja_pasar_una_sola_prueba`). [Post-mortem](post-mortem-2026-11-22-circuit-breaker.md) |
| [run 2](evidencia/gameday-local-run2.json) | E1: bajó a 9 llamadas, pero las 4 primeras explicaciones tardaron 4,4–7 s | **Bug real:** el timeout del SDK es por intento y había 1 reintento: 2 × timeout + backoff. Con el default de 8 s, el peor caso era ~17 s | Sin reintentos (ya hay respaldo) y timeout 3 s |
| [run 3](evidencia/gameday-local-run3.json) | Todo dentro de lo esperado, salvo la pérdida de datos | Estado en memoria (conocido, ADR 0006 y 0009) | No se arregla en el MVP: Aurora + outbox. Mitigación en el [plan de DR](dr-plan.md) |

## Lo que nos llevamos

1. **El fallback funciona, pero el primer diseño del breaker no.** Sin el game day habríamos defendido un circuit breaker con tests unitarios verdes y un bug de concurrencia en producción.
2. **El reintento automático del SDK era contraproducente** cuando ya existe una ruta de respaldo: duplicaba la espera del usuario sin aumentar la probabilidad de éxito.
3. **Un proceso de la API sostiene ~450 req/s con ~1 núcleo y 70 MiB.** Con eso dimensionamos `requests` y el techo del HPA ([FinOps, palanca 2](../finops/costos.md)).
4. **La pérdida de datos es real y medida.** Es la brecha número 1 del producto y la primera fila del roadmap.
