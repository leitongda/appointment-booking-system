import { defineConfig } from 'vitest/config';
import path from 'node:path';

/**
 * Vitest 配置（apps/admin）
 *
 * 背景：
 *   - 之前没有 vitest 配置，Vitest 走默认值，会把 `e2e/**` 下的 Playwright
 *     `*.spec.ts` 误拾取进来（它们只在 @playwright/test runner 下有意义），
 *     导致 `npx vitest run` 报大量「test.describe() 调用位置不对」的失败。
 *   - 单元测试里需要用项目的路径别名（`@` → src、`@config` → config），
 *     这些别名原先只在 Umi/MAX 构建期（config/config.ts）与 tsconfig paths 中声明，
 *     Vitest 默认不会解析 `@config`（`@hospital/*` 是 node_modules 符号链接，无需配置）。
 *
 * 本配置：
 *   - `resolve.alias` 显式声明 `@` 与 `@config`，让单测可导入业务代码与路由树。
 *   - `test.include` 限定为 src 下的单元测试文件，排除 e2e 目录。
 *   - 不强制 jsdom —— 现有单测为纯逻辑（Zustand store / 文本断言），默认 node 环境即可。
 *     如未来引入需要 DOM 的组件测试，再按需开启 environment: 'jsdom'（需安装 jsdom）。
 */
export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@config': path.resolve(__dirname, './config'),
    },
  },
  test: {
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },
});
