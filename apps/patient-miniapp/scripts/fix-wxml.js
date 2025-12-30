/**
 * 修复 Taro 编译生成的文件中的兼容性问题
 * 
 * 修复内容：
 * 1. base.wxml 中 input 标签未正确闭合的问题
 * 2. app-origin.wxss 中使用了小程序不支持的 * 通配选择器
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
  } else {
    console.log('[fix-wxml] base.wxml 无需修复');
  }
}

/**
 * 修复 WXSS 中的不兼容语法
 * 微信小程序不支持 * 通配选择器
 */
function fixWxss(silent = false) {
  if (!fs.existsSync(appOriginWxssPath)) {
    if (!silent) {
      console.log('[fix-wxss] app-origin.wxss 不存在，跳过修复');
    }
    return;
  }

  let content = fs.readFileSync(appOriginWxssPath, 'utf-8');
  const originalContent = content;

  // 移除包含 >* 选择器的规则
  // 这些规则通常是 NutUI 的样式，形如 .nut-xxx>*{...}
  // 由于小程序不支持 * 选择器，我们需要移除整个规则
  // 匹配模式: 选择器>*{规则内容}
  content = content.replace(/[^{}]*>\*\s*\{[^}]*\}/g, '');

  // 移除可能产生的连续分号
  content = content.replace(/;;+/g, ';');

  if (content !== originalContent) {
    fs.writeFileSync(appOriginWxssPath, content, 'utf-8');
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
  fixWxss(silent);
}

// 首次执行（watch 模式下静默，因为文件可能还未生成）
runAllFixes(isWatchMode);

// Watch 模式
if (isWatchMode) {
  console.log('[fix] 👀 监听模式已启动，等待编译产物生成...');
  
  // 使用防抖来避免频繁触发
  let debounceTimer = null;
  
  // 等待 dist 目录创建后再开始监听
  function startWatching() {
    fs.watch(distPath, { recursive: false }, (eventType, filename) => {
      // 监听 base.wxml 和 app-origin.wxss
      if (filename === 'base.wxml' || filename === 'app-origin.wxss') {
        if (debounceTimer) {
          clearTimeout(debounceTimer);
        }
        debounceTimer = setTimeout(() => {
          runAllFixes();
        }, 100);
      }
    });
    console.log('[fix] 👀 开始监听 dist 目录...');
  }
  
  // 如果 dist 目录不存在，等待它被创建
  if (!fs.existsSync(distPath)) {
    console.log('[fix] dist 目录不存在，等待 Taro 编译创建...');
    const checkInterval = setInterval(() => {
      if (fs.existsSync(distPath)) {
        clearInterval(checkInterval);
        startWatching();
      }
    }, 500);
  } else {
    startWatching();
  }
}

