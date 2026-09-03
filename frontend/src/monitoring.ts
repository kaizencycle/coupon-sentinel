/**
 * Coupon Sentinel - Frontend Monitoring (Milestone 5)
 *
 * Sentry error tracking, initialized only when VITE_SENTRY_DSN is set —
 * calling initMonitoring() is always safe without it, same guarded pattern
 * as every backend integration (Stripe, Kroger, email, Mixpanel, Sentry).
 * Unverified against a real Sentry project: no DSN exists for this project yet.
 */
import * as Sentry from '@sentry/react';

export function initMonitoring(): void {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  if (!dsn) return;

  Sentry.init({
    dsn,
    environment: import.meta.env.MODE,
    tracesSampleRate: 0.1,
  });
}
