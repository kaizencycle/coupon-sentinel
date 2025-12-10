import { useState } from 'react';
import { ShoppingListInput } from './components/ShoppingListInput';
import { StoreSelector } from './components/StoreSelector';
import { SavingsSummary } from './components/SavingsSummary';
import { OptimizedPlan } from './components/OptimizedPlan';
import { optimizeShoppingList } from './api/client';
import type { ShoppingItem, OptimizeResponse } from './types';
import './App.css';

function App() {
  // State
  const [shoppingList, setShoppingList] = useState<ShoppingItem[]>([]);
  const [selectedStores, setSelectedStores] = useState<string[]>(['Target', 'Walmart']);
  const [allowMultiStore, setAllowMultiStore] = useState(false);
  const [zipCode, setZipCode] = useState('11566');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OptimizeResponse | null>(null);

  // Handlers
  const handleAddItem = (item: ShoppingItem) => {
    setShoppingList([...shoppingList, item]);
    setResult(null); // Clear previous results
  };

  const handleRemoveItem = (index: number) => {
    setShoppingList(shoppingList.filter((_, i) => i !== index));
    setResult(null);
  };

  const handleToggleStore = (store: string) => {
    if (selectedStores.includes(store)) {
      setSelectedStores(selectedStores.filter((s) => s !== store));
    } else {
      setSelectedStores([...selectedStores, store]);
    }
    setResult(null);
  };

  const handleOptimize = async () => {
    if (shoppingList.length === 0) {
      setError('Please add at least one item to your shopping list.');
      return;
    }

    if (selectedStores.length === 0) {
      setError('Please select at least one store.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await optimizeShoppingList({
        shopping_list: shoppingList,
        zip_code: zipCode,
        preferred_stores: selectedStores,
        allow_multi_store: allowMultiStore,
        rebate_apps: ['Ibotta', 'Fetch'],
      });

      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Optimization failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setShoppingList([]);
    setResult(null);
    setError(null);
  };

  return (
    <div className="app">
      <header className="header">
        <h1>🛒 Coupon Sentinel</h1>
        <p className="tagline">Extreme couponing, automated.</p>
      </header>

      <main className="main">
        <div className="input-section">
          <ShoppingListInput
            items={shoppingList}
            onAdd={handleAddItem}
            onRemove={handleRemoveItem}
          />

          <StoreSelector
            selectedStores={selectedStores}
            onToggle={handleToggleStore}
            allowMultiStore={allowMultiStore}
            onMultiStoreChange={setAllowMultiStore}
          />

          <div className="zip-code-section">
            <label>
              📍 Zip Code:
              <input
                type="text"
                value={zipCode}
                onChange={(e) => setZipCode(e.target.value)}
                maxLength={5}
                className="zip-input"
              />
            </label>
          </div>

          <div className="actions">
            <button
              onClick={handleOptimize}
              disabled={isLoading || shoppingList.length === 0}
              className="optimize-button"
            >
              {isLoading ? '⏳ Finding Best Deals...' : '🔍 Find Best Deals'}
            </button>

            {(result || shoppingList.length > 0) && (
              <button onClick={handleReset} className="reset-button">
                🔄 Start Over
              </button>
            )}
          </div>

          {error && <div className="error-message">❌ {error}</div>}
        </div>

        {result && (
          <div className="results-section">
            <SavingsSummary result={result} />
            <OptimizedPlan result={result} />
          </div>
        )}
      </main>

      <footer className="footer">
        <p>
          Coupon Sentinel v0.1 • Built for real people, not corporations •{' '}
          <a href="https://github.com/kaizencycle/coupon-sentinel">GitHub</a>
        </p>
      </footer>
    </div>
  );
}

export default App;
