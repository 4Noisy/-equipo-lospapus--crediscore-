# ADR 0005: Plataforma de contenedores, Kubernetes e infraestructura como código

**Fecha:** 2026-10-15  
**Estado:** Propuesto  
**Relacionado con:** [ADR 0002](0002-estilo-arquitectonico.md), [ADR 0003](0003-cloud-style.md), [ADR 0004 de datos y eventos](0004-datos-y-eventos.md), [checklist 12-Factor](../12-factor-checklist.md), [servicios gestionados](../arch/managed-services.md), [Dockerfile](../../Dockerfile), [manifiestos K8s](../../k8s/), [Terraform](../../terraform/main.tf)


## Contexto

El ADR 0003 fijó AWS y un estilo híbrido (Fargate para los microservicios, Lambda para los consumidores asíncronos), y descartó "Kubernetes autogestionado" por falta de un SRE dedicado. La S07 pide empaquetar, orquestar y provisionar el servicio principal, y para eso faltan cuatro decisiones: la imagen base y el modo de publicarla, la distribución de Kubernetes (local y de destino), la herramienta de manifiestos y la herramienta de infraestructura como código.

Estado actual del repositorio: un `Dockerfile` multi-stage, nueve recursos en `k8s/` (Namespace, ServiceAccount, ConfigMap, Secret, Deployment, Service, Ingress, HPA y PodDisruptionBudget) y un `terraform/main.tf` con provider Kubernetes, backend S3 y namespace. El servicio es el `scoring-api` mínimo del lab, que todavía guarda el estado en memoria.

**Drivers de la decisión:**

| ID | Driver | Fuente |
| :-- | :--- | :--- |
| **P1** | Reproducibilidad: lo que se prueba es lo que se despliega. | Checklist 12-Factor #05 |
| **P2** | Seguridad: superficie mínima, ejecución sin root, sin secretos en la imagen ni en git. | CHARTER (Definition of Done), ADR 0003 |
| **P3** | Escalado horizontal e independiente de Scoring y Fraude. | ADR 0002, 12-Factor #08 |
| **P4** | Apagado ordenado (SIGTERM < 30 s) sin perder eventos en vuelo. | 12-Factor #09 |
| **P5** | Capacidad operativa: equipo de 6 personas, sin SRE 24/7. | ADR 0003 |
| **P6** | Paridad entre desarrollo y producción, y portabilidad entre proveedores. | 12-Factor #10, ADR 0003 (*Ports & Adapters*, multi-cloud como evolución) |
| **P7** | Costo acotado para un MVP. | ADR 0003 |

## Decisión

### 1. Imagen: multi-stage sobre distroless, publicada por digest

* **Build:** `python:3.11-slim`. **Runtime:** `gcr.io/distroless/python3-debian12:nonroot`, con `USER nonroot` (UID 65532) y puerto 8080.
* **Etiquetado:** la imagen se referencia por digest (`@sha256:<64 hex>`), nunca por `:latest`.
* **Registro:** GHCR durante la S07 y el pipeline de la S08; Amazon ECR cuando se despliegue en AWS (como ya indica `managed-services.md`).

**Por qué distroless.** El runtime no tiene shell ni gestor de paquetes: un atacante que logre ejecutar código no cuenta con herramientas para moverse, y hay menos paquetes que acumulen CVE (P2). Python 3.11 en el build coincide con el que trae la imagen distroless, de modo que los paquetes instalados en `/deps` funcionan en el runtime (el Dockerfile lo documenta). El multi-stage deja `pip` y el compilador fuera de la imagen final y la mantiene pequeña. El usuario `nonroot` coincide con el `runAsUser: 65532` del Deployment.

**Por qué digest.** Una etiqueta se puede mover; un digest identifica exactamente el contenido. Con él, lo que probó QA es byte a byte lo que se despliega (P1).

**Costo aceptado.** Sin shell no se puede entrar al contenedor ni usar `HEALTHCHECK` con `curl`; la depuración se hace con contenedores efímeros (`kubectl debug`) y la salud la verifican las probes de Kubernetes. Tampoco hay `preStop` con `sleep`: el Deployment confía en `terminationGracePeriodSeconds: 30` y en el apagado ordenado de uvicorn (25 s), que cumple P4.

### 2. Kubernetes: `kind` en local y Amazon EKS con Fargate como destino

* **Local (laboratorio, pruebas de manifiestos, CI de la S08): `kind`.** Ejecuta Kubernetes estándar dentro de Docker, arranca en segundos y funciona igual en GitHub Actions, lo que da la paridad que pide P6.
* **Destino en AWS: Amazon EKS con perfiles de Fargate.** Se mantiene Fargate como cómputo (sin nodos que parchear, P5) y se cambia el orquestador de ECS a Kubernetes. Esto **enmienda parcialmente el ADR 0003**, que contrapone "Fargate" a "Kubernetes autogestionado": lo descartado allí fue operar el clúster, y con EKS el plano de control es gestionado y con Fargate no hay nodos. Los consumidores asíncronos siguen en Lambda y los servicios de datos siguen fuera del clúster (Aurora, MSK, OpenSearch, Neptune, Redis).

**Argumento.** Los mismos manifiestos y el mismo provider de Terraform sirven en `kind` y en EKS (cambia el contexto de `kubeconfig`), lo que reduce el riesgo de "en mi máquina funciona" (P6). Kubernetes habilita el HPA, los *rollouts* declarativos y el flujo GitOps (Argo CD o Flux) previsto para la S08, y mantiene abierta la evolución multi-cloud del ADR 0003 sin atar el despliegue a la API de ECS.

**Costo aceptado, dicho sin adornos.** ECS sobre Fargate sería más simple y más barato: EKS cobra por el plano de control y suma conceptos que el equipo debe aprender (P5, P7). Se acepta porque el curso apunta a Kubernetes y GitOps, y porque la portabilidad vale más que la simplicidad en este proyecto. Además, en Fargate los pods no admiten DaemonSets y cada pod arranca en su propia máquina virtual ligera, de modo que el arranque es más lento que en nodos propios (ver criterios de revisión).

**Distribuciones descartadas para local:** `minikube` (más pesado, usa máquina virtual o driver de contenedor propio) y `k3d`/k3s (liviano, pero su distribución difiere de Kubernetes estándar: Traefik por defecto y componentes retirados, lo que erosiona la paridad con EKS).

### 3. Manifiestos: Kustomize

`kubectl apply -k k8s/` aplica los manifiestos sin herramientas adicionales. Hay un servicio y dos entornos previsibles (local y AWS), y la diferencia entre ellos es pequeña y estructural (el Ingress usa `nginx` en `kind` y `alb`, con AWS Load Balancer Controller, en EKS, como ya anota `ingress.yaml`): eso se resuelve con *overlays*, sin plantillas. Los manifiestos siguen siendo YAML válido y legible, y se validan igual con `kubeconform`. Helm se descarta por ahora: sus plantillas y el versionado de *charts* se justifican al distribuir una aplicación a terceros o al parametrizar muchos servicios, y hoy sumarían una capa sin beneficio (P5).

### 4. Línea base de seguridad del Pod (P2)

Todos los Pods cumplen el perfil *restricted* de los Pod Security Standards: `runAsNonRoot`, UID/GID 65532, `readOnlyRootFilesystem` (con `emptyDir` en `/tmp`), `allowPrivilegeEscalation: false`, `capabilities.drop: ["ALL"]` y `seccompProfile: RuntimeDefault`. El ServiceAccount no monta token (`automountServiceAccountToken: false`) porque el servicio no llama a la API de Kubernetes. Los secretos no se hornean en la imagen: en local el `Secret` es un *placeholder* y, en AWS, se sincroniza desde AWS Secrets Manager (decisión del ADR 0003).

### 5. Escalado y disponibilidad (P3, P4)

* **HPA** (`autoscaling/v2`): entre 3 y 20 réplicas, con objetivo de 65 % de CPU y 75 % de memoria. El escalado hacia arriba es agresivo y el de bajada usa una ventana de 300 s y retira un pod cada 2 minutos, para no reducir réplicas en medio de un pico de solicitudes de crédito.
* **PodDisruptionBudget** con `minAvailable: 2`, para que un mantenimiento de nodos no deje el servicio sin capacidad.
* **Rolling update** con `maxUnavailable: 0` y `maxSurge: 1`, más probes de `readiness` (`/ready`) y `liveness` (`/health`).
* **Restricción de estado:** las réplicas deben ser *stateless*. Hoy el `scoring-api` guarda las solicitudes en memoria por réplica, así que con 3 réplicas un reintento idempotente puede caer en otra y no encontrar su clave. El servicio solo debe escalar horizontalmente cuando el estado viva en Aurora ([ADR 0004 de datos](0004-datos-y-eventos.md)).

### 6. Infraestructura como código: Terraform con estado remoto en S3

* **Herramienta:** Terraform (≥ 1.10), con el provider `kubernetes` para el namespace y los objetos de plataforma. La estructura objetivo, fuera del alcance de la S07, son módulos `vpc`, `eks` y `aurora-postgres`.
* **Estado remoto:** bucket S3 cifrado y con versionado, con bloqueo nativo (`use_lockfile = true`) en lugar de una tabla DynamoDB: una dependencia menos que operar (P5). Un estado por dominio de cambio (clave `crediscore/scoring-api/`) y un *workspace* por entorno. El `.tfstate` no se versiona en git.

**Por qué Terraform.** Es declarativo, tiene el ecosistema más amplio y sirve tanto para recursos de AWS como para objetos de Kubernetes con la misma herramienta y el mismo flujo `plan`/`apply`. Mantiene abierta la ruta multi-cloud del ADR 0003 (P6). Pulumi permitiría escribir infraestructura en Python o TypeScript con pruebas unitarias, pero su ecosistema y la adopción son menores y el equipo tendría que mantener código imperativo donde HCL declarativo basta. CloudFormation es nativo de AWS y detecta *drift*, pero no gestiona objetos de Kubernetes con la misma facilidad y ata la infraestructura a un proveedor.

## Consecuencias

### Positivas
* **Reproducibilidad:** imagen inmutable por digest y manifiestos validados en CI (P1).
* **Seguridad:** imagen sin shell, ejecución sin root y perfil *restricted* desde el primer despliegue (P2).
* **Paridad:** los mismos manifiestos y el mismo provider sirven en `kind` y en EKS (P6).
* **Resiliencia:** HPA, PDB, probes y apagado ordenado cubren las brechas 08 y 09 del checklist 12-Factor (P3, P4).
* **Menos piezas operadas:** Fargate sin nodos y estado de Terraform sin DynamoDB (P5).

### Negativas y riesgos

| Riesgo | Mitigación |
| :--- | :--- |
| **Costo y complejidad de EKS** frente a ECS para un equipo de 6 sin SRE. | Plano de control gestionado, Fargate sin nodos, Kustomize sin plantillas; gobierno de costos (FinOps) ya previsto en el ADR 0003. |
| **Arranque lento de pods en Fargate** durante picos del HPA. | El `POST` responde `received` y la decisión es asíncrona; 3 réplicas mínimas; medir y, si hace falta, pasar a grupos de nodos gestionados. |
| **Los `requests` se redondean a configuraciones de Fargate** (hay un mínimo de CPU y memoria por pod), por lo que el uso relativo que mide el HPA cambia. | Recalibrar `requests` y `limits` con `kubectl top` antes de desplegar en EKS; hoy son una estimación sin benchmark. |
| **Digest placeholder:** la imagen aún no está publicada y el digest del Deployment no es válido. | Publicar en GHCR y reemplazar el digest; luego automatizarlo en el pipeline de la S08. |
| **Secretos:** el `Secret` es un *placeholder* en git. | En AWS, sincronizar desde Secrets Manager (por ejemplo, con External Secrets); nunca commitear valores reales. |
| **Depuración sin shell.** | `kubectl debug` con contenedor efímero; logs JSON a stdout con `trace_id` (12-Factor #11). |
| **Terraform ≥ 1.10:** el slide de la S07 pide ≥ 1.6 y el bucket del backend debe existir antes de `init`. | Documentar la versión mínima y el comando `terraform init -backend-config=...` en el README. |

## Alternativas descartadas

* **ECS sobre Fargate sin Kubernetes (ADR 0003 original):** más simple y barato; se descarta por portabilidad entre proveedores y por el ecosistema de HPA, *rollouts* y GitOps de la S08.
* **Kubernetes autogestionado (kubeadm o k3s en EC2):** el equipo no puede operar el clúster (regla del "sábado a las 3 PM" del ADR 0003).
* **EKS con grupos de nodos gestionados:** permite DaemonSets y escala más rápido, pero reintroduce el parcheo y el dimensionamiento de nodos. Queda como plan de repliegue.
* **`minikube` y `k3d` para el clúster local:** ver sección 2.
* **Helm:** ver sección 3.
* **Alpine como runtime:** usa musl, lo que obliga a ruedas `musllinux` o a compilar dependencias; no reduce la superficie tanto como distroless, porque sigue incluyendo shell y gestor de paquetes.
* **`python:3.11-slim` como runtime:** incluye shell y `apt`; más superficie de ataque sin beneficio para este servicio.
* **Pulumi y CloudFormation:** ver sección 6.
* **Bloqueo del estado con DynamoDB:** funciona, pero suma un recurso que operar; el bloqueo nativo de S3 lo reemplaza.
* **Solo Docker Compose:** útil para el desarrollo con dependencias reales (checklist #10), pero no valida manifiestos, probes ni HPA.

## Criterios de revisión

Este ADR debe reabrirse si ocurre alguno de estos casos:

1. El arranque de pods en Fargate impide absorber los picos de originación y el p95 de aceptación de solicitudes se degrada.
2. El costo de EKS más Fargate supera lo razonable para el MVP y ECS resulta suficiente.
3. El equipo no logra sostener la operación de Kubernetes sin un SRE.
4. Se requiere un servicio que Fargate no soporta (DaemonSets, privilegios o hardware específico).

## Acciones derivadas

* Publicar la imagen en GHCR y reemplazar el digest de `k8s/deployment.yaml` (hoy tiene 61 caracteres hex en lugar de 64 y apunta a un usuario que no es el del repositorio).
* Organizar `k8s/` en base y *overlays* (`local` con `nginx`, `aws` con `alb`) y cambiar `commonLabels`, obsoleto, por `labels`.
* Completar el README: fila S07 en "Documentación por sesión", requisitos de Terraform, y captura de `kubectl get all -n crediscore`.
* Probar el HPA con carga sintética y adjuntar la evidencia (`kubectl top`, número de réplicas).
* Enmendar el ADR 0003 (orquestador: de ECS a EKS con Fargate) y eliminar `terraform/override.tf`, que está vacío.
