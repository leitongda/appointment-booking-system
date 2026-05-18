import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { Header } from '../Header';

function renderHeader(path = '/') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Header />
    </MemoryRouter>,
  );
}

describe('Header', () => {
  it('renders site title', () => {
    renderHeader();
    expect(screen.getByText('医院挂号系统')).toBeInTheDocument();
  });

  it('renders navigation links on desktop', () => {
    renderHeader();
    expect(screen.getByRole('link', { name: '首页' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '产品' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '体验' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '定价' })).toBeInTheDocument();
  });

  it('renders login and register buttons', () => {
    renderHeader();
    expect(screen.getByRole('link', { name: '登录' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '免费试用' })).toBeInTheDocument();
  });

  it('highlights active nav item for home', () => {
    renderHeader('/');
    const homeLink = screen.getByRole('link', { name: '首页' });
    expect(homeLink.className).toContain('text-foreground');
  });

  it('highlights active nav item for products', () => {
    renderHeader('/products');
    const productsLink = screen.getByRole('link', { name: '产品' });
    expect(productsLink.className).toContain('text-foreground');
  });

  it('shows hamburger menu button on mobile', () => {
    renderHeader();
    const menuButton = screen.getByRole('button', { name: '打开菜单' });
    expect(menuButton).toBeInTheDocument();
    expect(menuButton.className).toContain('md:hidden');
  });

  it('opens mobile drawer when hamburger is clicked', async () => {
    renderHeader();
    const menuButton = screen.getByRole('button', { name: '打开菜单' });
    await userEvent.click(menuButton);
    // Drawer should appear with navigation text
    expect(screen.getByText('导航')).toBeInTheDocument();
    // Close button should exist in the drawer
    const closeButtons = screen.getAllByRole('button', { name: '关闭菜单' });
    expect(closeButtons.length).toBeGreaterThanOrEqual(1);
  });
});
