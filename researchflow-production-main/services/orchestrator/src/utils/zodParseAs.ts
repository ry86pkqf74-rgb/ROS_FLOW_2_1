import type { ZodSchema } from 'zod';

/**
 * Parse `body` with `schema` and return the result typed as `T`.
 *
 * Works around a Zod >= 3.25 type-depth regression where `z.infer<>`
 * degrades deeply-nested required fields to optional.  Erasing the
 * schema's output generic (via the `ZodSchema` base type) causes
 * `.parse()` to return `any`, which TypeScript assigns to `T`
 * without an explicit cast.  Runtime validation is fully enforced.
 *
 * @example
 * const body = zodParseAs<CreatePlanRequest>(createPlanSchema, req.body);
 */
export function zodParseAs<T>(schema: ZodSchema, body: unknown): T {
  return schema.parse(body);
}
