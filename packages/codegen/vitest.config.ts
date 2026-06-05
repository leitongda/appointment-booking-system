import { defineConfig } from 'vitest/config';
import path from 'node:path';

export default defineConfig({
  resolve: {
    alias: {
      '@hospital/shared': path.resolve(__dirname, '../shared/src'),
    },
  },
  test: {
    globals: true,
    include: ['src/**/*.{test,spec}.ts'],
  },
});
