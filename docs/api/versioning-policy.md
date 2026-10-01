# Política de versionado y compatibilidad de la API

Aplica al contrato [`api/openapi.yaml`](../../api/openapi.yaml), que es la fuente de verdad (*contract-first*).

## Esquema de versiones

* **Versión mayor en la URL:** `/v1`. Solo cambia cuando hay un cambio incompatible.
* **Versión del contrato:** `info.version` en SemVer (`1.0.0`).
  * *patch*: correcciones de documentación o ejemplos.
  * *minor*: cambios compatibles.
  * *major*: cambio incompatible; implica una nueva URL (`/v2`).

## Qué es compatible y qué no

| Compatible (sube *minor*) | Incompatible (exige `/v2`) |
| :--- | :--- |
| Agregar un endpoint. | Eliminar o renombrar un endpoint, campo o parámetro. |
| Agregar un campo **opcional** a una petición. | Volver obligatorio un campo o parámetro opcional. |
| Agregar un campo a una respuesta. | Cambiar el tipo, formato o significado de un campo. |
| Agregar un valor a un `enum` de respuesta. | Quitar un valor de un `enum`. |
| Agregar un código de error documentado. | Cambiar el código de estado de un caso existente. |

Los clientes deben ignorar campos desconocidos y tratar los valores de `enum` no reconocidos como un estado genérico. Así los cambios de la columna izquierda no los rompen.

## Deprecación

1. El endpoint o campo se marca `deprecated: true` en el contrato y se anuncia a los partners.
2. Las respuestas incluyen los headers `Deprecation` y `Sunset` con la fecha de retiro.
3. El plazo mínimo entre el anuncio y el retiro es de **6 meses**.
4. `/v1` y `/v2` conviven durante ese plazo. Pasada la fecha, `/v1` responde `410 Gone`.

## Eventos y webhooks

Los eventos llevan `event_version` (ver [catálogo de eventos](../data/event-catalog.md)) y siguen las mismas reglas: agregar campos opcionales no cambia la versión mayor; un cambio incompatible publica un evento nuevo con otra versión mientras el anterior sigue emitiéndose durante el plazo de deprecación.

## Control en el pipeline

* `spectral lint api/openapi.yaml` con las reglas de [`.spectral.yaml`](../../.spectral.yaml) debe pasar sin errores en cada PR.
* Un cambio en `api/openapi.yaml` exige regenerar `packages/api-client` en el mismo PR.
* La detección automática de cambios incompatibles contra `main` queda para S08 (CI/CD).
