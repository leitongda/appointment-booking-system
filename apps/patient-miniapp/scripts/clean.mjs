#!/usr/bin/env node

/**
 * 小程序缓存清理脚本
 * 清理 dist、node_modules/.cache、.swc 等缓存目录
 */

import { existsSync, rmSync, readdirSync, statSync } from 'fs';
import { join, resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
// 使用 dirname 获取脚本所在目录，再向上两级到项目根目录
const __dirname = resolve(dirname(__filename), '..');

// 需要清理的目录和文件列表
const CLEAN_TARGETS = [
  'dist',
  'node_modules/.cache',
  '.swc',
  '.temp',
  '.rn_temp',
  '.taro-cache',
  '*.log',
];

// 小程序特定的缓存目录（微信开发者工具可能生成的）
const MINIPROGRAM_CACHE_DIRS = [
  '.DS_Store',
  'Thumbs.db',
];

/**
 * 检查路径是否存在
 */
function pathExists(path) {
  try {
    return existsSync(path);
  } catch {
    return false;
  }
}

/**
 * 获取目录大小（递归）
 */
function getDirSize(path) {
  let totalSize = 0;

  try {
    const files = readdirSync(path);
    for (const file of files) {
      const filePath = join(path, file);
      const stats = statSync(filePath);

      if (stats.isDirectory()) {
        totalSize += getDirSize(filePath);
      } else {
        totalSize += stats.size;
      }
    }
  } catch {
    // 忽略无法读取的文件
  }

  return totalSize;
}

/**
 * 格式化文件大小
 */
function formatSize(bytes) {
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  return `${size.toFixed(2)} ${units[unitIndex]}`;
}

/**
 * 删除文件或目录
 */
function removePath(path) {
  try {
    rmSync(path, { recursive: true, force: true });
    return true;
  } catch (error) {
    console.error(`  ❌ 删除失败: ${error.message}`);
    return false;
  }
}

/**
 * 查找匹配的日志文件
 */
function findLogFiles(dir) {
  const logFiles = [];

  try {
    const files = readdirSync(dir);
    for (const file of files) {
      if (file.endsWith('.log') || file.endsWith('.log.gz')) {
        logFiles.push(join(dir, file));
      }
    }
  } catch {
    // 忽略无法读取的目录
  }

  return logFiles;
}

/**
 * 主清理函数
 */
function clean() {
  console.log('\n🧹 开始清理小程序缓存...\n');

  let totalCleaned = 0;
  let totalSize = 0;
  const cleanedItems = [];
  const failedItems = [];

  // 清理主要目标
  for (const target of CLEAN_TARGETS) {
    if (target.includes('*')) {
      // 处理通配符（如 *.log）
      const logFiles = findLogFiles(__dirname);
      for (const logFile of logFiles) {
        try {
          const stats = statSync(logFile);
          const size = stats.size;
          if (removePath(logFile)) {
            totalCleaned++;
            totalSize += size;
            cleanedItems.push({ path: logFile, size });
            console.log(`  ✅ 已清理: ${logFile} (${formatSize(size)})`);
          }
        } catch (error) {
          failedItems.push({ path: logFile, error: error.message });
        }
      }
      continue;
    }

    const targetPath = join(__dirname, target);

    if (!pathExists(targetPath)) {
      console.log(`  ⏭️  跳过（不存在）: ${target}`);
      continue;
    }

    // 获取目录大小
    const size = getDirSize(targetPath);

    // 删除目录
    if (removePath(targetPath)) {
      totalCleaned++;
      totalSize += size;
      cleanedItems.push({ path: target, size });
      console.log(`  ✅ 已清理: ${target} (${formatSize(size)})`);
    } else {
      failedItems.push({ path: target, error: '删除失败' });
    }
  }

  // 清理小程序特定的缓存文件
  for (const target of MINIPROGRAM_CACHE_DIRS) {
    const targetPath = join(__dirname, target);

    if (!pathExists(targetPath)) {
      continue;
    }

    const stats = statSync(targetPath);
    const size = stats.size;

    if (removePath(targetPath)) {
      totalCleaned++;
      totalSize += size;
      cleanedItems.push({ path: target, size });
      console.log(`  ✅ 已清理: ${target} (${formatSize(size)})`);
    }
  }

  // 输出汇总
  console.log('\n' + '='.repeat(50));
  console.log('📊 清理汇总:');
  console.log('='.repeat(50));
  console.log(`  总计清理: ${totalCleaned} 项`);
  console.log(`  释放空间: ${formatSize(totalSize)}`);

  if (cleanedItems.length > 0) {
    console.log('\n✨ 已清理的文件/目录:');
    for (const item of cleanedItems) {
      console.log(`  - ${item.path} (${formatSize(item.size)})`);
    }
  }

  if (failedItems.length > 0) {
    console.log('\n⚠️  清理失败的项:');
    for (const item of failedItems) {
      console.log(`  - ${item.path}: ${item.error}`);
    }
  }

  console.log('='.repeat(50));
  console.log('\n✅ 清理完成!\n');
}

// 执行清理
clean();
