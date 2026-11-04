# STRIDE ligero — CrediScore

Equipo lospapus · Versión 1.0 · 4 de noviembre de 2026

STRIDE aplicado al microservicio **Scoring Engine** (`scoring-api`) de CrediScore: 17 amenazas en las 6 categorías, 9 de prioridad alta y 6 brechas abiertas en el código y la configuración de hoy. Está contrastado con `src/main.py`, `k8s/`, `ci.yml`, `api/openapi.yaml` y los ADR 0002–0006.

## 1. Alcance

- **Microservicio:** Scoring Engine (`scoring-api`), que implementa HU2 (scoring automático) y HU5 (API partner idempotente). Es el único servicio con código en el repo y el que carga con el p95 < 60 s.
- **Dos fuentes:** lo implementado (`src/main.py`, `Dockerfile`, `k8s/`, `ci.yml`) y lo diseñado (ADR, contrato OpenAPI, catálogo de eventos). Hoy el servicio es un placeholder: estado en memoria, regla fija en vez del modelo, sin Aurora ni Kafka.
- **Columna "Estado hoy":** *Brecha* = no cubierto hoy; *Parcial* = existe una parte; *Diseñado* = decidido en un ADR o en el contrato, sin código todavía.
- **Fuera de alcance:** el interior de Onboarding, Antifraude y Compliance, el API Gateway y la configuración de Aurora y MSK.
- **Método:** una pasada STRIDE por categoría, prioridad Alta o Media, sin puntuación numérica; se revisa en cada release mayor.

## 2. Activos, flujo y límites de confianza

**Activos:** RUT y datos financieros del solicitante (`monthly_income`, `existing_debt`); score y decisión; modelo de ML y su `model_version`; claves de idempotencia; registro de auditoría; credenciales (cliente OAuth2, `DATABASE_URL`, `GITOPS_TOKEN`).

**Flujo de datos:**

1. Un partner o canal propio llama a `https://api.crediscore.cl/v1` con OAuth2 client credentials (mTLS en producción, según el contrato).
2. `POST /v1/credit-applications` con `Idempotency-Key` llega a `scoring-api` (3 réplicas en EKS sobre Fargate).
3. El servicio consume `applicant.kyc_verified` y `financial_profile.captured`, y coordina `fraud_check.requested` y `fraud_check.completed` con Antifraude.
4. Calcula el score (hoy una regla fija; después el modelo cargado desde S3) y decide.
5. Guarda solicitud, `ScoringResult` y `DecisionRecord` en Aurora junto con el outbox.
6. El relay publica `credit_decision.*` en MSK, el webhook avisa al partner y el analista re-evalúa desde el backoffice con JWT.

**Límites de confianza:**

- TB1: Internet → API Gateway / Ingress
- TB2: Gateway → `scoring-api` (namespace `crediscore`)
- TB3: `scoring-api` ↔ Aurora y S3 (modelo)
- TB4: `scoring-api` ↔ MSK (eventos)
- TB5: backoffice (analista) → servicio
- TB6: CI/CD → repo GitOps → clúster

## 3. Amenazas STRIDE y mitigaciones

Prioridad: A = alta, M = media.

| ID | Categoría | Amenaza | Mitigación | Estado hoy | Prio. |
| --- | --- | --- | --- | --- | --- |
| S1 | Spoofing | Un cliente sin credenciales, o con un token vencido o de otro partner, llama a `/v1/credit-applications`. Hoy `src/main.py` no valida el token OAuth2 y el Ingress no exige mTLS. | Validar el JWT en el servicio o en el authorizer del API Gateway (firma, `exp`, `aud`) y exigir el scope por endpoint (`applications:write` para POST, `applications:read` para GET); mTLS en producción como dice el contrato; NetworkPolicy para que solo el gateway llegue al pod. | Brecha | A |
| S2 | Spoofing | Un productor falso publica `applicant.kyc_verified`, `financial_profile.captured` o `fraud_check.completed` y fuerza una decisión sobre una solicitud sin KYC real. | Autenticación IAM de MSK por servicio y ACL por tópico, validación de esquema y `event_version`, descartar eventos cuyo `aggregate_id` no existe. | Diseñado | A |
| T1 | Tampering | Reintentos o replay duplican solicitudes: la idempotencia vive en un diccionario en memoria por réplica y hay 3 réplicas, así que un reintento que cae en otra réplica crea una segunda solicitud. | Guardar la `Idempotency-Key` y el hash del cuerpo en Aurora, en la misma transacción que la solicitud, con restricción UNIQUE y expiración (por ejemplo 24 h). Mantener el 409 cuando la clave llega con otro cuerpo. | Brecha | A |
| T2 | Tampering | Se altera una decisión o su registro de auditoría en Aurora, OpenSearch o S3. | Outbox en la misma transacción, Compliance con Event Sourcing y archivo en S3 con Object Lock; la cuenta de Scoring no tiene permisos sobre el archivo de auditoría. | Diseñado | A |
| T3 | Tampering | Se reemplaza o envenena el modelo que se carga desde S3, o se despliega una versión sin aprobación. | Bucket versionado, hash del modelo verificado al cargar, promoción por PR con revisión y `model_version` guardado en cada `ScoringResult`. Hoy `MODEL_VERSION` es un placeholder. | Diseñado | A |
| T4 | Tampering | Se compromete lo que se despliega: el PAT `GITOPS_TOKEN` o la imagen publicada en GHCR. | Mantener imagen por SHA con provenance y promoción a prod por PR; limitar el PAT al repo GitOps con permisos mínimos y expiración; firmar la imagen (cosign) y verificarla al desplegar; subir el gate de Trivy de CRITICAL a HIGH y CRITICAL. | Parcial | M |
| R1 | Repudiation | Un analista niega haber aprobado o revocado una decisión. | `ManualReview` ya guarda `analyst_id`, `outcome` y `notes`; hacer `notes` obligatorio y publicar `manual_review.completed` a Compliance. | Diseñado | M |
| R2 | Repudiation | No se puede reconstruir ante la CMF por qué se aprobó o rechazó un crédito. | Cada decisión ya lleva `model_version`, `reasons` y `trace_id`; agregar el snapshot del `FinancialProfile` usado y la versión de reglas, y definir la retención con Compliance. | Parcial | A |
| R3 | Repudiation | Un cliente falsifica registros de log: el servicio toma `X-Trace-Id` del request y lo escribe en un formato JSON armado a mano, sin escapar. | Generar el `trace_id` en el servidor o aceptar solo hexadecimal de largo fijo, y usar un formatter JSON real que escape los campos. | Brecha | M |
| I1 | Info disclosure | Cualquier token de lectura consulta cualquier solicitud: `GET /v1/credit-applications/{id}` y `/decision` no comprueban de quién es, y devuelven la solicitud (RUT, monto) y su decisión (score). | Asociar cada solicitud al `client_id` del token y filtrar por dueño (404 si no coincide); guardar solo `rut_hash` en Aurora, como define el DER, y enmascarar el RUT en las respuestas. | Brecha | A |
| I2 | Info disclosure | Los errores 422 devuelven `str(exc.errors())`, que incluye el valor recibido, por ejemplo el RUT. | Responder solo campo y motivo (`loc` y `msg`), nunca el valor; mantener el formato RFC 7807 y el `trace_id`. | Brecha | M |
| I3 | Info disclosure | Credenciales en git: `k8s/secret.yaml` trae `DATABASE_URL` con `CHANGE_ME` y el Deployment lo carga como opcional; en producción podría quedar un valor real por error. | External Secrets desde AWS Secrets Manager en stg y prod (ADR 0003 y 0006), rotación < 90 días y gitleaks con historial completo en CI. | Parcial | M |
| D1 | DoS | Ráfagas o abuso saturan el servicio y rompen el p95 < 60 s. | Rate limit por partner en API Gateway (el contrato ya define 429 y `Retry-After`); HPA, PDB y límite de cuerpo de 1 MB en el Ingress, que ya existen. | Parcial | M |
| D2 | DoS | `APPLICATIONS`, `DECISIONS` e `IDEMPOTENCY` crecen sin límite; con 256 Mi de memoria, repetir solicitudes con claves nuevas provoca OOMKill. | Pasar la persistencia a Aurora (ADR 0004), expirar las claves de idempotencia y poner cuota por cliente. | Brecha | A |
| D3 | DoS | El modelo, el buró o Kafka no responden y se pierden o retrasan decisiones y eventos. | Timeout de 5 s con envío a revisión manual (HU2), outbox para no perder eventos si Kafka cae, consumidores idempotentes por `event_id` y dead-letter queue. | Diseñado | M |
| E1 | Elevation | Un analista o un partner ejecuta acciones de otro rol, por ejemplo revocar una decisión (`credit_decision.revoked`). | Roles separados (OAuth2 para partners, JWT de analista para el backoffice), scopes por endpoint y doble aprobación para revocar o sobrescribir. | Diseñado | A |
| E2 | Elevation | Un contenedor comprometido se mueve por la red o usa permisos amplios de AWS. | Ya cumple Pod Security *restricted* (no root, FS de solo lectura, sin capabilities, sin token de ServiceAccount, imagen distroless). Falta una NetworkPolicy default-deny con egress solo a Aurora y MSK, y un rol IAM por ServiceAccount con permisos mínimos. | Parcial | M |

## 4. Qué ya está cubierto y qué cerrar primero

**Ya cubierto en el repo:** validación estricta de entrada (`extra="forbid"`, formato de RUT, límites de monto y plazo), 409 ante una `Idempotency-Key` con otro cuerpo, errores RFC 7807 con `trace_id`, pod endurecido, imágenes por SHA con provenance y SBOM adjuntos, promoción a prod por PR, y en CI ruff, bandit, pip-audit, Trivy y cobertura ≥ 70 %.

**Brechas a cerrar primero, en este orden:**

1. Validar JWT, scopes y dueño de la solicitud en `src/main.py` (S1, I1).
2. Mover idempotencia y estado a Aurora, con expiración de claves (T1, D2).
3. Sanear `trace_id` y los errores 422 (R3, I2).
4. Agregar NetworkPolicy default-deny y rol IAM por ServiceAccount (E2).
5. Completar el pipeline del taller: gitleaks con historial, Semgrep con reglas propias, `sbom.json` CycloneDX como artefacto del run y Trivy en HIGH y CRITICAL (I3, T4).

## 5. Revisión y pendientes

- Asignar un responsable por cada brecha; por rol del charter, DevSecOps para pipeline y plataforma, Tech Lead para autenticación y los dos AI / Data Engineer para el modelo (T3, R2).
- Releer las filas "Diseñado" cuando Aurora y Kafka entren al código, porque pasan a Parcial o a Brecha según lo que se implemente.
- Revisar este documento en cada release mayor.
