/**
 * Coupon Sentinel - API Client
 */

import type {
  OptimizeRequest,
  OptimizeResponse,
  StoresResponse,
  ItemsResponse,
  CouponsResponse,
  DealsResponse,
  DealDetailResponse,
  PriceObservationsResponse,
  AuthTokens,
  UserProfile,
  PlansResponse,
  CreateSubscriptionResponse,
  CancelSubscriptionResponse,
  SubscriptionStatus,
  ApiErrorBody,
} from '../types';

// Use relative URL in development (Vite proxy handles it)
// In production, set VITE_API_URL environment variable
const API_BASE = import.meta.env.VITE_API_URL || '';

/**
 * Generic fetch wrapper with error handling. Extracts FastAPI's
 * {"detail": "..."} error shape when present so callers get a readable
 * message ("Invalid email or password") instead of raw JSON text.
 */
async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    let message = errorText;
    try {
      const parsed = JSON.parse(errorText) as ApiErrorBody;
      if (parsed.detail) message = parsed.detail;
    } catch {
      // Not JSON — use the raw text as-is.
    }
    throw new Error(message || `API Error (${response.status})`);
  }

  return response.json();
}

function authHeaders(accessToken: string): HeadersInit {
  return { Authorization: `Bearer ${accessToken}` };
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Optimize a shopping list
 */
export async function optimizeShoppingList(
  request: OptimizeRequest,
  accessToken?: string | null
): Promise<OptimizeResponse> {
  return fetchAPI<OptimizeResponse>('/api/optimize', {
    method: 'POST',
    headers: accessToken ? authHeaders(accessToken) : undefined,
    body: JSON.stringify(request),
  });
}

/**
 * Get available stores
 */
export async function getStores(): Promise<StoresResponse> {
  return fetchAPI<StoresResponse>('/api/stores');
}

/**
 * Get available items
 */
export async function getItems(
  store?: string,
  category?: string
): Promise<ItemsResponse> {
  const params = new URLSearchParams();
  if (store) params.append('store', store);
  if (category) params.append('category', category);
  const query = params.toString();
  return fetchAPI<ItemsResponse>(`/api/items${query ? `?${query}` : ''}`);
}

/**
 * Get available coupons
 */
export async function getCoupons(
  store?: string,
  type?: string
): Promise<CouponsResponse> {
  const params = new URLSearchParams();
  if (store) params.append('store', store);
  if (type) params.append('coupon_type', type);
  const query = params.toString();
  return fetchAPI<CouponsResponse>(`/api/coupons${query ? `?${query}` : ''}`);
}

/**
 * Health check
 */
export async function healthCheck(): Promise<{
  status: string;
  version: string;
  database: string;
  features: Record<string, boolean>;
}> {
  return fetchAPI('/health');
}

/**
 * List deal events (mock fixture data)
 */
export async function getDeals(params?: {
  zip_code?: string;
  retailer?: string;
  deal_type?: string;
  product_id?: string;
}): Promise<DealsResponse> {
  const search = new URLSearchParams();
  if (params?.zip_code) search.append('zip_code', params.zip_code);
  if (params?.retailer) search.append('retailer', params.retailer);
  if (params?.deal_type) search.append('deal_type', params.deal_type);
  if (params?.product_id) search.append('product_id', params.product_id);
  const query = search.toString();
  return fetchAPI<DealsResponse>(`/api/deals${query ? `?${query}` : ''}`);
}

/**
 * Get a single deal by ID
 */
export async function getDeal(dealId: string): Promise<DealDetailResponse> {
  return fetchAPI<DealDetailResponse>(`/api/deals/${dealId}`);
}

/**
 * List price observations (evidence layer)
 */
export async function getPriceObservations(params?: {
  zip_code?: string;
  retailer?: string;
  product_id?: string;
  evidence_type?: string;
}): Promise<PriceObservationsResponse> {
  const search = new URLSearchParams();
  if (params?.zip_code) search.append('zip_code', params.zip_code);
  if (params?.retailer) search.append('retailer', params.retailer);
  if (params?.product_id) search.append('product_id', params.product_id);
  if (params?.evidence_type) search.append('evidence_type', params.evidence_type);
  const query = search.toString();
  return fetchAPI<PriceObservationsResponse>(
    `/api/price-observations${query ? `?${query}` : ''}`
  );
}

// ============================================================================
// Auth (Milestone 4)
// ============================================================================

export async function registerUser(email: string, password: string): Promise<AuthTokens> {
  return fetchAPI<AuthTokens>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function loginUser(email: string, password: string): Promise<AuthTokens> {
  return fetchAPI<AuthTokens>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function refreshTokens(refreshToken: string): Promise<AuthTokens> {
  return fetchAPI<AuthTokens>('/api/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export async function getProfile(accessToken: string): Promise<UserProfile> {
  return fetchAPI<UserProfile>('/api/user/profile', {
    headers: authHeaders(accessToken),
  });
}

export async function resendVerificationEmail(accessToken: string): Promise<{ status: string }> {
  return fetchAPI<{ status: string }>('/api/auth/resend-verification', {
    method: 'POST',
    headers: authHeaders(accessToken),
  });
}

export async function verifyEmail(token: string): Promise<{ status: string; email: string }> {
  return fetchAPI<{ status: string; email: string }>('/api/auth/verify-email', {
    method: 'POST',
    body: JSON.stringify({ token }),
  });
}

// ============================================================================
// Subscriptions / Billing (Milestone 4)
// ============================================================================

export async function listPlans(): Promise<PlansResponse> {
  return fetchAPI<PlansResponse>('/api/subscriptions/plans');
}

export async function createSubscription(
  accessToken: string,
  tier: 'pro' | 'premium'
): Promise<CreateSubscriptionResponse> {
  return fetchAPI<CreateSubscriptionResponse>('/api/user/subscription', {
    method: 'POST',
    headers: authHeaders(accessToken),
    body: JSON.stringify({ tier }),
  });
}

export async function cancelSubscription(accessToken: string): Promise<CancelSubscriptionResponse> {
  return fetchAPI<CancelSubscriptionResponse>('/api/user/subscription', {
    method: 'DELETE',
    headers: authHeaders(accessToken),
  });
}

export async function getSubscriptionStatus(accessToken: string): Promise<SubscriptionStatus> {
  return fetchAPI<SubscriptionStatus>('/api/user/subscription', {
    headers: authHeaders(accessToken),
  });
}
