/**
 * @hospital/codegen — 低代码 Schema 代码生成器
 *
 * 将低代码编辑器的 Schema JSON 分析并生成 Taro TSX 或原生微信小程序代码。
 */

// Taro 代码生成
export { generatePage } from './generators/taro/page-generator';
export type { StateVariable, GeneratePageOptions } from './generators/taro/page-generator';

// 原生微信小程序代码生成
export {
  generateWxmlPage,
  generateWxml,
  collectEventHandlers,
  collectDataBindings,
  generateTemplateImport,
  generateWxsImport,
} from './generators/native/wxml-generator';
export type { GenerateWxmlOptions, CollectedHandler } from './generators/native/wxml-generator';

// Schema 分析
export {
  analyzeSchema,
  collectUsedComponents,
  extractDataSources,
  buildDependencyGraph,
} from './analyzer/schema-analyzer';
export type {
  DependencyEdge,
  ComponentSummary,
  WarningSeverity,
  AnalysisWarning,
  AnalysisResult,
} from './analyzer/schema-analyzer';
