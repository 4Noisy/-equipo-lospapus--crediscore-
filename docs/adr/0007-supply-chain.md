# ADR 0007 — Cadena de suministro firmada (Cosign + SLSA)

- **Estado:** Aceptada
- **Fecha:** 2026-11-12
- **Equipo:** lospapus

> La S10 pide este ADR como `0006-supply-chain.md`, pero el número 0006 ya lo usa
> [plataforma K8s](0006-plataforma-k8s.md). Por eso queda como 0007.

## Contexto

Desde la S08 el CI publica `ghcr.io/4noisy/scoring-api:<sha>` y Argo CD la
despliega. El problema: nada prueba que la imagen que corre en el cluster sea
la que construyó **nuestro** pipeline. Alguien con acceso a GHCR podría subir
otra imagen con el mismo tag. En una fintech auditada por la CMF tenemos que
poder demostrar el origen de cada imagen desplegada.

## Decisión

1. **Firmar cada imagen con Cosign en modo keyless.** El job `sign-and-attest`
   de `ci.yml` pide un token OIDC a GitHub y Sigstore emite un certificado de
   10 minutos a nombre del workflow
   (`.../.github/workflows/ci.yml@refs/heads/main`). No hay llaves que guardar
   ni rotar, y la firma queda registrada en el log público Rekor.
2. **Adjuntar una attestation SLSA de provenance** (`cosign attest --type
   slsaprovenance`) con el repo, el commit, el workflow y la ejecución que
   construyeron la imagen. Apuntamos a **SLSA nivel 2**: el build corre en un
   servicio hospedado (GitHub Actions) y la provenance va firmada.
3. **Firmar siempre por digest** (`imagen@sha256:...`), nunca por tag, porque
   un tag se puede mover.
4. **Verificar en el pipeline**: el mismo job corre `cosign verify` y
   `cosign verify-attestation` exigiendo esa identidad exacta.
5. **Solo se promueve lo firmado**: `promote` depende de `sign-and-attest`.
6. **Verificar al entrar al cluster**: una policy de Kyverno rechaza los Pods
   cuya imagen no esté firmada por el workflow de `main`
   (`k8s/policies/require-signature.yaml`).

Las firmas y attestations se guardan en GHCR junto a la imagen mientras esté en
uso, y se respaldan 5 años (retención pedida por la CMF).

## Alternativas descartadas

- **Cosign con llave propia:** obliga a guardar y rotar una llave privada; si
  se filtra, cualquiera firma como nosotros.
- **SLSA nivel 3:** pide builders aislados y provenance que el propio workflow
  no pueda alterar (por ejemplo, `slsa-github-generator`). Lo dejamos para
  más adelante.

## Consecuencias

- Una auditoría puede verificar cualquier imagen con `cosign verify`.
- Una imagen subida a mano a GHCR no pasa la policy de admisión, aunque tenga
  el tag correcto.
- El pipeline depende de Sigstore (Fulcio y Rekor). Si Sigstore cae, no se
  publican versiones nuevas: preferimos eso a desplegar sin firmar.
