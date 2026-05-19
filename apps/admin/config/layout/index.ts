/**
 * Layout 配置桶导出
 *
 * - 默认导出：构建期 umi `defineConfig.layout` 配置（由 `config.ts` 消费）
 * - 命名导出 `runtimeSettings`：ProLayout 运行时默认设置（由 `src/app.tsx` 消费）
 */
export { default as runtimeSettings } from './runtime-settings';
export { default } from './settings';
