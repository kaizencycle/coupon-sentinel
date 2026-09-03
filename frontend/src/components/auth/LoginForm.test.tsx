import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { LoginForm } from './LoginForm';
import { AuthProvider } from '../../hooks/useAuth';
import * as client from '../../api/client';

vi.mock('../../api/client', () => ({
  loginUser: vi.fn(),
  registerUser: vi.fn(),
  getProfile: vi.fn(),
}));

function renderLoginForm(onSwitchToRegister = vi.fn()) {
  return render(
    <AuthProvider>
      <LoginForm onSwitchToRegister={onSwitchToRegister} />
    </AuthProvider>
  );
}

describe('LoginForm', () => {
  beforeEach(() => {
    vi.mocked(client.loginUser).mockReset();
    vi.mocked(client.getProfile).mockReset();
  });

  it('submits the entered email and password to login()', async () => {
    vi.mocked(client.loginUser).mockResolvedValue({
      access_token: 'a',
      refresh_token: 'r',
      token_type: 'bearer',
    });
    vi.mocked(client.getProfile).mockResolvedValue({
      id: 1,
      email: 'a@example.com',
      tier: 'free',
    } as never);

    renderLoginForm();

    await userEvent.type(screen.getByLabelText(/email/i), 'a@example.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'password123');
    await userEvent.click(screen.getByRole('button', { name: /log in/i }));

    await waitFor(() =>
      expect(client.loginUser).toHaveBeenCalledWith('a@example.com', 'password123')
    );
  });

  it('shows the backend error message on a failed login', async () => {
    vi.mocked(client.loginUser).mockRejectedValue(new Error('Invalid email or password'));

    renderLoginForm();

    await userEvent.type(screen.getByLabelText(/email/i), 'a@example.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'wrong-password');
    await userEvent.click(screen.getByRole('button', { name: /log in/i }));

    expect(await screen.findByText('Invalid email or password')).toBeInTheDocument();
  });

  it('clears a previous error as soon as the user edits the email field', async () => {
    vi.mocked(client.loginUser).mockRejectedValue(new Error('Invalid email or password'));

    renderLoginForm();

    await userEvent.type(screen.getByLabelText(/email/i), 'a@example.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'wrong-password');
    await userEvent.click(screen.getByRole('button', { name: /log in/i }));
    expect(await screen.findByText('Invalid email or password')).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText(/email/i), 'x');

    expect(screen.queryByText('Invalid email or password')).not.toBeInTheDocument();
  });

  it('calls onSwitchToRegister when the "Register" link is clicked', async () => {
    const onSwitchToRegister = vi.fn();
    renderLoginForm(onSwitchToRegister);

    await userEvent.click(screen.getByRole('button', { name: 'Register' }));

    expect(onSwitchToRegister).toHaveBeenCalled();
  });
});
