# FinOps · Costo mensual, palancas y presupuesto

Equipo lospapus · S18 · dueño: DevSecOps (Martin Jara) con el PO (Emilio Santibáñez)
Modelos reproducibles: [`scripts/finops_cost_model.py`](../../scripts/finops_cost_model.py) (infra) y [`scripts/finops_llm_lever.py`](../../scripts/finops_llm_lever.py) (LLM). Datos: [`evidencia/`](evidencia/).

## Supuestos (todo número de esta página depende de estos)

| Supuesto | Valor | De dónde sale |
| :--- | :--- | :--- |
| Volumen MVP | **30.000 solicitudes/mes** (~1.000/día) | Supuesto del PO; validar con los partners piloto |
| Ambientes en AWS | **prod + staging**. Dev corre en kind local (USD 0) | ADR 0005 y 0006 |
| Precios | Lista on-demand **us-east-1** × **factor 1,5** para sa-east-1 | El factor es un **supuesto**: no encontramos la tarifa pública de São Paulo por servicio. Reemplazar con [AWS Pricing Calculator](https://calculator.aws/) |
| Servicios incluidos | Los del camino crítico (EKS, Fargate, Aurora, MSK, NAT, ALB, API GW, logs, secretos) | [Servicios gestionados](../arch/managed-services.md). OpenSearch, Neptune y Redis (ADR 0004) quedan fuera: aún no tienen uso en el MVP |
| Tokens por explicación | ~343 de entrada, ~253 de salida | **Estimados** (caracteres ÷ 3,5 + 200 de razonamiento). Se reemplazan con la corrida de [`ai-eval-llm.yml`](../../.github/workflows/ai-eval-llm.yml), que cuenta lo facturado |

## Costo mensual estimado (después de las palancas)

| Línea | prod | staging | Total | % |
| :--- | ---: | ---: | ---: | ---: |
| **MSK Serverless** (clúster + 30 particiones) | 870,53 | 870,53 | **1.741,06** | **70 %** |
| EKS plano de control | 109,50 | 109,50 | 219,00 | 9 % |
| Aurora Serverless v2 (mínimo + 20 GB) | 134,40 | 26,76 | 161,16 | 7 % |
| Fargate (3 servicios) | 121,64 | 14,66 | 136,30 | 6 % |
| NAT Gateway | 49,28 | 49,28 | 98,56 | 4 % |
| ALB del Ingress | 24,64 | 24,64 | 49,28 | 2 % |
| CloudWatch, Secrets Manager, API Gateway | 12,08 | 5,51 | 17,59 | 1 % |
| **Infra** | **1.322,07** | **1.100,88** | **2.422,95** | |
| LLM explicador (palanca 1 aplicada) | 50,11 | — | 50,11 | 2 % |
| **Total** | | | **≈ USD 2.473 / mes** | |

**Costo por solicitud:** 2.473 ÷ 30.000 ≈ **USD 0,082** (infra 0,081 + LLM 0,0017).
**Techo (peor caso, HPA al máximo todo el mes):** USD 2.626 de infra.

## Palanca 1 · LLM solo donde agrega valor + caché (aplicada y medida)

**Qué:** el explicador redacta con el LLM solo las decisiones `review` y `rejected` (donde el derecho a explicación de la Ley 21.719 pesa más); lo aprobado sale de la plantilla. Además, una caché por contenido de la decisión evita pagar dos veces el mismo texto ([`src/explainer.py`](../../src/explainer.py), `EXPLAINER_LLM_OUTCOMES`, `EXPLAINER_CACHE_SIZE`).

**Cómo se midió:** el `Explainer` real sobre 4.000 solicitudes sintéticas, cada explicación pedida 2 veces (app + partner), con un cliente LLM que cuenta llamadas ([evidencia](evidencia/llm-lever.json)).

| Configuración | Llamadas al LLM (medidas) | por 1.000 explicaciones | USD/mes estimado |
| :--- | ---: | ---: | ---: |
| A · antes: LLM para todo, sin caché | 8.000 | 1.000 | 386,61 |
| B · + caché | 3.483 | 435 | 168,29 |
| C · + solo `review`/`rejected` | **1.042** | **130** | **50,11** |
| **Reducción A → C** | **−87 %** | | **−USD 336/mes** |

Sin pérdida de calidad: el golden set y los guardrails no cambian (la plantilla pasa el 100 % de la evaluación).

## Palanca 2 · Right-sizing con capacidad medida (aplicada)

**Medido en el game day E0** ([evidencia](../resiliencia/evidencia/gameday-local-run3.json)): un proceso sostiene ~456 req/s con p95 de 8,2 ms, usando 1,09 núcleos y 70,6 MiB de RSS máximo.

| Cambio | Antes | Después | Por qué |
| :--- | :--- | :--- | :--- |
| `requests.cpu` | 100m | **250m** | Fargate cobra mínimo 0,25 vCPU por pod: los 100m igual se pagaban como 250m, y el HPA medía contra una cifra que no era la pagada. Costo: igual |
| `requests.memory` | 128Mi | 128Mi | 70,6 MiB medidos; 128 + 256 (overhead de Fargate) = 384 MiB, dentro del tier de 0,5 GB |
| HPA `maxReplicas` | 20 | **8** | 8 pods × 0,25 vCPU ≈ 2 núcleos ≈ ~800 req/s con la capacidad medida (escalada lineal: supuesto). El pico de negocio estimado es < 5 req/s. Con 20, un cliente desbocado o un DoS podía escalar el gasto sin beneficio |
| staging | 3 réplicas 24×7, Aurora con 2 instancias | **1 réplica, 12 h × 22 días hábiles**, Aurora 1 instancia con auto-pausa | Staging no necesita alta disponibilidad fuera de horario. Se aplica en `gitops-repo` (overlay staging + CronJob de escalado a 0) |

| Resultado | Antes | Después | Ahorro |
| :--- | ---: | ---: | ---: |
| Costo esperado (infra) | 2.637,57 | 2.422,95 | **−214,62 (−8,1 %)** |
| Costo techo (infra) | 3.326,84 | 2.625,68 | **−701,16 (−21 %)** |

**Lo que no está medido:** el ahorro de infra sale del modelo de precios, no de una factura. Medido de verdad es la capacidad por proceso (E0) y la cantidad de llamadas al LLM. Cuando exista la cuenta AWS, el antes/después se valida con Cost Explorer filtrando por la etiqueta `cost-center`.

## Palanca 3 · MSK (identificada, **no aplicada**)

MSK Serverless es el **70 % del costo**, y con 30.000 solicitudes al mes el tráfico de eventos es mínimo. Opciones evaluadas para el [ADR 0010](../adr/0010-finops.md):

| Opción | USD/mes (2 ambientes, estimado) | Contra |
| :--- | ---: | :--- |
| MSK Serverless (hoy) | ~1.741 | Pago base alto sin importar el tráfico |
| MSK provisionado `kafka.t3.small` × 3 brokers por ambiente | ~300 | Hay que dimensionar y operar brokers (el ADR 0003 quería delegar eso) |
| Un solo MSK compartido por staging y prod, con ACLs | ~870 | Mezcla ambientes: un error en staging puede tocar prod. Seguridad lo rechaza |
| SNS + SQS para el MVP, Kafka después | < 20 | Reabre el ADR 0002 (event-driven con Kafka) y cambia el catálogo de eventos |

**Decisión:** no se aplica en el MVP sin medir el throughput real de eventos. Es la primera tarea de FinOps cuando haya tráfico de partners (ver [roadmap](../defensa/roadmap.md)).

## Presupuesto conectado al producto

| Concepto | Valor |
| :--- | :--- |
| Presupuesto mensual de infra + LLM | **USD 2.700** (costo esperado + 9 % de margen) |
| Alertas (AWS Budgets) | 50 %, 80 % y 100 % del presupuesto → `#equipo-crediscore`; 80 % del presupuesto del LLM → AI/Data |
| Unidad de negocio | **costo por solicitud evaluada**: objetivo < USD 0,10 (hoy ≈ 0,082) |
| Break-even (supuesto a validar por el PO) | Si cada crédito aprobado deja USD 10 de contribución y se aprueba ~69 % (simulación de fairness), la infra se paga con **~250 créditos aprobados al mes (~360 solicitudes)**. Sumando un equipo de 6 personas (USD 12.000/mes, supuesto), el break-even sube a **~1.450 créditos/mes (~2.100 solicitudes)**: 7 % del volumen supuesto |

## Tagging

Política y claves en [tagging.md](tagging.md). En el repo: labels `cost-center` y `owner` en todos los recursos de [`k8s/`](../../k8s/kustomization.yaml) y `local.finops_tags` en [Terraform](../../terraform/main.tf).
