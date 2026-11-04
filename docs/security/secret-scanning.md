Secret scanning con historial (S09 · DevSecOps I)
Responsable: DevSecOps · Herramienta: gitleaks v8.28.0
1. ¿Qué es y por qué con historial?
El secret scanning busca credenciales (API keys, tokens, contraseñas, claves privadas)
que quedaron escritas en el código. Git nunca olvida: si alguien commitea un token y
en el commit siguiente lo borra, el token sigue en el historial y cualquiera que clone el
repo puede recuperarlo. Por eso escaneamos todos los commits de todas las ramas y no
solo el estado actual de los archivos.
CrediScore maneja datos financieros y de identidad (KYC), y el ADR 0003 define que los
secretos viven en AWS Secrets Manager, no en el repo. Este control verifica que eso se cumpla.
2. Las tres capas de defensa
Capa	Dónde	Qué hace	Archivo
1. Pre-commit	PC del dev	Bloquea el secreto antes de que exista el commit	`.pre-commit-config.yaml`
2. CI (gate)	GitHub Actions	Escanea el historial completo y falla el PR	`.github/workflows/security.yml`
3. Plataforma	GitHub	Secret scanning + push protection nativos	Settings → Code security
Instalar el hook (una vez por clon): `pip install pre-commit && pre-commit install`
3. Cómo funciona el job de CI
`actions/checkout` con `fetch-depth: 0`: trae todo el historial (sin esto el clon es
superficial y un secreto borrado no se vería).
`gitleaks git . --log-opts="--all"`: recorre los commits de todas las ramas, no solo
el rango del PR.
Corre en cada PR, en cada push a `main`, semanalmente (reglas nuevas) y a demanda.
Si encuentra algo no justificado, el job falla y bloquea el merge (gate bloqueante).
Publica el reporte SARIF como artefacto y usa `--redact` para no exponer el valor en los logs.
4. Resultado del escaneo inicial
Fecha: 2026-11-04 · 64 commits con cambios escaneados · todas las ramas.
Gitleaks reportó 8 hallazgos, todos falsos positivos. Ningún secreto real.
#	Archivo	Qué es en realidad	Decisión
1-6	`api/examples/*.http`	UUIDs de ejemplo en el header `Idempotency-Key` para el mock local (Prism)	Allowlist acotada por ruta + patrón UUID
7	`k8s/deployment.yaml`	Tag de imagen `ghcr.io/4noisy/scoring-api:<sha-de-commit>`	Allowlist acotada al repo de la imagen
8	`docs/s08/evidencia.md`	Mismo tag de imagen, citado en la evidencia de la S08	Misma allowlist
Verificaciones adicionales sobre todo el historial: no hay llaves AWS (`AKIA…`), tokens de
GitHub (`ghp_…`, `github_pat_…`), claves privadas PEM/OpenSSH, tokens `sk-…` ni Slack.
El único `DATABASE_URL` que existió es el placeholder `CHANGE_ME` de `k8s/secret.yaml`, que no es una credencial.
Prueba de que el control funciona: se commiteó un token falso con formato `ghp_…`, se
borró en el commit siguiente y se escaneó. El escaneo del árbol de archivos no lo vio; el
escaneo del historial sí lo detectó (exit code ≠ 0).
5. Qué hacer si el CI detecta un secreto real
El orden importa. Rotar primero, limpiar después.
Revocar y rotar la credencial de inmediato en el servicio que la emitió (GitHub, AWS,
base de datos…). Borrar el commit no sirve: hay que asumir que ya fue copiado.
Avisar al Tech Lead y registrar el incidente (qué secreto, desde cuándo, qué alcance tenía).
Revisar los logs de acceso del servicio por uso indebido durante la ventana de exposición.
Mover el valor nuevo a AWS Secrets Manager / GitHub Secrets. Nunca de vuelta al repo.
Opcional: reescribir el historial (`git filter-repo`). Es disruptivo y no reemplaza el paso 1.
6. Cómo re-triar un hallazgo y pedir una excepción
Reproducir en local: `gitleaks git . --log-opts="--all" --config .gitleaks.toml -v`
Preguntarse: ¿esto da acceso a algo? Si hay duda, es real: aplicar la sección 5.
Si es falso positivo, abrir un PR que agregue un bloque `[[allowlists]]` en
`.gitleaks.toml` con: descripción, ruta y patrón lo más acotados posible.
El PR necesita revisión de DevSecOps. No se aceptan allowlists amplias (por ejemplo,
ignorar una carpeta entera) ni excepciones silenciosas.
7. Configuración manual pendiente en GitHub
Estos pasos se hacen en la interfaz (requieren permisos de admin del repo):
Settings → Code security → Secret scanning: activar.
Settings → Code security → Push protection: activar (bloquea el push con secretos conocidos).
Settings → Branches → regla de `main`: marcar el check `secrets (gitleaks, historial completo)`
como required status check.
