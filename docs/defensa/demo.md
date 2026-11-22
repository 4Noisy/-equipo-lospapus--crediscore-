# Demo en vivo: preparación y fallback

## Ambiente

No tenemos una cuenta AWS con EKS: **staging es el clúster con Argo CD de la S08** (GitHub Codespace de `gitops-repo` levantado con `bash scripts/argocd-up.sh`, app `scoring-api-dev`, [evidencia](../s08/evidencia.md)), sincronizado desde `gitops-repo` con la imagen de `main`. Lo decimos así si el panel pregunta: la defensa corre sobre staging real del equipo, no sobre EKS.

```bash
# 30 min antes, en el Codespace de gitops-repo
bash scripts/argocd-up.sh                            # si el clúster no está arriba
argocd app get scoring-api-dev                      # Synced / Healthy, revisión = último commit de main
kubectl -n crediscore get pods                      # 3/3 Running
kubectl -n crediscore port-forward svc/scoring-api 8080:80 &
export STAGING=http://localhost:8080
python scripts/smoke_e2e.py $STAGING                # 9/9 OK antes de entrar
```

> Con 3 réplicas y `port-forward` al Service, todas las requests de la demo van a un mismo Pod, así que el paso 3 (reintento idempotente) se ve bien. Si el panel pregunta qué pasa entre réplicas: es la brecha del ADR 0009, y la mostramos sin esconderla.

## Fallback {#fallback}

| Si falla… | Hacemos esto | Y decimos |
| :--- | :--- | :--- |
| El clúster de staging no levanta | `python -m src.main` en la laptop y `smoke_e2e.py http://localhost:8080` | "Staging cayó; esta es la misma imagen de código en local. La causa la vemos en el Q&A" |
| Argo CD fuera de sincronía | `argocd app sync` y se muestra el diff | "Esto es GitOps: el estado deseado está en Git" |
| La red de la sala | Todo corre en local; no dependemos de Internet (modo `template`) | "Por eso el explicador no depende del LLM para responder" |
| Un paso del smoke en rojo | Se lee el error en voz alta, se muestra el test que cubre ese caso | Honestidad técnica: causa raíz y mitigación |

## Qué tener abierto

1. Terminal con letra grande (≥ 20 pt).
2. `api/examples/*.http` para mostrar requests individuales si el panel pide uno.
3. Navegador: repo en `main`, último run verde de CI, run de `gameday`, `eval/results/template.md`.
