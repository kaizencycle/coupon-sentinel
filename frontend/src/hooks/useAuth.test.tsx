import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider, useAuth } from './useAuth';
import * as client from '../api/client';

vi.mock('../api/client', () => ({
  loginUser: vi.fn(),
  registerUser: vi.fn(),
  getProfile: vi.fn(),
}));

const STORAGE_KEY = 'coupon-sentinel-auth';

const tokens = { access_token: 'access-1', refresh_token: 'refresh-1', token_type: 'bearer' };
const profile = { id: 1, email: 'a@example.com', tier: 'free' } as const;

function TestHarness() {
  const { accessToken, user, isLoading, error, login, logout } = useAuth();
  return (
    <div>
      <div data-testid="loading">{String(isLoading)}</div>
      <div data-testid="token">{accessToken ?? 'none'}</div>
      <div data-testid="user">{user?.email ?? 'none'}</div>
      <div data-testid="error">{error ?? 'none'}</div>
      <button onClick={() => login('a@example.com', 'password123').catch(() => {})}>
        login
      </button>
      <button onClick={logout}>logout</button>
    </div>
  );
}

function renderWithProvider() {
  return render(
    <AuthProvider>
      <TestHarness />
    </AuthProvider>
  );
}

describe('AuthProvider / useAuth', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.mocked(client.loginUser).mockReset();
    vi.mocked(client.registerUser).mockReset();
    vi.mocked(client.getProfile).mockReset();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('starts logged out with no stored session', async () => {
    renderWithProvider();
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));

    expect(screen.getByTestId('token')).toHaveTextContent('none');
    expect(screen.getByTestId('user')).toHaveTextContent('none');
  });

  it('logging in persists tokens to localStorage and loads the profile', async () => {
    vi.mocked(client.loginUser).mockResolvedValue(tokens);
    vi.mocked(client.getProfile).mockResolvedValue(profile as never);

    renderWithProvider();
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));

    await userEvent.click(screen.getByText('login'));

    await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent('a@example.com'));
    expect(screen.getByTestId('token')).toHaveTextContent('access-1');

    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}');
    expect(stored).toEqual({ accessToken: 'access-1', refreshToken: 'refresh-1' });
  });

  it('a failed login surfaces the error and does not persist a session', async () => {
    vi.mocked(client.loginUser).mockRejectedValue(new Error('Invalid email or password'));

    renderWithProvider();
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));

    await userEvent.click(screen.getByText('login'));

    await waitFor(() =>
      expect(screen.getByTestId('error')).toHaveTextContent('Invalid email or password')
    );
    expect(screen.getByTestId('token')).toHaveTextContent('none');
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it('logout clears the session and localStorage', async () => {
    vi.mocked(client.loginUser).mockResolvedValue(tokens);
    vi.mocked(client.getProfile).mockResolvedValue(profile as never);

    renderWithProvider();
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));
    await userEvent.click(screen.getByText('login'));
    await waitFor(() => expect(screen.getByTestId('token')).toHaveTextContent('access-1'));

    await userEvent.click(screen.getByText('logout'));

    expect(screen.getByTestId('token')).toHaveTextContent('none');
    expect(screen.getByTestId('user')).toHaveTextContent('none');
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it('restores a session from localStorage on mount when the stored token is still valid', async () => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ accessToken: 'stored-token', refreshToken: 'stored-refresh' })
    );
    vi.mocked(client.getProfile).mockResolvedValue(profile as never);

    renderWithProvider();

    await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent('a@example.com'));
    expect(screen.getByTestId('token')).toHaveTextContent('stored-token');
    expect(client.getProfile).toHaveBeenCalledWith('stored-token');
  });

  it('drops an expired/invalid stored token instead of looping errors', async () => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ accessToken: 'expired-token', refreshToken: 'stored-refresh' })
    );
    vi.mocked(client.getProfile).mockRejectedValue(new Error('401 Unauthorized'));

    renderWithProvider();

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));
    expect(screen.getByTestId('token')).toHaveTextContent('none');
    expect(screen.getByTestId('user')).toHaveTextContent('none');
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });
});

describe('useAuth outside a provider', () => {
  it('throws a helpful error', () => {
    const Broken = () => {
      useAuth();
      return null;
    };
    // Suppress the expected React error-boundary console noise for this one assertion.
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<Broken />)).toThrow('useAuth must be used within an AuthProvider');
    spy.mockRestore();
  });
});
