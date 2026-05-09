#!/bin/bash
# 快速上传微信公众号草稿
# 用法: ./upload_draft.sh <文章编号>

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UPLOAD_SCRIPT="$SCRIPT_DIR/upload_from_feishu.py"

# 检查参数
if [ $# -eq 0 ]; then
    echo "用法: $0 <文章编号>"
    echo "示例: $0 008"
    exit 1
fi

ARTICLE_NO="$1"

# 检查环境
if [ -z "$JIANLIZHIZUO_API_KEY" ]; then
    echo "❌ JIANLIZHIZUO_API_KEY 未设置"
    exit 1
fi

# 执行上传
echo "=========================================="
echo "开始上传 NO.$ARTICLE_NO"
echo "=========================================="

python3 "$UPLOAD_SCRIPT" -n "$ARTICLE_NO"

echo ""
echo "=========================================="
echo "上传完成"
echo "=========================================="
