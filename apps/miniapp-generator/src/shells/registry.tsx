import type { ComponentType } from 'react';

type ShellComponent = ComponentType<any>;

interface ShellRegistry {
  [pagePath: string]: {
    [variantId: string]: ShellComponent;
  };
}

const registry: ShellRegistry = {};

export function registerShell(pagePath: string, variantId: string, component: ShellComponent) {
  if (!registry[pagePath]) {
    registry[pagePath] = {};
  }
  registry[pagePath][variantId] = component;
}

export function resolveShell(pagePath: string, variantId: string): ShellComponent | null {
  const page = registry[pagePath];
  if (!page) return null;
  return page[variantId] || page['standard'] || null;
}

export function getRegisteredShells(): ShellRegistry {
  return { ...registry };
}
