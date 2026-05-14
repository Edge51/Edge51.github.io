#!/bin/bash
# 生成今日复盘模板并追加到博客
# 用法: bash today-review.sh [--active-value -1.55]
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
source .venv/bin/activate
python main.py append-review "$@"