# Post-mortem · Circuit breaker semiabierto dejaba pasar ráfagas al LLM caído

**Fecha:** 22-nov-2026 · **Severidad:** SEV3 (detectado en game day, sin impacto en usuarios) · **Formato:** sin culpables
**Redactó:** Benjamín Garrido (Tech Lead), con asistencia de IA · **Revisión pendiente:** AI/Data y DevSecOps

## Resumen

En el game day E1 (proveedor LLM caído) el circuit breaker del explicador dejó pasar 12 llamadas al proveedor en 40 s, cuando el diseño esperaba unas 3–5. Además, las primeras explicaciones tardaron hasta 7 s y el generador de carga registró 4 timeouts. Ningún usuario se vio afectado: el modo LLM no está activo en ningún ambiente y siempre se respondió con la plantilla.

## Línea de tiempo (hora de Chile)

| Hora | Evento |
| :--- | :--- |
| 17:30 | Primera corrida del game day. E1 reporta `llm_calls_error = 12` y `explain_err = 4` |
| 17:31 | Se descarta el harness como causa: E0 y E2 tienen problemas propios (proceso lanzador), pero E1 cuenta desde las métricas de la API, no desde el proceso |
| 17:33 | Causa 1 identificada al leer `CircuitBreaker.allow()`: en semiabierto devuelve `True` a todos |
| 17:34 | Test de regresión escrito (falla) → arreglo → test verde. Segunda corrida: 9 llamadas, siguen 4 explicaciones lentas |
| 17:35 | Causa 2: medición directa de una explicación con el proveedor caído → 6,97 s, 4,41 s, 4,42 s, 0,0 s |
| 17:36 | Arreglo: `max_retries=0`, timeout 3 s. Tercera corrida: 6 llamadas, 0 errores, p95 3,5 ms |

## Causa raíz

1. **Semiabierto sin exclusión.** `allow()` devolvía `state != "open"`. Al cumplirse el `reset_s`, el estado pasa a semiabierto y **todas** las requests concurrentes (4 workers) lo ven igual, así que salían 4 llamadas de prueba en vez de 1. Los tests unitarios eran secuenciales y no podían verlo.
2. **Reintento sobre una dependencia con respaldo.** El cliente del SDK tenía `max_retries=1` y el `timeout` aplica por intento. Peor caso = 2 × timeout + backoff. Con el default de 8 s, una explicación podía tardar ~17 s antes de caer a la plantilla, que estaba disponible desde el primer milisegundo.

**Por qué no lo vimos antes:** probamos cada pieza por separado (breaker, timeout, fallback) y nunca la combinación bajo concurrencia contra una dependencia que no responde. Eso es justamente lo que cubre un game day.

## Qué funcionó

- La API respondió 200 en el 100 % de los casos: el fallback a plantilla aisló la falla.
- Las métricas `crediscore_llm_calls_total{result}` hicieron visible el problema en segundos.

## Acciones

| # | Acción | Dueño | Estado |
| :-: | :--- | :--- | :-: |
| 1 | Semiabierto con una sola prueba (`_probing`) + test de regresión | AI/Data | ✅ rama `feat/s18-defensa-final` |
| 2 | `max_retries=0` y timeout 3 s en el explicador | AI/Data | ✅ rama `feat/s18-defensa-final` |
| 3 | Agregar E1 al workflow semanal `gameday.yml` cuando el modo LLM se active en staging | DevSecOps | pendiente |
| 4 | Regla: toda dependencia con respaldo va sin reintentos automáticos (anotada en ADR 0009) | Tech Lead | ✅ propuesta en ADR 0009 |
| 5 | Test de concurrencia del breaker con hilos reales | QA | pendiente |

---

# Post-mortem · Webhook de Kyverno rechazaba la policy en el pipeline

**Fecha:** 12-nov-2026 · **Severidad:** SEV4 (CI rojo en un PR, sin impacto en producción)
**Redactado** el 22-nov-2026 a partir del run fallido y del arreglo de Justin Navarro (QA) · **Revisión pendiente:** DevSecOps

## Resumen

El job `admission (kyverno)` del workflow `supply-chain` falló en el PR [#29](https://github.com/4Noisy/-equipo-lospapus--crediscore-/pull/29) ([run 43345185443](https://github.com/4Noisy/-equipo-lospapus--crediscore-/actions/runs/43345185443)) al aplicar `require-signature.yaml`:

```
failed calling webhook "mutate-policy.kyverno.svc": ... dial tcp 10.96.76.252:443: connect: connection refused
```

## Causa raíz

`kubectl wait deploy --for=condition=Available` dice que el Deployment de Kyverno está disponible, pero eso no garantiza que su webhook ya acepte conexiones: el Service tarda unos segundos más en tener endpoints listos. Aplicábamos la policy en esa ventana.

## Arreglo

Commit [`0d79962`](https://github.com/4Noisy/-equipo-lospapus--crediscore-/commit/0d79962): reintentar el `apply` hasta 24 veces cada 5 s y después esperar `clusterpolicy ... condition=Ready`. Los runs siguientes del mismo PR pasaron ([43345410028](https://github.com/4Noisy/-equipo-lospapus--crediscore-/actions/runs/43345410028)).

## Lección

"Disponible" no es "listo para recibir tráfico". Lo aplicamos de nuevo en `gameday.yml`: esperamos `availableReplicas` y además corremos el smoke antes de dar por recuperado el servicio.
