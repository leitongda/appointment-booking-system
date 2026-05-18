import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';
import { Login } from '../Login';

// Mock @hospital/api
vi.mock('@hospital/api', () => ({
  request: {
    get: vi.fn(),
    post: vi.fn(),
  },
  rsaEncrypt: vi.fn((pwd: string) => `encrypted:${pwd}`),
  setPublicKey: vi.fn(),
}));

// Mock @hospital/shared
vi.mock('@hospital/shared', () => ({
  setToken: vi.fn(),
  setStorage: vi.fn(),
  STORAGE_KEYS: { REFRESH_TOKEN: 'hospital_refresh_token' },
}));

function renderLogin() {
  return render(
    <HelmetProvider>
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    </HelmetProvider>,
  );
}

describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders login form with inputs and button', () => {
    renderLogin();
    expect(screen.getByLabelText(/管理员账号/)).toBeInTheDocument();
    expect(screen.getByLabelText(/登录密码/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '登录' })).toBeInTheDocument();
  });

  it('renders register link', () => {
    renderLogin();
    expect(screen.getByRole('link', { name: '免费注册' })).toBeInTheDocument();
  });

  it('sets page title', () => {
    renderLogin();
    expect(document.title).toContain('登录');
  });

  it('validates empty username on form submit', async () => {
    renderLogin();
    const form = screen.getByRole('button', { name: '登录' }).closest('form')!;
    fireEvent.submit(form);
    // Validation should set error state
    // The error message appears as a sibling of the input
    expect(await screen.findByText('请输入管理员账号')).toBeInTheDocument();
  });
});
