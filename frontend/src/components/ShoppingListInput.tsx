import { useState } from 'react';
import type { ShoppingItem } from '../types';

interface Props {
  items: ShoppingItem[];
  onAdd: (item: ShoppingItem) => void;
  onRemove: (index: number) => void;
}

export function ShoppingListInput({ items, onAdd, onRemove }: Props) {
  const [name, setName] = useState('');
  const [quantity, setQuantity] = useState(1);
  const [unit, setUnit] = useState('count');

  const handleAdd = () => {
    if (!name.trim()) return;

    onAdd({
      name: name.trim(),
      quantity,
      unit,
      flexible: true,
    });

    setName('');
    setQuantity(1);
    setUnit('count');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleAdd();
    }
  };

  return (
    <div className="shopping-list-input">
      <h2>🛒 Shopping List</h2>

      <div className="add-item-form">
        <input
          type="text"
          placeholder="Item name (e.g., milk, eggs, bread)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={handleKeyDown}
          className="item-name-input"
        />

        <div className="quantity-group">
          <input
            type="number"
            min="1"
            value={quantity}
            onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
            className="quantity-input"
          />

          <select
            value={unit}
            onChange={(e) => setUnit(e.target.value)}
            className="unit-select"
          >
            <option value="count">count</option>
            <option value="lb">lb</option>
            <option value="oz">oz</option>
            <option value="gallon">gallon</option>
          </select>
        </div>

        <button onClick={handleAdd} className="add-button">
          + Add
        </button>
      </div>

      {items.length > 0 && (
        <ul className="items-list">
          {items.map((item, index) => (
            <li key={index} className="item-row">
              <span className="item-name">
                {item.quantity} {item.unit} of <strong>{item.name}</strong>
              </span>
              <button
                onClick={() => onRemove(index)}
                className="remove-button"
                title="Remove item"
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}

      {items.length === 0 && (
        <p className="empty-message">
          Add items to your shopping list to get started.
        </p>
      )}
    </div>
  );
}
