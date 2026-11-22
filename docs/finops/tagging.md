# Política de etiquetas (tagging) de costo

Sin etiquetas no hay FinOps: Cost Explorer no puede decir cuánto cuesta el scoring frente al onboarding, ni staging frente a prod.

## Claves obligatorias

| Clave | Valores | Para qué |
| :--- | :--- | :--- |
| `cost-center` | `crediscore-scoring`, `crediscore-onboarding`, `crediscore-fraud`, `crediscore-platform` | Costo por servicio / bounded context |
| `owner` | `lospapus` | A quién llega la alerta de presupuesto |
| `environment` | `dev`, `staging`, `prod` | Separar staging de prod |
| `managed-by` | `terraform`, `argocd` | Detectar recursos creados a mano (sin etiqueta = sospechoso) |

## Dónde se aplican hoy

| Capa | Cómo | Archivo |
| :--- | :--- | :--- |
| Kubernetes (todos los recursos de `scoring-api`) | `labels` de Kustomize **sin** tocar selectores (cambiar el selector de un Deployment es inmutable y rompería el sync de Argo CD) | [`k8s/kustomization.yaml`](../../k8s/kustomization.yaml) |
| Namespace (Terraform) | `merge(local.finops_tags, ...)` | [`terraform/main.tf`](../../terraform/main.tf) |
| `environment` en Kubernetes | Lo agrega cada overlay de `gitops-repo` | pendiente en `gitops-repo` |

## Cuando AWS entre a Terraform

```hcl
provider "aws" {
  region = "sa-east-1"
  default_tags {
    tags = local.finops_tags   # todas las claves de arriba, en cada recurso
  }
}
```

En EKS con Fargate, el costo de cada pod se reparte con *split cost allocation data* de AWS usando estas mismas labels de Kubernetes. Hay que activarlo en Billing.

## Control

- Checkov puede exigir etiquetas en recursos AWS cuando existan (política propia `CKV2_CREDISCORE_TAGS`, pendiente).
- Cada mes: un reporte de Cost Explorer agrupado por `cost-center` y `environment`, y una revisión de los recursos sin etiqueta.
