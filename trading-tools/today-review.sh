#!/bin/bash
# 生成今日复盘模板并追加到博客
# 工作流：通达信 → 复盘模板 → _posts/2026-04-16-blog-post-trade-record.md
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
source .venv/bin/activate
python main.py append-review "$@"