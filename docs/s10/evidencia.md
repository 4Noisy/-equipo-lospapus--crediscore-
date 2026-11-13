# Evidencia S10 — DevSecOps II (cadena de suministro)

La decisión está en el [ADR 0007](../adr/0007-supply-chain.md). Cada pieza entró por su propio PR.

## Rúbrica

| Criterio | Pts | Evidencia | Estado |
| :--- | :-: | :--- | :-: |
| DAST integrado en el pipeline | 15 | Job `dast (zap)` en [`security.yml`](../../.github/workflows/security.yml), PR [#27](https://github.com/4Noisy/-equipo-lospapus--crediscore-/pull/27). [Run](https://github.com/4Noisy/-equipo-lospapus--crediscore-/actions/runs/43342238389): 38 URLs, 120 reglas OK, 0 alertas. | ✅ |
| IaC scan + container scan bloqueantes | 20 | Jobs `iac (checkov)` ([#25](https://github.com/4Noisy/-equipo-lospapus--crediscore-/pull/25), [run](https://github.com/4Noisy/-equipo-lospapus--crediscore-/actions/runs/43342228731)) y `container-scan (trivy image)` ([#26](https://github.com/4Noisy/-equipo-lospapus--crediscore-/pull/26), [run](https://github.com/4Noisy/-equipo-lospapus--crediscore-/actions/runs/43342301227)). | ✅ |
| Firma Cosign + verify OK | 20 | Job `sign-and-attest` en [`ci.yml`](../../.github/workflows/ci.yml), PR [#28](https://github.com/4Noisy/-equipo-lospapus--crediscore-/pull/28). [Run de prueba](https://github.com/4Noisy/-equipo-lospapus--crediscore-/actions/runs/43341528827): `cosign verify` OK. | ✅ |
| Attestation SLSA nivel 2 | 20 | Mismo job: `cosign attest --type slsaprovenance` y `cosign verify-attestation` OK. | ✅ |
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

[Run](https://github.com/4Noisy/-equipo-lospapus--crediscore-/actions/runs/43342804177) en un cluster kind con la imagen firmada en la prueba de #28:

```
pod/firmada created
ghcr.io/4noisy/scoring-api:cc97070…@sha256:c55fdc8723f9b31f50c5755693841565bd6bdfe476dc76f44ef8e2223c2bbc20
```

La imagen sin firma de la S08 se rechazó en el mismo run. Una vez mergeado #28, `supply-chain.yml` repite esta prueba después de cada CI verde en `main`.

## Cómo verificar una imagen a mano

```bash
cosign verify \
  --certificate-identity "https://github.com/4Noisy/-equipo-lospapus--crediscore-/.github/workflows/ci.yml@refs/heads/main" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  ghcr.io/4noisy/scoring-api@sha256:<digest>
```
