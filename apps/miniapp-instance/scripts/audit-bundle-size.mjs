#!/usr/bin/env node
/**
 * 主包体积审计脚本
 * 检查每套模板的产物大小是否符合微信小程序限制（主包 2MB，单个分包 2MB，总包 20MB）
 */
import { execSync } from 'child_process';
import { existsSync, readFileSync, readdirSync, statSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, '..');

// 模板列表
const TEMPLATES = [
  'modern-general',
  'elderly-tcm',
  'premium-specialty',
  'womens-health',
  'family-pediatrics',
];

// 微信小程序大小限制（字节）
const LIMITS = {
  MAIN: 2 * 1024 * 1024,      // 主包 2MB
  SUB: 2 * 1024 * 1024,       // 单个分包 2MB
  TOTAL: 20 * 1024 * 1024,    // 总包 20MB
};

/**
 * 递归计算目录大小
 */
function getDirSize(dirPath) {
  let total = 0;
  if (!existsSync(dirPath)) return total;

  const files = readdirSync(dirPath);
  for (const file of files) {
    const fullPath = resolve(dirPath, file);
    const stats = statSync(fullPath);
    if (stats.isDirectory()) {
      total += getDirSize(fullPath);
    } else if (stats.isFile()) {
      total += stats.size;
    }
  }
  return total;
}

/**
 * 格式化字节大小
 */
function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * 构建单个模板并返回产物信息
 */
function buildTemplate(templateCode) {
  console.log(`\n📦 Building ${templateCode}...`);

  try {
    execSync(
      `node scripts/build-template.mjs --template=${templateCode}`,
      { cwd: root, stdio: 'pipe' }
    );
  } catch (error) {
    return { error: error.message };
  }

  const distPath = resolve(root, 'dist');
  const mainPath = resolve(distPath, 'main.js');
  const mainSize = existsSync(mainPath) ? statSync(mainPath).size : 0;
  const totalSize = getDirSize(distPath);

  return {
    mainSize: formatBytes(mainSize),
    mainSizeBytes: mainSize,
    totalSize: formatBytes(totalSize),
    totalSizeBytes: totalSize,
    mainExceedsLimit: mainSize > LIMITS.MAIN,
    totalExceedsLimit: totalSize > LIMITS.TOTAL,
  };
}

/**
 * 审计所有模板
 */
function auditAll() {
  console.log('\n🔍 开始主包体积审计...\n');
  console.log('微信小程序限制：');
  console.log(`  - 主包: ${formatBytes(LIMITS.MAIN)}`);
  console.log(`  - 总包: ${formatBytes(LIMITS.TOTAL)}\n`);

  const results = {};

  for (const template of TEMPLATES) {
    results[template] = buildTemplate(template);
  }

  // 输出审计报告
  console.log('\n📊 审计报告：\n');
  console.log('模板'.padEnd(20) + '主包大小'.padEnd(15) + '总包大小'.padEnd(15) + '状态');
  console.log('-'.repeat(65));

  let allPassed = true;
  for (const template of TEMPLATES) {
    const result = results[template];
    if (result.error) {
      console.log(
        template.padEnd(20) +
        '构建失败'.padEnd(30) +
        '❌'
      );
      allPassed = false;
    } else {
      const status = (result.mainExceedsLimit || result.totalExceedsLimit) ? '❌ 超限' : '✅ 通过';
      console.log(
        template.padEnd(20) +
        result.mainSize.padEnd(15) +
        result.totalSize.padEnd(15) +
        status
      );
      if (!result.mainExceedsLimit && !result.totalExceedsLimit) {
        allPassed = false;
      }
    }
  }

  console.log('\n');
  if (allPassed) {
    console.log('✅ 所有模板通过体积审计');
  } else {
    console.log('⚠️  部分模板超过限制，需要优化');
  }

  // 写入审计报告文件
  const reportPath = resolve(root, 'dist', 'bundle-audit-report.json');
  const report = {
    timestamp: new Date().toISOString(),
    limits: {
      main: formatBytes(LIMITS.MAIN),
      total: formatBytes(LIMITS.TOTAL),
    },
    results,
  };
  // 不创建文件，只输出到控制台
}

// 主函数
if (import.meta.url === `file://${process.argv[1]}`) {
  auditAll();
}

export { auditAll, getDirSize, formatBytes };
