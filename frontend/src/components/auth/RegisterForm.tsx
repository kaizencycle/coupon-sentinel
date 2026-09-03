import { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';

interface Props {
  onSwitchToLogin: () => void;
}

export function RegisterForm({ onSwitchToLogin }: Props) {
  const { register, error, clearError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await register(email, password);
    } catch {
      // Error is surfaced via useAuth().error
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      <h2>Create Account</h2>

      <label>
        Email
        <input
          type="email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            clearError();
          }}
          required
          autoComplete="email"
        />
      </label>

      <label>
        Password
        <input
          type="password"
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            clearError();
          }}
          required
          minLength={8}
          autoComplete="new-password"
        />
        <span className="field-hint">At least 8 characters</span>
      </label>

      {error && <div className="error-message">{error}</div>}

      <button type="submit" className="optimize-button" disabled={isSubmitting}>
        {isSubmitting ? 'Creating account…' : 'Create Account'}
      </button>

      <p className="auth-switch">
        Already have an account?{' '}
        <button type="button" className="link-button" onClick={onSwitchToLogin}>
          Log in
        </button>
      </p>
    </form>
  );
}
