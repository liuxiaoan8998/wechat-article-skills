---
name: wechat-article-extraction-pro
description: >
  微信公众号文章提取 Pro 版完整执行流程。
  基于 wechat-article-for-ai 增强，实现7文件/目录输出（article_original.html原始HTML + article.html查看器 + Markdown + OCR + JSON + images/ + slices/）+ RapidOCR 识别 + Hermes 总结填回 + 飞书 Base 同步。
  【全自动执行模式】用户只需发送微信文章链接，单次对话内自动完成：工具提取 → AI分析 → Base同步（23字段），无需任何确认。
---

# 微信公众号文章提取 Pro 版 - 全自动执行

> **🚀 使用方式**：直接发送微信文章链接，我将**自动执行完整流程**，无需确认。
>
> **⚠️ 工具维护提醒**：如果 `/tmp/wechat-article-for-ai-pro/` 目录为空或损坏，请重新克隆：
> ```bash
> cd /tmp && rm -rf wechat-article-for-ai-pro && git clone https://github.com/liuxiaoan8998/wechat-article-for-ai-pro.git
> ```

## 执行流程（全自动，无需确认）

```
用户发送微信文章链接
    ↓
┌─────────────────────────────────────────────────────────────┐
│  【全自动执行】单次对话内完成全部阶段，中途无需确认           │
│  ───────────────────────────────────────────────────────    │
│                                                             │
│  阶段 1：工具提取（自动执行）                                │
│  ─────────────────────────────                              │
│  1. 启动 Camoufox 浏览器访问文章                            │
│  2. 提取标题、作者、正文内容                                 │
│  3. 下载所有图片到 images/ 目录                             │
│  4. OCR 识别（RapidOCR）                                    │
│  5. 二维码识别（zbar-py）                                    │
│  6. 生成 8 位 UUID 作为文章ID（如 fa70b413）               │
  │  7. 输出 7 文件/目录到 /tmp/test_output/{article_id}/            │
│  8. ⚠️ 自动复制到 ~/.hermes/output/{article_id}/            │
│     （确保上传脚本可正确查找本地目录）
│                                                             │
│  阶段 2：AI 分析（自动执行）                                │
│  ─────────────────────────────                              │
│  1. 读取 OCR 内容，提取关键信息                              │
│  2. 分析 13 个 AI 字段（行业/岗位/地点/亮点等）             │
│  3. 生成结构化总结                                           │
│                                                             │
│  阶段 3：飞书 Base 同步（自动执行）                          │
│  ─────────────────────────────                              │
│  1. 构建 23 个字段的完整记录                                │
│  2. 同步到飞书 Base                                          │
│  3. 返回执行结果                                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
    ↓
输出完整执行报告（含二维码识别 + 23字段填充统计 + 记录ID）
```

> **✅ 同步执行保障**：三个阶段在单次对话内顺序执行，阶段2和阶段3自动触发，无需用户二次指令。
>
> **⚠️ 字段完整性保障**：写入 Base 前校验全部23个字段，缺失字段标记为 "/"，确保不遗漏。
>
> **🚀 全自动执行**：用户只需发送微信文章链接，我将自动完成提取 → 分析 → 同步，中途无需任何确认。

## 定期状态提醒

**机制**：每进行50轮对话时，自动提示：
```
[对话轮次提醒] 当前已进行XX轮对话，接近上下文压缩阈值（约358轮）。
建议：如有重要任务或状态需要保存，请告知我"保存当前进度"。
```

**用户指令**：
- 说"**保存当前进度**" → 我立即将任务状态写入标记文件
- 说"**查看状态**" → 我读取标记文件并汇报当前进度

## 技术栈

| 组件 | 技术 |
|------|------|
| 浏览器 | Camoufox（Playwright） |
| OCR 引擎 | RapidOCR（本地 ONNX） |
| 备用 OCR | AI Vision（云端） |
| 图片处理 | Pillow |
| 输出格式 | Markdown + HTML + JSON |

## 关键修复

| 问题 | 修复 |
|------|------|
| RapidOCR 返回坐标而非文字 | 修正结果解析：`item[1]` 才是文字内容（格式是 `[[box, text, confidence], ...]`） |
| RGBA 图片保存失败 | 切片前自动转换为 RGB 模式 |
| **API返回URL格式不兼容** | **修复 `validate_url()` 支持两种格式**：<br>• `/s/xxx` 标准路径格式<br>• `/s?__biz=xxx` 查询参数格式（极致了API返回） |
| **发布时间字段遗漏** | **修复同步流程**：`record_data` 必须包含 `published_at` 字段，不能遗漏 |
| **空字段标记** | **统一规范**：信息未获取的字段必须填充 `"/"`，不能留空 |

### URL格式兼容性修复（v3.0.1）

**问题**：极致了API返回的URL格式为 `https://mp.weixin.qq.com/s?__biz=xxx&mid=xxx`（查询参数格式），而原 `validate_url()` 只支持 `/s/xxx` 路径格式，导致提取失败。

**修复代码**（`/tmp/wechat-article-for-ai-pro/wechat_to_md/cli.py` 第77-80行）：

```python
def validate_url(url: str) -> bool:
    """Check that URL is a WeChat article URL."""
    # 支持带参数的 URL，如 ?scene=1&click_id=12
    # 支持两种格式: /s/xxx 或 /s?__biz=xxx
    return url.startswith("https://mp.weixin.qq.com/s/") or url.startswith("https://mp.weixin.qq.com/s?")
```

**使用场景**：
- 标准分享链接：`https://mp.weixin.qq.com/s/nJ-MZGEiYGM-epQVGKaLCA`
- 极致了API返回：`https://mp.weixin.qq.com/s?__biz=MzkwMTI4MzE1OQ==&mid=2247621516&idx=2&sn=...`

**注意事项**：
- 批量处理极致了API返回的文章列表时，需将 `http://` 转换为 `https://`
- 转换代码：`url = url.replace('http://', 'https://', 1)`

## 执行命令（同步执行模式 v3.0）

### 完整执行流程（单次对话内完成）

**注意**：使用系统 Python (`/usr/bin/python3`) 执行，避免虚拟环境依赖问题

```python
# ============================================================
# 阶段 1：工具提取（Python 执行）
# ============================================================

import subprocess
import os
import shutil

url = "用户提供的URL"
output_base = "/tmp/test_output"

# 执行工具提取（使用系统 Python）
result = subprocess.run(
    f'cd /tmp/wechat-article-for-ai-pro && /usr/bin/python3 main.py "{url}" -o {output_base} -v',
    shell=True, capture_output=True, text=True, timeout=300
)

if result.returncode != 0:
    raise Exception(f"工具提取失败: {result.stderr}")

# 获取输出目录（从 stdout 解析或使用已知路径）
# 假设输出目录为：/tmp/test_output/文章标题

# ⚠️ 关键：自动复制到 ~/.hermes/output/（供上传脚本使用）
import glob
from pathlib import Path

tmp_dirs = glob.glob(f"{output_base}/*")
if tmp_dirs:
    article_dir = tmp_dirs[0]
    article_id = os.path.basename(article_dir)
    
    # 目标目录
    hermes_output = Path.home() / ".hermes" / "output" / article_id
    
    # 如果已存在，先删除
    if hermes_output.exists():
        shutil.rmtree(hermes_output)
    
    # 复制目录
    shutil.copytree(article_dir, hermes_output)
    print(f"✅ 已复制到: {hermes_output}")
else:
    raise Exception("未找到工具提取的输出目录")

# ============================================================
# 阶段 2：Hermes 总结（AI 自动处理）
# ============================================================

# 1. 读取 article-ocr.md
# 2. AI 分析 OCR + 二维码内容
# 3. 生成结构化总结（行业、岗位类型、工作地点等13个AI字段）
# 4. 回填到 article-ocr.md 第三部分
# 5. 同步到 ~/.hermes/output/

# ============================================================
# 阶段 3：飞书 Base 同步（完整23字段）
# ============================================================

# 构建完整记录数据（基础10字段 + AI分析13字段）
record_data = {
    # 基础字段（10个）- 从 metadata.json 提取
    "文章标题": metadata.get('title', ''),
    "公众号": metadata.get('author', ''),
    "发布时间": metadata.get('published_at', ''),  # ⚠️ 关键：必须从metadata提取，不能遗漏！
    "文章链接": metadata.get('url', ''),
    "文章ID": metadata.get('article_id', ''),  # 新增：文章唯一ID，用于精确查找本地目录
    "文章状态": "待选题",
    "文章来源": "链接",
    "采集时间": int(datetime.now().timestamp() * 1000),
    # ID、最后更新时间由系统自动生成
    
    # AI分析字段（13个）- 从 OCR 内容分析
    "行业": analyze_industry(ocr_content),           # 互联网/金融/能源/传媒/制造/消费品/交通/咨询/其他
    "领域": analyze_field(ocr_content),             # 科技/投资/电力/娱乐/互联网/零售/消费品/交通/咨询/其他
    "岗位类型": analyze_job_types(ocr_content),     # ["实习"]/["校招"]/["社招"]/["兼职"]/["管培生"]（最多2个）
    "工作地点": analyze_location(ocr_content),      # 北京/上海/广州/深圳/杭州/多城市/其他
    "学历要求": analyze_education(ocr_content),     # 本科/硕士/博士/不限/本科（大三及以上优先）
    "截止日期": analyze_deadline(ocr_content) or "/",      # YYYY-MM-DD 或 "/"
    "投递方式": analyze_apply_method(ocr_content) or "/",  # 具体投递方式或 "/"
    "原文亮点": analyze_highlights(ocr_content),    # 分号分隔的关键词（P0-P5优先级）
    "文章概要": generate_summary(ocr_content),      # 500字内结构化总结
    "选题方向": determine_topic(ocr_content),     # 根据行业和岗位类型生成
    "适配账号": match_accounts(ocr_content),      # ["Joblinker"]/["研究生求职圈"]/["行研实习"]
    "优先级": "中",                                 # 高/中/低
    "标签": analyze_tags(ocr_content)               # ["热门","急招","大厂","国企","央企","外企","可内推"]（最多3个）
}

# 字段完整性校验
required_fields = [
    '文章标题', '公众号', '发布时间', '文章链接', '文章ID',
    '行业', '领域', '岗位类型', '工作地点', 
    '学历要求', '截止日期', '投递方式',
    '原文亮点', '文章概要', '选题方向',
    '文章状态', '文章来源', '适配账号',
    '优先级', '标签', '采集时间'
]

# ⚠️ 关键：检查字段是否为空（None、空字符串、空列表）
missing = [f for f in required_fields if not record_data.get(f) and record_data.get(f) != "/"]
if missing:
    print(f"⚠️ 警告：以下字段缺失或为空: {', '.join(missing)}")
    
# ⚠️ 关键：确保空字段填充 "/"，不能留空
for field in required_fields:
    if not record_data.get(field):
        record_data[field] = "/"
        print(f"ℹ️ 字段 '{field}' 已填充 '/'（原文未提及）")

# 写入临时文件并同步
with open('sync_data.json', 'w', encoding='utf-8') as f:
    json.dump(record_data, f, ensure_ascii=False)

result = subprocess.run(
    'lark-cli base +record-upsert --base-token E9y1bxjHGa9LeGs9q3Tc3J41nmf --table-id tblYIqHtHrWUlVnP --json @sync_data.json --as bot',
    shell=True, capture_output=True, text=True
)

# 解析结果并反馈
if result.returncode == 0:
    response = json.loads(result.stdout)
    if response.get('ok'):
        record_id = response['data']['record']['record_id_list'][0]
        print(f"✅ 同步成功！记录ID: {record_id}")
        print(f"📊 字段填充: {22-len(missing)}/22")
    else:
        print(f"❌ 同步失败: {response.get('error')}")
```

### 简化执行命令

#### 1. 工具提取

```bash
cd /tmp/wechat-article-for-ai-pro
python3 -c "
from wechat_to_md.cli import main
import sys
sys.argv = ['wechat_to_md', 'URL', '-o', 'OUTPUT_DIR']
main()
"
```

### 2. Hermes 总结回填

```python
# 读取 OCR 结果
read_file: path/to/article-ocr.md

# 分析 OCR 内容，生成结构化总结

# 回填到第三部分
patch: path/to/article-ocr.md
  old_string: "## 三、完整文字内容...\n\n*待 OCR 完成后自动更新*"
  new_string: "## 三、完整文字内容...\n\n### 公司概况\n..."

# 同步到 ~/.hermes/output/
cp -r /tmp/test_output/{article_id} ~/.hermes/output/  # article_id 从 metadata.json 中读取

# 同步到飞书 Base（内容管理）
export PATH="$HOME/.npm-global/lib/node_modules/@larksuite/cli/bin:$PATH"
lark-cli base +record-upsert \
  --base-token "E9y1bxjHGa9LeGs9q3Tc3J41nmf" \
  --table-id "tblYIqHtHrWUlVnP" \
  --json '{
    "文章标题": "文章标题",
    "公众号": "公众号名称",
    "发布时间": "2026-04-20",
    "文章内容概要总结": "AI生成的结构化总结...",
    "投递方式": "投递渠道...",
    "文章链接": "https://mp.weixin.qq.com/s/xxx",
    "行业/领域": {"text": "互联网/科技"},
    "岗位类型": {"text": "实习"},
    "工作地点": {"text": "北京"},
    "学历要求": {"text": "本科"},
    "优先级": {"text": "中"},
    "状态": {"text": "待处理"},
    "标签": [{"text": "大厂"}],
    "备注": ""
  }' \
  --as bot
```

## 输出结构

```
~/.hermes/output/{article_id}/  # article_id = metadata.json 中的 8位UUID
├── article_original.html   # 原始微信HTML（Camoufox 抓取的完整HTML，含base64图片，~3-4MB，保留原文章样式）
├── article.html            # HTML 查看器（formatter.py 生成的图片查看器，~4KB，仅含标题+图片+小程序码，无文字内容）
├── article.md              # 基础 Markdown
├── article-ocr.md          # OCR 结果 + 二维码 + 总结 ✅
├── metadata.json           # 元数据（含 article_id、url、title 等）
├── images/                 # 原始图片
└── slices/                 # 长图切片（如有）
```

**文件说明**：
- `article_original.html`: 原始抓取的微信HTML，包含完整的 `<html>`, `<head>`, `<body>` 结构和base64编码的图片，保留原文章的所有样式。但因文件过大（~3-4MB），不适合直接上传公众号。
- `article.html`: formatter.py 生成的图片查看器，仅包含标题、图片、二维码/小程序码，**不含文章正文文字**，不能用于公众号上传。
- `article.md`: 含有文章正文文字，是上传脚本应使用的内容来源。
- `article-ocr.md`: OCR识别结果+二维码+总结，用于AI分析和Base填充。

### article-ocr.md 结构（v1.7+）

```markdown
# 文章内容（含图片 OCR 识别）

## 一、原文文字内容
[原文 Markdown]

## 二、二维码识别内容
检测到 **N** 张包含二维码的图片

### img_XXX.jpg
**图片路径**: `images/img_XXX.jpg`

**二维码 1**:
- **类型**: 📝 招聘/报名链接 / 🔗 链接 / 📞 联系方式 / 📝 文本内容
- **内容**: {URL或文本}

---

## 三、图片 OCR 识别内容
[OCR 结果]

## 四、完整文字内容（原文 + OCR + 二维码）
*待 OCR 完成后自动更新*

### 二维码关键信息（供整合参考）
- **招聘/报名链接**: `http://weixin.qq.com/r/xxx`（来自 img_007.jpg）

> ⚠️ **注意**：检测到招聘/报名链接，请在总结中整合此信息

---
```

**第四章特点**：
- 标题明确包含"二维码"，提示 AI 需要整合
- 自动提取关键信息（招聘链接、联系方式等）
- 检测到招聘链接时显示警告提示，确保不被遗漏

## Hybrid 模式说明

### 为什么分离？

| 层级 | 职责 | 原因 |
|------|------|------|
| 工具 (Python) | 提取 + OCR | 适合网页抓取、本地 OCR 批量处理 |
| Hermes (AI) | 总结 + 回填 | 擅长理解上下文、结构化输出 |

### 协作流程

#### 单篇文章

1. **工具完成** → 输出文件路径
2. **用户通知 Hermes** → "请总结这篇文章"
3. **Hermes 读取** → article-ocr.md
4. **Hermes 生成** → 结构化总结
5. **Hermes 回填** → 更新 article-ocr.md
6. **Hermes 同步** → ~/.hermes/output/

#### 批量处理（多篇文章）

使用 `delegate_task` 并行处理：

```python
delegate_task(tasks=[
    {
        "context": "文件路径：/tmp/test_output/文章1/article-ocr.md",
        "goal": "读取 OCR 内容，生成结构化总结并回填",
        "toolsets": ["file", "terminal"]
    },
    {
        "context": "文件路径：/tmp/test_output/文章2/article-ocr.md", 
        "goal": "读取 OCR 内容，生成结构化总结并回填",
        "toolsets": ["file", "terminal"]
    },
    # ... 更多文章
])
```

**优势**：多篇文章并行处理，大幅提升效率

## 版本历史

| 版本 | 变更 |
|------|------|
| v1.0 | 标准输出（md+html+json+images） |
| v1.2 | 添加 article-ocr.md 占位符 |
| v1.3 | AI Vision OCR 集成 |
| v1.4 | 集成 RapidOCR 本地识别 |
| v1.5 | 可配置 OCR 引擎（rapidocr/vision/auto）|
| v1.5.1 | 修复 RGBA 图片切片保存问题 |
| v1.5.2 | 修复 RapidOCR 返回格式解析 bug |
| v1.6 | **Hybrid 模式**：工具提取+OCR，Hermes 总结回填 |

---

# 历史开发记录（参考）

## 项目架构

```
wechat-article-for-ai-pro/
├── main.py                 # 入口
├── requirements.txt        # 依赖
├── README.md              # 中文文档
├── wechat_to_md/          # 核心模块
│   ├── cli.py            # 命令行接口
│   ├── scraper.py        # Camoufox 抓取
│   ├── parser.py         # 内容解析
│   ├── converter.py      # Markdown 转换
│   ├── downloader.py     # 图片下载
│   ┌── formatter.py      # 标准化输出（md+html+json+images）
│   ├── ocr_adapter.py    # OCR 适配器 ⭐
│   └── ocr_processor.py  # OCR 处理模块
└── ...
```

基于 wechat-article-for-ai 的增强版本，实现标准化输出（md+html+json+images+ocr）+ AI Vision OCR 识别。

## 项目架构

```
wechat-article-for-ai-pro/
├── main.py                 # 入口
├── requirements.txt        # 依赖
├── README.md              # 中文文档
├── wechat_to_md/          # 核心模块
│   ├── cli.py            # 命令行接口
│   ├── scraper.py        # Camoufox 抓取
│   ├── parser.py         # 内容解析
│   ├── converter.py      # Markdown 转换
│   ├── downloader.py     # 图片下载
│   ┌── formatter.py      # 标准化输出（md+html+json+images）
│   └── ocr_processor.py  # OCR 处理模块
└── ...
```

## 开发流程

### 1. 项目初始化

```bash
# 克隆原项目
git clone https://github.com/bzd6661/wechat-article-for-ai.git /tmp/wechat-article-for-ai-pro
cd /tmp/wechat-article-for-ai-pro
rm -rf .git
git init
git add .
git commit -m "Initial commit: fork from bzd6661/wechat-article-for-ai"
```

### 2. 添加标准输出

创建 `wechat_to_md/formatter.py`：
- 生成 `article.md`（YAML frontmatter）
- 生成 `article.html`（HTML 查看器，formatter.py 生成，仅标题+图片）
- 生成 `article_original.html`（原始微信HTML，Camoufox抓取的完整HTML）
- 生成 `metadata.json`（结构化元数据）
- 整理 `images/` 文件夹
- 整理 `slices/` 文件夹（长图切片）

修改 `cli.py` 集成 formatter。

### 3. 添加 OCR 功能

**方案演进**：
- v1.2: 仅生成占位符，依赖 Hermes 外部识别
- v1.4: 集成 RapidOCR 本地识别，实现全自动 OCR

创建 `wechat_to_md/ocr_adapter.py`（可配置 OCR 引擎）：
```python
class RapidOCREngine(OCREngine):
    def ocr(self, image_path: Path) -> str:
        result, elapse = self._engine(str(image_path))
        # ⚠️ 关键：RapidOCR 返回格式是 [[box, text, confidence], ...]
        # 不是 [text, confidence, box]！
        for item in result:
            text = item[1]  # item[1] 才是文字内容
```

创建 `wechat_to_md/ocr_processor.py`：
- `process_all_images()` - 自动检测长图、切片、OCR
- `slice_long_image()` - 超长图切片（>2000px）
- `create_ocr_markdown_v2()` - 生成包含 OCR 结果的完整文档

**OCR 流程**：
1. 检测图片高度，超长图自动切片
2. 调用 OCRAdapter（默认 RapidOCR）
3. 生成 article-ocr.md（原文 + OCR 结果）

**RapidOCR 返回格式陷阱**（重要！已踩坑）：
```python
# 错误理解：[[text, confidence, box], ...]
# 正确格式：[[box, text, confidence], ...]
# box = [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]  # 四个角坐标
# text = "识别的文字"
# confidence = 0.99  # 置信度

# 正确解析代码：
for item in result:
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        text = item[1]  # item[1] 才是文字，不是 item[0]！
```

### 4.1 OCR 适配器设计（推荐）

创建 `ocr_adapter.py` 实现多引擎支持：

```python
class OCRAdapter:
    """统一 OCR 适配器，支持 rapidocr/vision/auto"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.engine_name = self.config.get('engine', 'rapidocr')
        self.engines = {
            'rapidocr': RapidOCREngine(),
            'vision': AIVisionEngine(),
        }
    
    def ocr(self, image_path: Path) -> str:
        engine = self.engines.get(self.engine_name)
        return engine.ocr(image_path)
```

**引擎选择策略**：
- `rapidocr`：本地运行，快速，适合批量处理
- `vision`：云端 AI，准确度高，适合复杂排版
- `auto`：先 rapidocr，失败时降级到 vision

### 4. Git 管理

**Commit 规范（中文）**：
```bash
git commit -m "v1.3: 添加图片 OCR 识别功能

- 新增 ocr_processor.py 模块
- 集成 AI Vision 识别图片文字
- 生成 article-ocr.md 包含原文+OCR结果"
```

**推送**：
```bash
git remote add origin https://github.com/username/repo.git
git push -u origin main
```

### 5. README 同步

每次代码修改后同步更新：
- 核心特性列表
- 输出文件结构
- 使用示例
- 与原版对比表

## 使用流程

### 提取文章

```bash
python main.py "https://mp.weixin.qq.com/s/..." -o ./output -v
```

### OCR 识别（Hermes 层）

```python
# 1. 获取图片列表
images = list(Path("output/文章标题/images").glob("img_*"))

# 2. 调用 vision_analyze 识别每张图片
for img in images:
    result = vision_analyze(image_url=str(img), question="提取所有文字")
    
# 3. 更新 article-ocr.md
```

## 输出结构

```
output/
└── 文章ID/
    ├── article_original.html  # 原始微信HTML（含base64图片，~3-4MB）
    ├── article.html         # HTML查看器（formatter.py生成，~4KB，仅标题+图片）
    ├── article.md           # Markdown 原文
    ├── metadata.json        # 结构化元数据
    ├── article-ocr.md       # OCR 识别结果 ⭐
    ├── images/              # 下载的图片
    │   ├── img_001.jpg
    │   └── ...
    └── slices/              # 长图切片（如有）
```

## 关键技术决策

### 为什么不用 PaddleOCR？
- 安装复杂，依赖多
- 环境兼容性问题
- 改用 AI Vision，无需本地安装

### 二维码识别方案（v1.7+）

**引擎选择**：
- **首选**：zbar-py（识别能力最强，支持复杂背景）
- **备选**：OpenCV QRCodeDetector（无需额外依赖）

**安装 zbar-py**：
```bash
pip3 install zbar-py
```

**智能分类**：基于URL关键词匹配（apply/job/career/校招/招聘/报名/投递等）自动标记招聘链接

**数据结构分离**：
- `process_all_images()` 返回 `(ocr_results, qr_results)` 元组
- 二维码内容独立成章（第二章节），而非附在每张图片OCR结果后
- 便于快速定位和批量处理

**第四章整合**：
- 标题：`完整文字内容（原文 + OCR + 二维码）`
- 自动提取关键信息（招聘链接、联系方式等）
- 检测到招聘链接时显示警告提示，确保 AI 总结时不遗漏

### 为什么分离 OCR 和提取？
- Python 环境无法直接调用 Hermes 工具
- 分离后流程清晰：提取 → 识别 → 整合
- 便于调试和替换 OCR 方案

## 常见问题

### 图片路径特殊字符
文件名中的引号等特殊字符可能导致路径问题，需要处理。

### OCR 识别失败
- 装饰图标无文字
- 二维码需解码
- 复杂排版识别不全

## 版本历史

| 版本 | 变更 |
|------|------|
| v1.0 | 标准输出（md+html+json+images） |
| v1.2 | 添加 article-ocr.md 占位符 |
| v1.3 | AI Vision OCR 集成 |
| v1.3.1 | README 同步更新 |
| v1.4 | 集成 RapidOCR 本地识别，修复返回格式解析 bug |
| v1.5 | 可配置 OCR 引擎（rapidocr/vision/auto）|
| v1.5.1 | 修复 RGBA 图片切片保存问题 |
| v1.6 | **hybrid 模式**：工具提取+OCR，Hermes 负责总结回填 |
| v1.7 | **新增二维码识别功能**：OpenCV QRCodeDetector 自动检测，智能分类招聘/报名链接 |
| v1.7.1 | **第四章整合二维码信息**：完整文字内容（原文+OCR+二维码），自动提取关键链接供 AI 总结 |
| v1.7.2 | **集成 zbar-py**：识别能力更强，解决 OpenCV 无法识别的复杂背景二维码问题 |

---

## Hybrid 模式（推荐）

### 流程设计

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   工具层     │ ──→ │   Hermes    │ ──→ │   最终输出   │
│ (Python)    │     │   (AI)      │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
      │                   │                   │
   1. 提取文章         4. 读取 OCR 结果      6. 完整文档
   2. 下载图片         5. AI 总结          (article-ocr.md)
   3. RapidOCR 识别
      生成 article-ocr.md
      (OCR 结果 + 占位符)
```

### 为什么分离？

| 层级 | 职责 | 原因 |
|------|------|------|
| 工具 | 提取 + OCR | Python 环境适合网页抓取和本地 OCR |
| Hermes | 总结 + 回填 | AI 擅长理解上下文、结构化总结 |

### 触发机制

工具生成 `article-ocr.md` 后，创建标记文件通知 Hermes：

```python
# 工具端
with open(f"{output_dir}/.hermes_summary_pending", "w") as f:
    f.write(f"article_dir={output_dir}\n")

# Hermes 检测到标记后，自动读取 OCR 结果并总结回填
```

### 回填内容示例

```markdown
## 三、完整文字内容（原文 + OCR）

### 公司概况
**九号公司**是一家...

### 招聘亮点
| 亮点 | 说明 |
|------|------|
| 留用通道 | 提前锁定秋招Offer |
...

---
*由 Hermes Agent 基于 OCR 结果自动总结生成*
```

---

## 故障排除与维护

### Python 环境兼容性问题（macOS 常见）

**问题现象**：
```
ModuleNotFoundError: No module named 'markdownify'
```

**根本原因**：
- 工具依赖 `markdownify` 等 Python 包
- Hermes 虚拟环境 (`venv/bin/python3`) 可能缺少这些依赖
- 系统 Python (`/usr/bin/python3`) 通常已安装所需包

**解决方案**：
使用系统 Python 执行工具：

```python
import subprocess

url = "https://mp.weixin.qq.com/s/xxx"
output_base = "/tmp/test_output"

# 使用系统 Python3 而非虚拟环境
result = subprocess.run(
    f'cd /tmp/wechat-article-for-ai-pro && /usr/bin/python3 main.py "{url}" -o {output_base} -v',
    shell=True, capture_output=True, text=True, timeout=300
)

if result.returncode != 0:
    raise Exception(f"工具提取失败: {result.stderr}")
```

**检查系统 Python 可用性**：
```bash
# 检查系统 Python 是否存在
ls -la /usr/bin/python3

# 检查依赖是否已安装
/usr/bin/python3 -c "import markdownify; print('OK')"
```

**备选方案**（如果系统 Python 也缺少依赖）：
```bash
# 在系统 Python 中安装依赖
/usr/bin/python3 -m pip install markdownify rapidocr zbar-py
```

**终极备选：使用浏览器工具提取**（当 Python 工具完全无法运行时）：

如果 Python 工具因依赖问题（如 orjson、camoufox 等）完全无法运行，可以使用 Hermes 内置浏览器工具作为 fallback：

```python
# 使用 browser_navigate 和 browser_snapshot 提取文章内容
# 然后手动保存为标准格式（article.md, article.html, metadata.json）

import json
from datetime import datetime
from pathlib import Path

# 1. 使用浏览器获取内容
# browser_navigate(url="https://mp.weixin.qq.com/s/xxx")
# snapshot = browser_snapshot(full=True)

# 2. 解析内容并创建标准输出
def create_standard_output(title, content, url, author, output_dir):
    article_dir = Path(output_dir) / title.replace("/", "_")
    article_dir.mkdir(parents=True, exist_ok=True)
    
    # article.md
    md_content = f"# {title}\n\n{content}"
    (article_dir / "article.md").write_text(md_content, encoding="utf-8")
    
    # article.html
    html_content = f"<!DOCTYPE html><html><body>{content}</body></html>"
    (article_dir / "article.html").write_text(html_content, encoding="utf-8")
    
    # metadata.json
    metadata = {
        "url": url,
        "title": title,
        "author": author,
        "published_at": "",
        "extraction_method": "browser-tool",
        "extraction_time": datetime.now().isoformat(),
        "image_count": 0,
        "images": []
    }
    (article_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), 
        encoding="utf-8"
    )
    
    return article_dir
```

**注意**：浏览器提取方式缺少 OCR 和二维码识别功能，适合纯文字文章或作为应急方案。

### Skill 丢失/损坏恢复

如果 Skill 目录被误删或损坏：

```bash
# 1. 从 GitHub 恢复 Skill
cd ~/.hermes/skills/web
git clone https://github.com/liuxiaoan8998/wechat-article-extraction-pro-skill.git wechat-article-extraction-pro

# 2. 重新部署 Python 项目
cd /tmp
rm -rf wechat-article-for-ai-pro
git clone https://github.com/liuxiaoan8998/wechat-article-for-ai-pro.git

# 3. 运行安装脚本
bash ~/.hermes/skills/web/wechat-article-extraction-pro/scripts/setup.sh
```

### 双仓库管理策略

| 仓库 | 地址 | 用途 | 更新时机 |
|------|------|------|----------|
| Python 源码 | `wechat-article-for-ai-pro` | 核心提取工具 | 功能迭代 |
| Hermes Skill | `wechat-article-extraction-pro-skill` | 调用指南和脚本 | 流程优化 |

**为什么分离？**
- Python 项目：关注功能实现（OCR、下载、解析）
- Skill 项目：关注调用流程（参数、步骤、示例）
- 不同迭代周期，避免互相干扰

### 版本控制工作流

**Skill 更新：**
```bash
cd ~/.hermes/skills/web/wechat-article-extraction-pro
git add .
git commit -m "v2.0.x: 描述"
git push origin main
```

**Python 源码更新：**
```bash
cd /tmp/wechat-article-for-ai-pro
git pull origin main  # 先同步远程
git add .
git commit -m "v1.x: 描述"
git push origin main
```

### 快速诊断命令

```bash
# 检查 Skill 是否存在
ls ~/.hermes/skills/web/wechat-article-extraction-pro/

# 检查 Python 项目是否存在
ls /tmp/wechat-article-for-ai-pro/

# 检查 Git 状态
cd ~/.hermes/skills/web/wechat-article-extraction-pro && git status
cd /tmp/wechat-article-for-ai-pro && git status

# 查看技能列表
hermes skills list web
```

---

## v2.1 新增：飞书多维表格集成（内容管理）

### 功能概述
将提取的公众号文章自动同步到飞书多维表格，支持选题管理和二创工作流。

### 完整流程图（v2.1）

```
用户提供 URL
    ↓
┌─────────────────────────────────────────────────────────┐
│  阶段 1：工具提取（本地执行）                              │
│  1. 启动 Camoufox 浏览器访问文章                          │
│  2. 提取标题、作者、正文内容                               │
│  3. OCR 识别（RapidOCR）                                  │
│  4. 生成 5 文件输出                                        │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│  阶段 2：Hermes 总结（AI 处理）                           │
│  1. 读取 article-ocr.md 的 OCR 内容                      │
│  2. 结构化分析并生成总结                                   │
│  3. 回填到 article-ocr.md 第三部分                        │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│  阶段 3：飞书 Base 同步（内容管理）                        │
│  1. 提取关键字段（标题、公众号、投递方式等）                │
│  2. 调用 Lark CLI 录入多维表格                             │
│  3. 标记状态为"待处理"                                     │
└─────────────────────────────────────────────────────────┘
    ↓
完成（可在飞书表格中进行选题和二创管理）
```

### 前置条件

1. **安装 Lark CLI**
```bash
npm install -g @larksuite/cli
export PATH="$HOME/.npm-global/lib/node_modules/@larksuite/cli/bin:$PATH"
```

2. **配置 Lark CLI 认证**
```bash
lark-cli config init --app-id "cli_xxx" --app-secret-stdin
lark-cli doctor  # 验证配置
```

3. **创建 Base（首次使用）**
```bash
# 创建 Base
lark-cli base +base-create --name "公众号文章选题库" --as bot

# 创建表格
lark-cli base +table-create --base-token "YOUR_BASE_TOKEN" --name "文章列表" --as bot

# 添加字段（参考下方字段结构）
```

### Base 字段结构

| 字段 | 类型 | 说明 |
|------|------|------|
| 文章标题 | 文本 | 主标题 |
| 公众号 | 文本 | 来源账号 |
| 发布时间 | 日期 | 原文发布时间 |
| 文章内容概要总结 | 文本 | AI生成的结构化总结 |
| 投递方式 | 文本 | 简历投递渠道 |
| 更新时间 | 日期 | 数据录入时间 |
| 文章链接 | 文本 | 原文URL |
| 行业/领域 | 单选 | 互联网/金融/能源/传媒等 |
| 岗位类型 | 单选 | 实习/校招/社招/兼职 |
| 工作地点 | 单选 | 城市列表 |
| 学历要求 | 单选 | 本科/硕士/博士/不限 |
| 截止日期 | 日期 | 招聘截止 |
| 优先级 | 单选 | 高/中/低 |
| 状态 | 单选 | 待处理/已选题/撰写中/已二创/已发布 |
| 标签 | 单选 | 热门/急招/大厂/国企/外企/可内推 |
| 备注 | 文本 | 编辑备注 |

### 标准同步流程（含字段检查）

```python
import subprocess
import json
import os
from datetime import datetime

def sync_article_to_feishu(article_dir: str) -> dict:
    """
    完整的文章同步流程，包含字段检查和自动补充
    
    Args:
        article_dir: 文章输出目录路径（如 ~/.hermes/output/文章标题/）
        
    Returns:
        dict: 包含 success, record_id, missing_fields 的结果
    """
    # 1. 读取metadata.json
    metadata_path = os.path.join(article_dir, 'metadata.json')
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    # 2. 读取article-ocr.md获取OCR内容
    ocr_path = os.path.join(article_dir, 'article-ocr.md')
    with open(ocr_path, 'r', encoding='utf-8') as f:
        ocr_content = f.read()
    
    # 3. 准备基础数据（从metadata提取）
    base_token = "E9y1bxjHGa9LeGs9q3Tc3J41nmf"
    table_id = "tblYIqHtHrWUlVnP"
    
    # 格式化发布时间
    published_at = metadata.get('published_at', '')
    if published_at:
        # 尝试解析并格式化为 YYYY/MM/DD
        try:
            dt = datetime.strptime(published_at, "%Y-%m-%d %H:%M:%S")
            formatted_date = dt.strftime("%Y/%m/%d")
        except:
            formatted_date = published_at
    else:
        formatted_date = "/"
    
    # 4. 构建完整记录数据
    record_data = {
        # ❗ 必填字段（从metadata提取）
        "文章标题": metadata.get('title', ''),
        "公众号": metadata.get('author', ''),
        "发布时间": formatted_date,
        "文章链接": metadata.get('url', ''),
        
        # AI分析字段（从OCR内容提取）
        "行业": analyze_industry(ocr_content),  # 需要实现
        "领域": analyze_field(ocr_content),
        "岗位类型": analyze_job_types(ocr_content),
        "工作地点": analyze_location(ocr_content),
        "学历要求": analyze_education(ocr_content),
        "截止日期": analyze_deadline(ocr_content),
        "投递方式": analyze_apply_method(ocr_content),
        "原文亮点": analyze_highlights(ocr_content),
        "文章概要": generate_summary(ocr_content),
        "选题方向": determine_topic_direction(ocr_content),
        
        # 固定值字段
        "文章状态": "待选题",
        "文章来源": "链接",
        "适配账号": match_accounts(ocr_content),
        "优先级": "中",
        "标签": analyze_tags(ocr_content),
        "采集时间": int(datetime.now().timestamp() * 1000),
    }
    
    # 5. 检查必填字段
    required_fields = ['文章标题', '公众号', '发布时间', '文章链接']
    missing_fields = [f for f in required_fields if not record_data.get(f) or record_data.get(f) == '/']
    
    if missing_fields:
        print(f"⚠️ 警告：以下必填字段缺失或为空: {', '.join(missing_fields)}")
    
    # 6. 写入临时文件并同步
    with open('sync_data.json', 'w', encoding='utf-8') as f:
        json.dump(record_data, f, ensure_ascii=False)
    
    try:
        cmd = (
            f'lark-cli base +record-upsert '
            f'--base-token {base_token} '
            f'--table-id {table_id} '
            f'--json @sync_data.json '
            f'--as bot'
        )
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            response = json.loads(result.stdout)
            if response.get('ok'):
                record_id = response['data']['record']['record_id_list'][0]
                print(f"✅ 同步成功！记录ID: {record_id}")
                if missing_fields:
                    print(f"⚠️ 但以下字段缺失，建议后续补充: {', '.join(missing_fields)}")
                return {
                    'success': True,
                    'record_id': record_id,
                    'missing_fields': missing_fields
                }
            else:
                return {
                    'success': False,
                    'error': response.get('error'),
                    'missing_fields': missing_fields
                }
        else:
            return {
                'success': False,
                'error': result.stderr,
                'missing_fields': missing_fields
            }
    finally:
        if os.path.exists('sync_data.json'):
            os.remove('sync_data.json')

# 使用示例
result = sync_article_to_feishu("~/.hermes/output/Peet's第二届暑期实习项目火热招聘中！/")
if result['success']:
    print(f"记录ID: {result['record_id']}")
    if result['missing_fields']:
        print(f"缺失字段: {result['missing_fields']}")
        # 可以选择立即补充
        # update_missing_fields(result['record_id'], metadata)
```

### 字段检查清单

同步前必须确认以下字段：

| 优先级 | 字段 | 来源 | 检查方法 |
|--------|------|------|----------|
| P0 | 文章标题 | metadata.json | `metadata.get('title')` |
| P0 | 公众号 | metadata.json | `metadata.get('author')` |
| P0 | 发布时间 | metadata.json | `metadata.get('published_at')` → 格式化为 YYYY/MM/DD |
| P0 | 文章链接 | metadata.json | `metadata.get('url')` |
| P1 | 行业 | AI分析 | 根据内容判断 |
| P1 | 岗位类型 | AI分析 | 实习/校招/社招/兼职 |
| P1 | 工作地点 | AI提取 | 从OCR内容提取 |
| P2 | 其他字段 | AI分析 | 截止日期、投递方式等 |

**注意**：P0字段缺失时必须警告，可选择立即补充或后续更新。

使用 Python 脚本标准化同步流程：

```python
import subprocess
import json
import os

def sync_to_feishu(record_data: dict) -> dict:
    """
    同步单条记录到飞书Base
    
    Args:
        record_data: 符合Base字段格式的字典
        
    Returns:
        dict: 包含 success, record_id, error 的结果
    """
    base_token = "E9y1bxjHGa9LeGs9q3Tc3J41nmf"
    table_id = "tblYIqHtHrWUlVnP"
    
    # ⚠️ 关键：Lark CLI 要求使用相对路径，不能使用绝对路径
    # 先切换到临时目录，写入文件后再执行命令
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        # 写入临时文件（相对路径）
        with open('sync_data.json', 'w', encoding='utf-8') as f:
            json.dump(record_data, f, ensure_ascii=False)
        
        try:
            # 执行同步命令（在临时目录中执行，使用相对路径）
            result = subprocess.run(
                f'lark-cli base +record-upsert --base-token {base_token} --table-id {table_id} --json @sync_data.json --as bot',
                shell=True, capture_output=True, text=True
            )
        
        # 解析结果
        if result.returncode == 0:
            response = json.loads(result.stdout)
            if response.get('ok'):
                record_id = response['data']['record']['record_id_list'][0]
                return {'success': True, 'record_id': record_id}
            else:
                return {'success': False, 'error': response.get('error')}
        else:
            return {'success': False, 'error': result.stderr}
        finally:
            # 清理临时文件（可选，TemporaryDirectory 会自动清理）
            pass

# 使用示例
record = {
    "文章标题": "文章标题",
    "行业": "消费品",  # 单选字段直接使用字符串
    "岗位类型": ["实习"],  # 多选字段使用数组
    # ... 其他字段
}

result = sync_to_feishu(record)
if result['success']:
    print(f"同步成功！记录ID: {result['record_id']}")
else:
    print(f"同步失败: {result['error']}")
```

**⚠️ 重要提示**：Lark CLI 的 `--json` 参数必须使用相对路径，不能使用绝对路径（如 `/tmp/sync_data.json`）。解决方案：
1. 使用 `tempfile.TemporaryDirectory()` 创建临时目录
2. `os.chdir()` 切换到该目录
3. 写入文件并使用相对路径 `@sync_data.json`
4. 命令执行完成后自动清理
```

### 更新已有记录

当需要补充或修改已同步记录时，使用 `--record-id` 参数：

```python
import subprocess
import json
import os

def update_feishu_record(record_id: str, update_data: dict) -> dict:
    """
    更新飞书Base中已有的记录
    
    Args:
        record_id: 记录ID（如 recvhq1MWUhyc5）
        update_data: 要更新的字段字典
        
    Returns:
        dict: 包含 success, record_id, error 的结果
    """
    base_token = "E9y1bxjHGa9LeGs9q3Tc3J41nmf"
    table_id = "tblYIqHtHrWUlVnP"
    
    # 写入临时文件
    with open('update_data.json', 'w', encoding='utf-8') as f:
        json.dump(update_data, f, ensure_ascii=False)
    
    try:
        # 执行更新命令（添加 --record-id 参数）
        cmd = (
            f'lark-cli base +record-upsert '
            f'--base-token {base_token} '
            f'--table-id {table_id} '
            f'--record-id {record_id} '  # 指定要更新的记录
            f'--json @update_data.json '
            f'--as bot'
        )
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            response = json.loads(result.stdout)
            if response.get('ok'):
                return {'success': True, 'record_id': record_id}
            else:
                return {'success': False, 'error': response.get('error')}
        else:
            return {'success': False, 'error': result.stderr}
    finally:
        if os.path.exists('update_data.json'):
            os.remove('update_data.json')

# 使用示例：补充缺失字段
record_id = "recvhq1MWUhyc5"  # Peet's的记录ID
update_data = {
    "文章标题": "Peet's第二届暑期实习项目火热招聘中！",
    "公众号": "皮爷招聘",
    "文章链接": "https://mp.weixin.qq.com/s/xxx"
}

result = update_feishu_record(record_id, update_data)
if result['success']:
    print(f"更新成功！记录ID: {result['record_id']}")
else:
    print(f"更新失败: {result['error']}")
```

**常见更新场景**：
1. **补充缺失字段**：初次同步时某些字段未填写，后续补充
2. **修正错误数据**：发现同步的数据有误，需要更正
3. **更新状态**：如从"待选题"更新为"已选题"
4. **添加标签**：为文章添加或修改标签
    print(f"同步失败: {result['error']}")
```

### 批量同步多篇文章

```python
import subprocess
import json
import os

def batch_sync_to_feishu(records: list) -> list:
    """
    批量同步多篇文章到飞书Base
    
    Args:
        records: 记录数据列表
        
    Returns:
        list: 每条记录的同步结果
    """
    results = []
    for i, record in enumerate(records):
        print(f"正在同步第 {i+1}/{len(records)} 篇文章...")
        result = sync_to_feishu(record)
        results.append(result)
        
        if result['success']:
            print(f"  ✅ 成功: {result['record_id']}")
        else:
            print(f"  ❌ 失败: {result['error']}")
    
    return results

# 使用示例
articles = [
    {"文章标题": "文章1", "行业": "互联网", "岗位类型": ["实习"]},
    {"文章标题": "文章2", "行业": "金融", "岗位类型": ["校招"]},
    {"文章标题": "文章3", "行业": "能源", "岗位类型": ["实习"]},
]

results = batch_sync_to_feishu(articles)
success_count = sum(1 for r in results if r['success'])
print(f"\n同步完成: {success_count}/{len(articles)} 篇成功")
```

### 命令行直接录入（备用）

```bash
export PATH="$HOME/.npm-global/lib/node_modules/@larksuite/cli/bin:$PATH"

# 先创建数据文件
cat > data.json << 'EOF'
{
  "文章标题": "文章标题",
  "行业": "消费品",
  "岗位类型": ["实习"],
  "工作地点": "/",
  "学历要求": "本科",
  "截止日期": "/",
  "投递方式": "扫码投递",
  "原文亮点": "亮点内容",
  "文章概要": "概要内容",
  "选题方向": "消费品行业实习机会",
    "文章状态": "待选题",
    "文章来源": "链接",
    "适配账号": ["Joblinker"],
    "优先级": "中",
    "标签": "大厂",
    "采集时间": 1776756180000
  }' \\
  --as bot
```

### 更新已有记录
### 二创工作流
    "采集时间": 1776756180000
  }' \\
  --as bot
```
# 清理临时文件
rm data.json
```

### 工作流建议

**二创管理流程：**
1. **待处理** → 新提取的文章默认状态
2. **已选题** → 编辑确认要二创的文章
3. **撰写中** → 正在撰写二创内容
4. **已二创** → 二创完成，待发布
5. **已发布** → 已发布到目标平台

**筛选视图：**
- 按行业筛选（金融/能源/传媒）
- 按岗位类型筛选（实习/校招/社招）
- 按状态筛选（待处理/已选题/已发布）
- 按优先级筛选（高/中/低）

### 自动化脚本（可选）

创建 `scripts/sync_to_feishu.sh`：

```bash
#!/bin/bash
# 将提取的文章同步到飞书 Base

BASE_TOKEN="YOUR_BASE_TOKEN"
TABLE_ID="YOUR_TABLE_ID"
ARTICLE_DIR="$1"

# 读取 metadata
TITLE=$(cat "$ARTICLE_DIR/metadata.json" | jq -r '.title')
AUTHOR=$(cat "$ARTICLE_DIR/metadata.json" | jq -r '.author')
URL=$(cat "$ARTICLE_DIR/metadata.json" | jq -r '.url')

# 读取总结内容（前500字）
SUMMARY=$(head -c 500 "$ARTICLE_DIR/article-ocr.md")

# 录入 Base
lark-cli base +record-upsert \
  --base-token "$BASE_TOKEN" \
  --table-id "$TABLE_ID" \
  --json "{
    \"文章标题\": \"$TITLE\",
    \"公众号\": \"$AUTHOR\",
    \"文章内容概要总结\": \"$SUMMARY\",
    \"文章链接\": \"$URL\"
  }" \
  --as bot
```

---

## 飞书 Base 内容管理

### 表格配置

| 属性 | 值 |
|------|-----|
| **Base 名称** | 公众号文章选题库 |
| **Base 链接** | https://rqtvt0xmrql.feishu.cn/base/E9y1bxjHGa9LeGs9q3Tc3J41nmf |
| **Base Token** | `E9y1bxjHGa9LeGs9q3Tc3J41nmf` |
| **Table ID** | `tblYIqHtHrWUlVnP` |

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| 文章标题 | 文本 | 主标题 |
| 公众号 | 文本 | 来源账号 |
| 发布时间 | 日期 | 原文发布时间 |
| 文章内容概要总结 | 文本 | AI生成的结构化总结 |
| 投递方式 | 文本 | 简历投递渠道 |
| 文章链接 | 文本 | 原文URL |
| **行业** | **单选** | **互联网/金融/能源/传媒/制造/消费品/其他** |
| **领域** | **单选** | **科技/投资/电力/娱乐/互联网/零售/其他** |
| 岗位类型 | 单选 | 实习/校招/社招/兼职 |
| 工作地点 | 单选 | 城市列表 |
| 学历要求 | 单选 | 本科/硕士/博士/不限 |
| 截止日期 | 日期 | 招聘截止 |
| 优先级 | 单选 | 高/中/低 |
| 状态 | 单选 | 待处理/已选题/撰写中/已二创/已发布 |
| 标签 | 单选 | 热门/急招/大厂/国企/外企/可内推 |
| **亮点** | **文本** | **招聘信息亮点总结** |

### 字段值格式（重要）

**单选字段格式**：直接使用字符串值，**不要**包装成 `{"text": "值"}`

| 字段类型 | 正确格式 | 错误格式 |
|---------|---------|---------|
| 文本 | `"文章标题": "标题内容"` | - |
| 单选 | `"行业": "消费品"` | `{"行业": {"text": "消费品"}}` ❌ |
| 多选 | `"标签": [{"text": "大厂"}]` | - |

**空字段填充规则**：信息未获取到的字段，统一填充 `"/"`

| 场景 | 处理方式 | 示例 |
|------|---------|------|
| 有明确信息 | 填充实际值 | `"工作地点": "深圳"` |
| 信息未提及/不确定 | **填充 `"/"`** | `"截止日期": "/"` |
| 字段不适用 | **填充 `"/"`** | `"亮点": "/"` |

> **目的**：区分"确实没有信息" vs "可能解析出了问题"
> 
> **禁止**：留空字符串或省略字段，必须显式标记 `"/"`

**完整示例**：
```bash
lark-cli base +record-upsert \
  --base-token "E9y1bxjHGa9LeGs9q3Tc3J41nmf" \
  --table-id "tblYIqHtHrWUlVnP" \
  --json '{
    "文章标题": "珀莱雅2026校招启动",
    "公众号": "珀莱雅招聘",
    "行业": "消费品",
    "领域": "消费品",
    "岗位类型": "校招",
    "工作地点": "杭州",
    "文章状态": "待选题",
    "文章来源": "链接",
    "适配账号": ["Joblinker"],
    "优先级": "中",
    "标签": "大厂",
    "采集时间": 1776756180000
  }' \\
  --as bot
```

### 更新已有记录
### 二创工作流

```
待处理 → 已选题 → 撰写中 → 已二创 → 已发布
```

**筛选视图建议：**
- 按「状态」筛选：查看待处理文章
- 按「优先级」筛选：优先处理高优先级
- 按「行业」筛选：互联网/金融/能源等
- 按「领域」筛选：科技/投资/电力/娱乐等
- 按「岗位类型」筛选：实习/校招/社招

### 自动录入脚本

```bash
#!/bin/bash
# 将提取的文章同步到飞书 Base

BASE_TOKEN="E9y1bxjHGa9LeGs9q3Tc3J41nmf"
TABLE_ID="tblYIqHtHrWUlVnP"
ARTICLE_DIR="$1"

# 读取 metadata
TITLE=$(cat "$ARTICLE_DIR/metadata.json" | jq -r '.title')
AUTHOR=$(cat "$ARTICLE_DIR/metadata.json" | jq -r '.author')
URL=$(cat "$ARTICLE_DIR/metadata.json" | jq -r '.url')
PUBLISHED=$(cat "$ARTICLE_DIR/metadata.json" | jq -r '.published_at')

# 读取总结内容（前500字）
SUMMARY=$(grep -A 50 "### 招聘概览\|### 公司介绍\|### 招募概览" "$ARTICLE_DIR/article-ocr.md" | head -c 500)

# 录入 Base
export PATH="$HOME/.npm-global/lib/node_modules/@larksuite/cli/bin:$PATH"
lark-cli base +record-upsert \
  --base-token "$BASE_TOKEN" \
  --table-id "$TABLE_ID" \
  --json "{
    \"文章标题\": \"$TITLE\",
    \"公众号\": \"$AUTHOR\",
    \"发布时间\": \"$PUBLISHED\",
    \"文章内容概要总结\": \"$SUMMARY\",
    \"文章链接\": \"$URL\",
    \"状态\": {\"text\": \"待处理\"}
  }" \
  --as bot
```

---

## 关键经验教训（必读）

### 1. OCR内容读取优先级（v3.0.2 新增）

**核心原则**：AI分析时优先读取 `article-ocr.md` 中的OCR结果，而非重新识别图片。

**原因**：
- 工具提取阶段已完成RapidOCR识别，结果保存在 `article-ocr.md` 中
- 重新调用 `vision_analyze` 识别图片效率低且重复
- OCR结果已包含在 `[段1]`, `[段2]`, `[段3]` 等标记中

**正确做法**：
```python
# 1. 直接读取 article-ocr.md
with open(os.path.join(article_dir, 'article-ocr.md'), 'r', encoding='utf-8') as f:
    ocr_content = f.read()

# 2. 从OCR内容提取关键信息
# OCR结果格式示例：
# [段1]
# 招聘对象
# 2027届毕业生
# ...

# 3. 基于OCR内容进行AI分析
analysis = {
    "行业": analyze_industry(ocr_content),
    "岗位类型": analyze_job_types(ocr_content),
    # ... 其他字段
}
```

**错误做法**：
```python
# ❌ 不要重新识别图片
vision_analyze(image_url="...", question="提取文字")
# 效率低，重复工作
```

### 2. 文章目录查找逻辑（v3.0.2 新增）

**问题**：文章标题包含特殊字符（如 `|`）时，提取的目录名可能被截断。

**示例**：
- 原标题：`实习 | 字节跳动2027届实习生招聘`
- 工具提取目录：`/tmp/test_output/实习`（被截断）
- 实际完整目录：`/tmp/test_output/实习 _ 字节跳动2027届实习生招聘`

**解决方案**：
```python
# 方法1：使用metadata.json中的标题查找
def find_article_dir_by_title(output_dir, target_title):
    """通过标题查找文章目录"""
    for dirname in os.listdir(output_dir):
        full_path = os.path.join(output_dir, dirname)
        if os.path.isdir(full_path):
            metadata_path = os.path.join(full_path, 'metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                if metadata.get('title') == target_title:
                    return full_path
    return None

# 方法2：使用URL查找（推荐）
def find_article_dir_by_url(output_dir, target_url):
    """通过URL查找文章目录"""
    for dirname in os.listdir(output_dir):
        full_path = os.path.join(output_dir, dirname)
        if os.path.isdir(full_path):
            metadata_path = os.path.join(full_path, 'metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                if metadata.get('url') == target_url:
                    return full_path
    return None
```

### 3. 飞书 Base 字段格式陷阱

**发现过程**：多次尝试后发现 API 报错 "Match one of the supported request payload shapes exactly"

**正确格式**：
```bash
# ✅ 正确：单选字段直接使用字符串
{"行业": "消费品", "领域": "科技"}

# ❌ 错误：不要包装成对象格式
{"行业": {"text": "消费品"}}  # 会导致验证失败
```

**适用规则**：
| 字段类型 | 格式 | 示例 |
|---------|------|------|
| 文本 | 直接字符串 | `"文章标题": "标题"` |
| 单选 | **直接字符串** | `"行业": "消费品"` ✅ |
| 多选 | 对象数组 | `"标签": [{"text": "大厂"}]` |

### 2. 空字段填充规则

**用户明确要求**：信息未获取到的字段，统一填充 `"/"`

**目的**：区分"确实没有信息" vs "可能解析出了问题"

**执行标准**：
| 场景 | 处理方式 | 示例 |
|------|---------|------|
| 有明确信息 | 填充实际值 | `"工作地点": "深圳"` |
| 信息未提及 | **填充 `"/"`** | `"截止日期": "/"` |
| 信息不确定 | **填充 `"/"`** | `"学历要求": "/"` |
| 字段不适用 | **填充 `"/"`** | `"亮点": "/"` |

**禁止**：留空字符串、null、或省略字段

### 3. 上下文压缩处理

**问题**：对话达到358轮时，上下文被压缩，导致"失忆"

**解决方案**：
1. **Memory存储**：关键配置写入长期Memory（飞书Base Token、字段格式规则）
2. **标记文件**：创建 `~/.hermes/.wechat_workflow_state` 保存任务状态
3. **定期提醒**：每50轮对话主动提醒保存进度

**用户指令**：
- "保存当前进度" → 立即更新标记文件
- "查看状态" → 读取标记文件汇报

### 微信公众号草稿验证（v3.0.6 新增）

**使用场景**：
- 上传后内容显示异常，需要诊断问题
- 验证图片是否正确上传
- 确认 HTML 结构是否完整

**API 验证方法**：

```python
import requests

def verify_wechat_draft(appid: str, media_id: str, api_key: str) -> dict:
    """
    验证微信公众号草稿内容
    
    Args:
        appid: 公众号 AppID
        media_id: 草稿 MediaID
        api_key: 简立制作 API Key
        
    Returns:
        dict: 包含 content_length, image_count, content_preview
    """
    url = f"https://mp.jianlizhizuo.cn/v1/accounts/{appid}/drafts/{media_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    response = requests.get(url, headers=headers, timeout=30)
    data = response.json()
    
    if data.get("code") != 0:
        return {"success": False, "error": data.get("message")}
    
    draft = data["data"]["draft"]
    content = draft.get("content", "")
    
    return {
        "success": True,
        "title": draft.get("title"),
        "content_length": len(content),
        "image_count": content.count("<img"),
        "thumb_media_id": draft.get("thumb_media_id"),
        "content_preview": content[:500] + "..." if len(content) > 500 else content
    }

# 使用示例
result = verify_wechat_draft(
    appid="wxa0e3ae2f81exxxxx",
    media_id="svD8zPLBr026J0ip2Vt08Mk7wXHqMje5dGGQ_i3741PYE4_EVI5YJVbLSp_aY3rW",
    api_key="sk-fe371224c96fd8ab819c8d9159099158ead65b5039ba5c4d"
)

if result["success"]:
    print(f"✅ 草稿验证成功")
    print(f"   标题: {result['title']}")
    print(f"   内容长度: {result['content_length']} 字符")
    print(f"   图片数量: {result['image_count']} 张")
    
    # 判断是否正常
    if result['content_length'] < 10000:
        print("⚠️ 警告: 内容长度异常，可能未正确上传")
    if result['image_count'] == 0:
        print("⚠️ 警告: 未检测到图片")
else:
    print(f"❌ 验证失败: {result['error']}")
```

**正常 vs 异常指标**：

| 指标 | 正常范围 | 异常信号 | 处理建议 |
|------|---------|---------|----------|
| 内容长度 | 50,000+ 字符（完整文章） | < 10,000 字符 | 重新提取原始 HTML |
| 图片数量 | 与原文一致（10-30张） | 0 张或少于原文 | 检查 images/ 目录和路径 |
| HTML 结构 | 包含 `<section>` 标签 | 只有 `<p>`, `<strong>` | 使用修复流程重新提取 |
| 标签闭合 | 正确闭合 `</strong>` | `<strong>text<strong>` | 重新抓取原始 HTML |

**诊断流程**：

```
上传草稿后
    ↓
调用 API 验证
    ↓
内容长度 < 10K?
    ├── 是 → 检查 article.html 是否为 Markdown 转换版
    │         └── 是 → 执行 fix_article_html() 修复
    │
    └── 否 → 图片数量 = 0?
              ├── 是 → 检查 images/ 目录是否存在
              │         └── 不存在 → 重新下载图片
              │
              └── 否 → 检查 HTML 标签是否正确闭合
                        └── 未闭合 → 修复 HTML 格式
```

### HTML 格式修复方案（v3.0.5 新增）

**问题现象**：
- `article.html` 标签未闭合：`<strong>text<strong>`（应为 `</strong>`）
- 图片未下载或路径错误
- HTML 结构混乱，MD 标记残留（如 `---`）
- 上传微信公众号后内容显示异常

**根本原因**：
- Python 提取工具未正确执行（依赖缺失、Camoufox 失败等）
- 手动创建的 HTML 是 Markdown 转换版，非微信原始 HTML
- `save_original_html()` 函数未被调用或执行失败

**修复流程**：

```python
import requests
import re
import os
from pathlib import Path
from datetime import datetime

def fix_article_html(article_url: str, output_dir: str) -> dict:
    """
    修复损坏的 HTML 文件，重新抓取微信原始 HTML
    
    Args:
        article_url: 微信文章 URL
        output_dir: 文章输出目录（如 ~/.hermes/output/文章标题/）
        
    Returns:
        dict: 包含 success, html_path, images_count, images_dir
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }
    
    # 1. 抓取原始页面
    response = requests.get(article_url, headers=headers, timeout=30)
    html = response.text
    
    # 2. 提取 #js_content 区域（微信文章正文）
    match = re.search(
        r'<div[^>]*id=["\']js_content["\'][^>]*>(.*?)</div>\s*</div>\s*<script', 
        html, re.DOTALL
    )
    
    if not match:
        return {"success": False, "error": "无法提取正文内容"}
    
    content_html = match.group(1)
    
    # 3. 提取图片 URL
    img_urls = re.findall(r'data-src=["\'](https?://[^"\']+)["\']', content_html)
    
    # 4. 构建完整 HTML
    article_dir = Path(output_dir)
    title = article_dir.name
    
    original_html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.8; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
img {{ max-width: 100%; height: auto; display: block; margin: 10px 0; }}
strong {{ font-weight: bold; }}
</style>
</head>
<body>
{content_html}
</body>
</html>'''
    
    # 5. 备份旧 HTML
    html_path = article_dir / "article.html"
    if html_path.exists():
        backup_path = article_dir / "article_broken_backup.html"
        html_path.rename(backup_path)
        print(f"✅ 已备份损坏文件: {backup_path}")
    
    # 6. 保存新 HTML
    html_path.write_text(original_html, encoding="utf-8")
    print(f"✅ 原始 HTML 已保存: {html_path} ({len(original_html)} 字符)")
    
    # 7. 下载图片
    images_dir = article_dir / "images"
    images_dir.mkdir(exist_ok=True)
    
    downloaded = []
    for i, img_url in enumerate(img_urls):
        try:
            img_response = requests.get(img_url, headers=headers, timeout=30)
            if img_response.status_code == 200:
                ext = img_url.split('?')[0].split('.')[-1]
                if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                    ext = 'jpg'
                img_path = images_dir / f"img_{i+1:03d}.{ext}"
                img_path.write_bytes(img_response.content)
                downloaded.append(img_path.name)
        except Exception as e:
            print(f"⚠️ 图片下载失败: {img_url[:50]}... - {e}")
    
    print(f"✅ 已下载 {len(downloaded)}/{len(img_urls)} 张图片")
    
    return {
        "success": True,
        "html_path": str(html_path),
        "html_size": len(original_html),
        "images_count": len(downloaded),
        "images_dir": str(images_dir)
    }

# 使用示例
result = fix_article_html(
    article_url="https://mp.weixin.qq.com/s/xxx",
    output_dir="~/.hermes/output/文章标题/"
)

if result["success"]:
    print(f"✅ 修复完成！")
    print(f"   HTML: {result['html_size']} 字符")
    print(f"   图片: {result['images_count']} 张")
else:
    print(f"❌ 修复失败: {result.get('error')}")
```

**对比验证**：

| 指标 | 修复前（损坏） | 修复后（正确） |
|------|-------------|--------------|
| HTML 长度 | ~5,000 字符 | ~60,000+ 字符 |
| 图片数量 | 0 张 | 15+ 张 |
| 标签格式 | `<strong>text<strong>` | `<strong>text</strong>` |
| 内容来源 | Markdown 转换 | 微信原始 `#js_content` |
| 上传结果 | 格式错乱 | 正常显示 |

**何时使用**：
- Python 提取工具执行失败或输出异常
- `article.html` 文件大小异常（< 10KB 且文章有图片）
- 上传微信公众号后内容显示异常
- 图片缺失或路径错误

### 4. 双仓库管理策略

| 仓库 | 用途 | 更新时机 |
|------|------|----------|
| `wechat-article-for-ai-pro` | Python提取工具 | 功能迭代 |
| `wechat-article-extraction-pro-skill` | Hermes调用指南 | 流程优化 |

**为什么分离**：不同迭代周期，避免互相干扰

---

### 原文亮点提炼规范（v2.6 新增）

**核心原则**：突出吸引学生查看和投递的关键点，按优先级排序

#### 关键词优先级

| 优先级 | 类型 | 关键词 | 示例 |
|--------|------|--------|------|
| **P0** | 硬性福利 | 包食宿、提供住宿、六险二金、补充医疗 | `"包食宿"`、`"六险二金"` |
| **P1** | 发展机会 | 可转正、提前锁定Offer、留用机会、实习转正 | `"可转正"`、`"提前获Offer"` |
| **P2** | 企业背书 | 央企A级、国企、大厂、世界500强、行业第一 | `"央企A级"`、`"国企"`、`"大厂"` |
| **P3** | 流程优势 | 免笔试、直通面试、无笔试、快速通道 | `"免笔试"`、`"直通面试"` |
| **P4** | 特殊政策 | 落户政策、优先落户、北京户口、上海户口 | `"可落户"`、`"优先落户"` |
| **P5** | 薪资优势 | 薪资上浮、竞争力薪酬、高薪、待遇优厚 | `"薪资上浮"`、`"待遇优厚"` |

#### 亮点格式规范

1. **使用分号分隔**，每个亮点独立成句
2. **关键词前置**，吸引眼球的内容放在前面
3. **控制长度**，总字数不超过50字
4. **避免冗余**，不重复同类信息

#### 优化示例

| 原标题亮点 | 优化后 |
|-----------|--------|
| 提前锁定27届校招Offer；六大招聘方向；近4000件授权专利；终端网点14万家；2016年上市 | **可转正**；**大厂**；**包食宿**；六大方向；4000+专利 |
| 提前批次录用机会；国家卓越工程师团队；全球五大电力保护设备企业之一；提供住宿；专业导师辅导 | **央企背景**；**可转正**；**包食宿**；国家卓越工程师团队 |
| 免笔试直通面试；管理规模20亿；三种实习类型(校招/暑期/日常)；六险二金；高频量化策略 | **免笔试**；**可转正**；**六险二金**；三种实习类型 |
| 央企A级；清洁能源装机世界第一(2.88亿千瓦)；六险二金；落户政策；68家二级单位；业务覆盖47个国家 | **央企A级**；**可落户**；**六险二金**；**包食宿**；清洁能源世界第一 |
| 11个组别招募（编剧/舞台/真人秀/统筹/音乐/艺人/听审/宣传/视觉/技术/后期）；实习到8月中；湖南长沙；大厂实习机会 | **大厂实习**；**可转正**；11个组别；实习到8月中 |

#### 提取流程

```
阅读OCR内容
    ↓
识别福利关键词（P0-P1优先）
    ↓
识别企业背书（P2）
    ↓
识别流程/政策优势（P3-P4）
    ↓
按优先级排序，去重
    ↓
生成亮点字符串（分号分隔）
```

#### 完整示例

**欧普照明**：
```
原文信息：
- 提前锁定27届校招Offer
- 六大招聘方向(研发/产品/算法/营销/品牌/职能)
- 近4000件授权专利
- 终端网点14万家
- 2016年上市
- 上海总部及多个生产办公园区

优化后亮点：
"可转正；大厂；包食宿；六大方向；4000+专利"
```

**南瑞继保**：
```
原文信息：
- 提前批次正式录用的机会
- 国家卓越工程师团队
- 全球五大电力保护设备企业之一
- 提供住宿
- 专业导师辅导
- 具有竞争力的实习工资

优化后亮点：
"央企背景；可转正；包食宿；国家卓越工程师团队"
```

---

## 飞书 Base 字段填充规范（v2.5 新增）

### 字段填充逻辑

| 字段 | 类型 | 填充规则 | 示例 |
|------|------|---------|------|
| 文章标题 | 文本 | 从metadata提取 | `"实习 \| 欧普照明27届实习生招聘正式开启！"` |
| 公众号 | 文本 | 从metadata提取 | `"欧普照明微招聘"` |
| 发布时间 | 日期 | 从metadata提取 | `"2026-04-21 15:01:39"` |
| 文章链接 | 文本 | 从metadata提取 | `"https://mp.weixin.qq.com/s/xxx"` |
| **文章ID** | **文本** | **从metadata提取，UUID格式** | **`"fa70b413"`** |
| 行业 | 单选 | AI分析文章内容判断 | `"消费品"` / `"金融"` / `"能源"` |
| 领域 | 单选 | AI分析文章内容判断 | `"消费品"` / `"投资"` / `"电力"` |
| 岗位类型 | 多选 | AI分析招聘类型，**最多2个** | `["实习"]` / `["校招"]` / `["实习", "校招"]` |
| 工作地点 | 单选 | AI提取地点信息 | `"上海"` / `"北京"` / `"深圳"` |
| 学历要求 | 单选 | AI提取学历要求 | `"本科"` / `"硕士"` / `"博士"` |
| 截止日期 | 日期 | AI提取截止时间，无则填`"/"` | `"2026-05-31"` / `"/"` |
| 投递方式 | 文本 | AI提取投递渠道，无则填`"/"` | `"关注公众号在线投递"` / `"/"` |
| 原文亮点 | 文本 | AI总结核心亮点 | `"提前锁定Offer；六大招聘方向；近4000件专利"` |
| 文章概要 | 文本 | AI生成结构化总结（500字内） | 公司概况+招聘亮点+关键信息 |
| 选题方向 | 文本 | AI根据行业和账号匹配生成 | `"消费品行业实习机会"` |
| 文章状态 | 单选 | 固定值 `"待选题"` | `"待选题"` |
| 文章来源 | 单选 | 固定值 `"链接"` | `"链接"` |
| 适配账号 | 多选 | 根据行业/领域/岗位类型匹配，**规则见下方** | `["Joblinker"]` / `["研究生求职圈", "行研实习"]` |
| 优先级 | 单选 | 默认 `"中"`，重要可标 `"高"` | `"中"` |
| 标签 | 多选 | AI判断标签，**最多3个** | `["央企", "大厂", "六险二金"]` |
| 采集时间 | 日期 | 当前时间Unix时间戳（毫秒） | `1776756180000` |

### 空字段填充规则

**必须填充 `"/"` 的字段**：
- 截止日期（未明确提及）
- 投递方式（未明确提及）
- 原文亮点（无法提取）
- 工作地点（未明确提及）
- 学历要求（未明确提及）

**目的**：区分"确实没有信息" vs "可能解析出了问题"

**禁止**：留空字符串、null、或省略字段

### 日期字段格式

**飞书Base日期字段需使用Unix时间戳（毫秒）**：

```python
from datetime import datetime

# 采集时间
dt = datetime.now()
timestamp_ms = int(dt.timestamp() * 1000)
# 结果: 1776756180000

# API调用
lark-cli api PUT /open-apis/bitable/v1/apps/.../records/RECORD_ID \
  --data '{"fields": {"采集时间": 1776756180000}}' --as bot
```

### 适配账号匹配规则（v2.10 新增）

根据文章内容和账号定位，自动匹配适配账号：

| 账号 | 定位 | 匹配规则 |
|------|------|----------|
| **Joblinker** | 实习岗位为主 | **仅当文章包含实习岗位时适配** |
| **研究生求职圈** | 校招岗位为主 | **校招文章优先适配** |
| **行研实习** | 行研/金融实习 | 金融/投资/行研相关实习岗位 |

**匹配逻辑**：
1. **纯实习文章** → 适配 `["Joblinker"]`
2. **纯校招文章** → 适配 `["研究生求职圈"]`
3. **实习+校招混合文章** → 根据内容侧重判断：
   - 侧重实习 → `["Joblinker", "研究生求职圈"]`
   - 侧重校招 → `["研究生求职圈", "Joblinker"]`
4. **金融/投资/行研类实习** → 同时适配 `["行研实习"]`

**示例**：
| 文章类型 | 适配账号 |
|---------|----------|
| 某大厂暑期实习招聘 | `["Joblinker"]` |
| 某央企2026校招启动 | `["研究生求职圈"]` |
| 某券商实习+校招混合招聘 | `["Joblinker", "研究生求职圈"]` 或 `["研究生求职圈", "Joblinker"]` |
| 某基金公司行研实习招聘 | `["Joblinker", "行研实习"]` |
| 某投行校招+实习 | `["研究生求职圈", "行研实习"]` |

| 类型 | 格式 | 示例 |
|------|------|------|
| 单选 | 字符串 | `"行业": "消费品"` |
| 多选 | 字符串数组 | `"适配账号": ["Joblinker"]` |

### 完整录入示例

```bash
export PATH="$HOME/.npm-global/lib/node_modules/@larksuite/cli/bin:$PATH"

lark-cli base +record-upsert \
  --base-token "E9y1bxjHGa9LeGs9q3Tc3J41nmf" \
  --table-id "tblYIqHtHrWUlVnP" \
  --json '{
    "文章标题": "实习 | 欧普照明27届实习生招聘正式开启！",
    "公众号": "欧普照明微招聘",
    "发布时间": "2026-04-21 15:01:39",
    "文章链接": "https://mp.weixin.qq.com/s/rQVzVfl4FJ8tj74yI8YLuw",
    "行业": "消费品",
    "领域": "消费品",
    "岗位类型": "实习",
    "工作地点": "上海",
    "学历要求": "本科",
    "截止日期": "/",
    "投递方式": "关注\"欧普照明微招聘\"公众号，点击\"加入欧普-实习招聘\"在线投递",
    "原文亮点": "提前锁定27届校招Offer；六大招聘方向(研发/产品/算法/营销/品牌/职能)；近4000件授权专利；终端网点14万家；2016年上市",
    "文章概要": "欧普照明27届实习生招聘，面向2026年11月-2027年10月毕业生。招聘研发类、产品类、算法类、营销类、品牌类、职能类六大方向。4月21日启动网申，5月7日起AI面试，实习表现优异者可提前获得校招Offer。",
    "选题方向": "消费品行业实习机会",
    "文章状态": "待选题",
    "文章来源": "链接",
    "适配账号": ["Joblinker"],
    "优先级": "中",
    "标签": "大厂",
    "采集时间": 1776756180000
  }' \\
  --as bot
```

### 更新已有记录
### 二创工作流
使用 `api PUT` 更新特定字段：

```bash
# 更新采集时间
lark-cli api PUT /open-apis/bitable/v1/apps/E9y1bxjHGa9LeGs9q3Tc3J41nmf/tables/tblYIqHtHrWUlVnP/records/RECORD_ID \
  --data '{"fields": {"采集时间": 1776756180000}}' \
  --as bot

# 更新投递方式
lark-cli api PUT /open-apis/bitable/v1/apps/E9y1bxjHGa9LeGs9q3Tc3J41nmf/tables/tblYIqHtHrWUlVnP/records/RECORD_ID \
  --data '{"fields": {"投递方式": "关注公众号在线投递"}}' \
  --as bot
```

---

## 版本历史

| 版本 | 变更 |
|------|------|
| v1.0 | 标准输出（md+html+json+images） |
| v1.2 | 添加 article-ocr.md 占位符 |
| v1.3 | AI Vision OCR 集成 |
| v1.4 | 集成 RapidOCR 本地识别 |
| v1.5 | 可配置 OCR 引擎（rapidocr/vision/auto）|
| v1.5.1 | 修复 RGBA 图片切片保存问题 |
| v1.6 | Hybrid 模式：工具提取+OCR，Hermes 总结回填 |
| v2.0 | 标准 Skill 结构，Git 版本控制 |
| v2.1 | **新增飞书 Base 集成**，支持内容管理和二创工作流 |
| v2.2 | 添加飞书Base字段值格式说明 |
| v2.3 | 添加定期状态提醒机制 |
| v2.4 | **添加空字段填充规则**，明确"/"标记规范 |
| v2.5 | **添加字段填充逻辑规范**，明确采集时间/二创深度等默认值 |
| v2.8 | **删除字段**：移除"状态"和"二创深度"字段 |
| v2.9 | **更新标签字段**：改为多选，最多可选3个 |
| v2.10 | **更新岗位类型字段**：改为多选（最多2个）；**新增适配账号匹配规则** |
| v2.11 | **添加飞书Base同步标准方法**：sync_to_feishu()函数、批量同步、命令行方案 |
| v2.12 | **添加飞书同步指南文档** references/feishu-sync-guide.md |
| v2.13 | **添加更新已有记录方法**：update_feishu_record()函数，支持补充缺失字段和修正数据 |
| v2.14 | **添加完整字段检查流程**：sync_article_to_feishu()函数，包含22个字段的必填检查清单 |
| v2.15 | **添加二维码识别功能说明**：v1.7 新增 OpenCV QRCodeDetector，智能分类招聘链接 |
| v2.16 | **更新第四章结构说明**：展示第四章新格式（原文+OCR+二维码） |
| v2.17 | **集成 zbar-py 说明**：v1.7.2 新增 zbar-py 支持，解决复杂背景二维码识别问题 |
| v2.18 | **添加执行反馈规范**：明确二维码识别状态和飞书 Base 写入成功的反馈格式 |
| **v3.0** | **【重大更新】同步执行模式**：<br>• 将 Hybrid 模式改为同步执行，单次对话内完成全部阶段<br>• 阶段2（AI总结）和阶段3（Base同步）自动触发，无需用户二次指令<br>• 添加22字段完整性校验机制<br>• 更新执行反馈规范，显示字段填充统计<br>• 解决字段缺失问题，确保100%字段填充率 |
| **v3.0.1** | **【修复】URL格式兼容性**：<br>• 修复 `validate_url()` 支持极致了API返回的查询参数格式（`/s?__biz=xxx`）<br>• 解决批量处理时"No valid WeChat URLs found"错误 |
| **v3.0.2** | **【新增】标准反馈格式**：<br>• 强制要求每次同步后按 `字段填充: X/22 (Y%)` 格式反馈<br>• 新增OCR内容读取优先级规范（优先读取article-ocr.md）<br>• 新增文章目录查找逻辑（处理特殊字符截断问题） |
| **v3.0.3** | **【优化】HTML 输出格式**：<br>• 新增 `save_original_html()` 函数保存原始微信HTML（`article_original.html`，~3-4MB，含base64图片）<br>• `article.html` 由 formatter.py 生成图片查看器（~4KB，仅标题+图片）<br>• 无 `article_viewer.html`（已移除，功能由 article.html 代替）<br>• 同时保留原始样式和便于查看的格式 |
| **v3.0.5** | **【新增】HTML 格式修复方案**：<br>• 添加 `fix_article_html()` 函数，用于修复损坏的 HTML<br>• 使用 requests + regex 重新抓取微信原始 HTML<br>• 自动下载图片并替换本地路径<br>• 提供完整的修复流程和对比验证指标 |
| **v3.0.7** | **【修复】Lark CLI 路径限制**：<br>• 修复 `--json` 参数必须使用相对路径的问题<br>• 使用 `tempfile.TemporaryDirectory()` + `os.chdir()` 方案<br>• 解决 `"--file must be a relative path"` 错误 |
| **v3.0.8** | **【新增】文章ID 字段**：<br>• 飞书 Base 新增「文章ID」字段（fldthrINWp）<br>• 用于存储 UUID 格式的文章目录名<br>• 上传脚本优先通过 article_id 查找本地目录<br>• 解决标题特殊字符导致的匹配问题 |
| **v3.0.10** | **【修复】发布时间字段遗漏**：<br>• 修复同步流程中 `published_at` 字段遗漏问题<br>• 新增空字段自动填充 `"/"` 机制<br>• 更新字段完整性校验逻辑，区分"未获取"和"已填充/" |
| **v3.0.11** | **【修复】自动复制到 ~/.hermes/output/**：<br>• 在阶段 1（工具提取）完成后自动复制文章目录到 `~/.hermes/output/{article_id}/`<br>• 解决上传脚本"找不到文章目录"问题<br>• 确保提取 → 上传流程无缝衔接 |

---

## 执行反馈规范（v3.0 更新）

**⚠️ 强制要求**：每次同步完成后，必须按照以下标准格式反馈字段填充率。

### 标准反馈格式（用户明确要求）

```
✅ 同步成功！
   记录ID: {record_id}
   字段填充: 22/22 (100%)
```

**格式规范**：
- 必须包含"同步成功！"或"同步失败！"
- 必须显示记录ID
- **必须显示字段填充率，格式为：`字段填充: X/22 (Y%)`**
- 如果字段缺失，显示实际填充数量和百分比

**示例**：
```
✅ 同步成功！
   记录ID: recvhvG9EUnpVg
   字段填充: 22/22 (100%)

✅ 同步成功！
   记录ID: recvhvG9EUnpVg
   字段填充: 19/22 (86%)
   缺失字段: 截止日期、学历要求、投递方式
```

### 必须反馈的信息

| 信息类别 | 具体内容 | 输出格式 |
|---------|---------|---------|
| **阶段执行状态** | 4个阶段全部完成 | `✅ 工具提取 → AI总结 → Base同步` |
| **二维码识别状态** | 检测到 N 张包含二维码的图片 | `✅ 二维码识别：检测到 3 张二维码` |
| **二维码详情** | 招聘链接/报名链接/普通链接分类 | 列出每个二维码的类型和内容 |
| **飞书 Base 写入状态** | 成功/失败 + 记录 ID + 字段统计 | `✅ 飞书 Base 同步成功：记录ID recvhtBMKreN0I` |
| **字段填充率** | **必须按标准格式显示** | `字段填充: 22/22 (100%)` |
| **字段填充详情** | 已填充 vs 缺失字段列表 | 显示22个字段的填充情况 |
| **本地输出路径** | 文件保存位置 | `~/.hermes/output/文章标题/` |

### 标准输出模板（v3.0）

```markdown
**任务完成**

## 执行摘要

| 阶段 | 状态 | 详情 |
|------|------|------|
| **工具提取** | ✅ 完成 | N 张图片，OCR 识别完成 |
| **二维码识别** | ✅ 完成 | 检测到 M 张二维码（含 K 个招聘链接） |
| **Hermes 总结** | ✅ 完成 | 13个AI分析字段已生成 |
| **飞书 Base 同步** | ✅ 完成 | 记录ID: `recvhtBMKreN0I` |

## 字段填充统计

| 类型 | 数量 | 状态 |
|------|------|------|
| **基础字段** | 10/10 | ✅ 全部填充 |
| **AI分析字段** | 13/13 | ✅ 全部填充 |
| **总计** | 23/23 | ✅ 完整 |

### 已填充字段详情

**基础字段（10个）**：
- ✅ 文章标题、公众号、发布时间、文章链接、**文章ID**
- ✅ 文章状态、文章来源、采集时间
- ✅ ID、最后更新时间（系统自动）

**AI分析字段（13个）**：
- ✅ 行业、领域、岗位类型、工作地点
- ✅ 学历要求、截止日期、投递方式
- ✅ 原文亮点、文章概要、选题方向
- ✅ 适配账号、优先级、标签

## 二维码识别结果

- **检测到的二维码数量**: 3 张
- **招聘/报名链接**: 2 个
  - `http://weixin.qq.com/r/xxx`（来自 img_004.jpg）
  - `http://weixin.qq.com/r/xxx`（来自 img_009.gif）
- **其他链接**: 1 个
  - `https://zhaopin.cnpc.com.cn/`（来自 img_003.jpg）

## 飞书 Base 同步结果

- **状态**: ✅ 写入成功
- **记录 ID**: `recvhtBMKreN0I`
- **字段填充**: 22/22 (100%)
- **Base 链接**: https://rqtvt0xmrql.feishu.cn/base/E9y1bxjHGa9LeGs9q3Tc3J41nmf

## 输出文件

```
~/.hermes/output/{article_id}/
├── article_original.html   # 原始微信HTML（含base64图片，~3-4MB）
├── article.html            # HTML查看器（~4KB，仅标题+图片，无文字）
├── article.md
├── article-ocr.md ✅（已回填结构化总结）
├── metadata.json
├── images/（N 张图片）
└── slices/（如有长图切片）
```
```

### 部分成功情况（字段缺失）

如果部分字段无法提取（标记为 "/"）：

```markdown
## 字段填充统计

| 类型 | 数量 | 状态 |
|------|------|------|
| **基础字段** | 9/9 | ✅ 全部填充 |
| **AI分析字段** | 10/13 | ⚠️ 部分缺失 |
| **总计** | 19/22 | ⚠️ 基本完整 |

### 缺失字段

- ❌ 截止日期：文章中未明确提及
- ❌ 投递方式：未找到具体投递渠道
- ❌ 学历要求：未明确说明
```

### 失败情况处理

如果任一阶段失败，必须明确告知失败环节：

```markdown
## 执行失败

| 阶段 | 状态 | 详情 |
|------|------|------|
| **工具提取** | ❌ 失败 | Camoufox 启动失败 |
| **Hermes 总结** | ⏸️ 跳过 | 依赖阶段1 |
| **飞书 Base 同步** | ⏸️ 跳过 | 依赖阶段2 |

### 错误信息
{具体错误原因}

### 建议
1. 检查网络连接
2. 重新运行完整流程
3. 如问题持续，联系管理员
```