# Servicios gestionados por contenedor

Selección en AWS para cada contenedor del [C4 L2](../c4/l2-container.png), según el marco de decisión de la S04: se construye solo lo que diferencia al producto (scoring, reglas de fraude, auditoría) y se delega lo demás. La justificación del estilo está en el [ADR 0003](../adr/0003-cloud-style.md).

| Contenedor | Servicio gestionado | Por qué | Alternativa descartada |
| :--- | :--- | :--- | :--- |
| Web App, Backoffice Web | **Amazon S3 + CloudFront** | Son SPA estáticas: no necesitan servidores y el CDN acerca el contenido al usuario. | Servir los estáticos desde un contenedor: más costo y nada a cambio. |
| API Gateway | **Amazon API Gateway (HTTP API)** | Valida JWT, limita 100 req/min por partner y versiona `/v1` sin código propio. | Kong o Envoy en EKS: hay que operarlos y actualizarlos. |
| Autenticación | **Amazon Cognito** | Emite tokens OAuth2 *client credentials* para partners y sesiones para analistas. La autenticación no diferencia al producto. | Keycloak autogestionado: otro servicio con estado que mantener. |
| Onboarding, Scoring, Fraud Detection, Compliance & Audit | **Amazon EKS** (nodos gestionados) | AWS opera el plano de control; el equipo solo mantiene manifiestos, que son los mismos de S07 y S08. | ECS Fargate: más simple, pero incompatible con el flujo Kubernetes del curso. |
| PostgreSQL | **Amazon RDS for PostgreSQL 16** (Multi-AZ) | Backups, parches y failover automáticos. Una instancia con un schema por servicio. | Aurora: el volumen del MVP no justifica su costo. |
| Event Bus | **Amazon MSK Serverless** | Protocolo Kafka sin administrar brokers ni capacidad; conserva el *replay* que pide la auditoría. | SNS + SQS: menos operación, pero sin *replay* ni orden por clave. |
| Redis | **Amazon ElastiCache for Redis** | Contadores de velocidad con TTL y listas negras con lectura en milisegundos. | DynamoDB: sirve, pero los contadores con ventana son más simples en Redis. |
| Object Storage | **Amazon S3 con Object Lock** | Modo *compliance*: ni el administrador puede borrar el archivo de auditoría durante la retención. Guarda también los modelos versionados. | Guardar el archivo en PostgreSQL: un `DELETE` con permisos suficientes lo destruye. |
| Secretos | **AWS Secrets Manager** | Rotación automática de credenciales de RDS y de las llaves de KYC y bureau. | Variables en el repositorio: viola el factor 03. |
| Logs, métricas y trazas | **Amazon CloudWatch + AWS Distro for OpenTelemetry** | Recolecta stdout y propaga el `trace_id` entre servicios y eventos. | Stack Prometheus/Grafana/Loki propio: se evalúa en S11. |
| Imágenes | **Amazon ECR** | Registro privado con escaneo de vulnerabilidades. | Docker Hub: límites de descarga y sin escaneo integrado. |

## Lo que sí construye el equipo

* **Modelo y servicio de scoring:** variables, entrenamiento, métricas de fairness y explicabilidad.
* **Reglas y modelo de fraude.**
* **Log de auditoría y flujo de re-evaluación humana.**
* **Contrato de la API pública** ([api/openapi.yaml](../../api/openapi.yaml)).

## Riesgos de costo

MSK Serverless, EKS y RDS Multi-AZ tienen costo fijo aunque no haya tráfico. En el ambiente de desarrollo se reemplazan por contenedores locales (ver factor 10 del [checklist 12-Factor](../12-factor-checklist.md)). El costo real se mide en S15 (FinOps).
