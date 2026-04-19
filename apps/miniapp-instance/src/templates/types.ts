// 模板类型 — 从 @hospital/shared 导入
// 此文件作为过渡入口，后续直接从 shared 包导入

export interface NavTab {
  pagePath: string;
  text: string;
  iconKey: string;
  activeIconKey: string;
}

export interface NavSchema {
  tabs: NavTab[];
  height: number;
}

export interface HomeModuleSchema {
  id: string;
  type: string;
  visible: boolean;
  order: number;
  config: Record<string, any>;
}

export interface DesignTokenSet {
  primary: string;
  primarySoft: string;
  accent: string;
  bodyFontSize?: number;
  displayFontSize?: number;
  radiusMd?: number;
  radiusLg?: number;
  spacingMultiplier?: number;
  touchTargetMin?: number;
  customColors?: Record<string, string>;
}

export interface TemplateAssetSet {
  iconStyle: 'filled' | 'outlined' | 'thin' | 'bold';
  tabBarIconStyle: 'filled' | 'outlined';
  decorationStyle: 'none' | 'minimal' | 'playful' | 'traditional' | 'floral';
}

export interface CopyToneConfig {
  bookingLabel: string;
  patientLabel: string;
  addressMode: string;
  emptyBookingText: string;
  confirmSuccessText: string;
  custom?: Record<string, string>;
}

export interface TemplateConstraints {
  lockedPages: string[];
  forceElderMode: boolean;
  confirmBeforeAction: boolean;
}

export interface MiniappStyleTemplate {
  code: string;
  name: string;
  description: string;
  category: string;
  audience: string[];
  navSchema: NavSchema;
  homeSchema: HomeModuleSchema[];
  pageShells: Record<string, string>;
  designTokens: DesignTokenSet;
  assets: TemplateAssetSet;
  tone: CopyToneConfig;
  constraints: TemplateConstraints;
}
