# Runbook de scoring-api

Para el on-call. Cada procedimiento tiene comandos copiables y un criterio de "resuelto". Los procedimientos R1, R3 y R5 se ejecutaron en el game day ([game-day.md](game-day.md)).

**Antes de empezar:** abre un hilo en `#equipo-crediscore` con `INC-<fecha>-<n>`, anota la hora y quién eres. Si toca datos de clientes (RUT, montos), avisa al PO (Emilio Santibáñez), porque la Ley 21.719 puede exigir notificar a la Agencia de Protección de Datos.

## Diagnóstico de 2 minutos

```bash
kubectl -n crediscore get deploy,pods,hpa,pdb -o wide
kubectl -n crediscore rollout history deploy/scoring-api
kubectl -n crediscore logs deploy/scoring-api --since=10m | grep -E '"level":"(ERROR|WARNING)"' | tail -50
kubectl -n crediscore port-forward deploy/scoring-api 8080:8080 &
curl -s localhost:8080/metrics | grep -E 'status="5|circuit_state|guardrail|llm_calls'
python scripts/smoke_e2e.py http://localhost:8080      # flujo crítico: 9 pasos
```

Argo CD: `argocd app get scoring-api-prod` (Synced/Healthy y revisión desplegada).

---

## R1 · Originación con errores 5xx o caída {#r1}

**Alerta:** `OriginacionBurnRateRapido` / `Lento`.

1. ¿Pods caídos o reiniciando? `kubectl -n crediscore get pods` → si hay `CrashLoopBackOff` u `OOMKilled`: `kubectl -n crediscore describe pod <pod>` y logs con `--previous`.
2. ¿Coincide con un despliegue? `kubectl -n crediscore rollout history deploy/scoring-api`. Si sí, **rollback por Git** (no con `kubectl`, Argo CD lo revertiría):
   ```bash
   # en gitops-repo
   git revert <commit-del-promote> && git push      # prod: PR con 2 revisores, marcado como hotfix
   ```
   Solo si Argo CD no responde: `kubectl -n crediscore rollout undo deploy/scoring-api` y después alinear Git.
3. ¿Un Pod solo? Bórralo; el Deployment lo repone y el PDB mantiene 2 vivos. Medido: 3/3 réplicas de vuelta en el game day E3.
4. **Resuelto cuando:** `smoke_e2e.py` da 9/9 y `crediscore:originacion_error_ratio:rate5m` < 0,005 por 15 min.

## R2 · Latencia de aceptación alta {#r2}

1. `kubectl -n crediscore top pods` y `get hpa`: si el HPA está en `maxReplicas` (8), el techo de costo está frenando el escalado. Subirlo es una decisión de costo: avisa a FinOps (Martin Jara) y súbelo por PR en gitops-repo.
2. Si el CPU está bajo y la latencia alta, el cuello no es la app: revisa API Gateway y ALB en CloudWatch.
3. **Resuelto cuando:** p95 < 300 ms por 30 min.

## R3 · Proveedor LLM caído o circuit breaker abierto {#r3}

**Alerta:** `ExplicadorCircuitoAbierto`. **Impacto en el usuario: ninguno funcional.** Las explicaciones salen de la plantilla (probado en el game day E1: 0 errores, p95 3,5 ms).

1. Mira el estado del proveedor (status.anthropic.com) y `crediscore_llm_calls_total{result}`: `error` = red o timeout; `refusal` = el modelo rechazó.
2. No hagas nada en la app: el breaker prueba una llamada cada `EXPLAINER_CB_RESET_S` (30 s) y se cierra solo.
3. Si dura > 1 h o el costo se dispara: pasa a plantilla explícitamente, por PR en gitops-repo (`EXPLAINER_MODE: "template"` en el ConfigMap del overlay).
4. **Resuelto cuando:** `crediscore_circuit_state == 0` y la tasa de fallback vuelve a su base.

## R4 · Guardrail bloqueó PII o un atributo protegido {#r4}

**Alerta:** `GuardrailDatoSensible`. El texto **no** llegó al usuario (se sirvió la plantilla), pero el modelo se comportó mal.

1. Busca el caso: `kubectl -n crediscore logs deploy/scoring-api | grep "guardrail de salida"`.
2. Pasa a plantilla mientras se investiga (paso 3 de R3).
3. AI/Data reproduce el caso, lo agrega a `eval/redteam_outputs.jsonl` y ajusta prompt o guardrail; el CI corre la evaluación antes de volver a `llm`.
4. Post-mortem obligatorio (plantilla en [post-mortems](post-mortem-2026-11-22-circuit-breaker.md)).

## R5 · Desastre: namespace o clúster perdido {#r5}

Ver [plan de DR](dr-plan.md). Resumen ejecutable (lo hace el job E4 de [`gameday.yml`](../../.github/workflows/gameday.yml)):

```bash
# 1. Clúster nuevo o namespace borrado: Argo CD reconcilia desde gitops-repo.
argocd app sync scoring-api-prod            # o, sin Argo CD:  kubectl apply -k <overlay>
kubectl -n crediscore rollout status deploy/scoring-api --timeout=300s
# 2. Verificar
python scripts/smoke_e2e.py https://api.crediscore.cl
```

**Hoy se pierden las solicitudes en curso** (estado en memoria, ADR 0009). Al cerrar el incidente, el PO avisa a los partners para que reintenten con la misma `Idempotency-Key`.

## R6 · Rotar un secreto

| Secreto | Dónde vive | Quién lo rota | Cada cuánto |
| :--- | :--- | :--- | :--- |
| `GITOPS_TOKEN` (PAT fine-grained) | GitHub Actions secrets | DevSecOps | 90 días o si se filtra |
| `ANTHROPIC_API_KEY` | AWS Secrets Manager → ExternalSecret (prod) · GitHub secret (eval) | AI/Data | 90 días o si se filtra |
| `DATABASE_URL` | AWS Secrets Manager → ExternalSecret | DevSecOps | 30 días (rotación automática de RDS) |
| Firma de imágenes | No hay llave: Cosign keyless (ADR 0007) | — | — |

Si se filtró: **rotar primero** y después limpiar ([guía](../security/secret-scanning.md)). gitleaks bloquea el PR que lo intente subir.
