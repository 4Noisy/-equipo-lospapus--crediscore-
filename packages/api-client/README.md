# @crediscore/api-client

Cliente TypeScript de la API de CrediScore. `src/schema.d.ts` se **genera** desde [`api/openapi.yaml`](../../api/openapi.yaml): no se edita a mano.

```bash
npm install
npm run generate   # regenera src/schema.d.ts tras cambiar el contrato
npm run typecheck
```

```ts
import { createCrediScoreClient } from "@crediscore/api-client";

const api = createCrediScoreClient("https://api.crediscore.cl/v1", accessToken);

const { data, error } = await api.POST("/credit-applications", {
  params: { header: { "Idempotency-Key": crypto.randomUUID() } },
  body: {
    rut: "12345678-5",
    amount: 250000,
    term_months: 12,
    identity_verification_id: verificationId,
  },
});
```
