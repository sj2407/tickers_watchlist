export const AUTH_COOKIE = "wl_auth";

// Deterministic token derived from the passcode — good enough for a personal
// single-user gate. (Not a substitute for real auth on a shared app.)
export function expectedToken(passcode: string): string {
  let h = 2166136261;
  const salt = passcode + "::tickers_watchlist";
  for (let i = 0; i < salt.length; i++) {
    h ^= salt.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0).toString(36);
}
