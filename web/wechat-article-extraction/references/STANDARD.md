# 微信公众号文章提取标准方案

## 1. 标准工具

**工具名称**: wechat-article-for-ai  
**GitHub**: https://github.com/bzd6661/wechat-article-for-ai  
**安装路径**: `/tmp/wechat-article-for-ai`

**Pro版本地路径**: `/tmp/wechat-article-for-ai-pro/` (自动5文件输出，含OCR)

### 1.1 安装

```bash
# 检查是否已存在（避免重复 clone）
if [ ! -d "/tmp/wechat-article-for-ai" ]; then
    git clone https://github.com/bzd6661/wechat-article-for-ai.git /tmp/wechat-article-for-ai
fi

# 安装依赖
cd /tmp/wechat-article-for-ai
pip install -r requirements.txt
```

### 1.2 基本使用

```bash
# 单篇文章提取
python main.py "https://mp.weixin.qq.com/s/ARTICLE_ID" -o ./output

# 带详细日志
python main.py "https://mp.weixin.qq.com/s/ARTICLE_ID" -o ./output -v

# 强制覆盖已存在输出
python main.py "https://mp.weixin.qq.com/s/ARTICLE_ID" -o ./output --force
```

---

## 2. 输出规范

### 2.1 输出文件结构

**基础版（4文件）**:
```
~/.hermes/output/{article_title}/
├── article.md              # Markdown格式（含本地图片路径）
├── article.html            # HTML查看器（优先展示原图）
├── metadata.json           # 结构化元数据
└── images/                 # 下载的所有图片
    ├── img_001.jpg
    ├── img_002.png
    └── ...
```

**Pro版（5文件，含OCR）**:
```
~/.hermes/output/{article_title}/
├── article.md              # Markdown格式（含本地图片路径）
├── article.html            # HTML查看器（优先展示原图）
├── metadata.json           # 结构化元数据
├── article-ocr.md          # 原文 + 图片OCR识别内容 ⭐
└── images/                 # 下载的所有图片
    ├── img_001.jpg
    ├── img_002.png
    └── ...
```

### 2.2 article-ocr.md 结构

```markdown
# 文章内容（含图片 OCR 识别）

> 本文档由 wechat-article-for-ai-pro 自动生成
> 包含原文文字 + 图片 OCR 识别结果

---

## 一、原文文字内容
[从 article.md 提取的纯文字，不含图片]

---

## 二、图片 OCR 识别内容
### 图片: img_001.png
[AI Vision 识别的图片文字内容]

### 图片: img_002.png
[AI Vision 识别的图片文字内容]

---

## 三、完整文字内容（原文 + OCR）
[整合后的完整文字，便于阅读和使用]
```

---

## 3. OCR 工作流程

### 3.1 混合模式（推荐）

由于 OCR 工具（如 PaddleOCR）依赖复杂，采用 **Python提取 + AI Vision识别** 的混合模式：

```
步骤1: Python 工具提取文章
        ↓
        生成: article.md, article.html, metadata.json, images/
        生成: article-ocr.md（占位符版本）
        
步骤2: Hermes 调用 AI Vision
        ↓
        遍历 images/ 文件夹中的所有图片
        对每个图片调用 vision_analyze 提取文字
        
步骤3: 更新 article-ocr.md
        ↓
        将 OCR 结果写入 article-ocr.md
        完成5文件结构
```

### 3.2 AI Vision OCR 实现

```python
# 识别单张图片
from hermes_tools import vision_analyze

result = vision_analyze(
    image_url="/path/to/image.png",
    question="提取图片中的所有文字内容"
)

# 更新 article-ocr.md
from wechat_to_md.ocr_processor import generate_ocr_output

image_ocr_results = [
    ("img_001.png", "识别的文字内容..."),
    ("img_002.png", "识别的文字内容..."),
]

generate_ocr_output(article_dir, image_ocr_results)
```

---

## 4. 质量检查清单

提取完成后，必须检查以下项目：

### 4.1 文件完整性

- [ ] `article.md` 存在且不为空
- [ ] `article.html` 存在且可正常打开
- [ ] `metadata.json` 存在且格式正确
- [ ] `images/` 文件夹存在
- [ ] `article-ocr.md` 存在（Pro版）
- [ ] 图片数量 ≥ 1 张

### 4.2 OCR 质量

- [ ] article-ocr.md 包含原文文字
- [ ] 图片 OCR 内容已填充（非占位符）
- [ ] 完整文字内容已整合

---

## 5. 常见问题

### 5.1 OCR 依赖安装失败

**问题**: PaddleOCR 安装失败（pydantic_core 冲突）  
**解决**: 使用 AI Vision API 替代，无需本地安装

### 5.2 图片识别为空

**问题**: 某些图片 OCR 返回空内容  
**原因**: 
- 图片本身是装饰图（无文字）
- GIF 格式识别效果差
- 文字与背景对比度低

**解决**: 
- 检查图片内容
- 转换为 PNG/JPG 后重试

---

## 6. 最佳实践

### 6.1 工具选择

| 场景 | 推荐工具 |
|------|----------|
| 快速提取 | wechat-article-for-ai-pro（自动5文件） |
| 离线环境 | 基础版 + 本地 PaddleOCR |
| 高质量 OCR | AI Vision API |

### 6.2 工作流

1. **提取文章**: 使用 Pro 版工具一键提取
2. **OCR 识别**: Hermes 自动调用 AI Vision
3. **质量检查**: 验证 article-ocr.md 内容完整性
4. **推送 GitHub**: 提交代码更新

---

**此文档为微信文章提取的标准操作规范，所有相关任务必须遵循。**
