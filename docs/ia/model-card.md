# Model card · Explicador de decisiones de CrediScore

Equipo lospapus · versión `explainer-prompt-v1` · 22 de noviembre de 2026
Dueños: rol AI/Data (Abdiel Ortiz, Nelson Arevalo) · revisión legal: PO (Emilio Santibáñez) · estado: borrador para revisión del equipo

## 1. Qué es y qué no es

| | |
| :--- | :--- |
| **Feature** | `GET /v1/credit-applications/{id}/explanation` ([contrato](../../api/openapi.yaml), [código](../../src/explainer.py)) |
| **Tarea** | Explicar en lenguaje claro una decisión de crédito **ya tomada** por el motor de scoring. |
| **Usuario** | La persona que pidió el crédito (por la web, la app o el partner). |
| **Modelo** | `claude-opus-5-5` con `effort: low` y `fallbacks: "default"` (Anthropic, SDK oficial). Se cambia con `EXPLAINER_MODEL`. |
| **Respaldo** | Plantilla determinística en español ([`template_explanation`](../../src/explainer.py)). Es el modo por defecto (`EXPLAINER_MODE=template`). |
| **No hace** | No decide, no cambia el puntaje, no ve el RUT, no lee texto libre del partner, no da asesoría financiera. |

**Por qué un LLM solo para redactar:** la decisión de crédito tiene que ser reproducible y auditable por la CMF. Un LLM no lo es. Por eso el LLM queda fuera de la decisión y se usa donde aporta: que una persona sin formación financiera entienda por qué le dijeron que no. Si el LLM falla, la persona igual recibe la explicación, desde la plantilla.

## 2. Datos que ve el modelo

Solo cinco campos estructurados ([`build_prompt_payload`](../../src/explainer.py)):

```json
{"outcome": "review", "score": 560, "reasons": ["para este monto y plazo necesitamos confirmar tus ingresos"],
 "amount_clp": 2000000, "term_months": 24}
```

- **Fuera del prompt:** RUT, `identity_verification_id`, `partner_reference`, IDs y cualquier dato de contacto. Esto es **minimización de datos** (Ley 21.719, principio de proporcionalidad): el proveedor del LLM nunca recibe datos personales identificables.
- **Atributos protegidos:** el contrato los rechaza en la entrada (`additionalProperties: false`, probado en [`test_contract.py`](../../tests/test_contract.py)). El modelo de scoring no los recibe y el LLM tampoco.

## 3. Guardrails

| Capa | Qué controla | Dónde | Si falla |
| :--- | :--- | :--- | :--- |
| **Entrada estructural** | El prompt no tiene texto libre del usuario: un prompt injection no tiene por dónde entrar | `build_prompt_payload` | — |
| **Detector de injection** | Marca `partner_reference` con patrones de ataque (es/en) | `detect_injection` | Se registra (`input_flags`, métrica, log WARNING) para que Seguridad lo investigue |
| **Salida: coherencia** | El texto dice el mismo resultado que el motor (aprobada / revisión / rechazada) | `check_output` → `outcome_mismatch` | Plantilla |
| **Salida: puntaje** | Si menciona "N de 1000", N es el puntaje real | `score_mismatch` | Plantilla |
| **Salida: PII** | Sin RUT ni correos | `pii` | Plantilla |
| **Salida: fairness** | Sin género, edad, comuna, nacionalidad, estado civil, etc. | `protected_attribute` | Plantilla |
| **Salida: promesas** | Sin "garantizado", "te aseguramos", "100 %" | `promise` | Plantilla |
| **Salida: fuga de prompt** | Sin "system prompt", "instrucciones", etiquetas XML, markdown | `prompt_leak` | Plantilla |
| **Salida: derecho a revisión humana** | Siempre informa que una persona puede revisar la decisión | `missing_human_review` | Plantilla |
| **Salida: largo** | 80–900 caracteres | `length` | Plantilla |
| **Proveedor** | Rechazo de seguridad (`stop_reason: refusal`), timeout (3 s, sin reintentos), error | `Explainer.explain` | Plantilla + circuit breaker |

Cada bloqueo suma `crediscore_guardrail_violations_total{rule}` y queda en la respuesta (`guardrails.output_violations`, `fallback_reason`).

**¿Qué hace el sistema frente a un prompt injection?** (pregunta del panel). Tres cosas, probadas en [`test_explainer.py`](../../tests/test_explainer.py) y en el paso 7 de la demo ([`smoke_e2e.py`](../../scripts/smoke_e2e.py)):
1. El texto del atacante **nunca llega al prompt** (`test_el_prompt_nunca_lleva_rut_ni_texto_libre`).
2. Se **detecta y marca** (`input_flags: ["prompt_injection"]`) para que Seguridad lo revise.
3. Si de todos modos el LLM produjera algo distinto a la decisión, el guardrail de salida lo **bloquea** y se responde con la plantilla (`test_salida_manipulada_del_llm_cae_a_plantilla`).

## 4. Evaluación

`python -m eval.run_eval` ([código](../../eval/run_eval.py)) corre cuatro suites con umbral. El CI la ejecuta en cada PR en modo plantilla y bloquea el merge si un umbral no se cumple (`ci.yml` > `quality`). Resultado del modo plantilla: [`eval/results/template.md`](../../eval/results/template.md).

| Suite | Datos | Métrica | Umbral | Plantilla | LLM |
| :--- | :--- | :--- | ---: | ---: | ---: |
| Golden set | [26 decisiones](../../eval/golden_set.jsonl) que cubren los tres resultados, los bordes 650/450 y 4 injections | casos que pasan los 8 criterios | 100 % (plantilla) · 95 % (LLM) | **100 %** | pendiente |
| Red team de salida | [24 textos](../../eval/redteam_outputs.jsonl): 8 paráfrasis válidas + 16 maliciosos en 7 categorías | recall de bloqueo · falsos positivos | 100 % · ≤ 10 % | **100 % · 0 %** | n/a |
| Prompt injection | [26 referencias](../../eval/injection_set.jsonl): 14 ataques + 12 normales | recall · falsos positivos | ≥ 90 % · ≤ 10 % | **100 % · 0 %** | n/a |
| Fairness | 4.000 solicitudes **sintéticas** (semilla 21719) | disparate impact mínimo (regla 4/5) | ≥ 0,80 | **0,959** | n/a |

Los 8 criterios del golden set: resultado y puntaje correctos, guardrails OK, menciona el motivo, informa la revisión humana, máximo 5 oraciones, flag de injection correcto y el texto del atacante no aparece en la salida.

**Por qué golden set y no RAGAS:** RAGAS mide recuperación y fidelidad en sistemas RAG (contexto recuperado → respuesta). Acá no hay recuperación: el contexto es la decisión misma, completa. Lo que importa medir es fidelidad a la decisión (el texto dice lo que decidió el motor), y eso lo cubren `outcome_mismatch` y `score_mismatch` de forma determinística, sin un LLM-juez que también se equivoca.

**Lo que no hicimos (honestidad técnica):**
- **El golden set no se ha corrido con el LLM real.** El equipo no tiene todavía una API key de Anthropic en el repo. El workflow manual [`ai-eval-llm.yml`](../../.github/workflows/ai-eval-llm.yml) lo corre cuando se cargue el secret `ANTHROPIC_API_KEY`; costo estimado de una corrida en [FinOps](../finops/costos.md).
- **Los sets de red team e injection los escribió el mismo equipo que escribió las reglas.** El 100 % es optimista. Siguiente paso: que otro equipo del taller haga red teaming a ciegas y sumar sus casos al set.
- **Fairness con datos sintéticos.** Medimos el sesgo que entra por proxies (monto y plazo distintos por zona). Con datos reales de originación hay que repetirlo por género, tramo de edad y región, y monitorearlo en producción (drift).

## 5. Fairness: cómo lo demostramos a un regulador

1. **Por diseño:** ni el contrato ni el modelo aceptan atributos protegidos (test automático, 422 si llegan).
2. **Por resultado:** la tasa de aprobación por grupo se mide con la regla 4/5 (disparate impact ≥ 0,8). En la población sintética: género 0,989 · zona 0,959.
3. **Por explicación:** cada decisión trae códigos de motivo y el texto nunca usa atributos protegidos (guardrail `protected_attribute`).
4. **Por trazabilidad:** `model_version` y `prompt_version` van en cada respuesta, y el reporte de evaluación queda como artefacto de cada run del CI.

## 6. Marco legal citado

| Norma | Qué exige | Cómo lo cumplimos |
| :--- | :--- | :--- |
| **Ley 21.719** (protección de datos personales; modifica a fondo la Ley 19.628 y crea la Agencia de Protección de Datos). Vigencia prevista: 1-dic-2026; un proyecto del Ejecutivo para postergarla al 15-oct-2027 sigue en trámite en el Congreso (nov-2026) | **Art. 8 bis:** derecho a no ser objeto de decisiones basadas únicamente en tratamiento automatizado que produzcan efectos jurídicos o afecten significativamente al titular; derecho a explicación y a intervención humana | Cada explicación informa la revisión humana (`human_review.legal_basis`). La re-evaluación por analista ya está en el contrato (`POST /reevaluations`, HU4) |
| Ley 21.719, principios de finalidad, proporcionalidad y seguridad | Tratar solo los datos necesarios | El LLM no recibe datos personales (§2). El proveedor del LLM sería encargado de tratamiento: contrato de procesamiento pendiente antes de pasar a modo `llm` en prod |
| **Ley 20.609** (antidiscriminación) | No discriminar arbitrariamente por sexo, edad, raza, etc. | Atributos fuera del modelo + medición 4/5 + guardrail de salida |
| **Ley 21.521** (Ley Fintec) y normativa CMF | Trazabilidad y gestión de riesgo operacional de proveedores tecnológicos | Versión de modelo y prompt en cada respuesta; fallback sin dependencia del proveedor; registro de auditoría (ADR 0004) |
| **Reglamento de IA de la UE** (referencia, no aplica en Chile) | El scoring crediticio de personas es "alto riesgo" (Anexo III) | Lo usamos como estándar de referencia para la documentación (esta model card) y la supervisión humana |

## 7. Costo

Con el modelo por defecto y la caché activa, el costo por explicación y por mes está en [docs/finops/costos.md](../finops/costos.md). La palanca medida (caché por contenido de la decisión) también está ahí.

## 8. Monitoreo en producción

| Señal | Métrica | Alerta |
| :--- | :--- | :--- |
| Tasa de fallback | `crediscore_explanations_total{source="template"}` / total | > 20 % en 15 min (con `EXPLAINER_MODE=llm`) |
| Bloqueos de guardrail | `crediscore_guardrail_violations_total` por regla | cualquier `protected_attribute` o `pii` → incidente |
| Intentos de injection | `crediscore_prompt_injection_flags_total` | > 5 en 1 h por partner → Seguridad |
| Circuit breaker | `crediscore_circuit_state` | abierto > 5 min |
| Costo | `crediscore_llm_cost_usd_total` | > 80 % del presupuesto mensual |
