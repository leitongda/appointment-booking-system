/**
 * 修复 Taro 编译生成的文件中的兼容性问题
 * 
 * 修复内容：
 * 1. base.wxml 中 input 标签未正确闭合的问题
 * 2. 所有 wxss 文件中使用了小程序不支持的 * 通配选择器
 * 
 * 相关 Issue: https://github.com/NervJS/taro/issues/10848
 * 
 * 使用方式：
 * - node scripts/fix-wxml.js          一次性修复
 * - node scripts/fix-wxml.js --watch  监听模式，配合 taro build --watch 使用
 */
const fs = require('fs');
const path = require('path');

const baseWxmlPath = path.resolve(__dirname, '../dist/base.wxml');
const appOriginWxssPath = path.resolve(__dirname, '../dist/app-origin.wxss');
const distPath = path.resolve(__dirname, '../dist');
const isWatchMode = process.argv.includes('--watch');

function fixBaseWxml(silent = false) {
  if (!fs.existsSync(baseWxmlPath)) {
    if (!silent) {
      console.log('[fix-wxml] base.wxml 不存在，跳过修复');
    }
    return;
  }

  let content = fs.readFileSync(baseWxmlPath, 'utf-8');
  const originalContent = content;

  // 修复 input 标签：将 <input ... data-sid="{{i.sid}}"></template> 
  // 替换为 <input ... data-sid="{{i.sid}}" /></template>
  // 注意：只修复后面紧跟 </template> 的情况
  content = content.replace(
    /(<input[^>]*data-sid="\{\{i\.sid\}\}")><\/template>/g,
    '$1 /></template>'
  );

  if (content !== originalContent) {
    fs.writeFileSync(baseWxmlPath, content, 'utf-8');
    console.log('[fix-wxml] ✅ 成功修复 base.wxml 中的 input 标签');
  } else if (!silent) {
    console.log('[fix-wxml] base.wxml 无需修复');
  }
}

/**
 * 修复单个 WXSS 文件中的不兼容语法
 * 微信小程序不支持 * 通配选择器
 */
function fixSingleWxss(filePath, silent = false) {
  if (!fs.existsSync(filePath)) {
    return false;
  }

  let content;
  try {
    content = fs.readFileSync(filePath, 'utf-8');
  } catch (error) {
    // 文件可能在 existsSync 检查后被删除（竞态条件）
    if (error.code === 'ENOENT') {
      return false;
    }
    throw error;
  }
  
  const originalContent = content;

  // 移除包含 >* 选择器的规则
  // 这些规则通常是 NutUI 的样式，形如 .nut-xxx>*{...}
  // 由于小程序不支持 * 选择器，我们需要移除整个规则
  // 匹配模式: 选择器>*{规则内容}
  content = content.replace(/[^{}]*>\*\s*\{[^}]*\}/g, '');
  
  // 同时处理 >*:pseudo-class 选择器，如 >*:first-child, >*:last-child
  content = content.replace(/[^{}]*>\*:[a-z-]+\s*\{[^}]*\}/g, '');

  // 移除可能产生的连续分号
  content = content.replace(/;;+/g, ';');

  if (content !== originalContent) {
    try {
      fs.writeFileSync(filePath, content, 'utf-8');
    } catch (error) {
      // 文件可能在处理过程中被删除
      if (error.code === 'ENOENT') {
        return false;
      }
      throw error;
    }
    return true;
  }
  return false;
}

/**
 * 递归查找所有 wxss 文件
 */
function findWxssFiles(dir, files = []) {
  if (!fs.existsSync(dir)) {
    return files;
  }
  
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      // 跳过 node_modules
      if (entry.name !== 'node_modules') {
        findWxssFiles(fullPath, files);
      }
    } else if (entry.isFile() && entry.name.endsWith('.wxss')) {
      files.push(fullPath);
    }
  }
  
  return files;
}

/**
 * 修复所有 WXSS 文件中的不兼容语法
 */
function fixAllWxss(silent = false) {
  if (!fs.existsSync(distPath)) {
    if (!silent) {
      console.log('[fix-wxss] dist 目录不存在，跳过修复');
    }
    return;
  }

  // 查找所有 wxss 文件
  const wxssFiles = findWxssFiles(distPath);

  let fixedCount = 0;
  for (const filePath of wxssFiles) {
    if (fixSingleWxss(filePath, silent)) {
      const relativePath = path.relative(distPath, filePath);
      console.log(`[fix-wxss] ✅ 修复 ${relativePath}`);
      fixedCount++;
    }
  }

  if (fixedCount === 0 && !silent) {
    console.log('[fix-wxss] 所有 wxss 文件无需修复');
  } else {
    if (fixedCount > 0) {
      console.log(`[fix-wxss] ✅ 共修复 ${fixedCount} 个文件`);
    }
  }
}

/**
 * 修复 WXSS 中的不兼容语法（兼容旧接口）
 * @deprecated 使用 fixAllWxss 代替
 */
function fixWxss(silent = false) {
  if (!fs.existsSync(appOriginWxssPath)) {
    if (!silent) {
      console.log('[fix-wxss] app-origin.wxss 不存在，跳过修复');
    }
    return;
  }

  if (fixSingleWxss(appOriginWxssPath, silent)) {
    console.log('[fix-wxss] ✅ 成功修复 app-origin.wxss 中的不兼容选择器');
  } else {
    console.log('[fix-wxss] app-origin.wxss 无需修复');
  }
}

/**
 * 执行所有修复
 */
function runAllFixes(silent = false) {
  fixBaseWxml(silent);
  fixAllWxss(silent);
}

// 首次执行（watch 模式下静默，因为文件可能还未生成）
runAllFixes(isWatchMode);

// Watch 模式
if (isWatchMode) {
  console.log('[fix] 👀 监听模式已启动，等待编译产物生成...');
  
  // fs.watch({ recursive: true }) can fail with EMFILE while Taro is also
  // watching the project. Polling the small dist tree is more predictable.
  setInterval(() => {
    try {
      runAllFixes(true);
    } catch (error) {
      console.error('[fix] 修复失败:', error.message);
    }
  }, 1000);
}
