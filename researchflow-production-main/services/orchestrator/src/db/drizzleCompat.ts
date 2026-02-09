import { sql } from "drizzle-orm";

export function ilike(column: any, pattern: string): any {
  return sql`${column} ILIKE ${pattern}`;
}

export function isNull(column: any): any {
  return sql`${column} IS NULL`;
}

export function ne(left: any, right: any): any {
  return sql`${left} <> ${right}`;
}
