/**
 * Coupon Sentinel - TypeScript Type Definitions
 */

// ============================================================================
// Request Types
// ============================================================================

export interface ShoppingItem {
  name: string;
  quantity: number;
  unit: string;
  brand_preference?: string;
  flexible: boolean;
}

export interface OptimizeRequest {
  shopping_list: ShoppingItem[];
  zip_code: string;
  preferred_stores: string[];
  allow_multi_store: boolean;
  rebate_apps: string[];
}

// ============================================================================
// Response Types
// ============================================================================

export interface StoreItem {
  store_name: string;
  item_name: string;
  brand?: string;
  package_size: number;
  package_unit: string;
  price: number;
  regular_price?: number;
  category: string;
  unit_price: number;
  in_stock: boolean;
}

export interface AppliedCoupon {
  coupon_id: string;
  description: string;
  coupon_type: 'manufacturer' | 'store' | 'rebate' | 'bogo' | 'threshold';
  discount_amount: number;
}

export interface OptimizedItem {
  requested_item: ShoppingItem;
  chosen_product: StoreItem;
  quantity_to_buy: number;
  base_cost: number;
  applied_coupons: AppliedCoupon[];
  final_cost: number;
  savings: number;
  notes: string[];
}

export interface StorePlan {
  store_name: string;
  items: OptimizedItem[];
  subtotal: number;
  store_level_discounts: AppliedCoupon[];
  final_total: number;
  estimated_savings: number;
}

export interface RebateOpportunity {
  app: string;
  item: string;
  rebate_amount: number;
  instructions: string;
}

export interface OptimizeResponse {
  plans: StorePlan[];
  grand_total: number;
  total_base_cost: number;
  total_savings: number;
  savings_percentage: number;
  unfulfilled_items: ShoppingItem[];
  action_steps: string[];
  rebate_opportunities: RebateOpportunity[];
}

// ============================================================================
// List Response Types
// ============================================================================

export interface StoresResponse {
  stores: string[];
  count: number;
}

export interface ItemsResponse {
  items: {
    store: string;
    name: string;
    brand?: string;
    price: number;
    size: string;
    unit_price: number;
    category: string;
  }[];
  count: number;
}

export interface CouponsResponse {
  coupons: {
    id: string;
    type: string;
    store: string;
    description: string;
    value: number;
    item_filter: string;
    source: string;
  }[];
  count: number;
}

// ============================================================================
// UI State Types
// ============================================================================

export interface AppState {
  shoppingList: ShoppingItem[];
  preferredStores: string[];
  allowMultiStore: boolean;
  zipCode: string;
  rebateApps: string[];
  isLoading: boolean;
  error: string | null;
  result: OptimizeResponse | null;
}
