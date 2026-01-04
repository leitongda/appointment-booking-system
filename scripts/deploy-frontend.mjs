#!/usr/bin/env node

/**
 * 前端构建并上传到服务器脚本（交互式）
 * 在本地 Mac 上执行
 *
 * 使用方式：
 *   pnpm deploy:frontend
 *   或
 *   node scripts/deploy-frontend.mjs
 *
 * 功能：
 *   - ASCII Art Banner
 *   - 进度条显示
 *   - 按 v 切换显示/隐藏详细日志
 *   - 错误时可选择查看详情/重试/跳过/退出
 */

import { spawn } from 'child_process';
import { existsSync, readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import prompts from 'prompts';
import chalk from 'chalk';
import ora from 'ora';
import figlet from 'figlet';
import readline from 'readline';

// 获取脚本所在目录
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const PROJECT_ROOT = resolve(__dirname, '..');

// 全局状态
let showLogs = false;
let currentLogBuffer = [];
let keyListener = null;

// Banner 动画状态
let bannerAnimationTimer = null;
let bannerColorOffset = 0;

// 配置：每个应用保留的最大备份数量
const MAX_BACKUPS_PER_APP = 5;

// 前端应用配置
const APPS = [
  { value: 'admin', title: 'admin', description: '管理后台' },
  { value: 'doctor', title: 'doctor', description: '医生端' },
  { value: 'patient-h5', title: 'patient-h5', description: '患者端 H5' },
  { value: 'temp-registration', title: 'temp-registration', description: '临时挂号' },
];

// 部署步骤定义（中文）
const DEPLOY_STEPS = [
  { id: 'compress', name: '压缩文件' },
  { id: 'backup-dir', name: '创建备份目录' },
  { id: 'backup', name: '备份现有文件' },
  { id: 'cleanup-old', name: '清理旧备份' },
  { id: 'clean', name: '清空目标目录' },
  { id: 'upload', name: '上传压缩包' },
  { id: 'extract', name: '解压并清理' },
  { id: 'cleanup', name: '清理临时文件' },
];

/**
 * 动态时间线进度类
 * 使用 ANSI 转义码实现动态更新
 */
class TimelineProgress {
  constructor(title, steps, options = {}) {
    this.title = title;
    this.steps = steps.map((step, index) => ({
      ...step,
      status: 'pending', // pending, running, completed, failed, skipped
    }));
    this.currentIndex = -1;
    this.linesRendered = 0;
    this.showHint = options.showHint !== false;
    this.taskIndex = options.taskIndex || 0;
    this.taskTotal = options.taskTotal || 1;
  }

  /**
   * 获取状态图标
   */
  getStatusIcon(status, isLast) {
    const icons = {
      pending: chalk.gray('○'),
      running: chalk.yellow('◐'),
      completed: chalk.green('✓'),
      failed: chalk.red('✗'),
      skipped: chalk.yellow('⊘'),
    };
    return icons[status] || icons.pending;
  }

  /**
   * 获取树形连接符
   */
  getTreeChar(index, isLast) {
    if (isLast) {
      return '└──';
    }
    return '├──';
  }

  /**
   * 渲染进度条
   */
  renderProgressBar(width = 20) {
    const completed = this.steps.filter(s => s.status === 'completed' || s.status === 'skipped').length;
    const total = this.steps.length;
    const percent = Math.round((completed / total) * 100);
    const filled = Math.round((completed / total) * width);
    const empty = width - filled;
    
    const filledBar = '█'.repeat(filled);
    const emptyBar = '░'.repeat(empty);
    
    const progressColors = ['#00FFFF', '#00AAFF', '#6A5ACD', '#BA55D3', '#FF69B4'];
    const colorIndex = Math.min(Math.floor((percent / 100) * progressColors.length), progressColors.length - 1);
    const barColor = progressColors[Math.max(0, colorIndex)];
    
    return `${chalk.hex(barColor)(filledBar)}${chalk.gray(emptyBar)} ${chalk.white(percent.toString().padStart(3))}%`;
  }

  /**
   * 清除之前渲染的行
   */
  clearPreviousRender() {
    if (this.linesRendered > 0) {
      // 光标上移并清除
      process.stdout.write(`\x1B[${this.linesRendered}A`);
      for (let i = 0; i < this.linesRendered; i++) {
        process.stdout.write('\x1B[2K\n'); // 清除当前行
      }
      process.stdout.write(`\x1B[${this.linesRendered}A`); // 回到起始位置
    }
  }

  /**
   * 更新步骤名称（用于动态添加信息如备份文件名）
   */
  updateStepName(index, newName) {
    if (index >= 0 && index < this.steps.length) {
      this.steps[index].name = newName;
    }
  }

  /**
   * 渲染整个时间线
   */
  render() {
    this.clearPreviousRender();
    
    const lines = [];
    
    // 标题行
    lines.push('');
    lines.push(chalk.cyan(`  ${this.title}`) + chalk.gray(` [${this.taskIndex + 1}/${this.taskTotal}]`) + '    ' + this.renderProgressBar());
    
    if (this.showHint) {
      lines.push(chalk.gray(`  按 [v] 显示日志 | [q] 退出`));
    }
    
    lines.push('');
    lines.push(chalk.cyan(`  ┌─ 步骤进度`));
    lines.push(chalk.cyan(`  │`));
    
    // 步骤列表
    this.steps.forEach((step, index) => {
      const isLast = index === this.steps.length - 1;
      const treeChar = this.getTreeChar(index, isLast);
      const icon = this.getStatusIcon(step.status, isLast);
      
      let stepName = step.name;
      if (step.status === 'running') {
        stepName = chalk.yellow(step.name + '...');
      } else if (step.status === 'completed') {
        stepName = chalk.green(step.name);
      } else if (step.status === 'failed') {
        stepName = chalk.red(step.name);
      } else if (step.status === 'skipped') {
        stepName = chalk.yellow(step.name);
      } else {
        stepName = chalk.gray(step.name);
      }
      
      lines.push(chalk.cyan(`  ${treeChar} `) + icon + ' ' + stepName);
    });
    
    lines.push('');
    
    // 输出所有行
    const output = lines.join('\n');
    process.stdout.write(output + '\n');
    this.linesRendered = lines.length;
  }

  /**
   * 开始一个步骤
   */
  startStep(index) {
    if (index >= 0 && index < this.steps.length) {
      this.currentIndex = index;
      this.steps[index].status = 'running';
      this.render();
    }
  }

  /**
   * 完成当前步骤
   */
  completeStep(index, status = 'completed') {
    if (index >= 0 && index < this.steps.length) {
      this.steps[index].status = status;
      this.render();
    }
  }

  /**
   * 完成所有渲染（显示光标）
   */
  finish() {
    // 不需要额外操作，保持最终状态
  }
}

/**
 * 渲染进度条
 * @param {number} current - 当前进度
 * @param {number} total - 总进度
 * @param {number} width - 进度条宽度
 * @returns {string} 进度条字符串
 */
function renderProgressBar(current, total, width = 30) {
  const percent = Math.round((current / total) * 100);
  const filled = Math.round((current / total) * width);
  const empty = width - filled;
  
  const filledBar = '█'.repeat(filled);
  const emptyBar = '░'.repeat(empty);
  
  // 渐变色进度条
  const progressColors = ['#00FFFF', '#00AAFF', '#6A5ACD', '#BA55D3', '#FF69B4'];
  const colorIndex = Math.min(Math.floor((percent / 100) * progressColors.length), progressColors.length - 1);
  const barColor = progressColors[colorIndex];
  
  return `${chalk.hex(barColor)(filledBar)}${chalk.gray(emptyBar)} ${chalk.white(percent.toString().padStart(3))}%`;
}

/**
 * 显示任务标题
 */
function showTaskTitle(title, current, total) {
  console.log('');
  console.log(chalk.cyan(`  ${title}`) + chalk.gray(` [${current + 1}/${total}]`));
  console.log(chalk.gray(`  按 [v] 显示日志 | [q] 退出`));
  console.log('');
}

/**
 * 将 HEX 颜色转换为 RGB
 */
function hexToRgb(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16),
  } : { r: 0, g: 0, b: 0 };
}

/**
 * 将 RGB 转换为 HEX
 */
function rgbToHex(r, g, b) {
  return '#' + [r, g, b].map(x => {
    const hex = Math.round(x).toString(16);
    return hex.length === 1 ? '0' + hex : hex;
  }).join('');
}

/**
 * 在两个颜色之间进行平滑插值
 */
function interpolateColor(color1, color2, factor) {
  const rgb1 = hexToRgb(color1);
  const rgb2 = hexToRgb(color2);
  
  const r = rgb1.r + (rgb2.r - rgb1.r) * factor;
  const g = rgb1.g + (rgb2.g - rgb1.g) * factor;
  const b = rgb1.b + (rgb2.b - rgb1.b) * factor;
  
  return rgbToHex(r, g, b);
}

/**
 * 根据位置获取渐变颜色（支持多色渐变）
 */
function getGradientColor(colors, position) {
  // position 范围 0-1
  const pos = Math.max(0, Math.min(1, position));
  const scaledPos = pos * (colors.length - 1);
  const index = Math.floor(scaledPos);
  const factor = scaledPos - index;
  
  if (index >= colors.length - 1) {
    return colors[colors.length - 1];
  }
  
  return interpolateColor(colors[index], colors[index + 1], factor);
}

// Banner 数据
const BANNER_LINES = [
  '██████╗ ███████╗██████╗ ██╗      ██████╗ ██╗   ██╗',
  '██╔══██╗██╔════╝██╔══██╗██║     ██╔═══██╗╚██╗ ██╔╝',
  '██║  ██║█████╗  ██████╔╝██║     ██║   ██║ ╚████╔╝ ',
  '██║  ██║██╔══╝  ██╔═══╝ ██║     ██║   ██║  ╚██╔╝  ',
  '██████╔╝███████╗██║     ███████╗╚██████╔╝   ██║   ',
  '╚═════╝ ╚══════╝╚═╝     ╚══════╝ ╚═════╝    ╚═╝   ',
];

// 渐变色 (青色 -> 蓝色 -> 紫色 -> 粉色)
const GRADIENT_COLORS = [
  '#00FFFF', // cyan
  '#00D4FF', // sky blue
  '#00AAFF', // azure
  '#0080FF', // blue
  '#4169E1', // royal blue
  '#6A5ACD', // slate blue
  '#8A2BE2', // blue violet
  '#9932CC', // dark orchid
  '#BA55D3', // medium orchid
  '#DA70D6', // orchid
  '#FF69B4', // hot pink
];

/**
 * 渲染 Banner（带颜色偏移量实现动画）
 * @param {number} colorOffset - 颜色偏移量 (0-1)
 * @param {boolean} isFirstRender - 是否首次渲染
 */
function renderBanner(colorOffset = 0, isFirstRender = true) {
  const totalRows = BANNER_LINES.length;
  const maxCols = Math.max(...BANNER_LINES.map(l => l.length));

  if (!isFirstRender) {
    // 保存当前光标位置
    process.stdout.write('\x1B[s');
    // 移动光标到屏幕顶部第2行（Banner 起始位置）
    process.stdout.write('\x1B[2;1H');
  }

  // 渲染 Banner
  if (isFirstRender) {
    process.stdout.write('\n');
  }
  
  BANNER_LINES.forEach((line, rowIndex) => {
    let coloredLine = '  ';
    for (let colIndex = 0; colIndex < line.length; colIndex++) {
      // 对角线渐变 + 颜色偏移实现脉冲效果
      const diagonalProgress = (rowIndex / totalRows + colIndex / maxCols) / 2;
      // 添加偏移量并循环
      const animatedProgress = (diagonalProgress + colorOffset) % 1;
      const color = getGradientColor(GRADIENT_COLORS, animatedProgress);
      coloredLine += chalk.hex(color)(line[colIndex]);
    }
    // 清除当前行并输出
    process.stdout.write('\x1B[2K' + coloredLine + '\n');
  });

  if (!isFirstRender) {
    // 恢复光标位置
    process.stdout.write('\x1B[u');
  }
}

/**
 * 启动 Banner 动画
 */
function startBannerAnimation() {
  console.clear();
  
  // 首次渲染 Banner
  renderBanner(0, true);
  
  // 输出静态部分
  console.log('');
  console.log(chalk.gray('  Frontend Deploy Tool v1.0'));
  console.log('');
  console.log(chalk.gray('━'.repeat(56)));
  console.log('');

  // 启动动画定时器
  bannerAnimationTimer = setInterval(() => {
    bannerColorOffset = (bannerColorOffset + 0.05) % 1; // 每次偏移 5%
    renderBanner(bannerColorOffset, false);
  }, 50); // 每 50ms 更新一次
}

/**
 * 停止 Banner 动画
 */
function stopBannerAnimation() {
  if (bannerAnimationTimer) {
    clearInterval(bannerAnimationTimer);
    bannerAnimationTimer = null;
  }
}

/**
 * 恢复 Banner 动画（不清屏，只重新启动定时器）
 * 注意：恢复后动画会继续在当前光标位置以上的 Banner 区域更新
 */
function resumeBannerAnimation() {
  if (bannerAnimationTimer) return; // 已经在运行
  
  // 重新启动动画定时器
  bannerAnimationTimer = setInterval(() => {
    bannerColorOffset = (bannerColorOffset + 0.05) % 1;
    renderBanner(bannerColorOffset, false);
  }, 50);
}

/**
 * 加载环境配置
 */
function loadConfig() {
  const envPath = resolve(__dirname, 'deploy.env');

  if (!existsSync(envPath)) {
    console.error(chalk.red('  错误: 配置文件不存在'));
    console.log('  请先复制配置文件: cp scripts/deploy.env.example scripts/deploy.env');
    console.log('  然后编辑 scripts/deploy.env 填入实际配置');
    process.exit(1);
  }

  const envContent = readFileSync(envPath, 'utf-8');
  const config = {};

  envContent.split('\n').forEach((line) => {
    const trimmed = line.trim();
    if (trimmed && !trimmed.startsWith('#')) {
      const [key, ...valueParts] = trimmed.split('=');
      if (key && valueParts.length > 0) {
        config[key.trim()] = valueParts.join('=').trim();
      }
    }
  });

  config.SERVER_PORT = config.SERVER_PORT || '22';
  config.SSH_KEY_PATH = config.SSH_KEY_PATH || '~/.ssh/github_deploy_key';

  return config;
}

/**
 * 设置按键监听
 */
function setupKeyListener() {
  if (keyListener) return;

  readline.emitKeypressEvents(process.stdin);
  if (process.stdin.isTTY) {
    process.stdin.setRawMode(true);
  }

  keyListener = (str, key) => {
    if (key.name === 'v') {
      showLogs = !showLogs;
      if (showLogs && currentLogBuffer.length > 0) {
        console.log(chalk.gray('\n--- Log Output ---'));
        currentLogBuffer.forEach((line) => console.log(chalk.gray(line)));
        console.log(chalk.gray('--- End Log ---\n'));
      }
    } else if (key.name === 'q' || (key.ctrl && key.name === 'c')) {
      cleanup();
      console.log(chalk.yellow('\n\nOperation cancelled'));
      process.exit(0);
    }
  };

  process.stdin.on('keypress', keyListener);
  process.stdin.resume();
}

/**
 * 清理资源
 */
function cleanup() {
  // 停止 Banner 动画
  stopBannerAnimation();
  
  if (process.stdin.isTTY) {
    process.stdin.setRawMode(false);
  }
  process.stdin.removeAllListeners('keypress');
  process.stdin.pause();
  keyListener = null;
}

/**
 * 执行命令并捕获输出到缓冲区
 */
function runCommand(command, spinner = null) {
  return new Promise((resolve) => {
    currentLogBuffer = [];
    const isWindows = process.platform === 'win32';
    const shell = isWindows ? 'cmd' : '/bin/sh';
    const shellFlag = isWindows ? '/c' : '-c';

    const child = spawn(shell, [shellFlag, command], {
      cwd: PROJECT_ROOT,
      env: process.env,
    });

    child.stdout.on('data', (data) => {
      const lines = data.toString().split('\n').filter((l) => l.trim());
      currentLogBuffer.push(...lines);
      if (showLogs) {
        lines.forEach((line) => console.log(chalk.gray(`  ${line}`)));
      }
    });

    child.stderr.on('data', (data) => {
      const lines = data.toString().split('\n').filter((l) => l.trim());
      currentLogBuffer.push(...lines);
      if (showLogs) {
        lines.forEach((line) => console.log(chalk.gray(`  ${line}`)));
      }
    });

    child.on('close', (code) => {
      resolve({
        success: code === 0,
        output: currentLogBuffer.join('\n'),
        code,
      });
    });

    child.on('error', (err) => {
      currentLogBuffer.push(err.message);
      resolve({
        success: false,
        output: err.message,
        code: -1,
      });
    });
  });
}

/**
 * 显示错误处理菜单
 */
async function showErrorMenu(stepName, errorOutput) {
  // 暂停按键监听以便 prompts 能工作
  if (process.stdin.isTTY) {
    process.stdin.setRawMode(false);
  }
  process.stdin.removeAllListeners('keypress');

  console.log('');
  console.log(chalk.red(`[x] ${stepName} 失败`));
  console.log('');

  const { action } = await prompts({
    type: 'select',
    name: 'action',
    message: '请选择操作:',
    choices: [
      { title: '查看错误详情', value: 'view' },
      { title: '重试此步骤', value: 'retry' },
      { title: '跳过继续', value: 'skip' },
      { title: '退出', value: 'exit' },
    ],
  });

  if (action === 'view') {
    console.log('');
    console.log(chalk.gray('━'.repeat(50)));
    console.log(chalk.red('错误输出:'));
    console.log(errorOutput || '无输出信息');
    console.log(chalk.gray('━'.repeat(50)));
    console.log('');
    return showErrorMenu(stepName, errorOutput);
  }

  // 重新设置按键监听
  setupKeyListener();

  return action;
}

/**
 * 获取当前时间戳字符串
 */
function getTimestamp() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hour = String(now.getHours()).padStart(2, '0');
  const minute = String(now.getMinutes()).padStart(2, '0');
  const second = String(now.getSeconds()).padStart(2, '0');
  return `${year}${month}${day}_${hour}${minute}${second}`;
}

/**
 * 显示步骤状态
 */
function printStepStatus(steps, currentIndex, status) {
  const statusIcons = {
    pending: chalk.gray('○'),
    running: chalk.yellow('◐'),
    completed: chalk.green('✓'),
    failed: chalk.red('✗'),
    skipped: chalk.gray('⊘'),
  };

  steps.forEach((step, idx) => {
    let stepStatus = 'pending';
    if (idx < currentIndex) stepStatus = 'completed';
    else if (idx === currentIndex) stepStatus = status;
    
    const icon = statusIcons[stepStatus];
    const name = stepStatus === 'running' 
      ? chalk.yellow(step.name) 
      : stepStatus === 'completed' 
        ? chalk.green(step.name)
        : stepStatus === 'failed'
          ? chalk.red(step.name)
          : chalk.gray(step.name);
    
    console.log(`  ${icon} ${name}`);
  });
}

/**
 * 获取应用中文名
 */
function getAppName(app) {
  const appNames = {
    'admin': '管理后台',
    'doctor': '医生端',
    'patient-h5': '患者端H5',
    'temp-registration': '临时挂号',
  };
  return appNames[app] || app;
}

/**
 * 执行步骤并更新时间线
 */
async function executeStepWithTimeline(timeline, stepIndex, command, stepName) {
  timeline.startStep(stepIndex);
  
  const result = await runCommand(command);

  if (result.success) {
    timeline.completeStep(stepIndex, 'completed');
    return { success: true };
  } else {
    timeline.completeStep(stepIndex, 'failed');
    const action = await showErrorMenu(stepName, result.output);
    
    if (action === 'retry') {
      return executeStepWithTimeline(timeline, stepIndex, command, stepName);
    } else if (action === 'skip') {
      timeline.completeStep(stepIndex, 'skipped');
      return { success: false, skipped: true };
    } else if (action === 'exit') {
      cleanup();
      process.exit(1);
    }
    return { success: false };
  }
}

/**
 * 处理应用（构建 + 部署合并为统一流程）
 */
async function processApp(app, config, index, total, shouldUpload) {
  const appName = getAppName(app);

  const { SERVER_HOST, SERVER_USER, SERVER_PORT, SSH_KEY_PATH, PROJECT_DIR } = config || {};

  const remoteAppDir = config ? `${PROJECT_DIR}/${app}` : '';
  const backupDir = config ? `${PROJECT_DIR}/backups` : '';
  const timestamp = getTimestamp();
  const backupFileName = `${app}_${timestamp}.tar.gz`;
  const backupFile = `${backupDir}/${backupFileName}`;

  const localDistDir = `apps/${app}/dist`;
  const localTarFile = `apps/${app}/${app}_deploy.tar.gz`;
  const remoteTarFile = config ? `${PROJECT_DIR}/${app}_deploy.tar.gz` : '';

  const sshArgs = config ? `-i "${SSH_KEY_PATH}" -p "${SERVER_PORT}" "${SERVER_USER}@${SERVER_HOST}"` : '';

  // 定义所有步骤（构建 + 部署）
  const allSteps = [
    { id: 'build', name: '编译' },
  ];

  // 如果需要上传，添加部署步骤
  if (shouldUpload) {
    allSteps.push(
      { id: 'compress', name: '压缩文件' },
      { id: 'backup-dir', name: `创建备份目录 (${backupFileName})` },
      { id: 'backup', name: '备份现有文件' },
      { id: 'cleanup-old', name: '清理旧备份' },
      { id: 'clean', name: '清空目标目录' },
      { id: 'upload', name: '上传压缩包' },
      { id: 'extract', name: '解压并清理' },
      { id: 'cleanup', name: '清理临时文件' },
    );
  }

  // 定义命令
  const allCommands = [
    `pnpm build:${app}`,
  ];

  if (shouldUpload) {
    allCommands.push(
      `cd ${localDistDir} && tar --exclude='.DS_Store' --exclude='__MACOSX' --exclude='._*' -czf ../${app}_deploy.tar.gz .`,
      `ssh ${sshArgs} "mkdir -p ${backupDir}"`,
      `ssh ${sshArgs} "if [ -d '${remoteAppDir}' ] && [ -n \\"\\$(ls -A '${remoteAppDir}' 2>/dev/null)\\" ]; then cd ${PROJECT_DIR} && tar -czf ${backupFile} ${app} && echo '备份完成'; else echo '跳过备份'; fi"`,
      `ssh ${sshArgs} "cd ${backupDir} && ls -t ${app}_*.tar.gz 2>/dev/null | tail -n +$((${MAX_BACKUPS_PER_APP} + 1)) | xargs -r rm -f && echo '已清理旧备份'"`,
      `ssh ${sshArgs} "mkdir -p ${remoteAppDir} && find ${remoteAppDir} -mindepth 1 -maxdepth 1 ! -name '.user.ini' ! -name '.htaccess' -exec rm -rf {} +"`,
      `scp -i "${SSH_KEY_PATH}" -P "${SERVER_PORT}" ${localTarFile} "${SERVER_USER}@${SERVER_HOST}:${remoteTarFile}"`,
      `ssh ${sshArgs} "cd ${remoteAppDir} && tar -xzf ${remoteTarFile} && rm -f ${remoteTarFile} && find . -name '.DS_Store' -delete && find . -name '._*' -delete && find . -name '__MACOSX' -type d -exec rm -rf {} + 2>/dev/null; echo '解压完成'"`,
      `rm -f ${localTarFile}`,
    );
  }

  // 哪些步骤失败可以继续（非关键步骤）- 备份和清理旧备份
  const nonCriticalSteps = shouldUpload ? [3, 4] : [];

  // 创建时间线
  const timeline = new TimelineProgress(appName, allSteps, {
    taskIndex: index,
    taskTotal: total,
  });

  timeline.render();

  // 执行所有步骤
  for (let i = 0; i < allSteps.length; i++) {
    const result = await executeStepWithTimeline(timeline, i, allCommands[i], allSteps[i].name);
    
    if (!result.success && !result.skipped) {
      // 构建失败（第0步）
      if (i === 0) {
        timeline.finish();
        return { success: false, skipped: false };
      }
      
      // 如果是关键步骤失败
      if (!nonCriticalSteps.includes(i)) {
        // 清理本地临时文件
        if (i > 1) {
          await runCommand(`rm -f ${localTarFile}`);
        }
        timeline.finish();
        return { success: false, skipped: false };
      }
    }
  }

  timeline.finish();

  return { success: true };
}

/**
 * 主函数
 */
/**
 * 延迟函数
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function main() {
  startBannerAnimation();

  // 加载配置（在动画期间加载）
  const config = loadConfig();

  // 等待动画显示一段时间（让用户能看到动画效果）
  await sleep(2000);

  // 显示服务器信息
  console.log(chalk.white(`  服务器: ${config.SERVER_USER}@${config.SERVER_HOST}:${config.SERVER_PORT}`));
  console.log(chalk.white(`  目标路径: ${config.PROJECT_DIR}`));
  console.log('');

  // 暂停动画以便 prompts 交互（prompts 需要控制终端光标）
  stopBannerAnimation();

  // 选择要构建的应用
  const { selectedApps } = await prompts({
    type: 'multiselect',
    name: 'selectedApps',
    message: '选择要构建的应用 (空格选择，回车确认)',
    choices: APPS.map((app) => ({
      title: `${app.title} - ${app.description}`,
      value: app.value,
      selected: false,
    })),
    hint: '- 空格选择，回车确认',
    instructions: false,
    min: 1,
  });

  if (!selectedApps || selectedApps.length === 0) {
    console.log(chalk.yellow('未选择任何应用，退出'));
    process.exit(0);
  }

  console.log('');
  console.log(`已选择: ${chalk.cyan(selectedApps.join(', '))}`);
  console.log('');

  // 询问是否上传到服务器
  const { shouldUpload } = await prompts({
    type: 'confirm',
    name: 'shouldUpload',
    message: '构建后是否上传到服务器?',
    initial: true,
  });

  if (shouldUpload === undefined) {
    console.log(chalk.yellow('操作已取消'));
    process.exit(0);
  }

  // 设置按键监听
  setupKeyListener();

  console.log('');
  console.log(chalk.gray('━'.repeat(56)));

  // 计算总任务数
  const totalApps = selectedApps.length;

  // 开始任务
  const failedApps = [];
  const skippedApps = [];

  console.log('');
  console.log(chalk.cyan.bold('  任务进度'));
  console.log(chalk.gray('━'.repeat(56)));
  
  // 重新启动 Banner 动画（在任务执行期间继续运行）
  resumeBannerAnimation();

  // 对每个应用依次执行构建和部署（合并为统一流程）
  for (let i = 0; i < totalApps; i++) {
    const app = selectedApps[i];
    
    const result = await processApp(app, config, i, totalApps, shouldUpload);
    
    if (!result.success) {
      if (result.skipped) {
        skippedApps.push(app);
      } else {
        failedApps.push(app);
      }
    }
  }

  // 清理资源
  cleanup();

  // 完成
  console.log('');
  console.log(chalk.gray('━'.repeat(56)));
  console.log('');

  if (failedApps.length === 0 && skippedApps.length === 0) {
    console.log(chalk.green.bold('  所有任务已完成!'));
  } else {
    if (failedApps.length > 0) {
      console.log(chalk.red(`  [x] 失败: ${failedApps.join(', ')}`));
    }
    if (skippedApps.length > 0) {
      console.log(chalk.yellow(`  [-] 跳过: ${skippedApps.join(', ')}`));
    }
  }

  console.log('');
  console.log(chalk.white('  处理结果:'));
  selectedApps.forEach((app) => {
    const name = getAppName(app);
    if (failedApps.includes(app)) {
      console.log(`    ${chalk.red('✗')} ${name} (${app})`);
    } else if (skippedApps.includes(app)) {
      console.log(`    ${chalk.yellow('⊘')} ${name} (${app})`);
    } else {
      console.log(`    ${chalk.green('✓')} ${name} (${app})`);
    }
  });
  console.log('');
}

// 处理 Ctrl+C
process.on('SIGINT', () => {
  cleanup();
  console.log(chalk.yellow('\n\n  操作已取消'));
  process.exit(0);
});

// 运行主函数
main().catch((error) => {
  cleanup();
  console.error(chalk.red('  错误:'), error.message);
  process.exit(1);
});
