# ADR 0001: Elección de Iniciativa — CrediScore

* **Fecha:** 2026-03-23
* **Autores:** Benjamín Garrido, Abdiel Ortiz, Emilio Santibáñez, Martin Jara, Justin Navarro
* **Estado:** Aceptado

## Contexto
El taller requiere seleccionar una iniciativa de desarrollo de software para el semestre. Se evaluaron las opciones disponibles considerando la complejidad técnica, el valor formativo en arquitectura de sistemas distribuidos, la integración de Machine Learning y el impacto en ingeniería de software aplicada.

## Decisión
Hemos decidido de forma unánime seleccionar la iniciativa **CrediScore (Scoring crediticio y detección de fraude)**.

## Justificación
1. **Desafío arquitectónico de alto rendimiento:** Requiere implementar patrones reactivos y arquitecturas orientadas a eventos (*event-driven*) para cumplir con restricciones críticas de latencia extrema (< 60s p95 para decisiones y propagación de eventos < 500 ms).
2. **Componente de ML y Datos Aplicado:** Permite integrar modelos supervisados de scoring y reglas de fraude en un flujo operativo real, enfrentando problemas contemporáneos como el *fairness* algorítmico y mitigación de sesgos.
3. **Robustez e Idempotencia:** El requerimiento de procesar pagos y solicitudes sin duplicación exige aplicar patrones de diseño sólidos a nivel de persistencia y APIs públicas.
4. **Cumplimiento y Auditoría:** La integración de lineamientos CMF y Finanzas Abiertas aporta un contexto realista de ingeniería empresarial y trazabilidad.

## Consecuencias
* **Positivas:**
  * Experiencia práctica en arquitecturas de eventos, alta concurrencia y MLOps.
  * Dominio de estándares de trazabilidad y diseño de APIs robustas/versionadas.
* **Riesgos y mitigaciones:**
  * *Complejidad de latencia y consistencia:* Se mitigará priorizando un diseño desacoplado mediante colas/tópicos de mensajería y benchmarks continuos de rendimiento.
