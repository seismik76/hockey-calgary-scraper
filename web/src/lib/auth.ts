import 'server-only';
import { cookies } from 'next/headers';

export const ADMIN_COOKIE = 'hca_admin';
const ONE_HOUR = 60 * 60;

/** Server-side check: is the request coming from an unlocked admin session? */
export async function isAdmin(): Promise<boolean> {
  const store = await cookies();
  return store.get(ADMIN_COOKIE)?.value === 'ok';
}

/** Whether the admin feature is enabled at all (env-gated). Matches the
 *  Streamlit posture: when ADMIN_PASSWORD isn't set, the admin UI is hidden
 *  entirely. */
export function adminEnabled(): boolean {
  return Boolean(process.env.ADMIN_PASSWORD);
}

/** Verify a submitted password against the configured ADMIN_PASSWORD.
 *  Returns false if either is unset. */
export function checkPassword(submitted: string): boolean {
  const expected = process.env.ADMIN_PASSWORD;
  if (!expected || !submitted) return false;
  if (submitted.length !== expected.length) return false;
  // Constant-time-ish comparison to avoid trivial timing attacks. Not perfect,
  // but cheap defence and we're not protecting national secrets.
  let diff = 0;
  for (let i = 0; i < submitted.length; i++) {
    diff |= submitted.charCodeAt(i) ^ expected.charCodeAt(i);
  }
  return diff === 0;
}

export async function setAdminCookie() {
  const store = await cookies();
  store.set(ADMIN_COOKIE, 'ok', {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: ONE_HOUR,
  });
}

export async function clearAdminCookie() {
  const store = await cookies();
  store.delete(ADMIN_COOKIE);
}
