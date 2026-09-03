import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import {
  cancelSubscription,
  createSubscription,
  getSubscriptionStatus,
  listPlans,
} from '../api/client';
import type { Plan, SubscriptionStatus } from '../types';
import { StripeCheckout } from './StripeCheckout';

// Stripe confirms payment client-side, but the tier/status update only
// happens once our backend processes Stripe's webhook asynchronously — a
// real network round-trip Stripe controls, not something confirmPayment()
// waits for. Poll briefly rather than treating one immediate profile
// refresh as authoritative, which would show "free" and re-offer Subscribe
// right after a successful payment.
const CONFIRMATION_POLL_INTERVAL_MS = 1500;
const CONFIRMATION_POLL_ATTEMPTS = 8; // ~12s

const OPEN_SUBSCRIPTION_STATUSES = new Set(['active', 'incomplete', 'trialing', 'past_due']);

export function SubscriptionPlans() {
  const { accessToken, user, refreshProfile } = useAuth();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [plansError, setPlansError] = useState<string | null>(null);
  const [subscribingTier, setSubscribingTier] = useState<string | null>(null);
  const [subscribeError, setSubscribeError] = useState<string | null>(null);
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [cancelError, setCancelError] = useState<string | null>(null);
  const [isCanceling, setIsCanceling] = useState(false);
  const [subscriptionStatus, setSubscriptionStatus] = useState<SubscriptionStatus | null>(null);
  const [isConfirmingPayment, setIsConfirmingPayment] = useState(false);

  const refreshSubscriptionStatus = useCallback(async () => {
    if (!accessToken) return;
    const status = await getSubscriptionStatus(accessToken);
    setSubscriptionStatus(status);
  }, [accessToken]);

  useEffect(() => {
    listPlans()
      .then((response) => setPlans(response.plans))
      .catch((err) => setPlansError(err instanceof Error ? err.message : 'Failed to load plans'));
  }, []);

  useEffect(() => {
    refreshSubscriptionStatus().catch(() => {
      // Non-fatal — the cancel button just won't show for a stuck
      // incomplete subscription until this succeeds on a later render.
    });
  }, [refreshSubscriptionStatus]);

  const handleSubscribe = async (tier: 'pro' | 'premium') => {
    if (!accessToken) return;
    setSubscribingTier(tier);
    setSubscribeError(null);
    setClientSecret(null);
    try {
      const response = await createSubscription(accessToken, tier);
      if (response.client_secret) {
        setClientSecret(response.client_secret);
      } else {
        await Promise.all([refreshProfile(), refreshSubscriptionStatus()]);
      }
    } catch (err) {
      setSubscribeError(err instanceof Error ? err.message : 'Subscription failed');
    } finally {
      setSubscribingTier(null);
    }
  };

  const handleCancel = async () => {
    if (!accessToken) return;
    setIsCanceling(true);
    setCancelError(null);
    try {
      await cancelSubscription(accessToken);
      await Promise.all([refreshProfile(), refreshSubscriptionStatus()]);
    } catch (err) {
      setCancelError(err instanceof Error ? err.message : 'Cancel failed');
    } finally {
      setIsCanceling(false);
    }
  };

  const handlePaymentSuccess = async () => {
    setClientSecret(null);
    setIsConfirmingPayment(true);
    try {
      for (let attempt = 0; attempt < CONFIRMATION_POLL_ATTEMPTS; attempt++) {
        await Promise.all([refreshProfile(), refreshSubscriptionStatus()]);
        const status = await getSubscriptionStatus(accessToken!);
        if (status.status === 'active') {
          return;
        }
        await new Promise((resolve) => setTimeout(resolve, CONFIRMATION_POLL_INTERVAL_MS));
      }
      // Poll window expired without the webhook landing — not an error, Stripe
      // still may deliver it any moment. Say so rather than silently giving up.
      setSubscribeError(
        'Payment succeeded — your account is still updating. Refresh the page in a moment if it doesn\'t update automatically.'
      );
    } finally {
      setIsConfirmingPayment(false);
    }
  };

  const hasOpenSubscription =
    subscriptionStatus?.status != null && OPEN_SUBSCRIPTION_STATUSES.has(subscriptionStatus.status);
  const isPending = hasOpenSubscription && subscriptionStatus?.status !== 'active';

  return (
    <div className="subscription-plans">
      <h2>Subscription</h2>

      {user && (
        <p className="current-tier">
          Current plan: <strong>{user.tier}</strong>
        </p>
      )}

      {isPending && (
        <div className="info-message">
          You have a <strong>{subscriptionStatus?.status}</strong> subscription to{' '}
          <strong>{subscriptionStatus?.tier}</strong>
          {subscriptionStatus?.status === 'incomplete'
            ? ' — finish payment above, or cancel it below before starting a new one.'
            : '.'}
        </div>
      )}

      {isConfirmingPayment && (
        <div className="info-message">Confirming your payment — this can take a few seconds…</div>
      )}

      {plansError && <div className="error-message">{plansError}</div>}

      <div className="plans-grid">
        {plans.map((plan) => {
          const isCurrentPlan = user?.tier === plan.tier || subscriptionStatus?.tier === plan.tier;
          return (
            <div key={plan.tier} className={`plan-card ${isCurrentPlan ? 'current' : ''}`}>
              <h3>{plan.name}</h3>
              <p className="plan-price">
                {plan.monthly_price_usd === 0 ? 'Free' : `$${plan.monthly_price_usd.toFixed(2)}/mo`}
              </p>
              <ul className="plan-features">
                <li>
                  {plan.shopping_lists} shopping list{plan.shopping_lists === 1 ? '' : 's'}
                </li>
                <li>{plan.store_comparison}</li>
                <li>Coupons: {plan.coupons}</li>
                <li>Deal alerts: {plan.deal_alerts}</li>
              </ul>
              {plan.tier !== 'free' && !isCurrentPlan && !hasOpenSubscription && (
                <button
                  className="optimize-button"
                  onClick={() => handleSubscribe(plan.tier as 'pro' | 'premium')}
                  disabled={subscribingTier !== null}
                >
                  {subscribingTier === plan.tier ? 'Starting…' : `Subscribe to ${plan.name}`}
                </button>
              )}
              {plan.tier !== 'free' && isCurrentPlan && hasOpenSubscription && (
                <button className="reset-button" onClick={handleCancel} disabled={isCanceling}>
                  {isCanceling
                    ? 'Canceling…'
                    : subscriptionStatus?.status === 'active'
                      ? 'Cancel subscription'
                      : `Cancel ${subscriptionStatus?.status} subscription`}
                </button>
              )}
            </div>
          );
        })}
      </div>

      {subscribeError && <div className="error-message">{subscribeError}</div>}
      {cancelError && <div className="error-message">{cancelError}</div>}

      {clientSecret && (
        <div className="stripe-checkout-section">
          <h3>Complete payment</h3>
          <StripeCheckout clientSecret={clientSecret} onSuccess={handlePaymentSuccess} />
        </div>
      )}
    </div>
  );
}
