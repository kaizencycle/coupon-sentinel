import { useEffect, useState } from 'react';
import { getStores } from '../api/client';

interface Props {
  selectedStores: string[];
  onToggle: (store: string) => void;
  allowMultiStore: boolean;
  onMultiStoreChange: (allow: boolean) => void;
}

export function StoreSelector({
  selectedStores,
  onToggle,
  allowMultiStore,
  onMultiStoreChange,
}: Props) {
  const [availableStores, setAvailableStores] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getStores()
      .then((response) => {
        setAvailableStores(response.stores);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load stores:', err);
        // Fallback stores
        setAvailableStores(['Target', 'Walmart', 'Costco']);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div className="store-selector">Loading stores...</div>;
  }

  return (
    <div className="store-selector">
      <h2>🏪 Stores</h2>

      <div className="stores-grid">
        {availableStores.map((store) => (
          <label key={store} className="store-checkbox">
            <input
              type="checkbox"
              checked={selectedStores.includes(store)}
              onChange={() => onToggle(store)}
            />
            <span className="store-name">{store}</span>
          </label>
        ))}
      </div>

      <div className="multi-store-toggle">
        <label className="toggle-label">
          <input
            type="checkbox"
            checked={allowMultiStore}
            onChange={(e) => onMultiStoreChange(e.target.checked)}
          />
          <span>
            Allow multi-store shopping
            <small> (split items across stores for max savings)</small>
          </span>
        </label>
      </div>

      {selectedStores.length === 0 && (
        <p className="warning-message">
          ⚠️ Select at least one store to optimize
        </p>
      )}
    </div>
  );
}
