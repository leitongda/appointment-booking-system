#!/usr/bin/env node
/**
 * 小程序主题切换脚本
 * 
 * 一键切换 patient-miniapp 的预设主题，自动同步更新所有相关配置文件。
 * 
 * 使用方式：
 *   node scripts/change-theme.mjs                    # 交互式选择主题
 *   node scripts/change-theme.mjs --theme "中医-绿"   # 直接指定主题
 *   node scripts/change-theme.mjs --dry-run          # 预览模式（不实际修改）
 *   node scripts/change-theme.mjs --list             # 列出所有可用主题
 */

import fs from 'fs';
import path from 'path';
import readline from 'readline';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '..');

// 文件路径
const PATHS = {
  themeConfig: path.join(ROOT_DIR, 'apps/patient-miniapp/src/config/theme.config.ts'),
  themesLess: path.join(ROOT_DIR, 'apps/patient-miniapp/src/styles/themes.less'),
  variablesLess: path.join(ROOT_DIR, 'apps/patient-miniapp/src/styles/variables.less'),
};

// 预设主题配置
const THEMES = {
  '中医-红': {
    nameEn: 'tcm-red',
    primary: '#C41E3A',
    primaryDark: '#A31631',
    primaryLight: '#DC3545',
    secondary: '#8B2942',
    secondaryLight: '#A23B55',
    gradientPrimary: 'linear-gradient(135deg, #C41E3A 0%, #8B2942 100%)',
    gradientPrimaryH: 'linear-gradient(90deg, #C41E3A 0%, #8B2942 100%)',
    gradientLight: 'linear-gradient(135deg, #FEE2E2 0%, #FECACA 100%)',
    shadowColor: 'rgba(196, 30, 58, 0.15)',
    shadowButton: '0 8rpx 28rpx 0 rgba(196, 30, 58, 0.3)',
    badgeBg: 'rgba(196, 30, 58, 0.1)',
  },
  '中医-绿': {
    nameEn: 'tcm-green',
    primary: '#2D8B56',
    primaryDark: '#1E6B42',
    primaryLight: '#3DA868',
    secondary: '#0D5C38',
    secondaryLight: '#1A7A4C',
    gradientPrimary: 'linear-gradient(135deg, #2D8B56 0%, #0D5C38 100%)',
    gradientPrimaryH: 'linear-gradient(90deg, #2D8B56 0%, #0D5C38 100%)',
    gradientLight: 'linear-gradient(135deg, #D1FAE5 0%, #A7F3D0 100%)',
    shadowColor: 'rgba(45, 139, 86, 0.15)',
    shadowButton: '0 8rpx 28rpx 0 rgba(45, 139, 86, 0.3)',
    badgeBg: 'rgba(45, 139, 86, 0.1)',
  },
  '现代-蓝': {
    nameEn: 'modern-blue',
    primary: '#1E6FD9',
    primaryDark: '#1557B0',
    primaryLight: '#3B82F6',
    secondary: '#4F46E5',
    secondaryLight: '#6366F1',
    gradientPrimary: 'linear-gradient(135deg, #1E6FD9 0%, #4F46E5 100%)',
    gradientPrimaryH: 'linear-gradient(90deg, #1E6FD9 0%, #4F46E5 100%)',
    gradientLight: 'linear-gradient(135deg, #DBEAFE 0%, #E0E7FF 100%)',
    shadowColor: 'rgba(30, 111, 217, 0.15)',
    shadowButton: '0 8rpx 28rpx 0 rgba(30, 111, 217, 0.3)',
    badgeBg: 'rgba(30, 111, 217, 0.1)',
  },
  '简约-白': {
    nameEn: 'minimal-white',
    primary: '#374151',
    primaryDark: '#1F2937',
    primaryLight: '#4B5563',
    secondary: '#6B7280',
    secondaryLight: '#9CA3AF',
    gradientPrimary: 'linear-gradient(135deg, #374151 0%, #1F2937 100%)',
    gradientPrimaryH: 'linear-gradient(90deg, #374151 0%, #1F2937 100%)',
    gradientLight: 'linear-gradient(135deg, #F9FAFB 0%, #F3F4F6 100%)',
    shadowColor: 'rgba(55, 65, 81, 0.12)',
    shadowButton: '0 8rpx 28rpx 0 rgba(55, 65, 81, 0.25)',
    badgeBg: 'rgba(55, 65, 81, 0.08)',
  },
  '故宫红': {
    nameEn: 'forbidden-city',
    primary: '#9D2933',
    primaryDark: '#7A1F28',
    primaryLight: '#B8323F',
    secondary: '#C5A028',
    secondaryLight: '#D4B23D',
    gradientPrimary: 'linear-gradient(135deg, #9D2933 0%, #7A1F28 100%)',
    gradientPrimaryH: 'linear-gradient(90deg, #9D2933 0%, #C5A028 100%)',
    gradientLight: 'linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%)',
    shadowColor: 'rgba(157, 41, 51, 0.15)',
    shadowButton: '0 8rpx 28rpx 0 rgba(157, 41, 51, 0.3)',
    badgeBg: 'rgba(157, 41, 51, 0.1)',
  },
  '青花瓷': {
    nameEn: 'blue-porcelain',
    primary: '#2563EB',
    primaryDark: '#1D4ED8',
    primaryLight: '#3B82F6',
    secondary: '#1E40AF',
    secondaryLight: '#3B5998',
    gradientPrimary: 'linear-gradient(135deg, #2563EB 0%, #1E40AF 100%)',
    gradientPrimaryH: 'linear-gradient(90deg, #2563EB 0%, #1E40AF 100%)',
    gradientLight: 'linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%)',
    shadowColor: 'rgba(37, 99, 235, 0.15)',
    shadowButton: '0 8rpx 28rpx 0 rgba(37, 99, 235, 0.3)',
    badgeBg: 'rgba(37, 99, 235, 0.1)',
  },
  '茶韵': {
    nameEn: 'tea',
    primary: '#6B4423',
    primaryDark: '#523318',
    primaryLight: '#8B5A2B',
    secondary: '#4A5D23',
    secondaryLight: '#5C7A2D',
    gradientPrimary: 'linear-gradient(135deg, #6B4423 0%, #4A5D23 100%)',
    gradientPrimaryH: 'linear-gradient(90deg, #6B4423 0%, #4A5D23 100%)',
    gradientLight: 'linear-gradient(135deg, #FEF9E7 0%, #F7F3E3 100%)',
    shadowColor: 'rgba(107, 68, 35, 0.15)',
    shadowButton: '0 8rpx 28rpx 0 rgba(107, 68, 35, 0.3)',
    badgeBg: 'rgba(107, 68, 35, 0.1)',
  },
  '紫禁': {
    nameEn: 'imperial-purple',
    primary: '#6B21A8',
    primaryDark: '#581C87',
    primaryLight: '#7C3AED',
    secondary: '#9333EA',
    secondaryLight: '#A855F7',
    gradientPrimary: 'linear-gradient(135deg, #6B21A8 0%, #9333EA 100%)',
    gradientPrimaryH: 'linear-gradient(90deg, #6B21A8 0%, #9333EA 100%)',
    gradientLight: 'linear-gradient(135deg, #FAF5FF 0%, #F3E8FF 100%)',
    shadowColor: 'rgba(107, 33, 168, 0.15)',
    shadowButton: '0 8rpx 28rpx 0 rgba(107, 33, 168, 0.3)',
    badgeBg: 'rgba(107, 33, 168, 0.1)',
  },
};

// 颜色代码
const COLORS = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
};

function log(message, color = '') {
  console.log(color ? `${color}${message}${COLORS.reset}` : message);
}

function logSuccess(message) {
  log(`✓ ${message}`, COLORS.green);
}

function logError(message) {
  log(`✗ ${message}`, COLORS.red);
}

function logInfo(message) {
  log(`→ ${message}`, COLORS.cyan);
}

function logWarn(message) {
  log(`! ${message}`, COLORS.yellow);
}

/**
 * 解析命令行参数
 */
function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    theme: null,
    dryRun: false,
    list: false,
    help: false,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--theme' || arg === '-t') {
      const nextArg = args[++i];
      if (!nextArg || nextArg.startsWith('-')) {
        console.error('错误: --theme 参数需要指定主题名称');
        process.exit(1);
      }
      options.theme = nextArg;
    } else if (arg === '--dry-run' || arg === '-d') {
      options.dryRun = true;
    } else if (arg === '--list' || arg === '-l') {
      options.list = true;
    } else if (arg === '--help' || arg === '-h') {
      options.help = true;
    }
  }

  return options;
}

/**
 * 显示帮助信息
 */
function showHelp() {
  console.log(`
${COLORS.bright}小程序主题切换脚本${COLORS.reset}

${COLORS.cyan}使用方式:${COLORS.reset}
  node scripts/change-theme.mjs [选项]

${COLORS.cyan}选项:${COLORS.reset}
  -t, --theme <主题名>    直接指定主题名称
  -d, --dry-run           预览模式，不实际修改文件
  -l, --list              列出所有可用主题
  -h, --help              显示帮助信息

${COLORS.cyan}示例:${COLORS.reset}
  node scripts/change-theme.mjs                    # 交互式选择
  node scripts/change-theme.mjs --theme "中医-绿"   # 指定主题
  node scripts/change-theme.mjs --dry-run          # 预览模式
`);
}

/**
 * 列出所有可用主题
 */
function listThemes() {
  console.log(`\n${COLORS.bright}可用主题列表:${COLORS.reset}\n`);
  console.log('  序号  主题名      主色      英文标识');
  console.log('  ─────────────────────────────────────────');
  
  Object.entries(THEMES).forEach(([name, config], index) => {
    console.log(`  ${String(index + 1).padStart(2)}    ${name.padEnd(8)}  ${config.primary}  ${config.nameEn}`);
  });
  console.log();
}

/**
 * 交互式选择主题
 */
async function selectTheme() {
  const themeNames = Object.keys(THEMES);
  
  console.log(`\n${COLORS.bright}请选择主题:${COLORS.reset}\n`);
  
  themeNames.forEach((name, index) => {
    const config = THEMES[name];
    console.log(`  ${COLORS.cyan}${index + 1}${COLORS.reset}. ${name} (${config.primary})`);
  });
  
  console.log();
  
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  return new Promise((resolve) => {
    rl.question(`请输入序号 (1-${themeNames.length}): `, (answer) => {
      rl.close();
      const index = parseInt(answer, 10) - 1;
      if (index >= 0 && index < themeNames.length) {
        resolve(themeNames[index]);
      } else {
        resolve(null);
      }
    });
  });
}

/**
 * 获取当前主题
 */
function getCurrentTheme() {
  try {
    const content = fs.readFileSync(PATHS.themeConfig, 'utf-8');
    const match = content.match(/default:\s*['"]([^'"]+)['"]/);
    return match ? match[1] : null;
  } catch {
    return null;
  }
}

/**
 * 更新 theme.config.ts
 */
function updateThemeConfig(themeName, dryRun) {
  const filePath = PATHS.themeConfig;
  let content = fs.readFileSync(filePath, 'utf-8');
  
  // 替换 default 值
  const newContent = content.replace(
    /(default:\s*['"])[^'"]+(['"])/,
    `$1${themeName}$2`
  );
  
  if (content === newContent) {
    logWarn(`theme.config.ts 已经是 "${themeName}" 主题`);
    return false;
  }
  
  if (!dryRun) {
    fs.writeFileSync(filePath, newContent, 'utf-8');
  }
  
  logSuccess(`theme.config.ts: default → "${themeName}"`);
  return true;
}

/**
 * 更新 themes.less 的 page 块
 */
function updateThemesLess(themeName, dryRun) {
  const filePath = PATHS.themesLess;
  const theme = THEMES[themeName];
  let content = fs.readFileSync(filePath, 'utf-8');
  
  // 构建新的 page 块内容
  const newPageBlock = `page {
  // 默认使用${themeName}主题
  --color-primary: ${theme.primary};
  --color-primary-dark: ${theme.primaryDark};
  --color-primary-light: ${theme.primaryLight};
  --color-secondary: ${theme.secondary};
  --color-secondary-light: ${theme.secondaryLight};
  --gradient-primary: ${theme.gradientPrimary};
  --gradient-primary-h: ${theme.gradientPrimaryH};
  --gradient-light: ${theme.gradientLight};
  --shadow-color: ${theme.shadowColor};
  --shadow-button: ${theme.shadowButton};
  --badge-bg: ${theme.badgeBg};
}`;

  // 替换 page 块
  const pageBlockRegex = /page\s*\{[^}]+\}/;
  const newContent = content.replace(pageBlockRegex, newPageBlock);
  
  if (content === newContent) {
    logWarn('themes.less page 块无变化');
    return false;
  }
  
  if (!dryRun) {
    fs.writeFileSync(filePath, newContent, 'utf-8');
  }
  
  logSuccess(`themes.less: page 块 → ${themeName} (${theme.primary})`);
  return true;
}

/**
 * 更新 variables.less 的主题变量
 */
function updateVariablesLess(themeName, dryRun) {
  const filePath = PATHS.variablesLess;
  const theme = THEMES[themeName];
  let content = fs.readFileSync(filePath, 'utf-8');
  
  // 定义需要替换的变量（只匹配行首非注释的变量声明）
  const replacements = [
    { pattern: /^(@theme-primary:\s*)#[0-9A-Fa-f]+;/m, value: `$1${theme.primary};` },
    { pattern: /^(@theme-primary-dark:\s*)#[0-9A-Fa-f]+;/m, value: `$1${theme.primaryDark};` },
    { pattern: /^(@theme-primary-light:\s*)#[0-9A-Fa-f]+;/m, value: `$1${theme.primaryLight};` },
    { pattern: /^(@theme-secondary:\s*)#[0-9A-Fa-f]+;/m, value: `$1${theme.secondary};` },
    { pattern: /^(@theme-secondary-light:\s*)#[0-9A-Fa-f]+;/m, value: `$1${theme.secondaryLight};` },
  ];
  
  let newContent = content;
  let changeCount = 0;
  
  for (const { pattern, value } of replacements) {
    if (pattern.test(newContent)) {
      const before = newContent;
      newContent = newContent.replace(pattern, value);
      if (before !== newContent) {
        changeCount++;
      }
    }
  }
  
  if (changeCount === 0) {
    logWarn('variables.less 主题变量无变化');
    return false;
  }
  
  if (!dryRun) {
    fs.writeFileSync(filePath, newContent, 'utf-8');
  }
  
  logSuccess(`variables.less: 更新了 ${changeCount} 个主题变量`);
  return true;
}

/**
 * 主函数
 */
async function main() {
  const options = parseArgs();
  
  // 显示帮助
  if (options.help) {
    showHelp();
    return;
  }
  
  // 列出主题
  if (options.list) {
    listThemes();
    return;
  }
  
  console.log(`\n${COLORS.bright}═══ 小程序主题切换工具 ═══${COLORS.reset}\n`);
  
  // 检查文件是否存在
  for (const [, filePath] of Object.entries(PATHS)) {
    if (!fs.existsSync(filePath)) {
      logError(`文件不存在: ${filePath}`);
      process.exit(1);
    }
  }
  
  // 获取当前主题
  const currentTheme = getCurrentTheme();
  if (currentTheme) {
    logInfo(`当前主题: ${currentTheme}`);
  }
  
  // 确定目标主题
  let targetTheme = options.theme;
  
  if (!targetTheme) {
    targetTheme = await selectTheme();
  }
  
  if (!targetTheme) {
    logError('未选择有效的主题');
    process.exit(1);
  }
  
  if (!THEMES[targetTheme]) {
    logError(`未知的主题: "${targetTheme}"`);
    log('\n可用主题:', COLORS.dim);
    Object.keys(THEMES).forEach(name => log(`  - ${name}`, COLORS.dim));
    process.exit(1);
  }
  
  if (targetTheme === currentTheme && !options.dryRun) {
    logWarn(`已经是 "${targetTheme}" 主题，无需切换`);
    return;
  }
  
  console.log();
  logInfo(`目标主题: ${targetTheme} (${THEMES[targetTheme].primary})`);
  
  if (options.dryRun) {
    console.log();
    logWarn('预览模式 - 以下变更不会实际执行:');
  }
  
  console.log();
  
  // 执行更新
  let hasChanges = false;
  
  hasChanges = updateThemeConfig(targetTheme, options.dryRun) || hasChanges;
  hasChanges = updateThemesLess(targetTheme, options.dryRun) || hasChanges;
  hasChanges = updateVariablesLess(targetTheme, options.dryRun) || hasChanges;
  
  console.log();
  
  if (hasChanges) {
    if (options.dryRun) {
      logInfo('预览完成，使用不带 --dry-run 参数执行实际变更');
    } else {
      logSuccess(`主题已切换为: ${targetTheme}`);
      console.log();
      log('下一步:', COLORS.dim);
      log('  1. 重新编译小程序: cd apps/patient-miniapp && pnpm dev:weapp', COLORS.dim);
      log('  2. 在微信开发者工具中刷新预览', COLORS.dim);
    }
  } else {
    logInfo('所有文件已是目标主题配置');
  }
  
  console.log();
}

main().catch((err) => {
  logError(`执行出错: ${err.message}`);
  process.exit(1);
});
