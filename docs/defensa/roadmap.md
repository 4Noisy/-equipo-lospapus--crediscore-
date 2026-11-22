# Roadmap: qué sigue si esto fuera un producto real

Ordenado por valor por unidad de esfuerzo. La estimación es en semanas-persona del equipo actual.

| # | Qué | Por qué primero | Esfuerzo | Valor |
| :-: | :--- | :--- | :-: | :--- |
| 1 | **Aurora + outbox** en `scoring-api` | Cierra el riesgo técnico número 1: hoy se pierde el 100 % de las solicitudes si cae un Pod, y una lectura puede caer en otra réplica | 3 | Sin esto no se puede ir a producción. Sube el SLO posible de 99,5 % a 99,9 % |
| 2 | **Golden set con el LLM real** y activar `llm` solo para rechazos en staging | El explicador ya está construido, probado y con respaldo; falta la evidencia con el modelo real | 0,5 | Valida la feature IA y reemplaza tokens estimados por tokens medidos |
| 3 | **Red team externo** (otro equipo ataca el explicador a ciegas) | El 100 % de nuestro red team es optimista porque lo escribimos nosotros | 0,5 | Evidencia de seguridad independiente |
| 4 | **Decisión sobre MSK** con tráfico real | MSK es el 70 % del costo | 1 | Hasta −USD 1.400/mes |
| 5 | Modelo de scoring supervisado + monitoreo de drift y fairness con datos reales | Hoy el puntaje es una regla fija | 4 | El producto de verdad |
| 6 | Validar el token OAuth2 en la API (hoy solo en el diseño) | Brecha del threat model | 1 | Seguridad de la API pública |
| 7 | Asistente RAG sobre normativa CMF para analistas | Valor para el backoffice (HU4) | 3 | Productividad del analista |

**Si tuviéramos 2 semanas más:** filas 1 (parcial: el repositorio en Aurora, sin outbox) y 2. Es lo que más reduce riesgo por semana invertida.

**La feature que más valor entrega por unidad de esfuerzo:** la explicación con derecho a revisión humana. Son ~390 líneas de código (más ~280 de tests) que convierten un código como `AMOUNT_TOO_HIGH_FOR_TERM` en algo que la persona entiende, y cumplen una obligación legal que entra en vigencia en diciembre de 2026.

## Cómo medimos que el producto ayuda al usuario

| Métrica | Hoy | Meta | Cómo |
| :--- | :--- | :--- | :--- |
| Tiempo a decisión (p95) | 8 ms síncrono (medido) | < 60 s extremo a extremo | SLO 3 |
| Solicitudes de revisión humana tras un rechazo | sin datos | < 15 % | Si sube, la explicación no convence o el modelo se equivoca |
| Reclamos por discriminación | sin datos | 0 | Atributos fuera del modelo + regla 4/5 mensual |
| Solicitudes completadas / iniciadas | sin datos | > 70 % | Embudo del onboarding |
| Costo por solicitud | USD 0,082 (modelado) | < USD 0,10 | Cost Explorer por `cost-center` |

## Aprendizajes del semestre (uno por rol)

Cada persona dice el suyo en el bloque 07. Estos son borradores para ensayar; cada uno los reescribe en sus palabras.

- **PO:** priorizar por riesgo y no por features: la fila 1 del roadmap no se ve en la demo y es la más importante.
- **Tech Lead:** un ADR con alternativas descartadas vale más que un diagrama bonito; el panel pregunta "por qué no X".
- **DevSecOps:** cada control tiene que haber bloqueado algo real al menos una vez, si no, no sabemos si funciona.
- **AI/Data:** el LLM es la parte fácil; lo difícil es decidir qué no le dejamos hacer y probarlo.
- **AI/Data:** fairness no es una métrica, son cuatro capas: diseño, resultado, explicación y trazabilidad.
- **QA:** los tests unitarios pasaban y el circuit breaker tenía un bug. El game day lo encontró en el primer intento.
