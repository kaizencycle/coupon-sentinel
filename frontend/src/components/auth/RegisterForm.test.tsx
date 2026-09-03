import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RegisterForm } from './RegisterForm';
import { AuthProvider } from '../../hooks/useAuth';
import * as client from '../../api/client';

vi.mock('../../api/client', () => ({
  loginUser: vi.fn(),
  registerUser: vi.fn(),
  getProfile: vi.fn(),
}));

function renderRegisterForm(onSwitchToLogin = vi.fn()) {
  return render(
    <AuthProvider>
      <RegisterForm onSwitchToLogin={onSwitchToLogin} />
    </AuthProvider>
  );
}

describe('RegisterForm', () => {
  beforeEach(() => {
    vi.mocked(client.registerUser).mockReset();
    vi.mocked(client.getProfile).mockReset();
  });

  it('submits the entered email and password to register()', async () => {
    vi.mocked(client.registerUser).mockResolvedValue({
      access_token: 'a',
      refresh_token: 'r',
      token_type: 'bearer',
    });
    vi.mocked(client.getProfile).mockResolvedValue({
      id: 1,
      email: 'new@example.com',
      tier: 'free',
    } as never);

    renderRegisterForm();

    await userEvent.type(screen.getByLabelText(/email/i), 'new@example.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'password123');
    await userEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() =>
      expect(client.registerUser).toHaveBeenCalledWith('new@example.com', 'password123')
    );
  });

  it('shows the backend error message on a failed registration (e.g. duplicate email)', async () => {
    vi.mocked(client.registerUser).mockRejectedValue(new Error('Email already registered'));

    renderRegisterForm();

    await userEvent.type(screen.getByLabelText(/email/i), 'taken@example.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'password123');
    await userEvent.click(screen.getByRole('button', { name: /create account/i }));

    expect(await screen.findByText('Email already registered')).toBeInTheDocument();
  });

  it('calls onSwitchToLogin when the "Log in" link is clicked', async () => {
    const onSwitchToLogin = vi.fn();
    renderRegisterForm(onSwitchToLogin);

    await userEvent.click(screen.getByRole('button', { name: 'Log in' }));

    expect(onSwitchToLogin).toHaveBeenCalled();
  });
});
