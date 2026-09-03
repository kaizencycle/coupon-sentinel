import { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { cancelSubscription, createSubscription, listPlans } from '../api/client';
import type { Plan } from '../types';
import { StripeCheckout } from './StripeCheckout';

export function SubscriptionPlans() {
  const { accessToken, user, refreshProfile } = useAuth();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [plansError, setPlansError] = useState<string | null>(null);
  const [subscribingTier, setSubscribingTier] = useState<string | null>(null);
  const [subscribeError, setSubscribeError] = useState<string | null>(null);
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [cancelError, setCancelError] = useState<string | null>(null);
  const [isCanceling, setIsCanceling] = useState(false);

  useEffect(() => {
    listPlans()
      .then((response) => setPlans(response.plans))
      .catch((err) => setPlansError(err instanceof Error ? err.message : 'Failed to load plans'));
  }, []);

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
        await refreshProfile();
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
      await refreshProfile();
    } catch (err) {
      setCancelError(err instanceof Error ? err.message : 'Cancel failed');
    } finally {
      setIsCanceling(false);
    }
  };

  const handlePaymentSuccess = async () => {
    setClientSecret(null);
    await refreshProfile();
  };

  return (
    <div className="subscription-plans">
      <h2>Subscription</h2>

      {user && (
        <p className="current-tier">
          Current plan: <strong>{user.tier}</strong>
        </p>
      )}

      {plansError && <div className="error-message">{plansError}</div>}

      <div className="plans-grid">
        {plans.map((plan) => (
          <div key={plan.tier} className={`plan-card ${user?.tier === plan.tier ? 'current' : ''}`}>
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
            {plan.tier !== 'free' && user?.tier !== plan.tier && (
              <button
                className="optimize-button"
                onClick={() => handleSubscribe(plan.tier as 'pro' | 'premium')}
                disabled={subscribingTier !== null}
              >
                {subscribingTier === plan.tier ? 'Starting…' : `Subscribe to ${plan.name}`}
              </button>
            )}
            {user?.tier === plan.tier && plan.tier !== 'free' && (
              <button className="reset-button" onClick={handleCancel} disabled={isCanceling}>
                {isCanceling ? 'Canceling…' : 'Cancel subscription'}
              </button>
            )}
          </div>
        ))}
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
