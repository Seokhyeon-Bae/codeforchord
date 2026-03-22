/**
 * Site origin used for Auth0 redirect_uri and logout returnTo.
 *
 * On Vercel: set VITE_APP_ORIGIN in Environment Variables to your live URL,
 * e.g. https://your-app.vercel.app (no trailing slash). Must match Auth0
 * Allowed Callback / Logout / Web Origins exactly.
 *
 * Leave unset for local dev — uses the current browser origin (localhost, etc.).
 */
export function getAppOrigin() {
  const fromEnv = import.meta.env.VITE_APP_ORIGIN?.trim()
  if (fromEnv) return fromEnv.replace(/\/$/, '')
  if (typeof window !== 'undefined') return window.location.origin
  return ''
}
