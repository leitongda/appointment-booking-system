import { defineConfig } from 'vitest/config';

/**
 * Vitest 配置（@hospital/api）
 *
 * - 单测为纯逻辑（拦截器 / 停服错误码解析等），默认 node 环境即可。
 * - `@hospital/shared` 走 pnpm workspace 符号链接解析到 TS 源码，无需 alias。
 * - `globals: true` 兼容早期按 Jest 全局 API 编写的用例（performance.test.ts）。
 */
export default defineConfig({
  test: {
    globals: true,
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },
});
