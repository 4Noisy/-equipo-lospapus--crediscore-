# Preparación del Q&A · las 15 preguntas del panel

Regla: **responder con un dato y un link**, y separar "lo que hicimos" de "lo que no alcanzamos". Quien responde primero es el rol indicado; cualquiera debe poder responder.

## Perfil técnico (Tech Lead / Arquitecto)

**1. ¿Por qué event-driven vs sincrónico?** — *Benjamín*
Porque hay dos tiempos distintos en el mismo flujo: fraude < 500 ms y decisión < 60 s p95. Uno síncrono haría esperar al partner por el más lento y acoplaría la disponibilidad de los dos servicios. El `POST` responde `received` y la decisión llega por consulta o webhook ([ADR 0002](../adr/0002-estilo-arquitectonico.md), contrato). **Lo que no hicimos:** en el MVP la decisión se calcula en el mismo request porque Kafka no está implementado; está escrito en `src/main.py`.

**2. ¿Qué alternativas descartaron en el ADR 0004?** — *Benjamín / Abdiel*
Abrir el [ADR 0004](../adr/0004-datos-y-eventos.md) en su sección de alternativas y leer el criterio comparativo, no la lista. Si preguntan por otro ADR: 9 de los 10 tienen su sección (el 0005 la tiene explícita desde la S18; el 0001, elección de iniciativa, no registró las opciones que se descartaron, y lo decimos).

**3. ¿Cómo evolucionaría esto a 100× tráfico?** — *Benjamín*
Con datos: un proceso sostiene ~456 req/s con ~1 núcleo (game day E0). 100× el volumen supuesto (30.000/mes → 3 M/mes) es ~1 req/s promedio y ~50 req/s de pico: cabe en el techo actual del HPA (8 pods). Lo que **no** escala hoy es el estado en memoria: a cualquier escala hay que pasar a Aurora (roadmap 1). Después, el cuello sería Aurora (escritura): outbox + réplicas de lectura (CQRS con OpenSearch, ya en el ADR 0004). El costo crecería poco: el 70 % es MSK, un costo fijo.

**4. Muéstrame un test que falle si borro esta función.** — *Justin*
Cualquier función del flujo crítico tiene uno. Ejemplos listos para mostrar en vivo:
- Borrar la rama `if saved_hash != body_hash` → falla `test_idempotencia_misma_key_otro_cuerpo_da_409`.
- Borrar `check_output` o una regla → fallan `test_guardrail_detecta_cada_violacion[*]` y la suite red team del CI.
- Borrar `self._probing` del breaker → falla `test_semiabierto_deja_pasar_una_sola_prueba`.
- Agregar un endpoint sin documentarlo → falla `test_no_hay_endpoints_sin_documentar` (contract test).
Hacerlo en vivo: `pytest -q -k idempotencia` antes y después de comentar la línea.

**5. ¿Dónde está el mayor riesgo técnico hoy?** — *Benjamín*
El estado en memoria. Medido: tras una caída del proceso se perdieron 20 de 20 solicitudes (game day E2), y con 3 réplicas una lectura puede no encontrar la solicitud. Mitigación hoy: reintento idempotente del partner. Arreglo: Aurora + outbox, fila 1 del roadmap ([ADR 0009](../adr/0009-resiliencia-degradacion.md)).

## Perfil de negocio (Product / Sostenedor)

**6. ¿Cómo miden que este producto ayuda al usuario?** — *Emilio*
Tabla de métricas del [roadmap](roadmap.md#cómo-medimos-que-el-producto-ayuda-al-usuario). La más importante: % de rechazos que piden revisión humana. Si la explicación funciona, la persona entiende y pide menos revisiones; si el modelo se equivoca, sube. **Hoy no tenemos datos de usuarios reales.**

**7. ¿Cuál es el costo por usuario / tenant / triage?** — *Martin*
USD 0,082 por solicitud evaluada (infra 0,081 + LLM 0,0017), con 30.000 solicitudes/mes y precios de lista ×1,5 por región ([costos](../finops/costos.md)). Es modelado, no facturado.

**8. ¿Qué feature entrega más valor por unidad de esfuerzo?** — *Emilio*
La explicación con derecho a revisión: ~390 líneas de código y ~280 de tests, convierte códigos internos en algo que la persona entiende y cumple una obligación legal (art. 8 bis) que entra en vigencia en diciembre de 2026.

**9. Si tuvieran 2 semanas más, ¿qué construirían?** — *Emilio*
Aurora en `scoring-api` (sin outbox todavía) y el golden set con el LLM real. Lo primero cierra el riesgo número 1; lo segundo valida la feature IA ([roadmap](roadmap.md)).

**10. ¿Cuál es el break-even estimado del producto?** — *Emilio / Martin*
Con el supuesto de USD 10 de contribución por crédito aprobado y 69 % de aprobación: la infra se paga con ~250 créditos/mes (~360 solicitudes); con un equipo de 6 (USD 12.000/mes, supuesto), con ~1.450 créditos/mes (~2.100 solicitudes), el 7 % del volumen supuesto. **Los dos supuestos de negocio los tiene que validar el PO con los partners** ([costos](../finops/costos.md#presupuesto-conectado-al-producto)).

## Perfil de seguridad (Security / DPO)

**11. ¿Cómo aplica la Ley 21.719 a este producto?** — *Abdiel / Emilio*
Tres puntos ([model card §6](../ia/model-card.md#6-marco-legal-citado)):
1. **Art. 8 bis, decisiones automatizadas:** cada explicación informa el derecho a revisión humana, y la re-evaluación por analista está en el contrato (HU4).
2. **Minimización:** el LLM no recibe datos personales; el RUT no sale del servicio.
3. **Encargado de tratamiento:** si se activa el LLM en prod, el proveedor necesita contrato. Por eso el default es `template`.
Vigencia: prevista para el 1-dic-2026; hay un proyecto en el Congreso para postergarla al 15-oct-2027. Diseñamos para la fecha vigente.

**12. Muéstrame un secret. ¿Dónde vive y quién lo rota?** — *Martin*
Abrir el [runbook R6](../resiliencia/runbook.md#r6--rotar-un-secreto): `GITOPS_TOKEN` en GitHub secrets (DevSecOps, 90 días); `ANTHROPIC_API_KEY` en Secrets Manager → ExternalSecret (AI/Data, 90 días); `DATABASE_URL` con rotación automática de RDS. La firma no tiene llave (keyless). Mostrar `k8s/secret.yaml`: solo un placeholder, y gitleaks en el CI.

**13. ¿Qué hace tu sistema frente a un prompt injection?** — *Abdiel*
Demo, paso 7. Tres capas: el texto libre nunca llega al prompt (por diseño), se detecta y marca (14/14 en el set de ataques, 0 falsos positivos en 12 normales), y si el LLM produjera algo distinto de la decisión, el guardrail de salida lo bloquea y sale la plantilla ([model card §3](../ia/model-card.md#3-guardrails)). **Límite:** el detector es por patrones; un ataque nuevo puede no marcarse, pero igual no tiene efecto porque no llega al modelo.

**14. ¿Cómo demuestran fairness a un regulador?** — *Nelson*
Cuatro capas ([model card §5](../ia/model-card.md#5-fairness-cómo-lo-demostramos-a-un-regulador)): por diseño (el contrato rechaza género y comuna, test automático), por resultado (regla 4/5: 0,989 género, 0,959 zona), por explicación (guardrail de atributos protegidos) y por trazabilidad (versión de modelo y prompt en cada respuesta). **Brecha:** la medición por resultado es con datos sintéticos.

**15. Enséñame el último post-mortem del equipo.** — *Justin*
[Post-mortem del 22-nov-2026](../resiliencia/post-mortem-2026-11-22-circuit-breaker.md): el game day encontró que el circuit breaker semiabierto dejaba pasar ráfagas y que el reintento del SDK duplicaba la espera. Causa raíz, línea de tiempo, arreglo con test de regresión y acciones pendientes con dueño. Hay uno anterior en el mismo archivo (webhook de Kyverno, 12-nov).

## Preguntas probables fuera de la lista

| Pregunta | Respuesta corta |
| :--- | :--- |
| ¿Por qué Claude y no otro modelo? | Es intercambiable (`EXPLAINER_MODEL`); el valor está en los guardrails y la evaluación, que no dependen del proveedor. Usamos el SDK oficial con fallbacks del servidor ante rechazos. |
| ¿Por qué EKS si ECS es más barato? | ADR 0006: portabilidad y el ecosistema de HPA/GitOps. El plano de control es el 9 % del costo; MSK es el 70 %. |
| ¿Por qué 99,5 % y no 99,9 %? | Porque no lo podemos respaldar con estado en memoria y una región ([SLOs](../resiliencia/slos.md)). |
| ¿El 100 % del red team no es sospechoso? | Sí, y lo decimos: lo escribimos nosotros. Por eso el red team externo está en el roadmap. |
| ¿Qué pasa si el LLM alucina una tasa de interés? | El prompt solo tiene 5 campos, y el guardrail de promesas y el de coherencia bloquean lo que no está en la decisión. Un número que no sea el puntaje sí puede pasar: brecha conocida, candidata al próximo guardrail. |
