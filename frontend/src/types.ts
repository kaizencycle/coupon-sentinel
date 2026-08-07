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
// Deal Intelligence Types (PR-1)
// ============================================================================

export type EvidenceType =
  | 'retailer_public'
  | 'receipt'
  | 'weekly_ad'
  | 'coupon_feed'
  | 'rebate_feed'
  | 'community_report'
  | 'manual';

export type ConfidenceLabel = 'LOW' | 'MEDIUM' | 'HIGH' | 'VERIFIED';

export type DealType =
  | 'sale'
  | 'clearance'
  | 'coupon'
  | 'rebate'
  | 'stack'
  | 'discontinued'
  | 'seasonal'
  | 'markdown'
  | 'penny_or_pull'
  | 'price_anomaly'
  | 'unknown';

export interface DealEvent {
  id: string;
  product_id: string;
  retailer: string;
  store_id?: string;
  zip_code?: string;
  deal_type: DealType;
  regular_price?: number;
  current_price: number;
  coupon_value: number;
  rebate_value: number;
  loyalty_savings: number;
  effective_price: number;
  savings_amount?: number;
  savings_percentage?: number;
  starts_at?: string;
  expires_at?: string;
  observed_at: string;
  observation_ids: string[];
  confidence: number;
  inventory_confirmed: boolean;
}

export interface DealEventDetail extends DealEvent {
  product_name: string;
  product_brand?: string;
  confidence_label: ConfidenceLabel;
  evidence_types: EvidenceType[];
  evidence_summary: string[];
  observation_count: number;
  receipt_verified: boolean;
  is_mock_data: boolean;
}

export interface PriceObservation {
  id: string;
  product_id: string;
  upc?: string;
  retailer: string;
  store_id?: string;
  zip_code?: string;
  observed_price: number;
  regular_price?: number;
  loyalty_price?: number;
  observed_at: string;
  evidence_type: EvidenceType;
  source?: string;
  confidence: number;
  in_stock?: boolean;
}

export interface PriceObservationDetail extends PriceObservation {
  product_name?: string;
  confidence_label: ConfidenceLabel;
  is_mock_data: boolean;
}

export interface DealsResponse {
  deals: DealEventDetail[];
  count: number;
  is_mock_data: boolean;
  notice: string;
}

export interface DealDetailResponse {
  deal: DealEventDetail;
  is_mock_data: boolean;
  notice: string;
}

export interface PriceObservationsResponse {
  observations: PriceObservationDetail[];
  count: number;
  is_mock_data: boolean;
  notice: string;
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
