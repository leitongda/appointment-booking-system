#!/usr/bin/env node
/**
 * 批量构建所有模板
 * 遍历 5 套模板，逐个构建并验证
 */
import { execSync } from 'child_process';
import { existsSync, readFileSync, readdirSync, statSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, '..');

const TEMPLATES = [
  'modern-general',
  'elderly-tcm',
  'premium-specialty',
  'family-pediatrics',
  'womens-health',
];

const MIN_FILE_COUNT = 200;

// 统计产物文件数
function countFiles(distPath) {
  if (!existsSync(distPath)) return 0;
  let fileCount = 0;
  const count = (dir) => {
    const files = readdirSync(dir);
    for (const file of files) {
      const fullPath = resolve(dir, file);
      const stats = statSync(fullPath);
      if (stats.isDirectory()) {
        count(fullPath);
      } else {
        fileCount++;
      }
    }
  };
  count(distPath);
  return fileCount;
}

// 读取构建信息
function readBuildInfo(distPath) {
  try {
    const infoPath = resolve(distPath, 'build-info.json');
    if (existsSync(infoPath)) {
      return JSON.parse(readFileSync(infoPath, 'utf-8'));
    }
  } catch {}
  return null;
}

// 构建单个模板
function buildTemplate(templateCode) {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`📦 Building template: ${templateCode}`);
  console.log('='.repeat(60));

  const startTime = Date.now();
  try {
    execSync(
      `node scripts/build-template.mjs --template=${templateCode} --version=1.0.0`,
      { cwd: root, stdio: 'inherit' }
    );

    const duration = ((Date.now() - startTime) / 1000).toFixed(1);
    const distPath = resolve(root, 'dist');
    const fileCount = countFiles(distPath);
    const buildInfo = readBuildInfo(distPath);

    const success = fileCount >= MIN_FILE_COUNT;

    return {
      template: templateCode,
      status: success ? '✅' : '⚠️',
      duration,
      fileCount,
      buildInfo,
      success,
    };
  } catch (error) {
    return {
      template: templateCode,
      status: '❌',
      duration: ((Date.now() - startTime) / 1000).toFixed(1),
      fileCount: 0,
      error: error.message,
      success: false,
    };
  }
}

// 格式化表格
function formatTable(results) {
  console.log('\n' + '='.repeat(60));
  console.log('📊 Build Summary');
  console.log('='.repeat(60));
  console.log(
    ` ${'Template'.padEnd(20)} ${'Status'.padEnd(8)} ${'Duration'.padEnd(10)} ${'Files'.padEnd(8)}`
  );
  console.log('-'.repeat(60));

  for (const result of results) {
    const template = result.template.padEnd(20);
    const status = result.status.padEnd(8);
    const duration = result.duration.padEnd(10);
    const files = (result.fileCount || 0).toString().padEnd(8);
    console.log(`${template}${status}${duration}${files}`);
  }

  const successCount = results.filter(r => r.success).length;
  const totalCount = results.length;
  console.log('='.repeat(60));
  console.log(`Total: ${successCount}/${totalCount} templates built successfully`);
  console.log('='.repeat(60));
}

// 主函数
async function main() {
  console.log('\n🚀 Building all miniapp templates...\n');

  const results = [];

  for (const template of TEMPLATES) {
    const result = buildTemplate(template);
    results.push(result);
  }

  formatTable(results);

  const allSuccess = results.every(r => r.success);
  if (!allSuccess) {
    console.log('\n⚠️  Some builds failed or produced too few files');
    process.exit(1);
  }

  console.log('\n✅ All templates built successfully!\n');
}

main();
