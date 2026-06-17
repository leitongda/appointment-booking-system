#!/usr/bin/env node

import { spawn, spawnSync } from 'node:child_process';
import { closeSync, openSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const children = new Set();
const lockPath = resolve('.taro-weapp-dev.lock');
let shuttingDown = false;
let ownsLock = false;

function acquireLock() {
  try {
    const lockFd = openSync(lockPath, 'wx');
    writeFileSync(lockFd, String(process.pid));
    closeSync(lockFd);
    ownsLock = true;
  } catch (error) {
    if (error.code !== 'EEXIST') throw error;

    const existingPid = Number(readFileSync(lockPath, 'utf8'));
    try {
      process.kill(existingPid, 0);
      console.error(`[dev-weapp] patient-miniapp watcher 已在运行（PID ${existingPid}）`);
      process.exit(1);
    } catch (processError) {
      if (processError.code === 'ESRCH') {
        rmSync(lockPath, { force: true });
        acquireLock();
        return;
      }

      console.error(`[dev-weapp] patient-miniapp watcher 已在运行（PID ${existingPid}）`);
      process.exit(1);
    }
  }
}

function start(command, args, env = process.env) {
  const child = spawn(command, args, {
    stdio: 'inherit',
    env,
  });

  children.add(child);
  child.once('error', () => {
    children.delete(child);
    shutdown(1);
  });
  child.once('exit', (code, signal) => {
    children.delete(child);
    if (!shuttingDown) {
      shutdown(signal ? 1 : (code ?? 1));
    }
  });

  return child;
}

function shutdown(exitCode = 0) {
  if (shuttingDown) return;
  shuttingDown = true;
  if (ownsLock) {
    rmSync(lockPath, { force: true });
    ownsLock = false;
  }

  for (const child of children) {
    child.kill('SIGTERM');
  }

  const forceExit = setTimeout(() => {
    for (const child of children) {
      child.kill('SIGKILL');
    }
    process.exit(exitCode);
  }, 3000);
  forceExit.unref();

  if (children.size === 0) {
    process.exit(exitCode);
  }

  for (const child of children) {
    child.once('exit', () => {
      children.delete(child);
      if (children.size === 0) {
        process.exit(exitCode);
      }
    });
  }
}

process.once('SIGINT', () => shutdown(0));
process.once('SIGTERM', () => shutdown(0));
process.once('exit', () => {
  if (ownsLock) {
    rmSync(lockPath, { force: true });
  }
});

acquireLock();

if (process.argv.includes('--clean')) {
  const cleanResult = spawnSync(process.execPath, ['scripts/clean.mjs'], {
    stdio: 'inherit',
    env: process.env,
  });
  if (cleanResult.status !== 0) {
    shutdown(cleanResult.status ?? 1);
  }
}

start('taro', ['build', '--type', 'weapp', '--watch', '--no-check'], {
  ...process.env,
  // 并行 loader 会在各自进程中重复输出同一条旧数据提醒。
  // 正式 build 不设置此变量，仍会提示依赖数据需要更新。
  BROWSERSLIST_IGNORE_OLD_DATA: '1',
  // 强制 Watchpack 使用轮询，避免 macOS 上 EMFILE 导致 watcher 退出并刷屏。
  WATCHPACK_POLLING: 'true',
  WATCHPACK_POLLING_INTERVAL: '1000',
});
start(process.execPath, ['scripts/fix-wxml.js', '--watch']);
