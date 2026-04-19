import type { MiniappStyleTemplate } from './types';
import { modernGeneral } from './modern-general';
import { elderlyTcm } from './elderly-tcm';
import { premiumSpecialty } from './premium-specialty';
import { womensHealth } from './womens-health';
import { familyPediatrics } from './family-pediatrics';

const templateMap: Record<string, MiniappStyleTemplate> = {
  'modern-general': modernGeneral,
  'elderly-tcm': elderlyTcm,
  'premium-specialty': premiumSpecialty,
  'womens-health': womensHealth,
  'family-pediatrics': familyPediatrics,
};

const DEFAULT_TEMPLATE_CODE = 'modern-general';

/**
 * 确保模板配置完整性，缺失项从默认模板填充
 */
function ensureTemplateIntegrity(template: MiniappStyleTemplate): MiniappStyleTemplate {
  const defaultTemplate = templateMap[DEFAULT_TEMPLATE_CODE];
  const result = { ...template };

  // 检查 pageShellBindings 完整性
  const requiredShellKeys: (keyof MiniappStyleTemplate['pageShells'])[] = [
    'home', 'department', 'doctorList', 'doctorDetail', 'appointment', 'profile'
  ];

  if (!result.pageShells) {
    console.warn('[template-loader] 模板缺少 pageShells 配置，使用默认值');
    result.pageShells = { ...defaultTemplate.pageShells };
  } else {
    for (const key of requiredShellKeys) {
      if (!result.pageShells[key]) {
        console.warn(`[template-loader] 模板 ${result.code} 缺少 ${key} Shell 绑定，回退到默认模板`);
        result.pageShells[key] = defaultTemplate.pageShells[key];
      }
    }
  }

  // 检查 designTokens 完整性
  if (!result.designTokens) {
    console.warn('[template-loader] 模板缺少 designTokens 配置，使用默认值');
    result.designTokens = { ...defaultTemplate.designTokens };
  }

  // 检查 tone 配置完整性
  if (!result.tone) {
    console.warn('[template-loader] 模板缺少 tone 配置，使用默认值');
    result.tone = { ...defaultTemplate.tone };
  } else {
    // 确保必需的文案字段存在
    const requiredToneKeys = ['bookingLabel', 'patientLabel', 'addressMode', 'emptyBookingText', 'confirmSuccessText'];
    for (const key of requiredToneKeys) {
      if (!result.tone[key]) {
        result.tone[key] = defaultTemplate.tone[key];
      }
    }
  }

  // 检查 navSchema 完整性
  if (!result.navSchema || !result.navSchema.tabs || result.navSchema.tabs.length === 0) {
    console.warn('[template-loader] 模板 navSchema 配置异常，使用默认值');
    result.navSchema = { ...defaultTemplate.navSchema };
  }

  // 检查 homeSchema 完整性
  if (!result.homeSchema || result.homeSchema.length === 0) {
    console.warn('[template-loader] 模板 homeSchema 配置异常，使用默认值');
    result.homeSchema = [...defaultTemplate.homeSchema];
  }

  return result;
}

export function loadTemplate(code?: string): MiniappStyleTemplate {
  const templateCode = code || process.env.TARO_APP_TEMPLATE_CODE || DEFAULT_TEMPLATE_CODE;
  const template = templateMap[templateCode];

  if (!template) {
    console.warn(`[template-loader] 模板 "${templateCode}" 未找到，回退到默认模板`);
    return ensureTemplateIntegrity({ ...templateMap[DEFAULT_TEMPLATE_CODE] });
  }

  try {
    return ensureTemplateIntegrity({ ...template });
  } catch (error) {
    console.error(`[template-loader] 模板 "${templateCode}" 配置损坏:`, error);
    console.warn('[template-loader] 回退到默认模板');
    return ensureTemplateIntegrity({ ...templateMap[DEFAULT_TEMPLATE_CODE] });
  }
}

export function getTemplateCode(): string {
  return process.env.TARO_APP_TEMPLATE_CODE || DEFAULT_TEMPLATE_CODE;
}

export function getTemplateVersion(): string {
  return process.env.TARO_APP_TEMPLATE_VERSION || '1.0.0';
}

export { modernGeneral, elderlyTcm, premiumSpecialty, womensHealth, familyPediatrics };
