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
- El CI (`.github/workflows/ci.yml`) corre tres jobs:
  1. **quality**, en cada PR y en cada push: lint y formato con ruff, tests
     con cobertura ≥ 70 % sobre `src/`, SAST con bandit y auditoría de
     dependencias con pip-audit. Cualquier hallazgo bloquea el pipeline.
  2. **build-and-push**, solo en push: publica
     `ghcr.io/4noisy/scoring-api:<sha del commit>` con SBOM y provenance, y la
     escanea con Trivy (bloquea si hay vulnerabilidades críticas).
  3. **promote**, solo en push a `main`: actualiza el tag en `gitops-repo`.
     - **dev:** commit directo a `main` de `overlays/dev`; Argo CD sincroniza
       solo. La revisión humana ya ocurrió en el PR del repo app, y así un merge
       a `main` llega a dev sin pasos manuales.
     - **prod:** abre o actualiza un Pull Request en `overlays/prod`, que
       requiere revisión antes del merge.
- `overlays/dev` quita el Ingress y el HPA, porque el cluster local no tiene
  ingress controller ni metrics-server; `overlays/prod` los mantiene.
- Los secretos reales no viven en Git: en stg/prod se reemplazan por
  ExternalSecrets desde AWS Secrets Manager (ADR 0003). El `secret.yaml`
  del repo solo contiene un placeholder.

**Por qué pull y no push:** el CI no necesita credenciales del cluster, el
drift se detecta y se corrige solo (`selfHeal`), y el rollback es un
`git revert`. Cada release queda registrado en Git (commit en dev, PR revisado
en prod), lo que da la trazabilidad que exige la CMF.

**Por qué Argo CD y no Flux:** su UI permite mostrar el estado
(Synced/Healthy) a todo el equipo y a quien audite, y soporta RBAC por
proyecto. Flux es más liviano y encaja bien en flujos 100 % Git, pero para un
equipo de seis personas con roles distintos pesa más la visibilidad que el
footprint.

## Consecuencias

**Positivas**
- Cada despliegue queda en el historial de Git; los de prod pasan por un PR revisado.
- Sin credenciales del cluster en el CI.
- Rollback simple y auditable.
- Drift detectable y corregido automáticamente.

**Negativas / costos**
- Dos repos que mantener y coordinar.
- Hay que instalar y operar Argo CD en el cluster.
- El paso CI → gitops requiere un token fine-grained (`GITOPS_TOKEN`) con
  permisos de Contents y Pull requests sobre `gitops-repo`, que hay que rotar.
- El tag es el SHA del commit, inmutable por convención y no por el registro;
  el digest de cada imagen queda registrado en el PR de prod.

**Pendiente**
- Despliegue canary con Argo Rollouts.
- Exigir dos revisores en el PR hacia `overlays/prod` y proteger `main` del
  repo app con el check `quality` obligatorio.
