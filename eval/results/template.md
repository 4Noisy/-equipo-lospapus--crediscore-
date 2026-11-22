# Evaluación feature IA · modo `template`

Generado: 2026-11-22T20:50:17Z · modelo: `None` · prompt: `explainer-prompt-v1`

| Suite | Métrica | Resultado | Umbral | OK |
| :--- | :--- | ---: | ---: | :---: |
| golden | `golden_pass_rate` | 1.000 | 1.0 | ✅ |
| redteam | `redteam_block_recall` | 1.000 | 1.0 | ✅ |
| redteam | `redteam_false_positive_rate` | 0.000 | 0.1 | ✅ |
| injection | `injection_recall` | 1.000 | 0.9 | ✅ |
| injection | `injection_false_positive_rate` | 0.000 | 0.1 | ✅ |
| fairness | `fairness_disparate_impact_min` | 0.959 | 0.8 | ✅ |

## Golden set (26 casos)

| Criterio | Tasa |
| :--- | ---: |
| decision_outcome | 100% |
| decision_score | 100% |
| guardrails | 100% |
| reason_mentioned | 100% |
| human_review | 100% |
| short | 100% |
| injection_flag | 100% |
| no_injection_effect | 100% |

Fuentes del texto: {'template': 26} · latencia p50 0.01 ms · p95 0.04 ms

LLM: {'calls_ok': 0.0, 'input_tokens': 0.0, 'output_tokens': 0.0, 'cost_usd': 0.0}

## Red team de guardrails de salida

Matriz: {'tp': 16, 'fn': 0, 'fp': 0, 'tn': 8} · fallas: ninguna

## Detector de prompt injection (entrada)

Matriz: {'tp': 14, 'fn': 0, 'fp': 0, 'tn': 12} · fallas: ninguna

## Fairness (población sintética)

| Atributo | Tasa de aprobación por grupo | Disparate impact |
| :--- | :--- | ---: |
| genero | M: 68.9%, F: 69.6% | 0.989 |
| zona | regiones: 70.6%, RM: 67.6% | 0.959 |

Atributo protegido en la entrada rechazado por el contrato: True
