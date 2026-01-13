#!/bin/bash
# 远程开发环境启动脚本
export PROXY_TARGET=https://yy.aicm.online
export HOST=127.0.0.1
export PORT=8005
export REACT_APP_ENV=dev
export NODE_OPTIONS='--require ./scripts/fix-network.js'

echo "🚀 Starting admin with PROXY_TARGET=$PROXY_TARGET"
npx max dev
