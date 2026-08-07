import type { DealEventDetail } from '../types';

function formatPrice(value: number): string {
  return value.toFixed(2);
}

function formatDealType(dealType: string): string {
  if (dealType === 'penny_or_pull') return 'PENNY/PULL';
  return dealType.toUpperCase().replace(/_/g, ' ');
}

interface DealsViewProps {
  deals: DealEventDetail[];
  isLoading: boolean;
  error: string | null;
  notice?: string;
}

export function DealsView({ deals, isLoading, error, notice }: DealsViewProps) {
  if (isLoading) {
    return <div className="deals-loading">Loading deal intelligence…</div>;
  }

  if (error) {
    return <div className="error-message">❌ {error}</div>;
  }

  return (
    <div className="deals-view">
      <div className="deals-header">
        <h2>📊 Consumer Deal Intelligence</h2>
        <p className="deals-subtitle">
          Evidence-backed prices from mock fixtures — not live retailer data.
        </p>
        {notice && <p className="mock-notice">{notice}</p>}
      </div>

      <div className="deals-grid">
        {deals.map((deal) => (
          <article key={deal.id} className="deal-card">
            <header className="deal-card-header">
              <h3>{deal.product_name}</h3>
              {deal.product_brand && (
                <span className="deal-brand">{deal.product_brand}</span>
              )}
            </header>

            <div className="deal-retailer">
              <span>{deal.retailer}</span>
              {deal.zip_code && <span className="deal-zip">ZIP {deal.zip_code}</span>}
            </div>

            <div className="deal-prices">
              {deal.regular_price != null && deal.regular_price !== deal.current_price && (
                <span className="price-regular">${formatPrice(deal.regular_price)}</span>
              )}
              {deal.current_price !== deal.effective_price && (
                <span className="price-current">${formatPrice(deal.current_price)}</span>
              )}
              <span className="price-effective">
                ${formatPrice(deal.effective_price)} effective
              </span>
            </div>

            {deal.savings_percentage != null && deal.savings_percentage > 0 && (
              <div className="deal-savings">
                {deal.savings_percentage}% savings
              </div>
            )}

            <div className="deal-type-badge">{formatDealType(deal.deal_type)}</div>

            <div className="deal-evidence">
              <strong>Evidence:</strong>
              <ul>
                {deal.evidence_summary.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </div>

            <div className="deal-meta">
              <span className={`confidence-badge confidence-${deal.confidence_label.toLowerCase()}`}>
                Confidence: {deal.confidence_label}
              </span>
              <span className={`inventory-badge ${deal.inventory_confirmed ? 'confirmed' : 'uncertain'}`}>
                {deal.inventory_confirmed
                  ? 'Inventory confirmed'
                  : 'Inventory not confirmed'}
              </span>
            </div>
          </article>
        ))}
      </div>

      {deals.length === 0 && (
        <p className="deals-empty">No deals match the current filters.</p>
      )}
    </div>
  );
}
