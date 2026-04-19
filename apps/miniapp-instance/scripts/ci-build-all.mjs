#!/usr/bin/env node

/**
 * CI 环境下的多模板构建脚本
 *
 * 特性:
 * - 无交互，严格模式（任何错误立即退出）
 * - 依次构建 5 套模板，记录耗时和文件数
 * - 每套模板构建后验证产物完整性
 * - 输出构建摘要表格
 *
 * 用法:
 *   node scripts/ci-build-all.mjs
 *
 * 环境变量:
 *   CI - 自动检测，CI 环境下强制启用严格模式
 */

import { execSync } from 'node:child_process';
import { existsSync, readdirSync, statSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = join(__dirname, '..');
const DIST_DIR = join(ROOT_DIR, 'dist');

// 模板定义
const TEMPLATES = [
  { code: 'modern-general', name: '现代综合医疗' },
  { code: 'premium-specialty', name: '高端专科门诊' },
  { code: 'pediatric', name: '亲子儿科' },
  { code: 'womens-health', name: '女性健康' },
  { code: 'elderly-tcm', name: '长辈友好中医康养' },
];

// 严格模式配置
const IS_CI = process.env.CI === 'true' || process.env.GITHUB_ACTIONS === 'true';
const MIN_FILE_COUNT = 200;

/**
 * 执行命令并返回结果
 */
function exec(cmd, options = {}) {
  const defaults = {
    cwd: ROOT_DIR,
    stdio: IS_CI ? 'pipe' : 'inherit',
    env: { ...process.env },
  };
  return execSync(cmd, { ...defaults, ...options });
}

/**
 * 统计目录文件数
 */
function countFiles(dir) {
  if (!existsSync(dir)) return 0;
  let count = 0;
  const items = readdirSync(dir, { withFileTypes: true });
  for (const item of items) {
    if (item.isDirectory()) {
      count += countFiles(join(dir, item.name));
    } else if (item.isFile()) {
      count++;
    }
  }
  return count;
}

/**
 * 清理构建产物和缓存
 */
function clean() {
  console.log('🧹 清理构建产物和缓存...');
  const dirsToClean = [
    join(ROOT_DIR, '.taro'),
    join(ROOT_DIR, 'node_modules', '.cache'),
    DIST_DIR,
  ];

  for (const dir of dirsToClean) {
    if (existsSync(dir)) {
      execSync(`rm -rf "${dir}"`, { stdio: 'ignore' });
    }
  }
  console.log('✅ 清理完成\n');
}

/**
 * 构建单个模板
 */
function buildTemplate(template) {
  const { code, name } = template;
  console.log(`\n🔨 构建模板: ${name} (${code})`);
  console.log('━'.repeat(50));

  const startTime = Date.now();

  try {
    // 设置环境变量
    const env = { ...process.env, TARO_APP_TEMPLATE_CODE: code, CI: 'true' };

    // 执行构建
    exec(`node scripts/build-template.mjs --template ${code}`, {
      env,
      stdio: IS_CI ? 'pipe' : 'inherit',
    });

    const duration = ((Date.now() - startTime) / 1000).toFixed(2);

    // 验证构建产物
    const fileCount = countFiles(DIST_DIR);
    console.log(`📦 产物文件数: ${fileCount}`);

    if (fileCount < MIN_FILE_COUNT) {
      throw new Error(
        `构建产物过小: 期望 >= ${MIN_FILE_COUNT} 个文件，实际 ${fileCount} 个`
      );
    }

    console.log(`✅ 构建成功 (耗时 ${duration}s)`);
    return { success: true, duration, fileCount };
  } catch (error) {
    const duration = ((Date.now() - startTime) / 1000).toFixed(2);
    console.error(`❌ 构建失败: ${error.message}`);
    console.error(`   耗时 ${duration}s`);
    return { success: false, duration, fileCount: 0, error: error.message };
  }
}

/**
 * 输出构建摘要
 */
function printSummary(results) {
  console.log('\n' + '='.repeat(70));
  console.log('📊 构建摘要');
  console.log('='.repeat(70));

  console.log(
    `| 模板代码      | 模板名称              | 状态  | 耗时    | 文件数 |`
  );
  console.log('|' + '-'.repeat(70) + '|');

  for (const [template, result] of Object.entries(results)) {
    const { name } = TEMPLATES.find((t) => t.code === template);
    const status = result.success ? '✅ 成功' : '❌ 失败';
    const duration = result.duration ? `${result.duration}s` : '-';
    const fileCount = result.fileCount || '-';

    console.log(
      `| ${template.padEnd(13)} | ${name.padEnd(20)} | ${status.padEnd(6)} | ${duration.padEnd(6)} | ${fileCount.padEnd(6)} |`
    );
  }

  console.log('='.repeat(70) + '\n');

  // 统计
  const successCount = Object.values(results).filter((r) => r.success).length;
  const totalCount = Object.keys(results).length;

  console.log(`总计: ${successCount}/${totalCount} 套模板构建成功`);

  if (successCount === totalCount) {
    console.log('🎉 全部构建成功！');
  } else {
    console.log('⚠️  部分构建失败，请检查上述错误信息');
  }
}

/**
 * 主函数
 */
function main() {
  console.log('🚀 多风格小程序模板 CI 构建\n');

  if (IS_CI) {
    console.log('📍 CI 环境检测: 严格模式已启用\n');
  }

  // 清理缓存
  clean();

  const results = {};

  // 依次构建每套模板
  for (const template of TEMPLATES) {
    const result = buildTemplate(template);
    results[template.code] = result;

    // CI 环境下任何失败立即退出
    if (IS_CI && !result.success) {
      printSummary(results);
      process.exit(1);
    }
  }

  // 输出摘要
  printSummary(results);

  // 全部成功则退出码 0，否则 1
  const allSuccess = Object.values(results).every((r) => r.success);
  process.exit(allSuccess ? 0 : 1);
}

// 执行
main();
