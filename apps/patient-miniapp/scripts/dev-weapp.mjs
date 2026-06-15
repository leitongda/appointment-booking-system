#!/usr/bin/env node

import { spawn } from 'node:child_process';

const children = new Set();
let shuttingDown = false;

function start(command, args) {
  const child = spawn(command, args, {
    stdio: 'inherit',
    env: process.env,
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

start('taro', ['build', '--type', 'weapp', '--watch', '--no-check']);
start(process.execPath, ['scripts/fix-wxml.js', '--watch']);
