# WeChat Article OCR Workflow

## 混合模式工作流程

由于 OCR 工具依赖复杂，采用 **Python提取 + AI Vision识别** 的混合模式。

## 流程图

```
用户发送文章链接
        ↓
[Python] wechat-article-for-ai-pro 提取文章
        ↓
生成: article.md, article.html, metadata.json, images/
生成: article-ocr.md（占位符版本）
        ↓
[Hermes] 读取 images/ 文件夹
        ↓
遍历每张图片
        ↓
调用 vision_analyze 识别文字
        ↓
收集所有 OCR 结果
        ↓
更新 article-ocr.md
        ↓
完成5文件结构
```

## 代码实现

### 步骤1: 提取文章

```bash
python /tmp/wechat-article-for-ai-pro/main.py "URL" -o ~/.hermes/output -v
```

### 步骤2: 获取图片列表

```python
from pathlib import Path

article_dir = Path('~/.hermes/output/文章标题')
images_dir = article_dir / 'images'
image_files = sorted(images_dir.glob('*.png')) + sorted(images_dir.glob('*.jpg'))
```

### 步骤3: OCR 识别

```python
from hermes_tools import vision_analyze

ocr_results = []
for img_path in image_files:
    result = vision_analyze(
        image_url=str(img_path),
        question="提取图片中的所有文字内容"
    )
    ocr_results.append((img_path.name, result))
```

### 步骤4: 更新 article-ocr.md

```python
import sys
sys.path.insert(0, '/tmp/wechat-article-for-ai-pro')
from wechat_to_md.ocr_processor import generate_ocr_output

generate_ocr_output(article_dir, ocr_results)
```

## 关键要点

1. **不要重复 clone**: 工具已存在于 `/tmp/wechat-article-for-ai-pro/`
2. **OCR 方法选择**: 
   - AI Vision: 简单可靠，需要 API
   - PaddleOCR: 免费本地，依赖复杂
3. **article-ocr.md 结构**:
   - 一、原文文字内容
   - 二、图片 OCR 识别内容
   - 三、完整文字内容（原文 + OCR）
