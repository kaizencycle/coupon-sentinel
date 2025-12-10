import type { OptimizeResponse } from '../types';

interface Props {
  result: OptimizeResponse;
}

export function OptimizedPlan({ result }: Props) {
  return (
    <div className="optimized-plan">
      <h2>📋 Your Shopping Plan</h2>

      {result.plans.map((plan, planIdx) => (
        <div key={planIdx} className="store-plan">
          <div className="store-header">
            <h3>
              {result.plans.length > 1 ? `Stop ${planIdx + 1}: ` : ''}
              {plan.store_name}
            </h3>
            <span className="store-total">${plan.final_total.toFixed(2)}</span>
          </div>

          <table className="items-table">
            <thead>
              <tr>
                <th>Item</th>
                <th>Product</th>
                <th>Qty</th>
                <th>Price</th>
                <th>Savings</th>
              </tr>
            </thead>
            <tbody>
              {plan.items.map((item, itemIdx) => (
                <tr key={itemIdx}>
                  <td className="requested-item">{item.requested_item.name}</td>
                  <td className="product-info">
                    <span className="brand">{item.chosen_product.brand}</span>
                    <span className="name">{item.chosen_product.item_name}</span>
                    <span className="size">
                      ({item.chosen_product.package_size}{' '}
                      {item.chosen_product.package_unit})
                    </span>
                  </td>
                  <td className="quantity">{item.quantity_to_buy}</td>
                  <td className="price">
                    <span className="final">${item.final_cost.toFixed(2)}</span>
                    {item.savings > 0 && (
                      <span className="base strikethrough">
                        ${item.base_cost.toFixed(2)}
                      </span>
                    )}
                  </td>
                  <td className="savings">
                    {item.savings > 0 && (
                      <span className="savings-amount">
                        -${item.savings.toFixed(2)}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={3}>Store Total</td>
                <td className="total-price">${plan.final_total.toFixed(2)}</td>
                <td className="total-savings">
                  {plan.estimated_savings > 0 && (
                    <span>-${plan.estimated_savings.toFixed(2)}</span>
                  )}
                </td>
              </tr>
            </tfoot>
          </table>

          {plan.items.some((i) => i.applied_coupons.length > 0) && (
            <div className="coupons-used">
              <h4>🎫 Coupons Applied</h4>
              <ul>
                {plan.items
                  .flatMap((i) => i.applied_coupons)
                  .filter((c, i, arr) => arr.findIndex((x) => x.coupon_id === c.coupon_id) === i)
                  .map((coupon, idx) => (
                    <li key={idx} className="coupon-item">
                      <span className="coupon-type">{coupon.coupon_type}</span>
                      <span className="coupon-desc">{coupon.description}</span>
                      <span className="coupon-value">
                        -${coupon.discount_amount.toFixed(2)}
                      </span>
                    </li>
                  ))}
              </ul>
            </div>
          )}
        </div>
      ))}

      {result.action_steps.length > 0 && (
        <div className="action-steps">
          <h3>📝 Step-by-Step Instructions</h3>
          <div className="steps-list">
            {result.action_steps.map((step, idx) => (
              <div
                key={idx}
                className={`step ${step.startsWith('**') ? 'header' : ''}`}
              >
                {step.replace(/\*\*/g, '')}
              </div>
            ))}
          </div>
        </div>
      )}

      {result.unfulfilled_items.length > 0 && (
        <div className="unfulfilled-items">
          <h3>⚠️ Items Not Found</h3>
          <ul>
            {result.unfulfilled_items.map((item, idx) => (
              <li key={idx}>
                {item.name} ({item.quantity} {item.unit})
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
