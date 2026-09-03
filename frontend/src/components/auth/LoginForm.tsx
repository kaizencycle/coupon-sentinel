import { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';

interface Props {
  onSwitchToRegister: () => void;
}

export function LoginForm({ onSwitchToRegister }: Props) {
  const { login, error, clearError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await login(email, password);
    } catch {
      // Error is surfaced via useAuth().error
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      <h2>Log In</h2>

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
          autoComplete="current-password"
        />
      </label>

      {error && <div className="error-message">{error}</div>}

      <button type="submit" className="optimize-button" disabled={isSubmitting}>
        {isSubmitting ? 'Logging in…' : 'Log In'}
      </button>

      <p className="auth-switch">
        Don't have an account?{' '}
        <button type="button" className="link-button" onClick={onSwitchToRegister}>
          Register
        </button>
      </p>
    </form>
  );
}
