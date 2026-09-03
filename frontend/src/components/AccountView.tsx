import { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { LoginForm } from './auth/LoginForm';
import { RegisterForm } from './auth/RegisterForm';
import { SubscriptionPlans } from './SubscriptionPlans';
import { resendVerificationEmail } from '../api/client';

export function AccountView() {
  const { accessToken, user, isLoading, logout } = useAuth();
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [verifySending, setVerifySending] = useState(false);
  const [verifyMessage, setVerifyMessage] = useState<string | null>(null);
  const [verifyError, setVerifyError] = useState<string | null>(null);

  // Without this, logging out while the register form was showing (e.g. the
  // user registered, then later logs out) leaves the form stuck on
  // "Create Account" instead of defaulting back to login.
  useEffect(() => {
    if (!accessToken) setAuthMode('login');
  }, [accessToken]);

  if (isLoading) {
    return (
      <div className="account-view">
        <p>Loading…</p>
      </div>
    );
  }

  if (!accessToken || !user) {
    return (
      <div className="account-view">
        {authMode === 'login' ? (
          <LoginForm onSwitchToRegister={() => setAuthMode('register')} />
        ) : (
          <RegisterForm onSwitchToLogin={() => setAuthMode('login')} />
        )}
      </div>
    );
  }

  const handleResendVerification = async () => {
    setVerifySending(true);
    setVerifyMessage(null);
    setVerifyError(null);
    try {
      const response = await resendVerificationEmail(accessToken);
      setVerifyMessage(
        response.status === 'already_verified'
          ? 'Your email is already verified.'
          : 'Verification email sent — check your inbox.'
      );
    } catch (err) {
      setVerifyError(err instanceof Error ? err.message : 'Failed to send verification email');
    } finally {
      setVerifySending(false);
    }
  };

  return (
    <div className="account-view">
      <div className="account-profile">
        <h2>Account</h2>
        <p className="account-email">{user.email}</p>
        <p>
          Email verified:{' '}
          {user.is_email_verified ? (
            <span className="verified-badge">Yes</span>
          ) : (
            <span className="unverified-badge">No</span>
          )}
        </p>

        {!user.is_email_verified && (
          <div className="verify-email-block">
            <button className="reset-button" onClick={handleResendVerification} disabled={verifySending}>
              {verifySending ? 'Sending…' : 'Send verification email'}
            </button>
            {verifyMessage && <p className="verify-message">{verifyMessage}</p>}
            {verifyError && <div className="error-message">{verifyError}</div>}
          </div>
        )}

        <button className="reset-button" onClick={logout}>
          Log out
        </button>
      </div>

      <SubscriptionPlans />
    </div>
  );
}
