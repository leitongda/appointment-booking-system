#!/usr/bin/env node
/**
 * 按模板启动开发服务器
 * 用法: node scripts/dev-template.mjs --template=elderly-tcm [--api-url=http://127.0.0.1:8000/api/v1]
 */
import { execSync } from 'child_process';
import { rmSync, existsSync } from 'fs';
import { resolve, dirname, spawn } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, '..');

// 解析参数
const args = process.argv.slice(2);
const getArg = (name) => {
  const arg = args.find(a => a.startsWith(`--${name}=`));
  return arg ? arg.split('=')[1] : undefined;
};

const templateCode = getArg('template') || 'modern-general';
const apiUrl = getArg('api-url') || '';
const watch = getArg('watch') !== 'false';

console.log(`\n🔧 Starting dev server for miniapp-generator`);
console.log(`   Template: ${templateCode}`);
console.log(`   API URL: ${apiUrl || 'default'}`);
console.log(`   Watch: ${watch}\n`);

// 清理缓存
console.log('🧹 Cleaning caches...');
for (const dir of ['.taro', 'dist', 'node_modules/.cache', '.swc']) {
  const fullPath = resolve(root, dir);
  if (existsSync(fullPath)) {
    rmSync(fullPath, { recursive: true, force: true });
  }
}

// 设置环境变量
const env = {
  ...process.env,
  TARO_APP_TEMPLATE_CODE: templateCode,
};

if (apiUrl) {
  env.TARO_APP_API_URL = apiUrl;
}

// 启动开发服务器
console.log('🚀 Starting dev server...\n');

try {
  // 启动 taro watch
  const taroArgs = ['build', '--type', 'weapp', '--watch', '--no-check'];
  const taro = spawn('pnpm', ['exec', 'taro', ...taroArgs], {
    cwd: root,
    stdio: 'inherit',
    env,
  });

  // 启动 fix-wxml watch
  setTimeout(() => {
    const fixWxml = spawn('node', ['scripts/fix-wxml.js', '--watch'], {
      cwd: root,
      stdio: 'inherit',
    });

    fixWxml.on('error', (err) => {
      console.error('fix-wml error:', err);
    });
  }, 2000);

  taro.on('error', (err) => {
    console.error('Failed to start dev server:', err);
    process.exit(1);
  });

  taro.on('exit', (code) => {
    console.log(`taro build exited with code ${code}`);
    process.exit(code);
  });

} catch (error) {
  console.error(`\n❌ Failed to start dev server: ${error.message}`);
  process.exit(1);
}
