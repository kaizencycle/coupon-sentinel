import { useEffect, useState } from 'react';
import { verifyEmail } from '../api/client';

export function VerifyEmailPage({ token }: { token: string }) {
  const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying');
  const [message, setMessage] = useState('');

  useEffect(() => {
    verifyEmail(token)
      .then((response) => {
        setStatus('success');
        setMessage(`Verified ${response.email}.`);
      })
      .catch((err) => {
        setStatus('error');
        setMessage(err instanceof Error ? err.message : 'Verification failed');
      });
  }, [token]);

  return (
    <div className="app">
      <div className="verify-email-page">
        <h1>Email Verification</h1>
        {status === 'verifying' && <p>Verifying…</p>}
        {status === 'success' && <p className="verify-message">{message}</p>}
        {status === 'error' && <div className="error-message">{message}</div>}
        <a href="/">Back to Coupon Sentinel</a>
      </div>
    </div>
  );
}
