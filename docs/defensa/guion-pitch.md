# Guion de defensa · 15 minutos

Estructura obligatoria de la S18, un rol por bloque. **No se leen las slides:** cada bloque tiene 3 ideas y 1 evidencia que se abre en vivo desde el repo. Los tiempos son acumulados para el cronómetro.

> Reparto propuesto según los roles del [CHARTER](../../CHARTER.md). El equipo lo confirma en el ensayo.

| # | Bloque | Quién | Tiempo | Reloj |
| :-: | :--- | :--- | :-: | :-: |
| 01 | Elevator pitch | Emilio (PO) | 1:00 | 0:00 → 1:00 |
| 02 | Demo en vivo | Justin (QA) | 3:00 | 1:00 → 4:00 |
| 03 | Arquitectura | Benjamín (Tech Lead) | 2:30 | 4:00 → 6:30 |
| 04 | DevSecOps | Martin (DevSecOps) | 2:00 | 6:30 → 8:30 |
| 05 | IA responsable | Abdiel (1:00) + Nelson (1:00) (AI/Data) | 2:00 | 8:30 → 10:30 |
| 06 | Resiliencia · FinOps | Justin (1:00) + Martin (1:00) | 2:00 | 10:30 → 12:30 |
| 07 | Roadmap y aprendizajes | Emilio + 1 frase de cada uno | 2:30 | 12:30 → 15:00 |

---

## 01 · Elevator pitch (Emilio · 1:00)

- **Problema:** una persona que pide un microcrédito espera días y, si le dicen que no, no sabe por qué.
- **Usuario:** solicitantes de microcrédito y los partners comerciales que originan por API.
- **Valor:** decisión en menos de 60 segundos, sin sesgo por género ni comuna, y una explicación que se entiende, con derecho a revisión humana.
- Cierre: "Lo que van a ver corre desde `main`, y cada número que digamos tiene un link en el repo".

## 02 · Demo en vivo (Justin · 3:00)

Contra staging (clúster con Argo CD de la S08, ver [demo.md](demo.md)). Terminal grande y `api/examples/` abierto.

| Seg. | Acción | Qué se dice |
| :-: | :--- | :--- |
| 0:00 | `python scripts/smoke_e2e.py $STAGING` | "Este script es el flujo crítico; lo corre el CI, el game day y ahora yo" |
| 0:20 | Paso 2 y 3: crear la solicitud y reintentarla | "Mismo `Idempotency-Key`: misma solicitud, `Idempotent-Replayed: true`. Un partner puede reintentar sin duplicar créditos" |
| 0:50 | Paso 4: misma clave, otro monto → 409 | "Y si alguien reusa la clave con otro cuerpo, se rechaza" |
| 1:10 | Paso 5: decisión | "Puntaje, motivo y versión del modelo: trazable para la CMF" |
| 1:40 | Paso 6: explicación | Leer el texto en voz alta. "Esto es lo que ve la persona, y termina con su derecho a revisión humana" |
| 2:10 | Paso 7: prompt injection en `partner_reference` | "Le pedimos al sistema que apruebe todo. Lo marcó y no tuvo efecto: ese texto nunca llega al modelo" |
| 2:30 | Paso 8: mandar `gender` → 422 | "El contrato no acepta atributos protegidos" |
| 2:45 | `curl $STAGING/metrics \| grep crediscore_http` | "Y todo queda medido: de aquí salen los SLOs" |

**Si algo falla:** se dice en voz alta, se muestra el fallback ([demo.md](demo.md#fallback)) y se explica la causa. Nada de videos pregrabados.

## 03 · Arquitectura (Benjamín · 2:30)

- **C4 en 3 niveles:** [L1](../c4/l1-context.png) → [L2](../c4/l2-container.png) → [L3 de scoring-api](../c4/l3-component-scoring-api.md). Mostrar el L3 y señalar el repositorio en memoria: "este es nuestro mayor riesgo, y lo decimos nosotros antes que ustedes".
- **Top 3 ADRs** (de 10 ADRs; 9 discuten alternativas descartadas):
  1. [ADR 0002](../adr/0002-estilo-arquitectonico.md) · event-driven: la decisión es asíncrona porque el fraude necesita < 500 ms y el scoring < 60 s; un flujo síncrono acopla los dos tiempos.
  2. [ADR 0008](../adr/0008-feature-ia-explicador.md) · **el LLM explica, no decide**: descartamos que el LLM tocara el puntaje porque no es reproducible ni auditable.
  3. [ADR 0009](../adr/0009-resiliencia-degradacion.md) · degradar con elegancia y aceptar el estado en memoria de forma explícita; descartamos sesiones pegajosas porque esconden el problema.
- **Simplicidad defendida:** el explicador vive en el mismo proceso, no en otro microservicio. "Podría ser más complejo y a propósito no lo es".

## 04 · DevSecOps (Martin · 2:00)

Abrir el último run verde de `main` en Actions y recorrerlo de izquierda a derecha:

- **SAST** Semgrep (reglas propias con tests) · **SCA** Trivy + SBOM CycloneDX · **secretos** gitleaks · **IaC** Checkov · **container scan** Trivy · **DAST** OWASP ZAP. Todos bloqueantes ([security.yml](../../.github/workflows/security.yml)).
- **Firma Cosign keyless + SLSA nivel 2**, y Kyverno rechaza en el clúster cualquier imagen no firmada por el CI de `main` ([ADR 0007](../adr/0007-supply-chain.md)). Falco vigila shell, escritura y conexiones salientes.
- **Secretos:** ninguno en el repo. Mostrar el runbook R6: dónde vive cada uno y quién lo rota.
- Evidencia negativa: "cada control bloqueó algo real" ([tabla de la S10](../s10/evidencia.md#pruebas-negativas-cada-control-bloqueó-algo-real)).

## 05 · IA responsable (Abdiel + Nelson · 2:00)

**Abdiel (1:00): la feature y los guardrails**
- El LLM redacta la explicación de una decisión ya tomada. No ve el RUT ni texto libre.
- 8 guardrails de salida; si uno falla, sale la plantilla. Mostrar `test_salida_manipulada_del_llm_cae_a_plantilla`.
- Marco legal: Ley 21.719 art. 8 bis (decisiones automatizadas), Ley 20.609, Ley Fintec ([model card §6](../ia/model-card.md#6-marco-legal-citado)).

**Nelson (1:00): evaluación y fairness**
- Golden set de 26 casos, red team de 24 salidas, 26 intentos de injection: todo corre en el CI y bloquea el merge ([reporte](../../eval/results/template.md)).
- Fairness: disparate impact 0,989 por género y 0,959 por zona (regla 4/5), en población **sintética**.
- **Lo que no hicimos:** el golden set con el LLM real (no tenemos API key cargada) y un red team externo. Decirlo así.

## 06 · Resiliencia · FinOps (Justin + Martin · 2:00)

**Justin (1:00): resiliencia**
- SLOs: 99,5 % de originación, p95 < 300 ms ([SLOs](../resiliencia/slos.md)).
- Game day: con el LLM caído, 0 errores. **Encontramos 2 bugs** en nuestro circuit breaker y los arreglamos ([post-mortem](../resiliencia/post-mortem-2026-11-22-circuit-breaker.md)).
- Caída del proceso: vuelve en 1,25 s, **pero se pierden las 20 solicitudes**. Es nuestra brecha número 1.

**Martin (1:00): FinOps**
- ≈ USD 2.473/mes, USD 0,082 por solicitud ([costos](../finops/costos.md)).
- Palanca 1: −87 % de llamadas al LLM. Palanca 2: right-sizing con la capacidad medida, −21 % del techo.
- Hallazgo: **MSK es el 70 % del costo**. No lo cambiamos sin datos de tráfico.

## 07 · Roadmap y aprendizajes (Emilio + todos · 2:30)

- Emilio (1:30): las 3 filas de arriba del [roadmap](roadmap.md) y el break-even (~2.100 solicitudes/mes con equipo incluido, con supuestos).
- Una frase de cada uno (10 s c/u): la lección del semestre desde su rol. Ensayarlas: nada de frases genéricas.
- Cierre (Emilio): "Lo que no alcanzamos está escrito en el repo con su porqué. Preguntas".

---

## Ensayo (checklist)

- [ ] Dos ensayos completos con cronómetro: ninguno pasa de 14:30.
- [ ] Cada persona puede explicar el bloque del lado (Q&A por rol).
- [ ] Staging arriba 30 min antes; `smoke_e2e.py` en verde; fallback probado.
- [ ] Pestañas abiertas: repo en `main`, último run de CI, `gameday`, model card, costos.
- [ ] `main` con este PR mergeado: **no hay reprise**.
