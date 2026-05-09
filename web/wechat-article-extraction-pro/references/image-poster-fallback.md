# 纯图片/海报文章处理指南（2026-05-06 新增）

> 本文档记录一次实际故障排查中形成的复原流程。
> 问题触发点：Python 提取工具因 `/tmp` 被清理而缺失，且目标文章为纯图片/海报形式（`#js_content` 几乎为空，仅 "阅读原文"）。

---

## 1. 问题现象

- `/tmp/wechat-article-for-ai-pro` 被删除（`/tmp` 为临时目录）
- 浏览器 `browser_snapshot` 获取的文章正文极少（仅 "阅读原文"）
- 文章本质是一系列海报长图，所有文字 baked into images

## 2. 检测方法

```python
import re

# 方法A：requests 获取 HTML 后检测
resp = requests.get(url, headers=headers, timeout=30)
html = resp.text

content_match = re.search(
    r'<div[^>]*id=["\']js_content["\'][^>]*>(.*?)</div>\s*</div>',
    html, re.DOTALL
)
if content_match:
    text_only = re.sub(r'<[^>]+>', '', content_match.group(1)).strip()
    if len(text_only) < 50:
        print("⚠️ 检测到纯图片/海报文章，需启用图片提取+OCR模式")
```

## 3. 恢复方案（Hybrid fallback）

```python
import requests
import re
import json
from pathlib import Path
from datetime import datetime

def extract_image_poster_article(url: str, output_dir: str) -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # Step 1: 获取原始 HTML
    resp = requests.get(url, headers=headers, timeout=30)
    html = resp.text
    
    # Step 2: 提取标题
    title_match = re.search(
        r'<h2[^>]*class=["\']rich_media_title["\'][^>]*>(.*?)</h2>',
        html, re.DOTALL
    )
    title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else "未提取到标题"
    
    # Step 3: 提取图片 URL（优先 data-src，其次 src）
    img_urls = re.findall(r'data-src=["\'](https?://[^"\']+)["\']', html)
    if not img_urls:
        img_urls = re.findall(r'src=["\'](https?://[^"\']+)["\']', html)
    
    # Step 4: 创建输出目录
    safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)
    article_dir = Path(output_dir) / safe_title
    article_dir.mkdir(parents=True, exist_ok=True)
    images_dir = article_dir / "images"
    images_dir.mkdir(exist_ok=True)
    
    # Step 5: 下载图片
    downloaded = []
    for i, img_url in enumerate(img_urls):
        try:
            img_resp = requests.get(img_url, headers=headers, timeout=30)
            if img_resp.status_code == 200:
                ext = img_url.split('?')[0].split('.')[-1]
                if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                    ext = 'jpg'
                img_path = images_dir / f"img_{i+1:03d}.{ext}"
                img_path.write_bytes(img_resp.content)
                downloaded.append(str(img_path))
        except Exception as e:
            print(f"⚠️ 图片下载失败: {img_url[:50]}... - {e}")
    
    # Step 6: 写入 metadata.json
    metadata = {
        "url": url,
        "title": title,
        "author": "",
        "published_at": "",
        "extraction_method": "image-poster-fallback",
        "extraction_time": datetime.now().isoformat(),
        "image_count": len(downloaded),
        "images": downloaded
    }
    (article_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    # Step 7: 生成 article-ocr.md 占位符（OCR 由 Vision 后续完成）
    ocr_md = f"""# {title}

## 一、原文文字内容
（本文以图片/海报形式发布，无文字正文）

## 二、二维码识别内容
待识别

## 三、图片 OCR 识别内容
待识别（共 {len(downloaded)} 张图片）

## 四、完整文字内容（原文 + OCR + 二维码）
*待 OCR 完成后自动更新*
"""
    (article_dir / "article-ocr.md").write_text(ocr_md, encoding="utf-8")
    
    return {
        "success": True,
        "article_dir": str(article_dir),
        "title": title,
        "image_count": len(downloaded),
        "images_dir": str(images_dir)
    }
```

## 4. 后续 OCR 流程

对每张下载的图片调用 `vision_analyze` 进行 OCR：

```python
from pathlib import Path

images = sorted(Path(article_dir / "images").glob("img_*"))
ocr_parts = []
for img in images:
    result = vision_analyze(
        image_url=str(img),
        question="提取图片中的所有文字，保持原有排版和段落结构"
    )
    ocr_parts.append(f"### {img.name}\n{result}\n")

# 回填到 article-ocr.md 第三部分
```

## 5. 何时使用本方案

| 条件 | 处理方式 |
|------|---------|
| Python 工具正常，文章为图文混合 | 标准 `wechat-article-for-ai-pro` 提取 |
| Python 工具缺失或执行失败，且文章正文为纯文字 | 「终极备选：浏览器工具提取」（原 skill 内容） |
| Python 工具缺失或执行失败，且文章为纯图片/海报 | **本方案：image-poster-fallback** |

## 6. 关键经验

1. `/tmp` 是临时目录，`wechat-article-for-ai-pro` 可能随时被清理。若缺失，首先尝试重新克隆。
2. 不要假设所有文章都是文字正文。海报式文章的 `#js_content` 可能几乎为空。
3. 检测关键点：去除 HTML 标签后文字长度 < 50 字符 → 按图片文章处理。
4. 图片下载完成后，必须通过 Vision OCR 或 RapidOCR 提取文字才能进行后续 AI 分析和 Base 同步。
