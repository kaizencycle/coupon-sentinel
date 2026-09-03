/**
 * Coupon Sentinel - Stripe Checkout (Milestone 4)
 *
 * Confirms a subscription's PaymentIntent using Stripe's Payment Element.
 * Built against Stripe's documented client-side API — NOT verified against
 * a real Stripe account, since VITE_STRIPE_PUBLIC_KEY isn't set for this
 * project. Renders a clear "not configured" message instead of a blank/
 * broken form when the key is missing, same guarded-degradation pattern
 * used throughout the backend (Stripe/Kroger/email all return 503 rather
 * than fail silently).
 */

import { useState, type FormEvent } from 'react';
// The `/pure` entry point matters: the default `@stripe/stripe-js` import
// injects a <script src="https://js.stripe.com/v3"> tag as a side effect of
// merely being imported — which happened on every page load of this app
// (StripeCheckout is statically imported via AccountView), even when the
// user never opens the subscription tab and even when Stripe isn't
// configured. `/pure` only loads Stripe.js when loadStripe() is actually
// called, which getStripe() below already gates on STRIPE_PUBLIC_KEY.
import { loadStripe } from '@stripe/stripe-js/pure';
import type { Stripe } from '@stripe/stripe-js';
import { Elements, PaymentElement, useElements, useStripe } from '@stripe/react-stripe-js';

const STRIPE_PUBLIC_KEY = import.meta.env.VITE_STRIPE_PUBLIC_KEY as string | undefined;

let stripePromise: Promise<Stripe | null> | null = null;

function getStripe(): Promise<Stripe | null> | null {
  if (!STRIPE_PUBLIC_KEY) return null;
  if (!stripePromise) stripePromise = loadStripe(STRIPE_PUBLIC_KEY);
  return stripePromise;
}

interface Props {
  clientSecret: string;
  onSuccess: () => void;
}

function CheckoutForm({ onSuccess }: { onSuccess: () => void }) {
  const stripe = useStripe();
  const elements = useElements();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!stripe || !elements) return;

    setIsSubmitting(true);
    setError(null);

    const { error: confirmError } = await stripe.confirmPayment({
      elements,
      redirect: 'if_required',
    });

    if (confirmError) {
      setError(confirmError.message ?? 'Payment failed');
      setIsSubmitting(false);
      return;
    }

    setIsSubmitting(false);
    onSuccess();
  };

  return (
    <form onSubmit={handleSubmit} className="stripe-checkout-form">
      <PaymentElement />
      {error && <div className="error-message">{error}</div>}
      <button type="submit" className="optimize-button" disabled={!stripe || isSubmitting}>
        {isSubmitting ? 'Confirming…' : 'Confirm Payment'}
      </button>
    </form>
  );
}

export function StripeCheckout({ clientSecret, onSuccess }: Props) {
  const stripe = getStripe();

  if (!stripe) {
    return (
      <div className="stripe-not-configured">
        <p>
          Stripe isn't configured for this deployment (<code>VITE_STRIPE_PUBLIC_KEY</code> is
          unset) — payment can't be collected yet. The subscription was created on Stripe's side;
          confirming it requires a configured publishable key.
        </p>
      </div>
    );
  }

  return (
    <Elements stripe={stripe} options={{ clientSecret }}>
      <CheckoutForm onSuccess={onSuccess} />
    </Elements>
  );
}
