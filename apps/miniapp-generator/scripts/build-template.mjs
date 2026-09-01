#!/usr/bin/env node
/**
 * 按模板构建小程序
 * 用法: node scripts/build-template.mjs --template=modern-general [--instance-id=xxx] [--version=1.0.0]
 */
import { execSync } from 'child_process';
import { rmSync, existsSync, writeFileSync, readdirSync, statSync } from 'fs';
import { resolve, dirname } from 'path';
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
const instanceId = getArg('instance-id') || '';
const version = getArg('version') || '1.0.0';

console.log(`\n🚀 Building miniapp-generator`);
console.log(`   Template: ${templateCode}`);
console.log(`   Version: ${version}`);
console.log(`   Instance: ${instanceId || 'local'}\n`);

// 清理缓存
console.log('🧹 Cleaning caches...');
for (const dir of ['.taro', 'dist', 'node_modules/.cache', '.swc']) {
  const fullPath = resolve(root, dir);
  if (existsSync(fullPath)) {
    rmSync(fullPath, { recursive: true, force: true });
  }
}

// 构建
console.log('📦 Building...\n');
const startTime = Date.now();
try {
  execSync(
    `TARO_APP_TEMPLATE_CODE=${templateCode} TARO_APP_TEMPLATE_VERSION=${version} TARO_APP_MINIAPP_INSTANCE_ID=${instanceId} pnpm exec taro build --type weapp --no-check`,
    { cwd: root, stdio: 'inherit', env: { ...process.env } }
  );

  // 执行 fix-wml
  console.log('\n🔧 Fixing WXML...');
  execSync('node scripts/fix-wxml.js', { cwd: root, stdio: 'inherit' });

  const duration = ((Date.now() - startTime) / 1000).toFixed(1);

  // 统计产物文件数
  let fileCount = 0;
  const distPath = resolve(root, 'dist');
  if (existsSync(distPath)) {
    const countFiles = (dir) => {
      const files = readdirSync(dir);
      for (const file of files) {
        const fullPath = resolve(dir, file);
        const stats = statSync(fullPath);
        if (stats.isDirectory()) {
          countFiles(fullPath);
        } else {
          fileCount++;
        }
      }
    };
    countFiles(distPath);
  }

  // 写构建元数据
  const buildInfo = {
    templateCode,
    templateVersion: version,
    instanceId,
    buildTime: new Date().toISOString(),
    buildDuration: `${duration}s`,
    buildTool: 'taro@4.1.9',
    fileCount,
  };

  writeFileSync(
    resolve(root, 'dist', 'build-info.json'),
    JSON.stringify(buildInfo, null, 2)
  );

  console.log(`\n✅ Build completed in ${duration}s`);
  console.log(`   Template: ${templateCode}`);
  console.log(`   Files: ${fileCount}`);
  console.log(`   Output: dist/`);
} catch (error) {
  console.error(`\n❌ Build failed: ${error.message}`);
  process.exit(1);
}
