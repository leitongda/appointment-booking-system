import { defineConfig } from 'vitest/config';

/**
 * Vitest 配置（@hospital/shared）
 *
 * - 单测为纯逻辑（parseTenantError / expression-engine 等），默认 node 环境即可，
 *   不引入 jsdom；如未来需要组件测试再按需开启。
 * - 测试通过相对路径导入 src 源码（包以 TS 源码分发，无需 alias）。
 */
export default defineConfig({
  test: {
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },
});
