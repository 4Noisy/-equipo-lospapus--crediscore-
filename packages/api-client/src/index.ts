import createClient from "openapi-fetch";
import type { components, paths } from "./schema.js";

export type { components, paths };
export type CreditApplication = components["schemas"]["CreditApplication"];
export type CreditApplicationInput = components["schemas"]["CreditApplicationInput"];
export type Decision = components["schemas"]["Decision"];
export type Problem = components["schemas"]["Problem"];

/** Cliente tipado de la API de CrediScore. `token` es el access token OAuth2 del partner. */
export function createCrediScoreClient(baseUrl: string, token: string) {
  return createClient<paths>({ baseUrl, headers: { Authorization: `Bearer ${token}` } });
}
