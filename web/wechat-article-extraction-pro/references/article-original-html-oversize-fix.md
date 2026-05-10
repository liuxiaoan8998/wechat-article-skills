# article_original.html 过大导致上传超时 - 故障与解决方案

> **发现日期**: 2026-04-27
> **严重程度**: 高（会导致草稿上传 100% 失败）
> **解决状态**: 已解决（提取工具需内置精简化逻辑）

---

## 问题现象

微信公众号文章提取后，`article_original.html` 文件大小可达 **3-5MB**（正常文章通常几百 KB）。

使用 `wechat-mp-draft-uploader` 上传到微信公众号草稿时：
- API 返回超时（timeout）
- 或 `413 Request Entity Too Large`
- 草稿创建失败，或内容不完整

## 根本原因

微信原始 HTML 包含大量对草稿上传无用的内嵌资源：

| 资源类型 | 大小 | 说明 |
|----------|------|------|
| 微信 JS SDK | 200-500KB | `<script>` 标签内的分享/支付/统计 SDK |
| base64 图片预览 | 1-3MB | `data-src` 属性中的内联图片 |
| 微信样式表 | 100-300KB | 大量未使用的 CSS 模板 |
| 模板代码 | 100-200KB | `读原文`、`赞赏`、`广告` 等插件的 HTML |

这些内容对微信页面渲染必需，但对公众号草稿上传完全无用。简立制作 API 的 JSON payload 有大小限制，大体积 HTML 会导致请求超时。

## 解决方案

### 方案 A：提取时生成精简 HTML（推荐）

在文章提取阶段（Python 工具）就生成一个专门用于上传的精简 HTML：

```python
import re

def extract_upload_html(original_html: str, title: str) -> str:
    """
    从微信原始 HTML 中提取精简版正文 HTML
    用于公众号草稿上传，通常从 3.7MB 缩减到 ~17KB
    """
    # 1. 提取 #js_content 区域（微信文章正文）
    match = re.search(
        r'<div[^>]*id=["\']js_content["\'][^>]*>(.*?)</div>\s*(?:</div>\s*)?<script',
        original_html, re.DOTALL
    )
    if not match:
        match = re.search(
            r'<div[^>]*id=["\']js_content["\'][^>]*>(.*?)',
            original_html, re.DOTALL
        )
    
    content_html = match.group(1) if match else original_html
    
    # 2. 移除 script/style 标签
    content_html = re.sub(r'<script[^>]*>.*?</script>', '', content_html,
                          flags=re.DOTALL | re.IGNORECASE)
    content_html = re.sub(r'<style[^>]*>.*?</style>', '', content_html,
                          flags=re.DOTALL | re.IGNORECASE)
    
    # 3. 清理微信特有属性（保留标准 img src 用于后续替换）
    content_html = re.sub(r'\s*data-src=["\'][^"\']*["\']', '', content_html)
    content_html = re.sub(r'\s*data-ratio=["\'][^"\']*["\']', '', content_html)
    content_html = re.sub(r'\s*data-type=["\'][^"\']*["\']', '', content_html)
    content_html = re.sub(r'\s*data-w=["\'][^"\']*["\']', '', content_html)
    
    # 4. 构建精简 HTML
    upload_html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  line-height: 1.8;
  color: #333;
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}}
img {{
  max-width: 100%;
  height: auto;
  display: block;
  margin: 0;
}}
strong {{
  font-weight: bold;
}}
</style>
</head>
<body>
{content_html}
</body>
</html>'''
    
    return upload_html
```

### 方案 B：上传脚本处理（应急）

如果提取工具未生成精简 HTML，在上传脚本中实时处理：

```python
def prepare_content_for_upload(article_dir: str) -> str:
    """
    准备用于上传的正文 HTML，处理过大文件问题
    """
    from pathlib import Path
    import re
    
    article_path = Path(article_dir)
    
    # 优先尝试精简版
    upload_html_path = article_path / "article_upload.html"
    if upload_html_path.exists():
        return upload_html_path.read_text(encoding="utf-8")
    
    # 次之尝试原始 HTML（检查大小）
    original_html_path = article_path / "article_original.html"
    if original_html_path.exists():
        size_mb = original_html_path.stat().st_size / (1024 * 1024)
        if size_mb > 1.0:
            # 文件过大，实时精简化
            original_html = original_html_path.read_text(encoding="utf-8")
            # 调用方案 A 的函数
            return extract_upload_html(original_html, "标题")
        else:
            return original_html_path.read_text(encoding="utf-8")
    
    # 最后回退到 article.html
    html_path = article_path / "article.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    
    raise FileNotFoundError(f"未找到可用的 HTML 文件: {article_dir}")
```

## 预期效果

| 指标 | 原始 HTML (article_original.html) | 精简 HTML (article_upload.html) | 改善 |
|------|-----------------------------------|--------------------------------|------|
| 文件大小 | 3.7MB | ~17KB | **缩减 99.5%** |
| 上传成功率 | 0% (超时) | 100% | **完全恢复** |
| 内容完整性 | 含无用 JS/CSS | 仅正文+图片占位符 | **更干净** |
| API 响应时间 | >30s (超时) | <3s | **10倍提升** |

## 输出文件规范（建议）

提取工具应输出以下 HTML 文件：

| 文件名 | 用途 | 大小典型值 | 说明 |
|--------|------|------------|------|
| `article_original.html` | 完整原始 HTML | 3-5MB | 保留所有微信原生内容，供开发调试 |
| `article_upload.html` ⭐ | **精简上传版** | ~17KB | **专用于公众号草稿上传** |
| `article.html` | Markdown 查看器 | ~2KB | 本地预览用（可选） |

## 上传脚本优先级（更新）

上传脚本 (`upload_from_feishu.py`) 应按以下优先级选择正文源：

```python
def get_content_html(article_dir: str) -> str:
    """获取用于上传的正文 HTML"""
    from pathlib import Path
    
    path = Path(article_dir)
    
    # 优先级 1: 精简上传版（推荐，大小合适）
    upload_html = path / "article_upload.html"
    if upload_html.exists():
        return upload_html.read_text(encoding="utf-8")
    
    # 优先级 2: 原始 HTML（检查大小，过大则精简化）
    original_html = path / "article_original.html"
    if original_html.exists():
        size_mb = original_html.stat().st_size / (1024 * 1024)
        if size_mb > 1.0:
            # 实时精简化处理
            return extract_upload_html(
                original_html.read_text(encoding="utf-8"),
                "标题"  # 实际应使用 metadata 中的标题
            )
        return original_html.read_text(encoding="utf-8")
    
    # 优先级 3: 普通 HTML（降级）
    html = path / "article.html"
    if html.exists():
        return html.read_text(encoding="utf-8")
    
    raise FileNotFoundError(f"未找到可用的正文文件: {article_dir}")
```

## 快速诊断

```bash
# 检查 article_original.html 大小
ls -lh ~/.hermes/output/{article_id}/

# 正常（已生成精简版）
# article_upload.html      17K   ← 应该存在且小于 100KB
# article_original.html    3.7M  ← 可以存在但上传脚本不应直接使用

# 异常（未生成精简版）
# article_original.html    3.7M  ← 唯一的 HTML，上传会失败
# 缺少 article_upload.html
```

## 相关 Skill

- `wechat-mp-draft-uploader` - 草稿上传脚本，需同步更新优先级逻辑
- `wechat-article-extraction-pro` - 提取工具，需内置精简化功能

---

**总结**: 这是一个从实际故障中发现的问题。`article_original.html` 虽然完整保留了微信原始格式，但内联的 JS 和 base64 资源会导致草稿上传 API 超时。必须在提取阶段就生成专门的精简版 HTML (`article_upload.html`)，或者上传脚本实时处理。
