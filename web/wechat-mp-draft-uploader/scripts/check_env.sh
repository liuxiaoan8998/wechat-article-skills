#!/bin/bash
# 检查 wechat-mp-draft-uploader 环境配置

echo "=========================================="
echo "微信公众号草稿上传 - 环境检查"
echo "=========================================="

# 检查 API Key
if [ -z "$JIANLIZHIZUO_API_KEY" ]; then
    echo "❌ JIANLIZHIZUO_API_KEY 未设置"
    echo "   请添加到 ~/.hermes/.env:"
    echo "   JIANLIZHIZUO_API_KEY=your_api_key"
    exit 1
else
    echo "✓ JIANLIZHIZUO_API_KEY 已设置"
    # 隐藏部分显示
    KEY_LENGTH=${#JIANLIZHIZUO_API_KEY}
    HIDDEN_KEY="${JIANLIZHIZUO_API_KEY:0:8}...${JIANLIZHIZUO_API_KEY: -4}"
    echo "   Key: $HIDDEN_KEY"
fi

# 检查 API 连通性
echo ""
echo "检查 API 连通性..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $JIANLIZHIZUO_API_KEY" \
    "https://mp.jianlizhizuo.cn/v1/accounts")

if [ "$RESPONSE" = "200" ] || [ "$RESPONSE" = "401" ]; then
    echo "✓ API 连通正常 (HTTP $RESPONSE)"
else
    echo "⚠ API 连通异常 (HTTP $RESPONSE)"
fi

# 检查 lark-cli
echo ""
echo "检查飞书 CLI..."
if command -v lark-cli &> /dev/null; then
    echo "✓ lark-cli 已安装"
else
    echo "❌ lark-cli 未安装"
    echo "   请运行: lark-cli install"
fi

# 检查本地输出目录
echo ""
echo "检查文章目录..."
OUTPUT_DIR="$HOME/.hermes/output"
if [ -d "$OUTPUT_DIR" ]; then
    ARTICLE_COUNT=$(find "$OUTPUT_DIR" -maxdepth 1 -type d | wc -l)
    echo "✓ 文章目录存在: $OUTPUT_DIR"
    echo "   文章数量: $((ARTICLE_COUNT - 1))"
else
    echo "⚠ 文章目录不存在: $OUTPUT_DIR"
fi

echo ""
echo "=========================================="
echo "检查完成"
echo "=========================================="
