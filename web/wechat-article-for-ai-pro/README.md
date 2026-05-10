# 微信公众号文章提取工具 Pro 版

基于 [wechat-article-for-ai](https://github.com/bzd6661/wechat-article-for-ai) 的增强版本，实现 **Hybrid 模式**：工具负责提取+OCR，Hermes 负责总结回填。

## 核心特性

| 特性 | 说明 |
|------|------|
| **自动5文件输出** | 提取后自动生成 `article.md` + `article.html` + `metadata.json` + `images/` + `article-ocr.md` |
| **本地 OCR 识别** | 使用 RapidOCR 本地识别图片文字，无需网络 |
| **长图自动切片** | 超长图片(>2000px)自动切片后分段 OCR |
| **Hybrid 模式** | 工具提取+OCR → Hermes 总结回填，分工明确 |
| **原图优先展示** | HTML 查看器优先展示原始图片，保留专业设计效果 |
| **完整内容提取** | 自动处理懒加载，获取 40+ 张图片（传统方法仅 2-7 张） |
| **反爬虫绕过** | 使用 Camoufox 隐身浏览器，绕过微信反爬检测 |
| **YAML 元数据** | Markdown 包含标准 frontmatter（标题、作者、日期、来源） |

## 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/wechat-article-for-ai-pro.git
cd wechat-article-for-ai-pro

# 安装依赖
pip install -r requirements.txt
```

### 系统依赖（macOS）

```bash
# 安装 camoufox 依赖
brew install --cask camoufox

# 或使用 pip
pip install camoufox[geoip]
```

## 使用方法

### 完整流程（Hybrid 模式）

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  阶段 1     │ ──→ │  阶段 2     │ ──→ │  阶段 3     │
│  工具提取    │     │  Hermes 总结 │     │  完成输出    │
└─────────────┘     └─────────────┘     └─────────────┘
```

#### 阶段 1：工具提取（本地执行）

```bash
python main.py "https://mp.weixin.qq.com/s/ARTICLE_ID" -o ./output
```

工具会自动：
1. 提取文章内容
2. 下载所有图片
3. **RapidOCR 识别图片文字**（本地执行，无需网络）
4. 生成 `article-ocr.md`（含 OCR 结果，第三部分待填充）

#### 阶段 2：Hermes 总结回填（AI 处理）

工具提取完成后，通知 Hermes：

```
"请总结这篇文章：./output/{article_id}"
```

Hermes 会：
1. 读取 `article-ocr.md` 的 OCR 内容
2. 结构化分析（公司概况、招聘亮点、关键信息）
3. 生成 Markdown 格式的第三部分
4. 回填到 `article-ocr.md`

### 单篇文章提取

```bash
python main.py "https://mp.weixin.qq.com/s/ARTICLE_ID" -o ./output
```

### 批量提取

```bash
# 从文件读取 URL 列表
python main.py -f urls.txt -o ./output

# urls.txt 格式（每行一个 URL，# 开头为注释）
# https://mp.weixin.qq.com/s/xxx
# https://mp.weixin.qq.com/s/yyy
```

### 常用参数

| 参数 | 说明 |
|------|------|
| `-o, --output` | 输出目录（默认：./output） |
| `-v, --verbose` | 启用详细日志 |
| `--force` | 覆盖已存在的输出目录 |
| `--no-headless` | 显示浏览器窗口（用于手动解决验证码） |
| `--no-images` | 跳过图片下载，保留远程 URL |

## 输出结构

```
output/
└── 文章标题/
    ├── article.md          # Markdown 格式（含本地图片路径）
    ├── article.html        # HTML 查看器（优先展示原图）
    ├── metadata.json       # 结构化元数据
    ├── article-ocr.md      # OCR 结果 + Hermes 总结 ⭐
    ├── images/             # 下载的所有图片
    │   ├── img_001.jpg
    │   ├── img_002.png
    │   └── ...
    └── slices/             # 长图切片（如有）
        ├── img_001_slice_01.jpg
        └── ...
```

### article-ocr.md

```markdown
# 文章内容（含图片 OCR 识别）

## 一、原文文字内容
[从 article.md 提取的文字内容]

## 二、图片 OCR 识别内容
### 图片: img_001.png
[OCR 识别的图片文字，按段落展示]

## 三、完整文字内容（原文 + OCR）
[Hermes 生成的结构化总结]

### 公司概况
...

### 招聘亮点
...

### 关键信息
...

### 投递方式
...
```

### article.md

```markdown
---
title: "文章标题"
author: "公众号名称"
date: "2026-04-13 19:53:52"
source: "https://mp.weixin.qq.com/s/..."
---

# 文章标题

![Image](images/img_001.jpg)
...
```

### metadata.json

```json
{
  "url": "https://mp.weixin.qq.com/s/...",
  "title": "文章标题",
  "author": "公众号名称",
  "published_at": "2026-04-13 19:53:52",
  "source": "...",
  "extraction_method": "wechat-article-for-ai-pro",
  "extraction_time": "2026-04-14T11:30:00",
  "image_count": 40,
  "images": ["images/img_001.jpg", "..."]
}
```

## 与原版的区别

| 项目 | 原版 | Pro 版 |
|------|------|--------|
| 输出文件 | 仅 Markdown + images | Markdown + HTML + JSON + images + OCR + slices |
| HTML 查看器 | ❌ | ✅ 原图优先展示 |
| OCR 识别 | ❌ | ✅ RapidOCR 本地识别 |
| 长图处理 | ❌ | ✅ 自动切片分段 OCR |
| Hybrid 模式 | ❌ | ✅ 工具提取+OCR，Hermes 总结 |
| 标准化输出 | ❌ | ✅ 固定5文件结构 |
| 元数据结构 | 简单 frontmatter | 完整 JSON 元数据 |

## 常见问题

### 遇到验证码

```bash
# 使用 --no-headless 手动解决
python main.py "URL" -o ./output --no-headless
```

### 图片下载失败

```bash
# 使用 --force 重新运行
python main.py "URL" -o ./output --force
```

### 内容为空

- 等待几分钟后重试（微信限流）
- 检查 URL 是否正确
- 使用 `--no-headless` 查看浏览器状态

## 技术架构

```
wechat_to_md/
├── cli.py           # 命令行接口
├── scraper.py       # Camoufox 页面抓取
├── parser.py        # HTML 内容解析
├── converter.py     # Markdown 转换
├── downloader.py    # 图片下载
├── formatter.py     # 标准化输出
├── ocr_adapter.py   # OCR 适配器（RapidOCR/Vision）⭐
└── ocr_processor.py # OCR 处理（切片、识别）⭐
```

## 贡献

欢迎提交 Issue 和 PR。

## 许可证

与原项目保持一致。

## 致谢

- 基于 [bzd6661/wechat-article-for-ai](https://github.com/bzd6661/wechat-article-for-ai) 开发
- 使用 [Camoufox](https://camoufox.com/) 实现隐身浏览
