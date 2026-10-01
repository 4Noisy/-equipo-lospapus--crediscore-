# Checklist 12-Factor — CrediScore

Auditoría del diseño ([C4 L2](c4/l2-container.png)) contra los 12 factores, presentada en la S04. El repositorio todavía no tiene código: **Cumple** significa que el diseño ya lo resuelve y **No cumple** que hay una brecha con acción y responsable. Las decisiones de plataforma están en el [ADR 0003](adr/0003-cloud-style.md).

| # | Factor | Estado | Acción concreta | Responsable |
| :-: | :--- | :--- | :--- | :--- |
| 01 | Codebase | No cumple | Un repositorio por servicio, con pipeline de CI independiente. | Martin Jara |
| 02 | Dependencies | No cumple | Manifiesto de dependencias aislado e imagen Docker propia por servicio. | Benjamín Garrido |
| 03 | Config | No cumple | Variables de entorno + AWS Secrets Manager; sin archivos `config.*.json` en el repo. | Martin Jara |
| 04 | Backing services | Cumple | Formalizar base de datos, Event Bus y KYC como URL inyectada por variable de entorno. | Benjamín Garrido |
| 05 | Build, release, run | No cumple | CI/CD: build → imagen versionada en ECR → deploy. | Martin Jara |
| 06 | Processes | Cumple | Confirmar que los servicios son *stateless*: sesión vía JWT, sin estado local. | Abdiel Ortiz / Nelson Arevalo |
| 07 | Port binding | Cumple | Cada imagen expone su propio puerto, sin servidor de aplicaciones externo. | Benjamín Garrido |
| 08 | Concurrency | No cumple | Auto-scaling horizontal (ECS) en Scoring y Fraude. | Martin Jara |
| 09 | Disposability | No cumple | *Graceful shutdown* (SIGTERM < 30 s) en los microservicios. | Justin Navarro |
| 10 | Dev/prod parity | No cumple | Docker Compose local con PostgreSQL y Kafka reales. | Justin Navarro |
| 11 | Logs | No cumple | JSON a stdout, centralizado en CloudWatch / OpenSearch. | Martin Jara |
| 12 | Admin processes | No cumple | Migraciones (Flyway) como *Job* del mismo pipeline. | Martin Jara |

## Resumen

* **Cumple:** 3 de 12 (04, 06, 07).
* **No cumple:** 9 de 12; todos con acción y responsable.
* **No aplica:** ninguno.

## Brechas prioritarias antes de desplegar

1. **Build, release, run (05).** Sin pipeline las tres etapas se mezclan: no hay forma de garantizar que lo que se prueba es lo que se despliega.
2. **Concurrency (08).** Scoring y Fraude deben escalar horizontalmente de forma independiente para sostener la propagación de fraude en < 500 ms bajo carga.
3. **Disposability (09).** Un cierre no controlado puede perder eventos de fraude en vuelo y romper la idempotencia y la trazabilidad CMF.
4. **Logs (11).** Sin logs estructurados y centralizados no se puede auditar una decisión de crédito ante la CMF.
