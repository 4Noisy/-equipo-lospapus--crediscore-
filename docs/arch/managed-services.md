# Servicios gestionados por contenedor

Selección en AWS para los contenedores del [C4 L2](../c4/l2-container.png). Criterio base, del [ADR 0003](../adr/0003-cloud-style.md): lo que diferencia al producto se construye; si existe un servicio gestionado maduro, se usa; sin SRE dedicado, la operación se delega.

## Elegidos en la S04 (ADR 0003)

| Contenedor L2 | Servicio AWS | Criterio de elección |
| :--- | :--- | :--- |
| API Gateway | **Amazon API Gateway** | Servicio maduro: centraliza autenticación, *rate limiting* y versionado sin construirlo. |
| Onboarding / Scoring / Fraud Microservices | **AWS Fargate (ECS)** | El diferenciador es el modelo y las reglas, no el cómputo: se delega la operación de contenedores. |
| Consumidores asíncronos del Event Bus | **AWS Lambda** | Notificaciones, reportes CMF por lotes y *feature engineering*; fuera del camino síncrono. |
| Core relations DB | **Aurora PostgreSQL Serverless v2** | Motor relacional con auto-scaling; ACID nativo para la idempotencia de las transacciones de crédito. |
| Event Bus | **Amazon MSK Serverless** | Kafka ya elegido en el ADR 0002; MSK delega la operación del clúster. |
| Configuración y logs | **Secrets Manager + CloudWatch Logs** | Resuelven el factor 03 (Config) y el factor 11 (Logs) sin construir nada propio. |
| Imágenes | **Amazon ECR** | Registro de las imágenes versionadas del factor 05. |

## Motores agregados en la S06 (ADR 0004)

| Contenedor L2 | Motor | Uso |
| :--- | :--- | :--- |
| Proyección de lectura | **OpenSearch** | Lado de lectura de CQRS para el dashboard de analistas de riesgo; búsqueda en Cumplimiento. |
| Redis | **Redis** | Sesión y OTP en Onboarding; contadores de velocidad en Antifraude; cola de solicitudes pendientes para analista y oficial. |
| Base de grafos | **Neo4j / Neptune** | Red de señales de riesgo de Antifraude. |
| Archivo de auditoría | **S3 + CloudWatch Logs** | Archivo inmutable: trazabilidad para la CMF. |
