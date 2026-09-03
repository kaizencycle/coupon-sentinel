import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ShoppingListInput } from './ShoppingListInput';
import type { ShoppingItem } from '../types';

describe('ShoppingListInput', () => {
  it('shows the empty-state message when the list has no items', () => {
    render(<ShoppingListInput items={[]} onAdd={vi.fn()} onRemove={vi.fn()} />);
    expect(screen.getByText(/Add items to your shopping list/i)).toBeInTheDocument();
  });

  it('adds an item with the entered name, quantity, and unit when "Add" is clicked', async () => {
    const onAdd = vi.fn();
    render(<ShoppingListInput items={[]} onAdd={onAdd} onRemove={vi.fn()} />);

    await userEvent.type(screen.getByPlaceholderText(/milk, eggs, bread/i), 'milk');
    await userEvent.click(screen.getByRole('button', { name: /\+ Add/i }));

    expect(onAdd).toHaveBeenCalledWith({
      name: 'milk',
      quantity: 1,
      unit: 'count',
      flexible: true,
    });
  });

  it('adds an item when Enter is pressed in the name field', async () => {
    const onAdd = vi.fn();
    render(<ShoppingListInput items={[]} onAdd={onAdd} onRemove={vi.fn()} />);

    const nameInput = screen.getByPlaceholderText(/milk, eggs, bread/i);
    await userEvent.type(nameInput, 'eggs{Enter}');

    expect(onAdd).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'eggs', quantity: 1, unit: 'count' })
    );
  });

  it('does not add an item when the name field is blank', async () => {
    const onAdd = vi.fn();
    render(<ShoppingListInput items={[]} onAdd={onAdd} onRemove={vi.fn()} />);

    await userEvent.click(screen.getByRole('button', { name: /\+ Add/i }));

    expect(onAdd).not.toHaveBeenCalled();
  });

  it('clears the name field after a successful add', async () => {
    render(<ShoppingListInput items={[]} onAdd={vi.fn()} onRemove={vi.fn()} />);

    const nameInput = screen.getByPlaceholderText(/milk, eggs, bread/i) as HTMLInputElement;
    await userEvent.type(nameInput, 'bread{Enter}');

    expect(nameInput.value).toBe('');
  });

  it('renders existing items and calls onRemove with the right index', async () => {
    const items: ShoppingItem[] = [
      { name: 'milk', quantity: 1, unit: 'gallon', flexible: true },
      { name: 'eggs', quantity: 12, unit: 'count', flexible: true },
    ];
    const onRemove = vi.fn();
    render(<ShoppingListInput items={items} onAdd={vi.fn()} onRemove={onRemove} />);

    expect(screen.getByText('milk')).toBeInTheDocument();
    expect(screen.getByText('eggs')).toBeInTheDocument();

    const removeButtons = screen.getAllByTitle('Remove item');
    await userEvent.click(removeButtons[1]);

    expect(onRemove).toHaveBeenCalledWith(1);
  });
});
