import postgres from "postgres";

// Portable Postgres client — works against the local Docker container, Neon,
// Supabase, anything, via DATABASE_URL. When unset, the app falls back to the
// pipeline's local JSON file (see data.ts) so dev works with no DB.
// Vercel's Neon integration injects WATCHLIST_DATABASE_URL (custom prefix); locally
// we use DATABASE_URL (Docker). Accept either.
const CONN = process.env.DATABASE_URL || process.env.WATCHLIST_DATABASE_URL;
export const hasDb = !!CONN;

// `prepare: false` keeps it compatible with transaction-pooled connections
// (the Neon pooler) used in serverless.
export const sql = hasDb ? postgres(CONN!, { prepare: false }) : null;
