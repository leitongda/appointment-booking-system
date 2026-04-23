import { createContext, useContext, type ReactNode, useEffect } from 'react';
import Taro from '@tarojs/taro';
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

  useEffect(() => {
    const envTemplateCode = process.env.TARO_APP_TEMPLATE_CODE || 'modern-general';
    if (templateCode !== envTemplateCode) {
      Taro.showToast({
        title: '已切换到默认主题',
        icon: 'none',
        duration: 2000,
      });
    }
  }, [templateCode]);

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
