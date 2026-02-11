/**
 * Normalize Express `req.params` / `req.query` / `req.headers` values
 * from `string | string[] | undefined` to `string`.
 *
 * Runtime-neutral: does NOT default undefined to "".
 * If `val` is an array, returns the first element.
 * Otherwise returns `val` cast to string (may still be undefined at runtime).
 */
export function asString(val: string | string[] | undefined): string {
  if (Array.isArray(val)) {
    return val[0] as string;
  }
  return val as string;
}
