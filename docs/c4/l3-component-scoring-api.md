# C4 Nivel 3 — Componentes de `scoring-api`

Completa los niveles 1 ([contexto](l1-context.png)) y 2 ([contenedores](l2-container.png)). Muestra lo que existe en el código hoy (`src/`) y marca con línea punteada lo diseñado que todavía no está implementado.

```mermaid
flowchart TB
    partner["Partner / App del solicitante<br/><i>[Persona / Sistema externo]</i>"]
    analista["Analista de riesgo<br/><i>[Persona]</i>"]
    prom["Prometheus<br/><i>[Observabilidad]</i>"]
    llm["Claude API (Anthropic)<br/><i>[Sistema externo, opcional]</i>"]
    aurora[("Aurora PostgreSQL<br/><i>[Diseñado · ADR 0004]</i>")]
    kafka[["MSK / Kafka<br/><i>[Diseñado · ADR 0004]</i>"]]

    subgraph api["scoring-api · contenedor Python 3.13 / FastAPI (distroless, nonroot)"]
        direction TB
        mw["Middleware HTTP<br/><i>trace_id, headers de seguridad, métricas</i><br/>src/main.py"]
        routes["Controladores REST<br/><i>/v1/credit-applications, /decision, /explanation</i><br/>src/main.py"]
        idem["Guardia de idempotencia<br/><i>hash del cuerpo por Idempotency-Key → 409 / replay</i><br/>src/main.py"]
        val["Validación de contrato<br/><i>Pydantic extra=forbid: sin atributos protegidos</i><br/>src/main.py"]
        scoring["Motor de scoring<br/><i>decide(): puntaje 0–1000, motivo, versión</i><br/>src/main.py"]
        store["Repositorio en memoria<br/><i>APPLICATIONS, DECISIONS, IDEMPOTENCY</i><br/>src/main.py"]
        subgraph ia["Feature IA · src/explainer.py"]
            direction TB
            inguard["Guardrail de entrada<br/><i>detect_injection()</i>"]
            payload["Minimizador de datos<br/><i>build_prompt_payload(): sin RUT ni texto libre</i>"]
            cache["Caché LRU por contenido<br/><i>palanca FinOps 1</i>"]
            cb["Circuit breaker<br/><i>3 fallas → abierto 30 s → 1 prueba</i>"]
            client["Cliente LLM<br/><i>SDK anthropic, timeout 3 s, sin reintentos</i>"]
            outguard["Guardrails de salida<br/><i>check_output(): 8 reglas</i>"]
            tpl["Plantilla determinística<br/><i>modo por defecto y respaldo</i>"]
        end
        metrics["Métricas Prometheus<br/><i>/metrics · src/metrics.py</i>"]
    end

    partner -- "HTTPS JSON (OAuth2 en el gateway)" --> mw
    mw --> routes
    routes --> val --> idem --> store
    routes --> scoring --> store
    routes -- "GET /explanation" --> inguard --> payload --> cache
    cache -- "miss" --> cb --> client -- "HTTPS, solo en modo llm" --> llm
    client --> outguard
    outguard -- "falla" --> tpl
    cb -- "abierto" --> tpl
    mw --> metrics
    prom -- "scrape" --> metrics
    analista -. "re-evaluación (HU4, diseñado)" .-> routes
    store -. "reemplazo: outbox + ACID" .-> aurora
    scoring -. "credit_decision.* vía outbox" .-> kafka
```

## Componentes y decisiones que los justifican

| Componente | Responsabilidad | ADR | Test que falla si se rompe |
| :--- | :--- | :--- | :--- |
| Guardia de idempotencia | Mismo cuerpo + misma clave → misma respuesta; otro cuerpo → 409 | [0004](../adr/0004-datos-y-eventos.md) | `test_idempotencia_misma_key_otro_cuerpo_da_409` |
| Validación de contrato | Rechaza campos fuera del contrato (género, comuna) | [0002](../adr/0002-estilo-arquitectonico.md) | `test_contrato_rechaza_atributos_protegidos` |
| Motor de scoring | Regla fija hoy; modelo supervisado en el diseño | [0004](../adr/0004-datos-y-eventos.md) | `test_reglas_de_scoring` |
| Repositorio en memoria | Placeholder de Aurora: **riesgo técnico número 1** | [0009](../adr/0009-resiliencia-degradacion.md) | game day E2 (pérdida medida) |
| Minimizador de datos | El LLM no ve datos personales | [0008](../adr/0008-feature-ia-explicador.md) | `test_el_prompt_nunca_lleva_rut_ni_texto_libre` |
| Guardrails de salida | Coherencia, PII, atributos protegidos, promesas, fuga | [0008](../adr/0008-feature-ia-explicador.md) | `test_guardrail_detecta_cada_violacion` (8 casos) + red team |
| Circuit breaker | No golpear a un proveedor caído | [0009](../adr/0009-resiliencia-degradacion.md) | `test_semiabierto_deja_pasar_una_sola_prueba` |
| Caché | No pagar dos veces el mismo texto | [0010](../adr/0010-finops.md) | `test_cache_evita_segunda_llamada_y_cuenta_costo` |
| Métricas | SLIs de los SLOs | [0009](../adr/0009-resiliencia-degradacion.md) | `test_metrics_expone_contadores` |

**Por qué todo vive en un solo proceso:** el servicio tiene un solo bounded context (scoring) y un equipo chico. Separar el explicador en otro microservicio sumaría red, un contrato y un despliegue más, sin una necesidad de escalado distinta. Si el explicador llegara a usar GPU o a escalar distinto, se separa: el componente ya tiene una interfaz pequeña (`Explainer.explain(decision, application)`).
