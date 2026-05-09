#!/bin/bash
# WeChat Article Extraction Pro - 安装脚本
# 用途：初始化Python环境和依赖

set -e

PROJECT_DIR="/tmp/wechat-article-for-ai-pro"
VENV_DIR="$PROJECT_DIR/venv"

echo "=== WeChat Article Extraction Pro 安装 ==="

# 检查项目目录
if [ ! -d "$PROJECT_DIR" ]; then
    echo "错误: 项目目录不存在: $PROJECT_DIR"
    echo "请先从GitHub克隆项目:"
    echo "  cd /tmp && git clone https://github.com/liuxiaoan8998/wechat-article-for-ai-pro.git"
    exit 1
fi

cd "$PROJECT_DIR"

# 创建虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    echo "创建Python虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# 安装Playwright浏览器（如果需要）
if ! command -v camoufox &> /dev/null; then
    echo "提示: 如需使用Camoufox浏览器，请单独安装"
    echo "  详见: https://github.com/liuxiaoan8998/wechat-article-for-ai-pro#安装"
fi

echo "=== 安装完成 ==="
echo "使用方式:"
echo "  cd $PROJECT_DIR"
echo "  source venv/bin/activate"
echo "  python main.py <微信文章URL>"
