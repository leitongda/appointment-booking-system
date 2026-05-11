#!/usr/bin/env node

/**
 * 构建后脚本：向index.html注入关键JS chunks的preload标签
 * 用法：node scripts/inject-preload.js
 */

const fs = require('fs');
const path = require('path');

const distDir = path.join(__dirname, '../dist');
const indexPath = path.join(distDir, 'index.html');

// 需要preload的关键chunks（首屏加载必需）
const PRELOAD_CHUNKS = [
  'react-lib',
  'vendors',
  'antd-lib',
  'utils-lib',
  'router-lib',
];

// 需要prefetch的chunks（可能很快需要）
const PREFETCH_CHUNKS = [
  'pro-components-lib',
  'umi',
];

function findChunkFiles() {
  const files = fs.readdirSync(distDir);
  const preloadFiles = [];
  const prefetchFiles = [];

  for (const file of files) {
    if (!file.endsWith('.js')) continue;

    // 检查是否需要preload
    for (const chunkName of PRELOAD_CHUNKS) {
      if (file.startsWith(chunkName + '.')) {
        preloadFiles.push(file);
        break;
      }
    }

    // 检查是否需要prefetch
    for (const chunkName of PREFETCH_CHUNKS) {
      if (file.startsWith(chunkName + '.')) {
        prefetchFiles.push(file);
        break;
      }
    }
  }

  return { preloadFiles, prefetchFiles };
}

function injectPreload() {
  if (!fs.existsSync(indexPath)) {
    console.error('index.html not found at:', indexPath);
    process.exit(1);
  }

  const html = fs.readFileSync(indexPath, 'utf-8');
  const { preloadFiles, prefetchFiles } = findChunkFiles();

  const tags = [];

  // 添加preload标签
  for (const file of preloadFiles) {
    tags.push(`    <link rel="preload" href="/${file}" as="script" crossorigin>`);
  }

  // 添加prefetch标签
  for (const file of prefetchFiles) {
    tags.push(`    <link rel="prefetch" href="/${file}">`);
  }

  if (tags.length === 0) {
    console.log('No chunks to preload/prefetch');
    return;
  }

  // 注入到</head>之前
  const tagHtml = tags.join('\n');
  const newHtml = html.replace('</head>', `${tagHtml}\n  </head>`);

  fs.writeFileSync(indexPath, newHtml, 'utf-8');

  console.log('Injected preload/prefetch tags:');
  console.log('  Preload:', preloadFiles.join(', '));
  console.log('  Prefetch:', prefetchFiles.join(', '));
}

injectPreload();
