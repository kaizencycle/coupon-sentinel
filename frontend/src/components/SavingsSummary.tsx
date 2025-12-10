import type { OptimizeResponse } from '../types';

interface Props {
  result: OptimizeResponse;
}

export function SavingsSummary({ result }: Props) {
  const savingsClass =
    result.savings_percentage >= 20
      ? 'excellent'
      : result.savings_percentage >= 10
      ? 'good'
      : 'modest';

  return (
    <div className={`savings-summary ${savingsClass}`}>
      <div className="summary-card">
        <div className="summary-header">
          <h2>💰 Your Savings</h2>
        </div>

        <div className="summary-stats">
          <div className="stat">
            <span className="stat-label">You Pay</span>
            <span className="stat-value">${result.grand_total.toFixed(2)}</span>
          </div>

          <div className="stat">
            <span className="stat-label">Without Coupons</span>
            <span className="stat-value strikethrough">
              ${result.total_base_cost.toFixed(2)}
            </span>
          </div>

          <div className="stat highlight">
            <span className="stat-label">You Save</span>
            <span className="stat-value savings">
              ${result.total_savings.toFixed(2)}
              <span className="percentage">
                ({result.savings_percentage.toFixed(1)}%)
              </span>
            </span>
          </div>
        </div>

        <div className="stores-summary">
          <span className="stores-label">Shopping at:</span>
          <span className="stores-list">
            {result.plans.map((p) => p.store_name).join(' → ')}
          </span>
        </div>
      </div>

      {result.rebate_opportunities.length > 0 && (
        <div className="rebates-card">
          <h3>📱 Bonus Rebates Available</h3>
          <ul className="rebates-list">
            {result.rebate_opportunities.map((rebate, idx) => (
              <li key={idx} className="rebate-item">
                <span className="rebate-app">{rebate.app}</span>
                <span className="rebate-amount">
                  +${rebate.rebate_amount.toFixed(2)}
                </span>
                <span className="rebate-item-name">{rebate.item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
