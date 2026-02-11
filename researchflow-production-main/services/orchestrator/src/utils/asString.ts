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
 * If `val` is an array, returns the first element (or '' if empty).
 * If `val` is undefined, returns ''.
 * Otherwise returns `val` directly (already a string).
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
