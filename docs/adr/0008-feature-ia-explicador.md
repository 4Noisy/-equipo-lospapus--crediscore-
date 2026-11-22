# ADR 0008 — Feature IA: el LLM explica la decisión, no la toma

- **Estado:** Aceptada
- **Fecha:** 2026-11-22
- **Equipo:** lospapus

## Contexto

La S18 pide una feature de IA evaluada, con guardrails y model card. CrediScore ya decide con un motor de scoring (hoy una regla fija; después un modelo supervisado, ADR 0004). Dos restricciones mandan:

1. **CMF y auditoría:** cada decisión tiene que ser reproducible y explicable a un regulador.
2. **Ley 21.719, art. 8 bis:** la persona tiene derecho a no quedar sujeta a una decisión solo automatizada y a recibir una explicación y revisión humana.

Hoy la API devuelve códigos como `AMOUNT_TOO_HIGH_FOR_TERM`, que nadie fuera del equipo entiende.

## Decisión

1. **Nuevo endpoint** `GET /v1/credit-applications/{id}/explanation` (contrato 1.1.0, cambio compatible) que devuelve un párrafo en español, el origen del texto, el resultado de los guardrails y la base legal de la revisión humana.
2. **El LLM solo redacta.** Recibe cinco campos estructurados (resultado, puntaje, motivos, monto, plazo). No recibe RUT, IDs ni texto libre. No puede cambiar la decisión.
3. **Plantilla determinística como modo por defecto y como respaldo.** `EXPLAINER_MODE=template` es el default en todos los ambientes. El modo `llm` se activa por ambiente cuando la evaluación con el modelo real pase el umbral (golden set ≥ 95 %).
4. **Guardrails de salida obligatorios** (coherencia con la decisión, puntaje, PII, atributos protegidos, promesas, fuga de prompt, derecho a revisión, largo). Si uno falla, se sirve la plantilla.
5. **Modelo:** `claude-opus-5-5` con `effort: low` y fallbacks del servidor ante rechazos, por el SDK oficial de Anthropic. Configurable con `EXPLAINER_MODEL`.
6. **Evaluación en el CI:** `python -m eval.run_eval` bloquea el merge si un umbral no se cumple ([model card](../ia/model-card.md)).

## Alternativas descartadas

| Alternativa | Por qué no |
| :--- | :--- |
| **El LLM decide el crédito** (o ajusta el puntaje) | No es reproducible ni auditable; un prompt injection podría aprobar un crédito; incumple el estándar de explicabilidad de la CMF. Es el error que más caro sale en una fintech. |
| **Solo plantillas, sin LLM** | Es lo que corre por defecto, y por eso es el respaldo. Pero no se adapta al caso (varios motivos, montos, tono) y no escala a más idiomas ni a preguntas de seguimiento. Lo dejamos como piso, no como techo. |
| **RAG sobre la normativa CMF para un asistente de analistas** | Más valor para el backoffice, pero más superficie (documentos, recuperación, alucinaciones legales) y nada que el solicitante vea. Queda en el roadmap. |
| **Modelo pequeño propio (fine-tuning) en el clúster** | Sin costo por token, pero exige GPU o un modelo que no cabe en el tier de Fargate, MLOps propio y evaluación de seguridad del modelo. No se justifica con el volumen del MVP. |
| **Modelo más barato (`claude-haiku-5-5`) desde el inicio** | ~40 veces más barato por token. No se descarta: se decide midiendo. Correr `ai-eval-llm.yml` con `model: claude-haiku-5-5` y cambiar solo si pasa los mismos umbrales. |
| **LLM-juez para evaluar las explicaciones** | Agrega otro modelo que también se equivoca y cuesta. Las propiedades que importan (coherencia, puntaje, PII) se verifican de forma determinística. |

## Consecuencias

- **Positivas:** el solicitante entiende la decisión; el derecho del art. 8 bis queda informado en cada respuesta; prompt injection sin vía de entrada; la API nunca falla porque el LLM falló.
- **Negativas:** costo por token (acotado por la palanca FinOps 1, ADR 0010); dependencia de un proveedor externo (acotada por el respaldo); el proveedor pasa a ser encargado de tratamiento y hace falta un contrato antes de activar `llm` en prod.
- **Seguridad de red:** en modo `template` la NetworkPolicy (solo DNS) y la regla Falco de conexión saliente siguen intactas. Activar `llm` exige: egress 443 al proveedor, excepción Falco para ese destino y el secret `ANTHROPIC_API_KEY` por ExternalSecret.

## Criterios para revisar esta decisión

- El golden set con el LLM real queda bajo 95 % → se mantiene `template`.
- Un guardrail `pii` o `protected_attribute` se dispara en producción → se vuelve a `template` y post-mortem.
- El costo del LLM supera el 10 % del presupuesto mensual.
