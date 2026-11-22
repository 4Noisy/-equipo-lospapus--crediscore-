# ADR 0010 — FinOps: presupuesto por solicitud, etiquetas y palancas medidas

- **Estado:** Aceptada (palancas 1 y 2) · Propuesta (palanca 3, MSK)
- **Fecha:** 2026-11-22
- **Equipo:** lospapus

## Contexto

El ADR 0003 dejó pendiente "gobierno de costos sobre MSK y Aurora", y el ADR 0006 aceptó el costo de EKS frente a ECS. La S18 pide un costo mensual creíble, tagging y al menos 2 palancas medidas antes y después. No hay todavía una cuenta AWS con facturación, así que el costo se modela con precios de lista y supuestos explícitos ([costos](../finops/costos.md)).

## Decisión

1. **Unidad de costo del producto: USD por solicitud evaluada**, objetivo < 0,10. Hoy ≈ 0,082 con 30.000 solicitudes/mes.
2. **Presupuesto mensual USD 2.700** con alertas al 50/80/100 %.
3. **Etiquetas obligatorias** `cost-center`, `owner`, `environment`, `managed-by` en Kubernetes y Terraform ([política](../finops/tagging.md)), sin tocar selectores.
4. **Palanca 1 (aplicada):** LLM solo para `review`/`rejected` + caché por contenido. Medido: −87 % de llamadas (8.000 → 1.042 por 8.000 explicaciones).
5. **Palanca 2 (aplicada):** right-sizing con la capacidad medida en el game day: `requests.cpu` 250m (lo que Fargate cobra igual), HPA máximo 8, staging con 1 réplica en horario hábil. −8,1 % del costo esperado y −21 % del techo.
6. **Palanca 3 (propuesta):** MSK Serverless es el 70 % del costo. Se decide con datos de tráfico real de eventos; las opciones están evaluadas en [costos](../finops/costos.md#palanca-3--msk-identificada-no-aplicada).

## Alternativas descartadas

| Alternativa | Por qué no |
| :--- | :--- |
| **Volver de EKS a ECS** para ahorrar el plano de control (USD 219/mes en 2 ambientes) | Reabre el ADR 0006 por el 9 % del costo, mientras MSK es el 70 %. Se ataca primero lo grande. |
| **Fargate Spot en prod** | Hasta 70 % más barato en cómputo, pero puede interrumpir pods con 2 min de aviso, y el cómputo es solo el 6 % del total. En staging sí es una opción futura. |
| **Savings Plans / reservas** | Exigen compromiso de 1–3 años con un volumen que aún no conocemos. Se evalúa después de 3 meses de uso estable. |
| **Modelo LLM más barato sin evaluar** | Ahorro grande en tokens, pero sin evidencia de calidad. Ver ADR 0008: se cambia solo si pasa el golden set. |
| **Apagar el explicador LLM** | El costo del LLM ya es el 2 % del total tras la palanca 1; apagarlo resta valor al usuario por un ahorro marginal. |

## Consecuencias

- Cada número de costo tiene un script que lo reproduce (`scripts/finops_*.py`) y sus supuestos a la vista.
- **Brecha:** los ahorros de infra son modelados, no facturados. El factor regional de sa-east-1 (1,5) es un supuesto. Se validan con Cost Explorer por `cost-center` en cuanto exista la cuenta.
