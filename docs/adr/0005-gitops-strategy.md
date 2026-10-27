# ADR 0005 — Estrategia GitOps para CrediScore

- **Estado:** Aceptada
- **Fecha:** 2026-10-27
- **Equipo:** lospapus

## Contexto

CrediScore es una plataforma de scoring crediticio y antifraude sujeta a
auditoría de la CMF (CHARTER, atributos de calidad). En la S07 dejamos listos
el Dockerfile multi-stage (runtime distroless, usuario nonroot) y los
manifiestos Kustomize de `scoring-api` en `k8s/` (Deployment, Service, Ingress,
ConfigMap, HPA, PDB). Falta decidir cómo llegan los cambios al cluster de
forma automática, trazable y reversible.

Opciones evaluadas para el despliegue:

1. **Push-based:** el pipeline de CI ejecuta `kubectl apply` o `helm upgrade`.
2. **Pull-based (GitOps):** un agente dentro del cluster observa un repo Git y
   reconcilia el estado real con el declarado.

Opciones evaluadas de herramienta GitOps: **Argo CD** y **Flux**.

## Decisión

Adoptamos **GitOps pull-based con Argo CD** y un repo separado
(`gitops-repo`) con estructura Kustomize: `base/` (los manifiestos de la
S07) y `overlays/{dev,prod}`.

- El repo de la app contiene código, Dockerfile, tests y el pipeline CI.
- El CI corre los gates (lint, tests con cobertura ≥ 70 %, SAST con Semgrep),
  publica la imagen en GHCR etiquetada con el SHA del commit y abre un Pull
  Request en el repo gitops actualizando ese tag.
- Al hacer merge del PR, Argo CD detecta el cambio y sincroniza el ambiente.
- Los secretos reales no viven en Git: en stg/prod se reemplazan por
  ExternalSecrets desde AWS Secrets Manager (ADR 0003). El `secret.yaml`
  del repo solo contiene un placeholder.

**Por qué pull y no push:** el CI no necesita credenciales del cluster, el
drift se detecta y se corrige solo (`selfHeal`), y el rollback es un
`git revert`. Cada release queda como PR revisable, lo que da la trazabilidad
que exige la CMF.

**Por qué Argo CD y no Flux:** su UI permite mostrar el estado
(Synced/Healthy) a todo el equipo y a quien audite, y soporta RBAC por
proyecto. Flux es más liviano y encaja bien en flujos 100 % Git, pero para un
equipo de seis personas con roles distintos pesa más la visibilidad que el
footprint.

## Consecuencias

**Positivas**
- Cada despliegue es un PR con historial y revisión.
- Sin credenciales del cluster en el CI.
- Rollback simple y auditable.
- Drift detectable y corregido automáticamente.

**Negativas / costos**
- Dos repos que mantener y coordinar.
- Hay que instalar y operar Argo CD en el cluster.
- El paso CI → PR al gitops requiere un token (`GITOPS_TOKEN`) con permisos
  sobre el repo gitops, que hay que rotar.

**Pendiente**
- Despliegue canary con Argo Rollouts.
- Exigir dos revisores en el PR hacia `overlays/prod`.
