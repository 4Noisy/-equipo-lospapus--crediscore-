# Evidencia S10 — DevSecOps II (cadena de suministro)

La decisión está en el [ADR 0007](../adr/0007-supply-chain.md). Cada pieza entró por su propio PR.

## Rúbrica

| Criterio | Pts | Evidencia | Estado |
| :--- | :-: | :--- | :-: |
| DAST integrado en el pipeline | 15 | Job `dast (zap)` en [`security.yml`](../../.github/workflows/security.yml), PR [#27](https://github.com/4Noisy/-equipo-lospapus--crediscore-/pull/27). [Run](https://github.com/4Noisy/-equipo-lospapus--crediscore-/actions/runs/43342238389): 38 URLs, 120 reglas OK, 0 alertas. | ✅ |
| IaC scan + container scan bloqueantes | 20 | Jobs `iac (checkov)` ([#25](https://github.com/4Noisy/-equipo-lospapus--crediscore-/pull/25), [run](https://github.com/4Noisy/-equipo-lospapus--crediscore-/actions/runs/43342228731)) y `container-scan (trivy image)` ([#26](https://github.com/4Noisy/-equipo-lospapus--crediscore-/pull/26), [run](https://github.com/4Noisy/-equipo-lospapus--crediscore-/actions/runs/43342301227)). | ✅ |
| Firma Cosign + verify OK | 20 | Job `sign-and-attest` en [`ci.yml`](../../.github/workflows/ci.yml), PR [#28](https://github.com/4Noisy/-equipo-lospapus--crediscore-/pull/28). [Run de `main`](https://github.com/4Noisy/-equipo-lospapus--crediscore-/actions/runs/43344834186) (commit `60d617b`): `cosign verify` OK con identidad `ci.yml@refs/heads/main`. | ✅ |
| Attestation SLSA nivel 2 | 20 | Mismo run: `cosign attest --type slsaprovenance` y `cosign verify-attestation` OK (`predicateType: https://slsa.dev/provenance/v0.2`, builder = `ci.yml@refs/heads/main`). | ✅ |
| Policy de admisión + reglas Falco | 20 | [`require-signature.yaml`](../../k8s/policies/require-signature.yaml) y [`rules-custom.yaml`](../../falco/rules-custom.yaml), PR [#29](https://github.com/4Noisy/-equipo-lospapus--crediscore-/pull/29). Probado en [`supply-chain.yml`](../../.github/workflows/supply-chain.yml), ver abajo. | ✅ |

## Pruebas negativas (cada control bloqueó algo real)

| Qué metimos a propósito | Quién lo atrapó | Resultado |
| :--- | :--- | :--- |
| `hostNetwork: true` en el Deployment | Checkov | `CKV_K8S_19` FAILED, exit 1 |
| Imagen base distroless debian12 (sin parches desde abril de 2026) | Trivy | [45 CVE HIGH](https://github.com/4Noisy/-equipo-lospapus--crediscore-/actions/runs/43341298399), PR bloqueado. Arreglo: base debian13 + Python 3.13 |
| API sin header `Cross-Origin-Resource-Policy` | OWASP ZAP | [Alerta 90004](https://github.com/4Noisy/-equipo-lospapus--crediscore-/actions/runs/43341816550), PR bloqueado. Arreglo: headers de seguridad |
| Imagen de `main` aún sin firmar | Kyverno | [Rechazada](https://github.com/4Noisy/-equipo-lospapus--crediscore-/actions/runs/43342353629): `no signatures found` |
| Shell, escritura y conexión saliente dentro del contenedor | Falco | [3 alertas](https://github.com/4Noisy/-equipo-lospapus--crediscore-/actions/runs/43342353629) (job `runtime (falco)`) |

## Admisión con imagen firmada

[Run](https://github.com/4Noisy/-equipo-lospapus--crediscore-/actions/runs/43345410028) en un cluster kind con Kyverno y la policy, usando la imagen que firmó el CI de `main`:

```
pod/firmada created
ghcr.io/4noisy/scoring-api:60d617bb7d161e075a88ff46f7b094365372dc88@sha256:bd3d8a4a9d0ef81537a73f8fc25007f901286d9b7d3d691ee38a724a607b87ab
Error from server: admission webhook "mutate.kyverno.svc-fail" denied the request   <- imagen sin firma de la S08
```

Kyverno admitió la imagen firmada (y la fijó por digest) y rechazó la sin firma. `supply-chain.yml` repite esta prueba después de cada CI verde en `main`.

## Cómo verificar una imagen a mano

```bash
cosign verify \
  --certificate-identity "https://github.com/4Noisy/-equipo-lospapus--crediscore-/.github/workflows/ci.yml@refs/heads/main" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  ghcr.io/4noisy/scoring-api@sha256:<digest>
```
