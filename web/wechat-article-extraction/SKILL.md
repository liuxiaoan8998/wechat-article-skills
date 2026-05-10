---
name: wechat-article-extraction
description: >
  Extract full content from WeChat Official Account articles (mp.weixin.qq.com).
  Uses wechat-article-for-ai tool as the standard method.
  See STANDARD.md for complete workflow and output specifications.
---

# WeChat Article Content Extraction

Extract complete content from WeChat Official Account articles (微信公众号文章).

## ⚡ Quick Start

```bash
# Extract article
python /tmp/wechat-article-for-ai/main.py "https://mp.weixin.qq.com/s/..." -o ./output -v

# Then organize into standard format (see STANDARD.md)
```

## 📋 Standard Output Format

All extractions must follow this structure:

```
~/.hermes/output/{article_title}/
├── article.md          # Markdown with local image paths
├── article.html        # HTML viewer (shows original images)
├── metadata.json       # Structured metadata
├── article-ocr.md      # (Pro version) Text + OCR from images
├── images/             # All downloaded images (40+)
│   ├── img_001.jpg
│   ├── img_002.png
│   └── ...
└── slices/             # (Pro v1.5+) Long image segments for OCR
    ├── img_002_slice_01.jpg
    └── ...
```

**See `STANDARD.md` for complete specifications.**

## 🛠️ Standard Tool

**wechat-article-for-ai** (GitHub: bzd6661/wechat-article-for-ai)

### Tool Location

- **原始工具**: `/tmp/wechat-article-for-ai/` (已克隆，无需重复 clone)
- **增强版**: `/tmp/wechat-article-for-ai-pro/` (本地 Git 仓库，自动4文件输出)

### Why This Tool

| Aspect | Old Methods | wechat-article-for-ai |
|--------|-------------|----------------------|
| Image count | 2-7 | **40+** |
| Content completeness | Partial | **Complete** |
| Lazy loading | ❌ Not handled | ✅ **Auto-handled** |
| Anti-bot | ❌ Blocked | ✅ **Bypassed** |
| Automation | Manual | **Fully automatic** |

### Installation

```bash
# 检查是否已存在（避免重复 clone）
if [ ! -d "/tmp/wechat-article-for-ai" ]; then
    git clone https://github.com/bzd6661/wechat-article-for-ai.git /tmp/wechat-article-for-ai
fi

# 安装依赖
cd /tmp/wechat-article-for-ai
pip install -r requirements.txt
```

### Basic Usage

```bash
# 使用原始工具
python /tmp/wechat-article-for-ai/main.py "https://mp.weixin.qq.com/s/ARTICLE_ID" -o ./output

# 使用增强版（自动4文件输出）
python /tmp/wechat-article-for-ai-pro/main.py "https://mp.weixin.qq.com/s/ARTICLE_ID" -o ./output

# 参数说明
# -o: 输出目录
# -v: 详细日志
# --force: 强制覆盖
# --no-headless: 显示浏览器（用于验证码）
```

## 📖 Complete Documentation

- **`STANDARD.md`** - Full workflow, output specifications, and best practices
- **Comparison analysis** - `~/.hermes/output/方案对比分析报告.md`

## ✅ Quality Checklist

After extraction, verify:
- [ ] `article.md` exists with YAML frontmatter
- [ ] `article.html` displays all original images
- [ ] `metadata.json` has correct structure
- [ ] `images/` folder has 10+ images
- [ ] All files use local paths (not remote URLs)
- [ ] (Pro version) `article-ocr.md` contains OCR text from images
- [ ] (Pro version v1.5+) Long images (>2000px) have `slices/` directory with segments
- [ ] (Pro version v1.5+) OCR placeholders in `article-ocr.md` are filled by Hermes

## 🎯 Key Principles

1. **Always use the tool** - Don't use browser scroll + vision
2. **Show original images first** - Preserve professional design
3. **Download all images locally** - No external URLs
4. **Provide all three formats** - Markdown, HTML, and metadata

## 🧠 Lessons Learned

### Tool Selection Matters (Critical!)
- **Browser scroll + vision**: Only gets 2-7 images, incomplete content
- **wechat-article-for-ai**: Gets 40+ images, complete content (20x better)
- **Why**: Handles lazy loading (`data-src` → `src`), bypasses anti-bot detection, waits for networkidle
- **Lesson**: Always compare approaches before settling on standard

### Don't Over-Engineer (Important!)
- Initially tried complex "collapsible content" with visual distinction, badges, toggle buttons
- **User feedback**: "撤回这个优化，保持上一个版本吧" (Revert this, keep previous version)
- **Principle**: Validate with user BEFORE implementing fancy features; Simple > Complex

### Don't Repeat Clone
- Tool already exists at `/tmp/wechat-article-for-ai/`
- Check existence before cloning: `if [ ! -d "/tmp/wechat-article-for-ai" ]`
- Saves time and bandwidth

### Don't Replace Core Dependencies Blindly
- **Mistake**: Tried to replace camoufox with playwright due to one install failure
- **Reality**: camoufox is specifically designed for anti-bot detection (the tool's core advantage)
- **Lesson**: Don't abandon proven solutions due to temporary issues; fix the root cause instead

### When Local Tools Fail, Use APIs (Critical!)
- **Scenario**: PaddleOCR installation failed with dependency conflicts (pydantic_core)
- **Attempted fixes**: Multiple pip installs, path adjustments - all failed
- **Solution**: Switched to AI Vision API approach
- **Lesson**: Don't get stuck on environment issues; API alternatives are often more reliable
- **Trade-off**: API costs vs. time spent debugging local dependencies
- **User confirmation**: User explicitly approved this approach ("可以了！") after seeing results

### Pro Version Development
- Created local fork at `/tmp/wechat-article-for-ai-pro/`
- Added `formatter.py` module for automatic 4-file output
- Added `ocr_processor.py` module for image text extraction
- Keeps camoufox (core anti-bot detection) while adding enhancements
- Git initialized for version control with Chinese commit messages

### Long Image OCR Solution (v1.5.0+) - Hybrid Workflow Pattern

**Problem**: AI Vision API cannot process超长图 (e.g., 1080x11258px) - exceeds size limits

**Solution**: Tool + Hermes协作流程 (Collaborative workflow)

| Component | Responsibility |
|-----------|---------------|
| **Tool** | Detect long images (>2000px) → Slice (max 2000px, 100px overlap) → Save to `slices/` → Generate `article-ocr.md` with placeholders |
| **Hermes** | Read slices → `vision_analyze` OCR → Backfill results to `article-ocr.md` |

**Output Structure**:
```
article_dir/
├── article.md
├── article.html
├── article-ocr.md      # Contains OCR placeholders
├── metadata.json
├── images/
│   └── img_002.jpg     # Original long image
└── slices/             # NEW: Sliced segments
    ├── img_002_slice_01.jpg
    ├── img_002_slice_02.jpg
    └── ...
```

**Placeholder Format in article-ocr.md**:
```markdown
#### 图片: img_002.jpg
**状态**: [超长图 1080x11258，已切片为 6 段，待OCR]

**切片文件**:
- `slices/img_002_slice_01.jpg`
- `slices/img_002_slice_02.jpg`
...

**OCR 结果**（待 Hermes 回填）：

<!-- OCR_SLICE_1: -->
[待识别]
```

**Why This Pattern Works**:
1. **Separation of concerns**: Tool handles preprocessing, Hermes handles AI
2. **Resumable**: Can OCR slices incrementally
3. **Transparent**: User sees exactly what's being processed
4. **Reusable**: Pattern applies to any "too large for AI" preprocessing scenario

**Key Implementation Details**:
- Slice overlap (100px) prevents text cutoff at boundaries
- Max slice height (2000px) fits AI Vision limits
- Placeholder comments (`<!-- OCR_SLICE_N: -->`) enable automated backfill

### Commit Message Language
- **Rule**: Use Chinese for commit messages (用户要求)
- **Example**: `v1.0-pro: 添加标准4文件输出格式`
- **Why**: User explicitly requested Chinese commit messages
1. **原文文字内容** - Text from article.md
2. **图片 OCR 识别内容** - Text extracted from each image
3. **完整文字内容** - Combined text + OCR results

**OCR Methods**:

| Method | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **AI Vision** | No install needed, high accuracy, understands context | Uses API credits | ✅ **Preferred** |
| **PaddleOCR** | Free, local, fast after setup | Complex dependencies, version conflicts | Use if offline required |

**AI Vision Implementation** (Recommended):
```python
# Use vision_analyze tool
from hermes_tools import vision_analyze

result = vision_analyze(
    image_url="path/to/image.png",
    question="提取图片中的所有文字内容"
)
```

**PaddleOCR Implementation** (Offline):
```bash
pip install paddleocr paddlepaddle
```
- First run downloads models (~100MB)
- GIF files may not OCR well (use PNG/JPG)
- Processing time: ~3-5 seconds per image
- **Note**: May have dependency conflicts on some systems

**Key Learning**: 
- Started with PaddleOCR but hit dependency issues (pydantic_core conflicts)
- Switched to AI Vision approach - simpler, more reliable
- When local tools fail due to environment issues, consider API-based alternatives

### Commit Message Language
- **Rule**: Use Chinese for commit messages (用户要求)
- **Example**: `v1.0-pro: 添加标准4文件输出格式`
- **Why**: User explicitly requested Chinese commit messages

### Communication Patterns
- **End with "以上"**: All task outputs must end with "以上" on its own line
- **Git discipline**: Every skill modification needs `git add` + `git commit`
- **Clear commit messages**: Include version number and change summary

### Standard Output Works
- 4-file structure (md, html, json, images/) is practical and complete
- Git version management helps track changes
- **Location**: `~/.hermes/skills/web/wechat-article-extraction/` (Git managed)

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| CAPTCHA | Use `--no-headless` flag |
| Empty content | Wait and retry (rate limiting) |
| Image failures | Use `--force` to re-run |
| Tool not installed | See Installation section above |
| RGBA to JPEG error | PNG with transparency can't save as JPEG. Fix: Convert RGBA → RGB before saving |

### RGBA to JPEG Conversion Error (Fixed in v1.5.1)

**Error**: `cannot write mode RGBA as JPEG`

**Cause**: Some PNG images contain transparency (RGBA, LA, or P mode), but JPEG format doesn't support alpha channels.

**Fix** (v1.5.1): In `ocr_processor.py`, automatically convert to RGB before saving slices:
```python
if segment.mode in ('RGBA', 'LA', 'P'):
    segment = segment.convert('RGB')
segment.save(slice_path, "JPEG", quality=95)
```

**Status**: ✅ Fixed - article-ocr.md now generates correctly even with transparent PNG images.

## 📚 References

- Tool repository: https://github.com/bzd6661/wechat-article-for-ai
- Standard specification: `STANDARD.md` (this skill folder)
- Example output: `~/.hermes/output/{article_id}/` (article_id 为8位UUID)

---

**Last updated**: 2026-04-14  
**Skill version**: v2.5  
**Standard tool**: wechat-article-for-ai  
**Pro version**: `/tmp/wechat-article-for-ai-pro/` (auto 4-file output, long-image slicing, hybrid OCR workflow, RGBA fix v1.5.1, Chinese commits)
