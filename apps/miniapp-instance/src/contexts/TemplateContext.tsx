import { createContext, useContext, type ReactNode } from 'react';
import { loadTemplate } from '../templates/loader';
import type { MiniappStyleTemplate, DesignTokenSet, CopyToneConfig } from '../templates/types';

interface TemplateContextValue {
  template: MiniappStyleTemplate;
  tokens: DesignTokenSet;
  tone: CopyToneConfig;
  templateCode: string;
}

const TemplateContext = createContext<TemplateContextValue | null>(null);

interface TemplateProviderProps {
  children: ReactNode;
}

export function TemplateProvider({ children }: TemplateProviderProps) {
  const template = loadTemplate();
  const templateCode = template.code;

  return (
    <TemplateContext.Provider
      value={{
        template,
        tokens: template.designTokens,
        tone: template.tone,
        templateCode,
      }}
    >
      {children}
    </TemplateContext.Provider>
  );
}

export function useTemplate(): TemplateContextValue {
  const ctx = useContext(TemplateContext);
  if (!ctx) {
    throw new Error('useTemplate must be used within TemplateProvider');
  }
  return ctx;
}

export function useTemplateTokens(): DesignTokenSet {
  return useTemplate().tokens;
}

export function useTemplateTone(): CopyToneConfig {
  return useTemplate().tone;
}
