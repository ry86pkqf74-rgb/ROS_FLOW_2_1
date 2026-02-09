export function asString(value: unknown, fallback = ''): string {
  if (typeof value === 'string') {
    return value;
  }

  if (Array.isArray(value) && typeof value[0] === 'string') {
    return value[0];
  }

  return fallback;
}

export function asOptionalString(value: unknown): string | undefined {
  const result = asString(value, '');
  return result.length > 0 ? result : undefined;
}

export function asInt(value: unknown, fallback: number): number {
  const parsed = parseInt(asString(value, ''), 10);
  return Number.isNaN(parsed) ? fallback : parsed;
}
