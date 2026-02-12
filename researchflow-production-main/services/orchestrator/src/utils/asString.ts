/**
 * Narrow Express `req.params` / `req.query` / `req.headers` values
 * from `string | string[] | undefined` to `string`.
 *
 * Pure runtime narrowing — zero type-casts.
 *
 * Root cause: Express's ParamsDictionary types values as
 * `string | string[]` (see @types/express-serve-static-core line 44).
 * Our express.d.ts augmentation cannot override this because the
 * generic `Request<P>.params: P` takes precedence.
 *
 * @param val - The raw value from `req.params`, `req.query`, or `req.headers`.
 * @returns The narrowed string value.
 *
 * Behaviour:
 * - `undefined` → `''`  (safe for route params — they are never undefined
 *   when the route matches — but callers processing *query* values should
 *   be aware that a missing key will now yield `''` rather than `undefined`)
 * - `string[]`  → first element, or `''` if empty
 * - `string`    → returned as-is
 */
export function asString(val: string | string[] | undefined): string {
  if (val === undefined) {
    return '';
  }
  if (Array.isArray(val)) {
    return val.length > 0 ? val[0] : '';
  }
  return val;
}
