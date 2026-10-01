# ADR 0003: Estilo cloud y servicios gestionados

**Fecha:** 2026-09-09 (decisión presentada en la S04; documentada en el repositorio el 2026-10-01)  
**Estado:** Aceptado  
**Relacionado con:** [ADR 0002](0002-estilo-arquitectonico.md), [checklist 12-Factor](../12-factor-checklist.md), [servicios gestionados](../arch/managed-services.md)

## Contexto
El ADR 0002 definió microservicios orientados a eventos. Falta fijar tres decisiones para poder desplegar:

1. El proveedor cloud tentativo (AWS, Azure o GCP).
2. El estilo de despliegue: monolito modular, microservicios en contenedores, serverless o un modelo híbrido.
3. Qué *backing services* opera el equipo y cuáles se delegan al proveedor.

Restricciones que condicionan la decisión: decisión de crédito en < 60 s p95, propagación de fraude en < 500 ms, idempotencia estricta, trazabilidad inmutable para auditorías CMF y un equipo de 6 personas sin SRE dedicado 24/7.

## Decisión

**Proveedor cloud tentativo: AWS.** Encaja con Apache Kafka (ADR 0002) a través de Amazon MSK y ofrece el ecosistema gestionado más maduro para arquitecturas de eventos.

**Estilo de despliegue: híbrido.**
* **Contenedores (AWS Fargate)** para Onboarding, Scoring y la validación síncrona de Fraude. No tienen *cold starts* y sostienen el p95 de 60 s.
* **Serverless (AWS Lambda)** para los consumidores asíncronos del Event Bus: notificaciones, reportes CMF por lotes y *feature engineering*.

**Backing services gestionados:**

| Necesidad | Servicio |
| :--- | :--- |
| Entrada de la API | Amazon API Gateway |
| Base relacional | Amazon Aurora PostgreSQL Serverless v2 |
| Event Bus | Amazon MSK Serverless |
| Configuración y secretos | AWS Secrets Manager |
| Logs | Amazon CloudWatch Logs + OpenSearch |
| Artefactos y modelos de ML | Amazon S3 |

El detalle por contenedor está en [managed-services.md](../arch/managed-services.md). Los motores de datos de cada contexto se deciden en el [ADR 0004](0004-datos-y-eventos.md).

## Consecuencias

### Positivas
* Cero gestión de servidores en Fargate, MSK y Aurora Serverless: el equipo se enfoca en scoring y fraude, no en infraestructura.
* Escalado elástico alineado a los atributos de latencia y a los picos de fraude.
* Costos variables (pago por uso), razonables para un MVP académico.
* Logs inmutables (CloudWatch + S3) y CloudTrail facilitan las auditorías CMF.

### Negativas
* *Vendor lock-in* parcial a AWS (MSK, Aurora); se mitiga con Ports & Adapters.
* *Cold start* de Lambda si se usa en el camino síncrono crítico; por eso se limita a consumidores asíncronos.
* Requiere gobierno de costos (FinOps) sobre MSK y Aurora cuando crezca el tráfico.
* Curva de aprendizaje del equipo en servicios gestionados de AWS.

## Alternativas descartadas
* **Monolito modular sobre EC2 o máquinas virtuales:** no permite escalar el motor de fraude de forma independiente del scoring; el escalado vertical no sostiene los picos de fraude.
* **100% serverless (Lambda + DynamoDB + SQS):** los *cold starts* ponen en riesgo el p95 del camino síncrono, y DynamoDB no encaja con el modelo relacional y transaccional del core de créditos.
* **Kubernetes autogestionado o Kafka en EC2:** regla del "sábado a las 3 PM"; el equipo no tiene un SRE dedicado para operar el clúster.
* **Multi-cloud desde el día 1:** complejidad injustificada para un MVP. Queda como evolución futura (recuperación ante desastres), mitigada por Ports & Adapters.
