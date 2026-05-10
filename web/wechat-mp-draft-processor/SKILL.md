---
name: wechat-mp-draft-processor
description: >
  微信公众号草稿处理器。对原始提取的文章进行账号化加工处理，
  包括：投递方式隐藏、标题转换、摘要生成、推广模板追加。
  当前支持【行研实习】账号模板。
required_env_vars: []
required_commands:
  - python3
---

# Skill 输入参数

## 必需参数

| 参数名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `article_dir` | string | 原始文章提取目录 | `~/.hermes/output/85c8245b/` |

## 可选参数

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `account` | string | 账号配置名称 | `xingyan_shixi` |
| `keyword` | string | 关键词编号 | 自动生成 `MMdd` |
| `digest` | string | 文章摘要 | 自动提取 |
| `output_dir` | string | 输出目录 | `article_dir/draft/` |

---

# 微信公众号草稿处理器

## 功能概述

将 `wechat-article-extraction-pro` 提取的原始文章，按不同公众号的模板规则进行加工处理，输出可直接供 `wechat-mp-draft-uploader` 上传的草稿文件。

### 核心处理步骤

```
原始提取文章
    ↓
检测文章模式（文字模式 / 长图模式）
    ↓
隐藏投递方式（文本删除 / 图片裁剪）
    ↓
标题转换（添加前缀 + 精简）
    ↓
摘要生成（自动提取 / 手动指定）
    ↓
追加固定推广模板（含关键词编号）
    ↓
输出 draft.html + draft.json
```

## 当前支持账号

| 账号 | 配置文件 | 状态 |
|------|----------|------|
| 行研实习 | `templates/xingyan_shixi.md` | ✅ 可用 |

## 前置条件

### 1. Python 依赖

```bash
pip install Pillow
```

可选（用于更精确的长图 OCR 定位）：
```bash
pip install pytesseract
# 同时需要安装 Tesseract-OCR 引擎
# macOS: brew install tesseract tesseract-lang
# Ubuntu: sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim
```

### 2. 输入来源

脚本读取 `wechat-article-extraction-pro` 提取的目录结构：

```
~/.hermes/output/{article_id}/
├── metadata.json          # 文章元数据
├── article_original.html  # 原始微信 HTML（优先）
├── article.html           # 本地查看 HTML（备选）
├── article.md             # Markdown 格式（降级）
├── article-ocr.md         # OCR 识别结果（长图模式必需）
└── images/                # 图片目录
    ├── img_001.jpg
    └── slices/            # 长图切片（如有）
```

## 使用方式

### 命令行

```bash
# 基本用法
python process_draft.py --article-dir ~/.hermes/output/85c8245b/

# 指定关键词编号
python process_draft.py --article-dir ~/.hermes/output/85c8245b/ --keyword 0427

# 指定摘要
python process_draft.py --article-dir ~/.hermes/output/85c8245b/ --digest "这是一个摘要..."

# 指定输出目录
python process_draft.py --article-dir ~/.hermes/output/85c8245b/ --output-dir /tmp/draft/
```

### Python API

```python
from scripts.process_draft import process_draft

result = process_draft(
    article_dir="~/.hermes/output/85c8245b/",
    account="xingyan_shixi",
    keyword="0427",
)

# 返回结果
{
    "title": "实习｜明湖汇证券 2026暑期实习",
    "digest": "明湖汇证券招聘暑期实习生...",
    "keyword": "0427",
    "author": "行研实习",
    "content_source_url": "https://mp.weixin.qq.com/s/xxx",
    "mode": "long_image",  # 或 "text"
    "original_title": "明湖汇证券魏建榕团队｜2026暑期实习",
    "processed_at": "2026-04-27T16:30:00",
    "account": "xingyan_shixi"
}
```

## 输出文件

### draft.html

处理后的正文 HTML，供上传脚本读取。

内容结构：
```html
<div class="draft-content">
  <!-- 处理后的正文（已隐藏投递方式） -->
  <p>...</p>
  <p><br/></p>
  <p><br/></p>
  <!-- 固定推广模板 -->
  <p><strong>简历投递</strong></p>
  <p>点击名片，回复关键词：<strong>0427</strong> 获取简历投递方式</p>
  ...
</div>
```

### draft.json

处理后的元数据：
```json
{
  "title": "实习｜明湖汇证券 2026暑期实习",
  "digest": "摘要内容...",
  "keyword": "0427",
  "author": "行研实习",
  "content_source_url": "https://mp.weixin.qq.com/s/xxx",
  "mode": "long_image",
  "original_title": "原始标题...",
  "processed_at": "2026-04-27T16:30:00",
  "account": "xingyan_shixi"
}
```

## 处理规则详解

### 1. 文章模式检测

| 模式 | 检测条件 | 处理方式 |
|------|----------|----------|
| **文字模式** | article.md 文字量 >500 字符，无超长图 | 读取 HTML，正则删除投递方式段落 |
| **长图模式** | 有超长图切片，或 article.md 文字量 <300 | OCR 定位投递方式区域，裁剪图片后重新拼接 |

### 2. 投递方式隐藏

#### 文字模式
- 删除以以下关键词开头的段落（含后续内容）：
  - `简历投递`、`投递方式`、`联系方式`、`申请方式`
  - `如何投递`、`邮箱投递`、`如何申请`、`简历发送`、`联系我们`
- 删除包含邮箱地址的段落
- 删除包含手机号的段落

#### 长图模式
1. OCR 识别长图中的"投递方式"区域
2. 定位该区域的 Y 坐标
3. 裁剪掉该区域及以下内容
4. 重新拼接为新的长图

**裁剪策略**：
- 优先使用 pytesseract OCR 精确定位关键词位置
- 若 OCR 不可用，使用启发式规则（保留切片上部 55%）
- **尾部切片丢弃**：当投递关键词出现在最后 1-2 个切片时，直接丢弃从该切片开始的所有尾部切片（更彻底）
- **普通图片处理**：普通图片（非超长图）也检测 OCR 关键词，含"二维码+扫码/即刻"组合的直接丢弃整张图片

**OCR 关键词库**：
`投递方式、简历投递、联系方式、申请方式、如何申请、简历发送、联系我们、招聘流程、扫码申请、即刻扫码、二维码、网申链接、校园招聘官网、招聘官网、投递邮箱、邮箱投递、网申、邮件投递、发送简历、报名链接`

### 3. 标题转换规则

#### 前缀规则
| 原始标题特征 | 添加前缀 |
|-----------|---------|
| 含"量化" | `量化实习 \| ` |
| 含"金融工程"/金融 | `实习｜` |
| 含"行研" | `行研实习 \| ` |
| 含"投行" | `投行实习 \| ` |
| 含"基金" | `基金实习 \| ` |
| 含"证券" | `证券实习 \| ` |
| 其他 | `实习｜` |

#### 精简规则
- 移除年份信息（如"2026"、"2027"）
- 移除过长的团队/公司修饰语
- 保留核心信息：公司/机构名 + 岗位/类型

#### 长度限制
- 最大 64 字符（微信 API 限制）
- 超长时截断并添加"…"

### 4. 关键词编号规则

- **默认格式**：`MMdd`（月日，4位数字）
- 如 4月27日发布 → `0427`
- **冲突解决**：当天已有文章使用该编号时，追加序号 `0427a`、`0427b`
- **手动指定**：通过 `--keyword` 参数覆盖

### 5. 摘要生成规则

1. 从正文中提取前 100-120 字符
2. 移除 HTML 标签和格式标记
3. 确保不被截断在句子中间
4. 支持通过 `--digest` 参数手动覆盖

### 6. 固定推广模板

每个账号有独立的推广模板，行研实习模板包含：
- 关键词回复引导（`回复关键词：{keyword} 获取简历投递方式`）
- 转发提醒
- 暑期实习/校招/秋招信息表推广（含下箭头引导 GIF、信息表推广海报 PNG）
- 订阅引导

推广模板中的图片使用微信素材库永久 URL，上传脚本会自动跳过这些已上传的图片。

## 与上传工作流集成

### 完整流程

```
1. 提取文章
   wechat-article-extraction-pro → /tmp/test_output/{article_id}/
   
2. 复制到上传目录
   cp -r /tmp/test_output/{article_id} ~/.hermes/output/
   
3. 处理草稿（本脚本）
   python process_draft.py --article-dir ~/.hermes/output/{article_id}/
   
4. 上传到草稿箱
   upload_from_feishu.py --article-id {article_id}
   （上传脚本会自动优先读取 draft.html）
```

### 上传脚本适配

`wechat-mp-draft-uploader` 的上传脚本已完全适配 `draft.html`：

```python
# 读取优先级（从高到低）
1. draft/draft.html       ← 处理后的草稿（本脚本输出）
2. article_original.html  ← 微信原始 HTML
3. article.html           ← 本地查看 HTML
4. article.md             ← Markdown
```

**自动读取 draft.json 元数据**：上传脚本会自动读取 `draft/draft.json`，获取处理后的标题、摘要、作者、关键词，无需手动重新设置。

**draft 子目录图片路径适配**：当使用 `draft/draft.html` 时，上传脚本会自动将图片查找路径调整为 `article_dir/draft/`，确保能正确找到处理后的图片文件。

## 账号模板配置

### 添加新账号模板

1. 在 `templates/` 下创建新的 `.md` 配置文件
2. 参考 `xingyan_shixi.md` 的结构定义规则
3. 在 `process_draft.py` 中添加对应的配置类

### 模板配置结构

```markdown
# 【账号名】账号草稿处理配置

## 标题转换规则
### 前缀规则
| 原始标题特征 | 添加前缀 |
### 精简规则
### 长度限制

## 投递方式隐藏规则
### 文字模式处理
### 长图模式处理
### OCR 定位关键词

## 固定推广模板
```html
<p>...</p>
```
### 占位符
- `{keyword}`: 文章关键词编号

## 关键词编号规则
## 摘要生成规则
## 作者字段
```

## 推广图片素材管理

推广模板中的图片（如下箭头引导GIF、信息表推广图等）需预先上传至公众号素材库，获取 `mediaId` 后嵌入模板。支持从参考文章自动提取并上传。

### 从参考文章提取推广图片

当用户发送一篇包含完整推广模板的文章链接并要求提取推广图片时，按以下步骤执行：

```
1. 使用 wechat-article-extraction-pro 提取文章
2. 遍历文章中的图片（img_001, img_002...）
3. 使用 vision_analyze 识别每张图片的内容和用途
4. 分类：正文图片 vs 推广/引导图片
5. 对推广图片执行上传
```

### 图片分类标准

| 类型 | 特征 | 处理方式 |
|------|------|----------|
| **正文图片** | 包含公司Logo、招聘信息、岗位详情、人物照片 | 跳过不上传 |
| **推广图片** | 下箭头引导GIF、信息表推广海报、订阅引导图、二维码 | 上传至素材库 |
| **装饰图片** | 极简线条、透明背景、无信息内容 | 跳过不上传 |
| **按钮/引导** | "点击名片"、"关注我们"等引导元素 | 视情况上传 |

### 行研实习账号推广图片素材

当前已上传的素材（存储于 `promotion_media_ids.json`）：

| 用途 | mediaId | 格式 |
|------|---------|------|
| 下箭头引导 | `p140FBsh29-3c3Z6VFHCCGcCHZ4p-TEHPVz1InHSLl_LjMvfj1krD5xiAI7BO58n` | GIF |
| 信息表推广图 | `p140FBsh29-3c3Z6VFHCCDgL1kfxsdkcV7G3uFdq47L13XqQVSlM5GQnwDEmr1se` | PNG |

> **注意**：推广模板通常需要 3 张固定图片（下箭头引导、关键词回复引导、信息表推广图），但不同文章可能只包含其中部分图片。缺失的图片需要从其他参考文章补充，或使用纯文字替代。

### 3. WEBP 格式陷阱（关键！）

微信文章中的图片文件**扩展名不可信**。经常出现 `.png` 或 `.jpg` 扩展名但实际格式为 WEBP 的情况，会导致上传 API 返回 `unsupported file type` 错误。

**检测方法**：读取文件头 magic bytes

```python
with open(filepath, 'rb') as f:
    header = f.read(16)
    
if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
    print("实际格式: WEBP")
    # 需要转换
```

**转换方法**：

```python
from PIL import Image

img = Image.open(webp_path)
if img.mode in ('RGBA', 'P'):
    img = img.convert('RGB')
img.save(png_path, 'PNG')
```

**前置依赖**：
```bash
python3 -m pip install pillow
```

### 4. mediaId 字段名注意

简立制作 API 返回的素材 ID 字段名为 `mediaId`（驼峰），不是 `media_id`（下划线）。

```python
# ✅ 正确
media_id = result['data']['mediaId']

# ❌ 错误
media_id = result['data']['media_id']  # KeyError
```

---

## 注意事项与踩坑记录

### 1. Unicode 竖线 `｜` 陷阱（关键！）
微信公众号标题中的竖线分隔符是 **全角竖线 `｜`（U+FF5C）**，不是 ASCII 的 `|`（U+007C）。正则匹配标题时必须使用 `[\uff5c|]` 同时兼容两者，否则会匹配失败。

```python
# ❌ 错误：只匹配 ASCII |
r"\|\s*..."

# ✅ 正确：同时匹配全角｜和 ASCII |
r"[\uff5c|]\s*..."
```

### 2. BeautifulSoup 遍历策略
删除投递方式段落时，**不要对所有块元素做 find_parent/find_next_sibling**，这会导致死循环或误删父容器。正确策略：
- 只遍历"叶级"块元素（没有子块元素的 `p`, `div`, `section`）
- 或使用 `recursive=False` 控制遍历深度

### 3. 长图处理精度
- 长图模式的裁剪依赖 OCR 定位，精度取决于图片质量
- 如果 OCR 定位失败，会使用启发式规则（保留 60%）
- 建议处理后在本地检查 draft.html 中的图片效果

### 4. 推广模板图片管理
- 推广模板中的图片使用微信素材库永久 URL，不会被重复上传
- 模板内已内嵌 2 张图片（下箭头引导 GIF、信息表推广海报 PNG）
- 若需更换图片，修改 `XingyanShixiConfig.PROMOTION_TEMPLATE` 中的 `<img>` 标签 src 属性

### 5. 关键词编号冲突
- 同一天多篇文章时可能产生编号冲突
- 上传前检查 `draft.json` 中的关键词，必要时手动调整

### 6. 摘要质量
- 自动提取的摘要可能不够精准
- 重要文章建议手动指定 `--digest` 参数

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-04-27 | 初始版本，支持行研实习账号模板，包含文字模式/长图模式处理、标题转换、摘要生成、推广模板追加 |
| v1.1 | 2026-04-27 | 完成长图模式真实文章测试、推广模板内嵌微信图片 URL、与上传脚本完成集成测试（draft.html 读取优先级 + draft/ 子目录图片路径适配） |
| v1.2 | 2026-05-09 | 修复回归测试脚本路径错误，新增回归测试文档；发现投递方式移除、模板交叉污染、长图重叠检查公式等 11 项待修复问题 |
| v1.26 | 2026-05-10 | 修复投递方式检测遗漏：① 扩展 OCR 关键词库（+12个）② 普通图片也检测投递关键词，含"二维码+扫码/即刻"组合的直接丢弃 ③ 长图尾部切片含关键词时直接丢弃从该切片开始的所有尾部切片（而非仅裁剪单个切片）④ 启发式裁剪比例从 60% 改为 55% |

---

## 回归测试

### 执行脚本

```bash
cd ~/.hermes/skills/web/wechat-mp-draft-processor/scripts
python3 regression_test.py [--force-extract]
```

报告输出：`/tmp/wechat_draft_regression_report.json`

### 测试覆盖

| 用例 | 文章类型 | 期望模式 | 验证点 |
|------|----------|----------|--------|
| pure_image_with_qr | 纯图片+二维码 | long_image | 推广模板、重叠检查 |
| gif_pure_image_delivery | GIF+长图混合 | long_image | 推广模板、重叠检查 |
| mixed_image_delivery | 图文混合 | text | 模式检测、重叠检查 |
| text_delivery_content | 纯文字 | text | 投递方式移除、推广模板交叉污染 |

### 已修复的脚本问题（2026-05-09）

`regression_test.py` 原版本存在 3 处路径错误，已修复：

1. `process_script` 原指向脚本自身 → 修正为 `scripts_dir / "process_draft.py"`
2. `extract_main` 路径多了 `web/` 层级 → 移除
3. `repo_root` 计算 `parents[2]` 导致指向 `skills/` → 修正为 `parents[1]`

### 已知待修复问题

执行回归测试后发现的 11 项失败：

1. **文字模式投递方式未完全移除**（2 项）：`text_delivery_content` 中 "投递方式"、"简历投递" 关键词仍残留于正文
2. **推广模板交叉污染**（1 项）：Joblinker 账号模板混入了 "行研实习"（xingyan_shixi 的标记）
3. **模式检测偏差**（2 项）：`mixed_image_delivery` 被检测为 `long_image`，但期望为 `text`
4. **长图重叠检查公式不适用**（6 项）：硬编码 `expected = original - 100 * (slices - 1)` 与实际裁剪逻辑不匹配（未裁剪时高度不变，裁剪投递区时裁剪量远大于 100px）。需 redesign 检查逻辑，改为验证视觉无重复而非高度公式。
