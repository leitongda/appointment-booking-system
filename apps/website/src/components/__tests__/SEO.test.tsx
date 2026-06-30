import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { HelmetProvider } from 'react-helmet-async';
import { SEO } from '../SEO';

function renderWithHelmet(ui: React.ReactElement) {
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <HelmetProvider>{children as any}</HelmetProvider>
  );

  return render(ui, { wrapper: Wrapper });
}

describe('SEO', () => {
  it('sets page title with site name suffix', () => {
    renderWithHelmet(<SEO title="产品" />);
    expect(document.title).toBe('产品 | 医院挂号系统');
  });

  it('sets default title when no title prop', () => {
    renderWithHelmet(<SEO />);
    expect(document.title).toBe('医院挂号系统');
  });

  it('sets meta description', () => {
    renderWithHelmet(<SEO description="Test description" />);
    const meta = document.querySelector('meta[name="description"]');
    expect(meta).toHaveAttribute('content', 'Test description');
  });

  it('sets Open Graph tags', () => {
    renderWithHelmet(<SEO title="Test" description="Desc" type="website" />);
    expect(document.querySelector('meta[property="og:title"]')).toHaveAttribute(
      'content',
      'Test | 医院挂号系统',
    );
    expect(document.querySelector('meta[property="og:description"]')).toHaveAttribute(
      'content',
      'Desc',
    );
    expect(document.querySelector('meta[property="og:type"]')).toHaveAttribute(
      'content',
      'website',
    );
  });
});
