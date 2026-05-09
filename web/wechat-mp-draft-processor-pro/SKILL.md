---
name: wechat-mp-draft-processor-pro
description: >
  微信公众号草稿处理器 Pro：多步骤精准清洗原始HTML，生成可上传草稿箱的文章HTML。
  支持多账号推广模板自动追加。从 article_original.html 出发，通过去除尾部噪音、头部噪音、
  追加账号推广模板等步骤，生成带有元数据的完整草稿。
tags: [wechat, mp, draft, processor, html, cleanup]
---

# 微信公众号草稿处理器 Pro

## 概述

该 Skill 提供一套多步骤流水线，将 `wechat-article-extraction-pro` 提取的 `article_original.html` 进行精准清洗，生成可以直接上传到微信公众号草稿箱的完整草稿（HTML + 元数据）。

支持多账号推广模板，可根据不同公众号账号自动追加对应的尾部推广内容。

## 存储结构

每篇文章的工作目录：`~/.hermes/output/{article_id}/`

- `article_original.html` — 输入，原始微信HTML（含大量噪音），**永不修改**
- `images/img_*.png` — 输入，提取工具下载的原始图片
- `draft/draft.html` — 输出，清洗后的可上传HTML（含推广模板）
- `draft/draft.json` — 输出，草稿元数据（标题、摘要、关键词、作者、原文链接等）
- `draft/images/img_*.png` — 输出，处理后的图片（本地路径引用）
- `draft/images/delivery/img_*_delivery.png` — 输出，裁剪掉的投递方式部分
- `draft/image_map.json` — 输出，图片处理映射表（记录每张图片的处理决策）

> **设计原则**：`article_original.html` 是只读源文件，所有清洗步骤的输入都从这里开始，输出统一写到 `draft/draft.html`。这样 `uploader` 可以稳定地只读取 `draft/draft.html`和 `draft/draft.json`，无需猜测哪个中间文件是最新的。

## 流水线步骤

  步骤1: 删除尾部噪音（"预览时标签不可点"之后的所有内容）
  步骤2: 删除头部噪音（activity-name、meta_content、js_novel_card）
  步骤2.5: 图片智能处理（识别并移除/裁剪投递方式图片，重写HTML图片引用为本地路径）
  步骤3: 追加账号推广模板（根据 --account 参数）
  步骤5: 智能摘要生成（基于标题和OCR提取招聘类信息的结构化摘要）
  步骤6: 标题转换（根据文章类型添加前缀、清理冗余词）

## 统一入口（推荐）

一键执行完整清洗流水线：

```bash
python3 scripts/process.py <article_id>
# 例如：
python3 scripts/process.py e3e9eabf
```

可选参数：
- `--step 1` — 只执行步骤1
- `--steps 1,2` — 执行步骤1+2
- `--steps 1,2,3,5,6` — 执行完整流程（默认）
- `--account xingyan_shixi` — 指定行研实习账号配置
- `--account joblinker` — 指定 Joblinker 账号配置
- `--keyword 0429` — 手动指定关键词（默认自动生成 MMdd）

## 单独步骤说明

### 步骤1: 清理尾部噪音

**目的**：删除文章正文之后的所有无用内容。

**位置**: `scripts/step1_clean_noise.py`

**逻辑**:
1. 查找噪音分界标记 `"预览时标签不可点"`
2. 若找到，删除从该标记开始到文件末尾的所有内容
3. 若未找到，保留原文件内容（某些文章没有底部标签区，标记不存在是正常情况）
4. 保证清理后HTML结构完整（补上 `</body></html>`）
5. 输出写入 `draft/draft.html`（不修改 `article_original.html`）

**用法**:
```bash
python3 scripts/step1_clean_noise.py <article_id>
```

**输入/输出**:
- 输入: `~/.hermes/output/{article_id}/article_original.html`
- 输出: `~/.hermes/output/{article_id}/draft/draft.html`

**重要发现** ⚠️:
- **不是所有文章都有这个标记**！测试发现，部分文章（如 `e3e9eabf`）没有底部标签区，因此不含该标记。
- 当标记存在时，可以有效删除 2MB+ 的尾部噪音（脚本、模态框、视频播放器等）。
- 脚本在未找到标记时不会报错，而是记录警告并将原文件写入输出路径。

### 步骤2: 清理头部噪音

**目的**：删除文章正文之前的所有无用内容。

**位置**: `scripts/step2_clean_header_noise.py`

**逻辑**:
1. 解析 HTML 为 DOM 树（使用 BeautifulSoup）
2. 定位 `img-content` 容器，找出其内部的 `js_content`（正文区域）
3. 删除位于 `js_content` 之前的所有头部噪音元素：
   - `<h1 id="activity-name" class="rich_media_title">` — 文章标题区
   - `<div id="meta_content" class="rich_media_meta_list">` — 元信息区（发布时间、IP属地等）
   - `<div id="js_novel_card" class="novel-card">` — 小说推荐卡片
4. 保留 `js_content` 之后的所有内容（如底部脚本）
5. 输出写入 `draft/draft.html`

**输入优先级**:
- 优先读取 `draft/draft.html`（步骤1的输出，如果存在）
- 若不存在，回退到 `article_original.html`

**用法**:
```bash
python3 scripts/step2_clean_header_noise.py <article_id>
```

**输入/输出**:
- 输入: `~/.hermes/output/{article_id}/draft/draft.html`（如果存在）或 `article_original.html`
- 输出: `~/.hermes/output/{article_id}/draft/draft.html`

**实现细节**:
- 通过 DOM 父子关系判断元素位置，不依赖字符串匹配
- 仅删除在 `img-content` 内且在 `js_content` 之前的元素
- 输出使用 `prettify()` 格式化，文件大小可能因缩进而略有增加

**测试验证** ✅:
- `4192e361`: 成功删除 3 个头部噪音元素
- `e3e9eabf`: 成功删除 3 个头部噪音元素
- 清洗后 `img-content` 子元素仅剩 `['div', 'script']`（`div` 即为 `js_content`）

### 步骤2.5: 图片智能处理

**目的**：识别并处理正文图片（移除/裁剪投递方式图片），重写 HTML 图片引用为本地路径。

**位置**: `scripts/step2_5_process_images.py`

**逻辑**:
1. 调用 `image-processor` 对文章图片进行 OCR 分析
2. 根据关键词识别结果，将图片分为三类：
   - **A类整图移除**：图片中 70%+区域含投递关键词 → 从 HTML 中删除该 `<img>` 标签
   - **B类底部裁剪**：关键词仅在图片底部区域 → 裁剪掉图片底部，保留上部正文部分
   - **C类原样保留**：未检测到关键词 → 保留完整图片
3. 重写 `draft.html` 中的图片引用：
   - 将微信 CDN 地址（`src` 和 `data-src`）替换为本地路径 `images/img_xxx.png`
   - 移除微信懒加载属性（`data-w`、`data-ratio`、`data-index` 等）
4. 清理因删除图片导致的空 `<p>` 和 `<section>` 标签

**输入/输出**:
- 输入: `~/.hermes/output/{article_id}/draft/draft.html` + `~/.hermes/output/{article_id}/images/img_*.png`
- 输出: `~/.hermes/output/{article_id}/draft/draft.html` (图片引用重写后)
- 输出: `~/.hermes/output/{article_id}/draft/images/img_*.png` (处理后的图片)
- 输出: `~/.hermes/output/{article_id}/draft/images/delivery/img_*_delivery.png` (裁剪掉的投递部分)
- 输出: `~/.hermes/output/{article_id}/draft/image_map.json` (图片处理映射表)

**测试验证** ✅:
- `5e1a2c72`: 15 张图片中，1 张裁剪，14 张保留，所有正文图片引用重写为本地路径
- 推广模板中的图片保留原始微信 CDN 地址，不会被误处理

### 步骤3: 追加推广模板

**目的**：根据账号配置，在正文区域尾部追加对应的推广模板，并生成 `draft.json` 元数据文件。

**位置**: `scripts/step3_append_promotion.py`

**逻辑**:
1. 加载账号对应的推广模板（`templates/{account}.html`）
2. 检测正文是否已包含推广内容（避免重复追加）
3. 自动生成关键词（格式：MMdd），或使用用户指定的关键词
4. 将推广模板中的 `{keyword}` 占位符替换为实际关键词
5. 在 `js_content` 内部尾部追加推广模板
6. **输出 HTML 时使用 `str(soup)`，禁用 `prettify()`** — 保持微信原生紧凑格式
7. 生成 `draft/draft.json`，包含：
   - `title` — 原始标题（从 metadata.json 读取）
   - `digest` — 自动提取的摘要
   - `keyword` — 关键词编号
   - `author` — 账号对应的作者名称
   - `content_source_url` — 原文链接
   - `account` — 账号配置名
   - `processed_at` — 处理时间

**模板要求** ⚠️:
- 推广模板必须使用从参考文章提取的完整原生 HTML（含微信内联样式、`<mp-common-profile>` 名片组件等）
- 不能手动拼凑简化版，否则会丢失格式
- 模板内 HTML 必须为紧凑单行格式

**输入优先级**:
- 优先读取 `draft/draft.html`（步骤1+2 的输出，如果存在）
- 若不存在，回退到 `article_original.html`

**用法**:
```bash
python3 scripts/step3_append_promotion.py <article_id> --account xingyan_shixi
python3 scripts/step3_append_promotion.py <article_id> --account xingyan_shixi --keyword 0429
python3 scripts/step3_append_promotion.py <article_id> --account joblinker
python3 scripts/step3_append_promotion.py <article_id> --account joblinker --keyword 0430
```

**输入/输出**:
- 输入: `~/.hermes/output/{article_id}/draft/draft.html`
- 输出: `~/.hermes/output/{article_id}/draft/draft.html` (追加模板后)
- 输出: `~/.hermes/output/{article_id}/draft/draft.json`

**现有账号配置**:
- `xingyan_shixi` — 行研实习（推广模板: `templates/xingyan_shixi.html`）
- `joblinker` — Joblinker（推广模板: `templates/joblinker.html`）

**测试验证** ✅:
- `f9d1d82e`: 成功追加推广模板，关键词 `0429`
- 再次执行时正确检测到已含推广内容并跳过
- `draft.json` 元数据正确生成

### 步骤5: 智能摘要生成

**目的**：基于文章标题和 OCR 内容，自动提取招聘类文章的核心信息，生成结构化摘要。

**位置**: `scripts/step5_smart_digest.py`

**提取逻辑**:
1. 从 `metadata.json` 读取标题，提取关键信息：
   - 公司名：通过标题中的企业关键词匹配
   - 岗位类型：实习/校招/社招/暑期实习
   - 届数：2026届、2027届等
   - 实习员/研究员等岗位
   - 工作地点：北京/上海/深圳等
2. 优先读取 `article-ocr.md` 作为正文补充
3. 按“类型 | 届数 | 岗位 | 地点”格式组装摘要
4. 限制在 120 字以内，超长时智能截断

**输入/输出**:
- 输入: `~/.hermes/output/{article_id}/metadata.json` + `~/.hermes/output/{article_id}/article-ocr.md`
- 输出: 更新 `~/.hermes/output/{article_id}/draft/draft.json` 的 `digest` 字段

**用法**:
```bash
python3 scripts/step5_smart_digest.py <article_id>
```

**测试验证** ✅:
- `4192e361`: “校园招聘 | 2026届 | 暑期实习 | 招商基金2026年暑期实习 | 北京 / 上海 / 深圳”
- `5e1a2c72`: “华为云计算BU | 2027届 | 实习 | 2027届华为云BD实习生 | 北京 / 上海 / 深圳 等”

### 步骤6: 标题转换

**目的**：根据文章类型添加前缀并清理冗余词，生成适合微信公众号发布的标题。

**位置**: `scripts/step6_title_transform.py`

**转换规则**:
1. **类型前缀映射**（优先级从高到低）：
   - “暑期实习”/“暑假实习” → “暑期实习 | ”
   - “实习生”/“实习” → “实习 | ”
   - “校园招聘”/“校招”/“秋招”/“春招” → “校招 | ”
   - “社招”/“社会招聘”/“全职” → “社招 | ”
2. **冗余词清理**：
   - 移除: “热招中!”、“诚聘”、“正式启动”、“启动!”、“招聘启动”等
   - 移除多余空格和标点
3. **格式标准化**：
   - “|” 统一为 “ | ”
   - 多余空格去除

**输入/输出**:
- 输入: `~/.hermes/output/{article_id}/metadata.json` 中的 `title`
- 输出: 更新 `~/.hermes/output/{article_id}/draft/draft.json` 的 `title` 和 `original_title` 字段

**用法**:
```bash
python3 scripts/step6_title_transform.py <article_id>
```

**测试验证** ✅:
- `4192e361`: “校园招聘|梦想，招之即来！招商基金2026年暑期实习招聘启动！” → “暑期实习 | 校园招聘 | 梦想，招之即来！招商基金2026年暑期实习招聘”
- `5e1a2c72`: “华为云计算BU | 2027届华为云BD实习生热招中！” → “实习 | 华为云计算BU | 2027届华为云BD实习生”

## 如何新增账号推广模板

当需要支持新的公众号账号时，按以下步骤操作：

### 1. 准备参考文章

找到一篇该账号已发布的、**包含完整推广尾部**的文章，提取其原始 HTML：

```bash
cd /tmp/wechat-article-for-ai-pro
python3 main.py <参考文章URL> --output /tmp/test_output
```

> ⚠️ 必须使用 `article_original.html`，不要直接用 `article.html`（后者只是图片查看器，不含正文）。

### 2. 提取推广部分 HTML

用 Python 脚本从 `article_original.html` 中截取从推广起始词到结尾的完整 HTML：

```python
import re
from bs4 import BeautifulSoup
from pathlib import Path

html = Path('article_original.html').read_text(encoding='utf-8')

# 提取 js_content 正文区（去除 script/style/head 等噪音）
match = re.search(r'id="js_content"[^>]*>(.*?)</div>\s*(?=<div[^>]*id="js_tags_preview_toast"|</body>|</html>|$)', html, re.DOTALL)
if not match:
    raise RuntimeError("无法定位 js_content")
content = match.group(1)
content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)

# 用 BeautifulSoup 查找推广起始位置
soup = BeautifulSoup(content, 'html.parser')
start_text = "简历投递"  # 或该账号推广起始关键词
elements = list(soup.find_all())
start_idx = None
for i, el in enumerate(elements):
    if start_text in el.get_text():
        start_idx = i
        break

if start_idx is None:
    raise RuntimeError(f"未找到推广起始标记: {start_text}")

# 收集从起始元素到末尾的所有元素 HTML
parts = [str(el) for el in elements[start_idx:]]
promotion_html = ''.join(parts)

# 替换硬编码关键词为占位符（根据参考文章实际使用的关键词调整）
promotion_html = promotion_html.replace('0429', '{keyword}')  # 示例

# 保存模板
Path(f'templates/{{account}}.html').write_text(promotion_html, encoding='utf-8')
print(f"模板已保存，大小: {len(promotion_html)} 字符")
```

### 3. 更新脚本配置

修改 `scripts/step3_append_promotion.py`：

**a. 新增作者映射：**
```python
def get_account_author(account: str) -> str:
    authors = {
        "xingyan_shixi": "行研实习",
        "joblinker": "Joblinker",
        # 新增:
        "your_account": "YourDisplayName",
    }
```

**b. 新增账号校验（主函数中）：**
```python
valid_accounts = ["xingyan_shixi", "joblinker", "your_account"]
```

**c. 新增推广检测特征（`has_promotion_content()`）：**

每个账号的推广文案不同，需在 `has_promotion_content()` 中新增该账号的检测指标，避免重复追加：

```python
# your_account 检测指标
your_account_indicators = [
    ("特征关键词1" in text and "特征关键词2" in text),
    ("独有短语" in text),
]

your_hit = sum(your_account_indicators)
return xingyan_hit >= 2 or joblinker_hit >= 2 or your_hit >= 2
```

> 检测特征应选择该账号推广模板中**独有且稳定出现**的文本组合，误报率应极低。

### 4. 更新文档

在 `SKILL.md` 的以下位置补充新账号：
- "可选参数" 中的 `--account` 说明
- "步骤3" 的用法示例
- "现有账号配置" 列表
- `process.py` 的 help epilog 示例

### 5. 清理旧 draft 并验证

```bash
# 清理旧草稿（避免 has_promotion_content 误判）
rm -rf ~/.hermes/output/{article_id}/draft

# 运行完整流程
python3 scripts/process.py {article_id} --account your_account --keyword 0501

# 验证模板已追加
grep -c '推广特有短语' ~/.hermes/output/{article_id}/draft/draft.html
```

---

## 已知陷阱 (Pitfalls)

### 1. `find_all()` 误伤正文内容
**问题**: 使用 `soup.find_all(class_="rich_media_title")` 可能匹配到正文内部的同 class 元素，导致误删用户内容。
**解决**: 先定位 `img-content` 容器，仅在其直接子元素范围内查找，并通过 DOM 索引判断元素是否在 `js_content` 之前。

### 2. `prettify()` 破坏微信 HTML 格式 ⚠️ 严重
**问题**: BeautifulSoup 的 `prettify()` 会重新格式化 HTML（添加换行和缩进），破坏微信编辑器要求的紧凑单行结构。这会导致：样式异常、间距错乱、原生组件（如 `<mp-common-profile>`）失效。
**解决**: **最终输出必须使用 `str(soup)`**，绝对不能用 `prettify()`。参考文章的原生 HTML 是紧凑单行格式，必须原样保留。

### 3. 推广模板必须从参考文章提取完整原生 HTML
**问题**: 手动拼凑的简化版 `<p>` 标签模板会丢失微信原生样式（`font-family`, `letter-spacing`, `-webkit-tap-highlight-color` 等）、公众号名片组件 `<mp-common-profile>`、装饰性背景图区块等。
**解决**: 
1. 从已发布的参考文章中提取完整的推广部分 HTML（使用提取工具的 `promotion_template_final.html`）
2. 替换模板中的 `{keyword}` 占位符即可
3. 保留 `<mp-common-profile>` 等微信原生组件
4. 确保提取的模板是紧凑单行格式（不含多余换行缩进）

### 4. 修改推广模板后必须清理旧 draft 文件 ⚠️ 严重
**问题**: `step3_append_promotion.py` 有 `has_promotion_content()` 检测逻辑。如果 `draft/draft.html` 已经包含了旧格式的推广内容，重新运行 `process.py` 时会检测到已有推广并**跳过追加**，导致新模板永远不会生效。
**解决**:
1. 修改 `templates/{account}.html` 后，必须先删除旧 draft 文件：
   ```bash
   rm ~/.hermes/output/{article_id}/draft/draft.html
   rm ~/.hermes/output/{article_id}/draft/draft.json
   ```
2. 然后重新运行 `process.py`：
   ```bash
   python3 scripts/process.py {article_id}
   ```
**检查**: 重新生成后，用以下命令确认新模板已生效：
```bash
grep -c 'mp-common-profile' ~/.hermes/output/{article_id}/draft/draft.html
```

### 5. 部分文章无尾部标记
**问题**: 不是所有文章都有 `"预览时标签不可点"` 标记。
**解决**: 步骤1脚本已处理该情况（未找到标记时不报错，继续执行）。未来可考虑补充备用分界点。

### 6. BeautifulSoup4 环境依赖陷阱 ⚠️
**问题**: 脚本依赖 `beautifulsoup4`，但某些环境中 `python3` 和 `pip3` 指向不同的 Python 解释器。例如，`python3` 可能指向 venv 的 Python 3.11，而 `pip3` 指向系统的 Python 3.9。此时运行 `pip3 install beautifulsoup4` 会装到错误的 site-packages，脚本继续报 `ModuleNotFoundError`。
**解决**:
1. 优先使用与 `python3` 对应的 pip：
   ```bash
   python3 -m pip install beautifulsoup4
   ```
2. 若 venv 中无 pip，可尝试 uv（如果环境已安装）：
   ```bash
   uv pip install beautifulsoup4
   ```
3. 验证安装是否到位：
   ```bash
   python3 -c "from bs4 import BeautifulSoup; print('bs4 OK')"
   ```

### 7. 前次失败运行残留的 draft 文件
**问题**: 若前次运行因依赖缺失（如 bs4 未装）导致步骤2/3失败，`draft/` 目录已存在不完整的 `draft.html`。再次运行 `process.py` 时，虽然 step0 会覆盖 draft.html，但 step3 的 `has_promotion_content()` 若检测到旧内容可能跳过追加。
**解决**: 重试前建议清理旧 draft：
```bash
rm -rf ~/.hermes/output/{article_id}/draft
python3 scripts/process.py {article_id}
```

## 后续步骤

- 步骤4: 标签与属性清理（移除多余的 `data-*` 属性和空标签）
- 步骤7: 交互式配置导出（支持不同账号配置的管理和选择）

## 依赖

- Python 3.8+
- `beautifulsoup4`（步骤2、步骤3必需）
- 需要 `wechat-article-extraction-pro` 提供的 `article_original.html`
