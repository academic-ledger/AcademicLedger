import { Pool } from "pg";

// Single pooled connection for the read API. Vercel reuses this across warm
// serverless invocations; it never runs heavy compute — only reads precomputed
// tables (works, qal_records, cohort_percentiles, authors).
declare global {
  // eslint-disable-next-line no-var
  var _pgPool: Pool | undefined;
}

function makePool(): Pool {
  const connectionString = process.env.DATABASE_URL;
  if (!connectionString) {
    throw new Error("DATABASE_URL is not set");
  }
  return new Pool({
    connectionString,
    // Neon requires TLS; the pooled string already carries sslmode=require.
    ssl: { rejectUnauthorized: false },
    max: 5,
    idleTimeoutMillis: 30_000,
  });
}

export const pool: Pool = global._pgPool ?? makePool();
if (process.env.NODE_ENV !== "production") global._pgPool = pool;

export async function query<T = any>(text: string, params?: any[]): Promise<T[]> {
  const res = await pool.query(text, params);
  return res.rows as T[];
}
