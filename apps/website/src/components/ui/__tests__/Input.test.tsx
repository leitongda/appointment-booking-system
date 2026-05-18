import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { Input } from '../Input';

describe('Input', () => {
  it('renders with label', () => {
    render(<Input label="Username" />);
    expect(screen.getByLabelText('Username')).toBeInTheDocument();
  });

  it('displays error message', () => {
    render(<Input label="Email" error="Invalid email" />);
    expect(screen.getByText('Invalid email')).toBeInTheDocument();
    const input = screen.getByLabelText('Email');
    expect(input.className).toContain('border-red-500');
  });

  it('displays hint when no error', () => {
    render(<Input label="Password" hint="At least 6 characters" />);
    expect(screen.getByText('At least 6 characters')).toBeInTheDocument();
  });

  it('hides hint when error is present', () => {
    render(<Input label="Password" hint="At least 6 characters" error="Too short" />);
    expect(screen.queryByText('At least 6 characters')).not.toBeInTheDocument();
    expect(screen.getByText('Too short')).toBeInTheDocument();
  });

  it('handles user input', async () => {
    const onChange = vi.fn();
    render(<Input label="Name" onChange={onChange} />);
    await userEvent.type(screen.getByLabelText('Name'), 'test');
    expect(onChange).toHaveBeenCalled();
  });

  it('renders with left icon', () => {
    render(<Input label="Search" leftIcon={<span data-testid="icon">@</span>} />);
    expect(screen.getByTestId('icon')).toBeInTheDocument();
  });
});
