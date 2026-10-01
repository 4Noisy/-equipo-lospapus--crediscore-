# Checklist 12-Factor — CrediScore

Auditoría del diseño ([C4 L2](c4/l2-container.png), [ADR 0003](adr/0003-cloud-style.md)) contra los 12 factores. El repositorio todavía no tiene código, así que **Cumple** significa que el diseño ya lo resuelve y **No cumple** que hay una brecha con una acción asignada.

| # | Factor | Estado | Evidencia o brecha | Acción | Responsable |
| :-: | :--- | :--- | :--- | :--- | :--- |
| 01 | Codebase | No cumple | El repo solo tiene documentación; los 4 servicios compartirán un monorepo. | Un directorio por servicio (`services/<servicio>/`) con build y pipeline propios. Prohibido copiar código entre servicios: lo compartido son los contratos (`api/`, catálogo de eventos). | Tech Lead |
| 02 | Dependencies | No cumple | No hay manifiestos de dependencias. | `pyproject.toml` + lockfile por servicio, `package-lock.json` en los frontends e imágenes Docker sin librerías instaladas a mano. | DevSecOps |
| 03 | Config | Cumple | Toda la configuración entra por variables de entorno (`DATABASE_URL`, `KAFKA_BOOTSTRAP_SERVERS`, `REDIS_URL`, `KYC_API_URL`, `BUREAU_API_URL`, `MODEL_URI`); los secretos viven en AWS Secrets Manager. | Publicar `.env.example` por servicio; `.env` ya está en `.gitignore`. | DevSecOps |
| 04 | Backing services | Cumple | PostgreSQL, Kafka, Redis, S3, KYC y bureau se adjuntan por URL; cambiar de proveedor no exige recompilar. | Acceder a KYC y bureau detrás de una interfaz (Ports & Adapters) para poder simularlos. | Tech Lead |
| 05 | Build, release, run | No cumple | No existe pipeline. | GitHub Actions construye una imagen por commit (tag = SHA) y la publica en ECR; release = imagen + configuración del ambiente; nunca se edita en ejecución. Se implementa en S08. | DevSecOps |
| 06 | Processes | Cumple | Los servicios no guardan estado: solicitudes y claves de idempotencia en PostgreSQL, contadores de fraude en Redis, modelo de ML de solo lectura. | Prohibir sesiones en memoria en la revisión de PR. | Tech Lead |
| 07 | Port binding | Cumple | Cada servicio expone HTTP con uvicorn en `$PORT`; no depende de un servidor de aplicaciones externo. | — | Tech Lead |
| 08 | Concurrency | Cumple | Tres tipos de proceso por servicio (`web`, `consumer`, `outbox-relay`) que escalan por réplicas; el consumo se reparte con particiones y *consumer groups* de Kafka. | Definir HPA por tipo de proceso en S07. | DevSecOps |
| 09 | Disposability | No cumple | El Scoring Service carga el modelo de ML al arrancar, lo que alarga el inicio. | *Readiness probe* que solo pasa con el modelo cargado; al recibir SIGTERM se deja de consumir, se confirman offsets y se termina en < 30 s. Medir el arranque y fijar un máximo de 20 s. | AI/Data |
| 10 | Dev/prod parity | No cumple | No hay ambiente de desarrollo definido. | `docker-compose` con PostgreSQL 16, Kafka y Redis en las mismas versiones mayores que producción, LocalStack para S3 y Prism para simular KYC y bureau. Prohibido SQLite. | QA |
| 11 | Logs | Cumple | Logs JSON a stdout con `trace_id` y `application_id`, recolectados por CloudWatch. | Enmascarar el RUT y no registrar datos personales; añadir una prueba que falle si aparece un RUT en los logs. | QA |
| 12 | Admin processes | No cumple | No hay mecanismo de migraciones ni tareas puntuales. | Migraciones con Alembic como *Job* de Kubernetes desde la misma imagen; el control normativo diario (HU4) y el reentrenamiento como *CronJob*. Nada por SSH. | DevSecOps |

## Resumen

* **Cumple:** 6 de 12 (03, 04, 06, 07, 08, 11).
* **No cumple:** 6 de 12 (01, 02, 05, 09, 10, 12); todos tienen acción y responsable.
* **No aplica:** ninguno.

Los factores 01, 02, 05, 10 y 12 se cierran al crear el esqueleto de servicios y el pipeline (S07 y S08). El 09 depende del tamaño del modelo y se verifica con una medición, no con una revisión de diseño.
