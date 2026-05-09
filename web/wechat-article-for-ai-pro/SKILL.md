---
name: wechat-article-for-ai-pro
description: >
  微信公众号文章提取 Pro 版完整执行流程。
  基于 wechat-article-for-ai 增强，实现7文件/目录输出（article_original.html原始HTML + article.html精简上传版 + article_viewer.html查看器 + Markdown + OCR + JSON + images/ + slices/）+ RapidOCR 识别 + Hermes 总结填回 + 飞书 Base 同步。
  【全自动执行模式】用户只需发送微信文章链接，单次对话内自动完成：工具提取 → AI分析 → Base同步（23字段），无需任何确认。
---

# 微信公众号文章提取 Pro 版 - 全自动执行

> **🚀 使用方式**：直接发送微信文章链接，我将**自动执行完整流程**，无需确认。
>
> **⚠️ 工具维护提醒**：如果 `~/.hermes/skills/web/wechat-article-for-ai-pro/` 目录为空或损坏，请重新克隆：
> ```bash
> cd ~/.hermes/skills/web && rm -rf wechat-article-for-ai-pro && git clone https://github.com/liuxiaoan8998/wechat-article-for-ai-pro.git
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
│  5. 二维码识别（pyzbar + OpenCV fallback）                   │
│  6. 生成 8 位 UUID 作为文章ID（如 fa70b413）               │
│  7. 保存 article_original.html（原始微信HTML，~3-4MB）      │
│  8. 生成 article.html（精简上传版，~17KB，提取 js_content） │
│  9. 输出到 ~/.hermes/output/{article_id}/                   │
│     （确保上传脚本可正确查找本地目录）                       │
│                                                             │
│  阶段 2：AI 分析（自动执行）                                │
│  ─────────────────────────────                              │
│  1. 读取 OCR 内容，提取关键信息                              │
│  2. 分析 13 个 AI 字段（行业/岗位/地点/亮点等）             │
│  3. 生成结构化总结                                           │
│                                                             │
│  阶段 3：飞书 Base 同步（自动执行）                          │
│  ─────────────────────────────                              │
│  1. Base 查重：检查文章链接是否已存在                        │
│  2. 构建 23 个字段的完整记录                                │
│  3. 字段完整性校验（缺失填 "/"）                            │
│  4. 同步到飞书 Base                                          │
│  5. 返回执行结果                                             │
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
| 二维码识别 | pyzbar（首选）+ OpenCV QRCodeDetector（fallback） |
| 图片处理 | Pillow |
| 输出格式 | Markdown + HTML + JSON |

## 关键修复（v2.0+）

| 问题 | 修复 |
|------|------|
| RapidOCR 返回坐标而非文字 | 修正结果解析：`item[1]` 才是文字内容（格式是 `[[box, text, confidence], ...]`） |
| RGBA 图片保存失败 | 切片前自动转换为 RGB 模式 |
| **API返回URL格式不兼容** | **修复 `validate_url()` 支持两种格式**：<br>• `/s/xxx` 标准路径格式<br>• `/s?__biz=xxx` 查询参数格式（极致了API返回） |
| **发布时间字段遗漏** | **修复同步流程**：`record_data` 必须包含 `published_at` 字段，不能遗漏 |
| **空字段标记** | **统一规范**：信息未获取的字段必须填充 `"/"`，不能留空 |
| **原始HTML过大** | **内置精简HTML**：`formatter.py` 自动生成 `article.html`（~17KB），提取 `js_content` 并清理冗余属性，避免上传超时/413错误 |
| **缺少原始HTML** | **新增 `save_original_html()`**：保存完整微信HTML到 `article_original.html`，用于恢复和重提取 |
| **缺少article_id** | **新增 `generate_article_id()`**：metadata.json 包含8位UUID，用于Base同步和目录查找 |
| **Hermes output未自动复制** | **新增自动复制**：提取完成后自动 `shutil.copytree` 到 `~/.hermes/output/{article_id}/` |

### URL格式兼容性修复

**问题**：极致了API返回的URL格式为 `https://mp.weixin.qq.com/s?__biz=xxx&mid=xxx`（查询参数格式），而原 `validate_url()` 只支持 `/s/xxx` 路径格式，导致提取失败。

**修复代码**（`wechat_to_md/cli.py`）：

```python
def validate_url(url: str) -> bool:
    """Check that URL is a WeChat article URL.

    Supports two formats:
        - https://mp.weixin.qq.com/s/XXXXX
        - https://mp.weixin.qq.com/s?__biz=xxx&mid=xxx...
    """
    if url.startswith("https://mp.weixin.qq.com/s/"):
        return True
    if re.match(r"https://mp\.weixin\.qq\.com/s\?[a-zA-Z0-9_]+", url):
        return True
    return False
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
    f'cd ~/.hermes/skills/web/wechat-article-for-ai-pro && /usr/bin/python3 main.py "{url}" -o {output_base} -v',
    shell=True, capture_output=True, text=True, timeout=300
)

if result.returncode != 0:
    raise Exception(f"工具提取失败: {result.stderr}")

# 获取输出目录
import glob
from pathlib import Path

tmp_dirs = glob.glob(f"{output_base}/*")
if tmp_dirs:
    article_dir = tmp_dirs[0]
    # 读取 metadata.json 获取 article_id
    metadata_path = Path(article_dir) / "metadata.json"
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    article_id = metadata.get('article_id', '')
    
    # 工具已自动复制到 ~/.hermes/output/{article_id}/
    # 但为确保，再次确认
    hermes_output = Path.home() / ".hermes" / "output" / article_id
    if not hermes_output.exists():
        shutil.copytree(article_dir, hermes_output)
    print(f"✅ 已复制到: {hermes_output}")
else:
    raise Exception("未找到工具提取的输出目录")

# ============================================================
# 阶段 2：Base 查重（自动执行）
# ============================================================

import subprocess, json

base_token = "E9y1bxjHGa9LeGs9q3Tc3J41nmf"
table_id = "tblYIqHtHrWUlVnP"

# 拉取全部记录进行查重
cmd = f'lark-cli base +record-list --base-token {base_token} --table-id {table_id} --as bot'
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

if result.returncode == 0:
    response = json.loads(result.stdout)
    if response.get('ok'):
        records = response['data']['items']
        existing = {}
        for r in records:
            fields = r.get('fields', {})
            existing_url = fields.get('文章链接', '')
            if existing_url:
                existing[existing_url] = {
                    'record_id': r['record_id'],
                    'article_id': fields.get('文章ID', ''),
                    'title': fields.get('文章标题', ''),
                    'status': fields.get('文章状态', '')
                }

# 查重判断
target_url = metadata.get('url', '')
if target_url in existing:
    dup = existing[target_url]
    print(f"⚠️ 文章已存在于Base中！跳过创建。")
    print(f"   记录ID: {dup['record_id']}, 文章ID: {dup['article_id']}")
    # 清理本次提取的输出目录
    shutil.rmtree(article_dir, ignore_errors=True)
    shutil.rmtree(hermes_output, ignore_errors=True)
    # 结束流程
else:
    # 继续阶段 3
    pass

# ============================================================
# 阶段 3：Hermes 总结（AI 自动处理）
# ============================================================

# 1. 读取 article-ocr.md
# 2. AI 分析 OCR + 二维码内容
# 3. 生成结构化总结（行业、岗位类型、工作地点等13个AI字段）
# 4. 回填到 article-ocr.md 第四部分
# 5. 同步到 ~/.hermes/output/

# ============================================================
# 阶段 4：飞书 Base 同步（完整23字段）
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
        print(f"📊 字段填充: {21-len(missing)}/21")
    else:
        print(f"❌ 同步失败: {response.get('error')}")
```

### 简化执行命令

#### 1. 工具提取

```bash
cd ~/.hermes/skills/web/wechat-article-for-ai-pro
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

# 回填到第四部分
patch: path/to/article-ocr.md
  old_string: "## 四、完整文字内容（原文 + OCR + 二维码）\n\n*待 OCR 完成后自动更新*"
  new_string: "## 四、完整文字内容（原文 + OCR + 二维码）\n\n### 公司概况\n..."

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
├── article.html            # 精简上传版（提取 js_content，~17KB，用于公众号草稿上传）
├── article_viewer.html     # HTML 查看器（formatter.py 生成，~4KB，仅标题+图片，供人阅读）
├── article.md              # 基础 Markdown（含正文文字）
├── article-ocr.md          # OCR 结果 + 二维码 + 总结 ✅
├── metadata.json           # 元数据（含 article_id、url、title 等）
├── images/                 # 原始图片
└── slices/                 # 长图切片（如有）
```

**文件说明**：
- `article_original.html`: 原始抓取的微信HTML，包含完整的 `<html>`, `<head>`, `<body>` 结构和base64编码的图片，保留原文章的所有样式。用于恢复、重提取和调试。
- `article.html`: **精简上传版**，从原始HTML中提取 `js_content` 并清理冗余属性后生成，~17KB。这是公众号草稿上传应使用的HTML源。
- `article_viewer.html`: 图片查看器，仅包含标题、图片、二维码/小程序码，**不含文章正文文字**，供人阅读。
- `article.md`: 含有文章正文文字，是 Markdown 格式的内容来源。
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
| v1.7 | **新增二维码识别**：pyzbar + OpenCV fallback |
| v1.7.1 | **第四章整合二维码信息**：完整文字内容（原文+OCR+二维码） |
| v1.7.2 | **集成 zbar-py**：识别能力更强 |
| v2.0 | **内置精简HTML**：formatter.py 自动生成 article.html（~17KB） |
| v2.0.1 | **新增 article_original.html 保存**：保留完整原始HTML |
| v2.0.2 | **新增 article_id**：metadata.json 包含8位UUID |
| v2.0.3 | **新增 URL 兼容性**：支持 `/s?__biz=` 查询参数格式 |
| v2.0.4 | **新增自动复制**：提取完成后自动复制到 `~/.hermes/output/{article_id}/` |

---

# 历史开发记录（参考）

## 项目架构

```
wechat-article-for-ai-pro/
├── main.py                 # 入口
├── requirements.txt        # 依赖
├── README.md              # 中文文档
├── SKILL.md               # Hermes Skill 规范（本文件）
├── wechat_to_md/          # 核心模块
│   ├── cli.py            # 命令行接口
│   ├── scraper.py        # Camoufox 抓取
│   ├── parser.py         # 内容解析
│   ├── converter.py      # Markdown 转换
│   ├── downloader.py     # 图片下载
│   ├── formatter.py      # 标准化输出（7文件：原始HTML+精简HTML+查看器+md+json+ocr+images+slices）
│   ├── ocr_adapter.py    # OCR 适配器 ⭐
│   ├── ocr_processor.py  # OCR 处理模块
│   ├── qr_detector.py    # 二维码识别
│   └── utils.py          # 工具函数
└── ...
```

## 关键技术决策

### 为什么不用 PaddleOCR？
- 安装复杂，依赖多
- 环境兼容性问题
- 改用 RapidOCR + AI Vision，无需复杂本地安装

### 二维码识别方案（v1.7+）

**引擎选择**：
- **首选**：pyzbar（识别能力最强，支持复杂背景）
- **备选**：OpenCV QRCodeDetector（无需额外依赖）

**安装 pyzbar**：
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
    f'cd ~/.hermes/skills/web/wechat-article-for-ai-pro && /usr/bin/python3 main.py "{url}" -o {output_base} -v',
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
# 1. 从 GitHub 恢复 Python 项目
cd ~/.hermes/skills/web
rm -rf wechat-article-for-ai-pro
git clone https://github.com/liuxiaoan8998/wechat-article-for-ai-pro.git

# 2. 运行安装脚本
bash ~/.hermes/skills/web/wechat-article-for-ai-pro/scripts/setup.sh
```

### 双仓库管理策略

| 仓库 | 地址 | 用途 | 更新时机 |
|------|------|------|----------|
| Python 源码 | `wechat-article-for-ai-pro` | 核心提取工具 | 功能迭代 |
| Hermes Skill | `wechat-article-for-ai-pro`（内含 SKILL.md） | 调用指南和脚本 | 流程优化 |

**为什么合并？**
- Python 项目：关注功能实现（OCR、下载、解析）
- Skill 规范：关注调用流程（参数、步骤、示例）
- 同一代码仓库管理，避免版本不一致

### 版本控制工作流

**Python 源码 + Skill 更新：**
```bash
cd ~/.hermes/skills/web/wechat-article-for-ai-pro
git add .
git commit -m "v2.0.x: 描述"
git push origin main
```

### 快速诊断命令

```bash
# 检查 Skill 是否存在
ls ~/.hermes/skills/web/wechat-article-for-ai-pro/

# 检查 Git 状态
cd ~/.hermes/skills/web/wechat-article-for-ai-pro && git status

# 查看技能列表
hermes skills list web
```

---

## v2.1 新增：飞书多维表格集成（内容管理）

### 功能概述
将提取的公众号文章自动同步到飞书多维表格，支持选题管理和二创工作流。

### 完整流程图（v3.0）

```
用户提供 URL
    ↓
┌─────────────────────────────────────────────────────────┐
│  阶段 1：工具提取（本地执行）                              │
│  1. 启动 Camoufox 浏览器访问文章                          │
│  2. 提取标题、作者、正文内容                               │
│  3. OCR 识别（RapidOCR）                                  │
│  4. 二维码识别（pyzbar）                                  │
│  5. 生成 7 文件输出                                        │
│  6. 自动复制到 ~/.hermes/output/{article_id}/             │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│  阶段 2：Base 查重                                        │
│  1. 拉取全部 Base 记录                                    │
│  2. 匹配文章链接                                          │
│  3. 重复则跳过，清理输出目录                               │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│  阶段 3：Hermes 总结（AI 处理）                           │
│  1. 读取 article-ocr.md 的 OCR 内容                      │
│  2. 结构化分析并生成总结                                   │
│  3. 回填到 article-ocr.md 第四部分                        │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│  阶段 4：飞书 Base 同步（内容管理）                        │
│  1. 提取关键字段（标题、公众号、投递方式等）                │
│  2. 字段完整性校验（缺失填 "/"）                          │
│  3. 调用 Lark CLI 录入多维表格                             │
│  4. 标记状态为"待选题"                                     │
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
| 文章ID | 文本 | 8位UUID，用于查找本地目录 |
| 行业/领域 | 单选 | 互联网/金融/能源/传媒等 |
| 岗位类型 | 单选 | 实习/校招/社招/兼职 |
| 工作地点 | 单选 | 城市列表 |
| 学历要求 | 单选 | 本科/硕士/博士/不限 |
| 截止日期 | 日期 | 招聘截止 |
| 优先级 | 单选 | 高/中/低 |
| 文章状态 | 单选 | 待选题/已选题/撰写中/已二创/已发布 |
| 文章来源 | 单选 | 链接/原创/转载 |
| 适配账号 | 多选 | Joblinker/研究生求职圈/行研实习 |
| 标签 | 多选 | 热门/急招/大厂/国企/外企/可内推 |
| 原文亮点 | 文本 | 招聘信息亮点总结 |
| 选题方向 | 文本 | 二创选题建议 |
| 采集时间 | 数字 | 数据录入时间戳 |

### Base 查重机制（v3.0.12）

**问题**：用户可能多次发送相同的微信文章链接，导致Base中出现重复记录。

**解决方案**：`lark-cli base +record-search` API 需要 `keyword` + `search_fields` 参数，不适用于精确链接查重。改用 `record-list` 全量拉取+本地匹配：

```python
import subprocess, json

base_token = "YOUR_BASE_TOKEN"
table_id = "YOUR_TABLE_ID"

# 1. 拉取全部记录
cmd = f'lark-cli base +record-list --base-token {base_token} --table-id {table_id} --as bot'
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

# 2. 解析响应，构建链接映射
if result.returncode == 0:
    response = json.loads(result.stdout)
    if response.get('ok'):
        records = response['data']['items']
        existing = {}
        for r in records:
            fields = r.get('fields', {})
            url = fields.get('文章链接', '')
            if url:
                existing[url] = {
                    'record_id': r['record_id'],
                    'article_id': fields.get('文章ID', ''),
                    'title': fields.get('文章标题', ''),
                    'status': fields.get('文章状态', '')
                }

# 3. 查重判断
target_url = metadata.get('url', '')
if target_url in existing:
    dup = existing[target_url]
    print(f"⚠️ 文章已存在于Base中！")
    print(f"   记录ID: {dup['record_id']}")
    print(f"   文章ID: {dup['article_id']}")
    print(f"   状态: {dup['status']}")
    # 跳过创建，结束流程
```

**处理逻辑**：
- 发现重复 → 保留原始记录，不创建新记录
- 清理本次提取产生的输出目录，避免占用磁盘空间
- 最终报告中显示重复检测结果

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
  }' \
  --as bot
```

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
        article_dir: 文章输出目录路径（如 ~/.hermes/output/{article_id}/）
        
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
    
    # 3. 准备基础数据
    base_token = "E9y1bxjHGa9LeGs9q3Tc3J41nmf"
    table_id = "tblYIqHtHrWUlVnP"
    
    # 格式化发布时间
    published_at = metadata.get('published_at', '')
    if published_at:
        try:
            dt = datetime.strptime(published_at, "%Y-%m-%d %H:%M:%S")
            formatted_date = dt.strftime("%Y/%m/%d")
        except:
            formatted_date = published_at
    else:
        formatted_date = "/"
    
    # 4. 构建完整记录数据
    record_data = {
        "文章标题": metadata.get('title', ''),
        "公众号": metadata.get('author', ''),
        "发布时间": formatted_date,
        "文章链接": metadata.get('url', ''),
        "文章ID": metadata.get('article_id', ''),
        
        "行业": analyze_industry(ocr_content),
        "领域": analyze_field(ocr_content),
        "岗位类型": analyze_job_types(ocr_content),
        "工作地点": analyze_location(ocr_content),
        "学历要求": analyze_education(ocr_content),
        "截止日期": analyze_deadline(ocr_content),
        "投递方式": analyze_apply_method(ocr_content),
        "原文亮点": analyze_highlights(ocr_content),
        "文章概要": generate_summary(ocr_content),
        "选题方向": determine_topic_direction(ocr_content),
        
        "文章状态": "待选题",
        "文章来源": "链接",
        "适配账号": match_accounts(ocr_content),
        "优先级": "中",
        "标签": analyze_tags(ocr_content),
        "采集时间": int(datetime.now().timestamp() * 1000),
    }
    
    # 5. 检查必填字段
    required_fields = ['文章标题', '公众号', '发布时间', '文章链接', '文章ID']
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
            f'--record-id {record_id} '
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
```

**常见更新场景**：
1. **补充缺失字段**：初次同步时某些字段未填写，后续补充
2. **修正错误数据**：发现同步的数据有误，需要更正
3. **更新状态**：如从"待选题"更新为"已选题"
4. **添加标签**：为文章添加或修改标签

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
}
EOF

# 执行同步
lark-cli base +record-upsert \
  --base-token "E9y1bxjHGa9LeGs9q3Tc3J41nmf" \
  --table-id "tblYIqHtHrWUlVnP" \
  --json @data.json \
  --as bot

# 清理临时文件
rm data.json
```

### 工作流建议

**二创管理流程：**
1. **待选题** → 新提取的文章默认状态
2. **已选题** → 编辑确认要二创的文章
3. **撰写中** → 正在撰写二创内容
4. **已二创** → 二创完成，待发布
5. **已发布** → 已发布到目标平台

**筛选视图：**
- 按行业筛选（金融/能源/传媒）
- 按岗位类型筛选（实习/校招/社招）
- 按状态筛选（待选题/已选题/已发布）
- 按优先级筛选（高/中/低）

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

**解决方案**：使用 `article_id`（8位UUID）作为目录名，从 `metadata.json` 中读取：

```python
# 推荐：使用 article_id 查找目录
article_id = metadata.get('article_id', '')
article_dir = Path.home() / ".hermes" / "output" / article_id

# 或者从 ~/.hermes/output/ 下遍历查找
import json
from pathlib import Path

def find_article_dir_by_id(target_id: str):
    """通过 article_id 查找文章目录"""
    output_dir = Path.home() / ".hermes" / "output"
    for subdir in output_dir.iterdir():
        if subdir.is_dir():
            metadata_path = subdir / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data.get('article_id') == target_id:
                    return subdir
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

### 4. 空字段填充规则

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

### 5. 上下文压缩处理

**问题**：对话达到358轮时，上下文被压缩，导致"失忆"

**解决方案**：
1. **Memory存储**：关键配置写入长期Memory（飞书Base Token、字段格式规则）
2. **标记文件**：创建 `~/.hermes/.wechat_workflow_state` 保存任务状态
3. **定期提醒**：每50轮对话主动提醒保存进度

**用户指令**：
- "保存当前进度" → 立即更新标记文件
- "查看状态" → 读取标记文件汇报

### 6. 精简 HTML 生成（v2.0 新增）

**问题**：`article_original.html` 达 3-5MB，含微信 JS SDK、base64 图片预览、未使用 CSS，导致上传超时/413错误。

**解决方案**：`formatter.py` 内置 `create_upload_html()`，使用正则提取 `js_content`：

```python
import re

# 从原始HTML中提取 js_content
match = re.search(
    r'<div[^>]*id=["\']js_content["\'][^>]*>(.*?)</div>\s*(?:</div>\s*)?<script',
    html_raw, re.DOTALL
)

if match:
    content_html = match.group(1)
    # 清理冗余属性
    content_html = re.sub(r'style=["\'][^"\']*["\']', '', content_html)
    content_html = re.sub(r'class=["\'][^"\']*["\']', '', content_html)

# 构建精简HTML（~17KB）
clean_html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
img{{max-width:100%;height:auto;display:block;margin:10px 0}}
p{{margin:8px 0;line-height:1.6}}
body{{font-family:-apple-system,BlinkMacSystemFont,sans-serif;padding:16px}}
strong{{font-weight:bold}}
</style></head>
<body><div id="js_content">{content_html}</div></body></html>"""
```

**效果**：文件大小从 ~3.7MB 降至 ~17KB，上传成功率从 0% 提升至 100%。

### 7. 长图OCR自动处理（v3.0.12）

**问题**：超长图文章（如 1080x14232）需要多次OCR识别，手动处理效率低。

**解决方案**：工具已自动处理：

1. **自动切片**：检测图片高度 > 2000px 时自动切片为多段
2. **自动OCR**：每个切片调用 RapidOCR 识别
3. **自动回填**：OCR 结果回填至 `article-ocr.md` 的 `[段N]` 标记中

**AI分析阶段**：AI 分析时直接读取 `article-ocr.md` 中的 OCR 结果，无需额外调用 `vision_analyze`。

---

## 微信公众号草稿验证（v3.0.6 新增）

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
    
    # 统计图片数量
    image_count = content.count("<img")
    
    # 提取内容预览（前500字符）
    import re
    text_only = re.sub(r'<[^>]+>', '', content)
    preview = text_only[:500]
    
    return {
        "success": True,
        "content_length": len(content),
        "image_count": image_count,
        "content_preview": preview,
        "title": draft.get("title", ""),
        "author": draft.get("author", ""),
        "digest": draft.get("digest", "")
    }
```

**诊断清单**：
- content_length < 1000：可能内容未正确上传
- image_count = 0：图片未上传成功
- content_preview 不包含正文关键词：HTML 结构可能有问题

---

*最后更新: 2026-05-06*
