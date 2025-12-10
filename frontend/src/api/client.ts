/**
 * Coupon Sentinel - API Client
 */

import type {
  OptimizeRequest,
  OptimizeResponse,
  StoresResponse,
  ItemsResponse,
  CouponsResponse,
} from '../types';

// Use relative URL in development (Vite proxy handles it)
// In production, set VITE_API_URL environment variable
const API_BASE = import.meta.env.VITE_API_URL || '';

/**
 * Generic fetch wrapper with error handling
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
    throw new Error(`API Error (${response.status}): ${errorText}`);
  }

  return response.json();
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Optimize a shopping list
 */
export async function optimizeShoppingList(
  request: OptimizeRequest
): Promise<OptimizeResponse> {
  return fetchAPI<OptimizeResponse>('/api/optimize', {
    method: 'POST',
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
