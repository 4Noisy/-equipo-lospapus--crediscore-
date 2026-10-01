# ADR 0003: Estilo cloud y plataforma de despliegue

**Fecha:** 2026-10-01  
**Estado:** Aceptado  
**Relacionado con:** [ADR 0002](0002-estilo-arquitectonico.md) (estilo arquitectónico), [ADR 0004](0004-datos-y-eventos.md) (datos y eventos)

## Contexto
El ADR 0002 eligió microservicios orientados a eventos. Esa decisión tiene un costo que no quedó acotado: el equipo es de 6 personas, sin SRE dedicado, y el criterio del taller dice que con menos de 15 personas y un MVP lo adecuado es un monolito modular. Hay que decidir cómo se despliega en la nube sin que la operación se coma al equipo.

Fuerzas en juego:
* **Latencia:** alertas de fraude propagadas en < 500 ms y decisión de crédito en < 60 s p95.
* **Perfiles de carga distintos:** el camino de fraude es asíncrono y de ráfagas; el scoring es inferencia de ML y se vuelve a liberar con cada reentrenamiento.
* **Capacidad operacional:** un solo DevSecOps. Nadie puede operar un clúster de Kafka un sábado.
* **Curso:** las sesiones S07 y S08 trabajan con manifiestos de Kubernetes y GitOps.

## Decisión
Microservicios **acotados a 4 servicios desplegables** (Onboarding, Scoring, Fraud Detection, Compliance & Audit) sobre **AWS**, con **todo lo que no es núcleo del producto delegado a servicios gestionados**: Amazon EKS, API Gateway, RDS PostgreSQL, MSK Serverless, ElastiCache, S3, Cognito y Secrets Manager. La selección por contenedor está en [managed-services.md](../arch/managed-services.md).

Reglas que acotan el costo:
1. No se crea un quinto servicio sin un ADR nuevo.
2. Un solo monorepo y una sola instancia de RDS con un schema por servicio; ningún servicio lee el schema de otro.
3. Los servicios se comunican por eventos. La única llamada síncrona entre contenedores es la del API Gateway hacia cada servicio.

## Consecuencias

### Positivas
* El camino de fraude escala y falla de forma independiente al scoring (*bulkhead*).
* El Scoring Service se libera con cada modelo nuevo sin tocar onboarding ni auditoría.
* El equipo no opera brokers, bases de datos ni planos de control: se paga por ellos.
* Los manifiestos de S07 y el pipeline de S08 se aplican directamente sobre EKS.

### Negativas
* Costo fijo mensual mayor que el de un monolito en un solo contenedor (EKS, MSK y RDS cobran aunque no haya tráfico).
* Consistencia eventual entre servicios: una solicitud puede verse `received` mientras fraude y scoring aún no terminan.
* Depurar un flujo exige trazas distribuidas (`trace_id` en cada evento y cada log) desde el primer día.
* Acoplamiento a AWS. Se mitiga usando interfaces estándar: SQL, protocolo Kafka, API S3 y OIDC.

### Plan de repliegue
Si a la S12 el equipo no logra operar 4 servicios, Onboarding y Compliance & Audit se fusionan en un solo desplegable. Fraud Detection y Scoring se mantienen separados porque son los que justifican la decisión.

## Alternativas descartadas
* **Monolito modular en un solo contenedor:** es lo que recomienda el criterio de tamaño de equipo y sería más barato y simple. Se descarta porque obliga a escalar juntos el consumo de eventos de fraude y la inferencia de ML, y porque cada reentrenamiento redeplegaría todo el sistema. Es el plan de repliegue parcial descrito arriba.
* **Serverless (Lambda + API Gateway):** costo por uso y cero servidores. Se descarta por los *cold starts* al cargar el modelo de ML y porque no garantiza la propagación de fraude en < 500 ms.
* **ECS Fargate en vez de EKS:** menos operación que Kubernetes. Se descarta porque el curso usa manifiestos de Kubernetes, Helm y GitOps en S07 y S08; con ECS habría que mantener dos formas de desplegar.
* **Kafka autogestionado en EC2:** más barato en infraestructura. Se descarta por la regla del "sábado a las 3 PM": exige operar brokers, particiones y actualizaciones sin un SRE.
* **Azure o GCP:** equivalentes funcionales. Se elige AWS porque MSK Serverless ofrece el protocolo Kafka que el ADR 0002 ya asume, sin administrar brokers.
