import { afterEach, describe, expect, it, vi } from 'vitest';
import { getProfile, loginUser, optimizeShoppingList } from './client';
import type { OptimizeRequest } from '../types';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const baseRequest: OptimizeRequest = {
  shopping_list: [{ name: 'milk', quantity: 1, unit: 'gallon', flexible: true }],
  zip_code: '11566',
  preferred_stores: ['Target'],
  allow_multi_store: false,
  rebate_apps: [],
};

describe('fetchAPI (via the exported client functions)', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('resolves with the parsed JSON body on a successful response', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ status: 'ok', version: '1' }));
    vi.stubGlobal('fetch', fetchMock);

    const result = await loginUser('a@example.com', 'password123');
    expect(result).toEqual({ status: 'ok', version: '1' });
  });

  it('extracts FastAPI\'s {"detail": ...} error shape into the thrown message', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ detail: 'Invalid email or password' }, 401));
    vi.stubGlobal('fetch', fetchMock);

    await expect(loginUser('a@example.com', 'wrong')).rejects.toThrow(
      'Invalid email or password'
    );
  });

  it('falls back to the raw response text when the error body is not JSON', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('Internal Server Error', { status: 500 })
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(loginUser('a@example.com', 'x')).rejects.toThrow('Internal Server Error');
  });

  it('falls back to a generic message when the error body is empty', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('', { status: 503 }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(loginUser('a@example.com', 'x')).rejects.toThrow('API Error (503)');
  });

  it('sends an Authorization header built from the access token', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ email: 'a@example.com' }));
    vi.stubGlobal('fetch', fetchMock);

    await getProfile('token-abc');

    const [, init] = fetchMock.mock.calls[0];
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBe('Bearer token-abc');
  });
});

describe('optimizeShoppingList', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('omits the Authorization header for anonymous calls', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ plans: [], grand_total: 0, total_savings: 0 })
    );
    vi.stubGlobal('fetch', fetchMock);

    await optimizeShoppingList(baseRequest);

    const [, init] = fetchMock.mock.calls[0];
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
  });

  it('sends the Authorization header when a signed-in access token is provided', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ plans: [], grand_total: 0, total_savings: 0 })
    );
    vi.stubGlobal('fetch', fetchMock);

    await optimizeShoppingList(baseRequest, 'signed-in-token');

    const [, init] = fetchMock.mock.calls[0];
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBe('Bearer signed-in-token');
  });

  it('sends the shopping list as the JSON request body', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ plans: [], grand_total: 0, total_savings: 0 })
    );
    vi.stubGlobal('fetch', fetchMock);

    await optimizeShoppingList(baseRequest, null);

    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(init.body as string)).toEqual(baseRequest);
  });
});
