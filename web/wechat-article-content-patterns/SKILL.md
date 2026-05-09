---
name: wechat-article-content-patterns
description: >
  微信公众号文章内容模式识别指南。
  识别长图模式 vs 正常HTML模式，正确处理不同发布形式的文章。
---

# 微信公众号文章内容模式识别

## 长图文章模式（重要发现）

### 现象
部分公众号文章（如南航校招）的 `js_content` 仅包含 500-1000 字节，只有一张图片。

### 原因
这是微信公众号的**长图发布模式**——文章内容全部嵌入在一张超长图片中，而非HTML文本。

### 特征识别

| 指标 | 长图模式 | 正常HTML模式 |
|------|---------|-------------|
| js_content 大小 | < 1KB | 10KB+ |
| 内容形式 | 单张超长图片（高度>2000px） | 多段落文字+图片 |
| 正文获取 | 必须通过OCR识别 | 直接提取HTML文本 |
| HTML文件大小 | 20-30KB（主要是页面框架） | 50KB+（含完整内容） |
| 图片数量 | 1张（超长图） | 多张（正常尺寸） |

### 识别代码

```python
import os
import re

def detect_content_mode(article_dir: str) -> dict:
    """
    检测文章发布模式
    
    Args:
        article_dir: 文章输出目录
        
    Returns:
        dict: 包含 mode, confidence, reason
    """
    html_path = os.path.join(article_dir, "article.html")
    ocr_path = os.path.join(article_dir, "article-ocr.md")
    
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # 提取js_content
    js_match = re.search(
        r'<div[^>]*id=["\']js_content["\'][^>]*>(.*?)</div>\s*</div>\s*(?:<script|<div class="rich_media_tool")',
        html_content, re.DOTALL | re.IGNORECASE
    )
    
    if not js_match:
        return {"mode": "unknown", "confidence": 0, "reason": "无法提取js_content"}
    
    inner_content = js_match.group(1)
    js_size = len(inner_content)
    
    # 检查图片数量
    img_count = html_content.count('<img')
    
    # 检查OCR内容
    ocr_size = 0
    if os.path.exists(ocr_path):
        ocr_size = os.path.getsize(ocr_path)
    
    # 判断模式
    if js_size < 2000 and img_count <= 2 and ocr_size > 2000:
        return {
            "mode": "long_image",
            "confidence": 0.95,
            "reason": f"js_content仅{js_size}字节，{img_count}张图片，但OCR内容{ocr_size}字节",
            "recommendation": "使用article-ocr.md获取正文"
        }
    elif js_size > 10000:
        return {
            "mode": "normal_html",
            "confidence": 0.9,
            "reason": f"js_content{js_size}字节，内容充足",
            "recommendation": "HTML内容可直接使用"
        }
    else:
        return {
            "mode": "mixed",
            "confidence": 0.7,
            "reason": f"js_content{js_size}字节，需进一步检查",
            "recommendation": "结合OCR和HTML使用"
        }
```

### 正确处理流程

```
提取文章
    ↓
检查 js_content 大小
    ↓
< 2KB? → 长图模式 → 依赖OCR识别
    ↓
> 10KB? → 正常模式 → HTML直接可用
    ↓
OCR结果回填到 article-ocr.md
    ↓
AI分析OCR内容提取关键信息
```

### 关键认知

1. **这不是bug**：长图模式是公众号的合法发布形式
2. **工具工作正常**：HTML提取完整、图片下载成功、OCR识别完成
3. **必须使用OCR**：通过 `article-ocr.md` 获取正文内容，而非 `article.html`
4. **OCR已自动完成**：工具已运行RapidOCR，结果保存在 `article-ocr.md` 中

### OCR 结果不足时的 Fallback 处理

当 `article-ocr.md` 内容为空或不足时（如 RapidOCR 识别失败），使用 `slices/` 目录下的切片进行手动 OCR：

```python
import glob
from hermes_tools import vision_analyze

def manual_ocr_slices(article_dir: str) -> str:
    """
    手动 OCR 识别 slices/ 目录下的图片切片
    作为 article-ocr.md 内容不足时的 fallback
    """
    slices_dir = os.path.join(article_dir, "slices")
    slices = sorted(glob.glob(os.path.join(slices_dir, "img_*_slice_*.jpg")))
    
    full_text = ""
    for slice_path in slices:
        result = vision_analyze(
            image_url=slice_path,
            question="请识别图片中的所有文字内容，特别关注岗位信息、学历要求、工作地点、投递方式、截止日期等关键字段"
        )
        full_text += f"\n--- 切片: {os.path.basename(slice_path)} ---\n"
        full_text += result.get("analysis", "")
    
    return full_text
```

**触发条件**：
- `article-ocr.md` 文件大小 < 500 字节
- `article-ocr.md` 只包含占位符，无实际 OCR 结果
- 文章内容明显在长图中，但 OCR 未提取出有效文字

**工作流程**：
```
提取文章
    ↓
检查 article-ocr.md
    ↓
内容充足 (>2KB)? → 直接使用
    ↓
内容不足 (<500B)? → 检查 slices/ 目录
    ↓
存在切片? → vision_analyze 逐片识别
    ↓
整合所有切片 OCR 结果 → 用于后续分析
```

### 常见长图文章类型

- 校招合集（多岗位汇总）
- 活动海报（招聘/宣讲会）
- 宣传长图（企业文化/福利介绍）
- 信息图表（数据可视化）

### 验证示例

**南航2026届校招**：
```
js_content大小: 940 bytes
图片数量: 1张（750x9426超长图）
OCR内容: 2,278 bytes（完整岗位信息）
模式: 长图模式 ✅
```

**交通银行2026校招**：
```
js_content大小: 9,461 bytes
图片数量: 7张
OCR内容: 3,752 bytes
模式: 混合模式（图文结合）
```

## 提取质量评估

### 健康指标

| 指标 | 健康范围 | 异常信号 |
|------|---------|---------|
| HTML总大小 | 20KB+ | < 15KB |
| js_content大小 | 2KB+（长图除外） | < 1KB（需检查OCR） |
| 图片数量 | 1-30张 | 0张 |
| OCR内容大小 | 2KB+（有图片时） | < 500字节 |
| 二维码识别 | 有/无都正常 | - |

### 诊断流程

```
提取完成
    ↓
HTML < 15KB?
    ├── 是 → 检查是否提取失败
    │         └── 重新提取
    │
    └── 否 → js_content < 1KB?
              ├── 是 → 检查OCR内容
              │         ├── OCR > 2KB → 长图模式，正常
              │         └── OCR < 500字节 → OCR失败，需修复
              │
              └── 否 → 正常HTML模式
```
