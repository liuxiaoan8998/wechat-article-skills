---
name: wechat-article-search
description: >
  公众号文章搜索 Skill，基于极致了API提供两种搜索模式：
  1. 【数据库模式】搜索历史数据库中的文章（0.02元/条）
  2. 【搜一搜模式】实时搜索微信客户端结果（0.5元/次）
  
  搜索结果自动保存到本地JSON文件，并支持同步到飞书Base"搜索文章池"表。
tags: [wechat, search, api, feishu]
related_skills: [wechat-article-extraction-pro]
---

# 公众号文章搜索 Skill

## 功能概述

基于极致了API的公众号文章搜索工具，提供完整的搜索-存储-同步工作流：

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   搜索文章   │ ──→ │  保存JSON   │ ──→ │ 同步飞书Base │
│ (极致了API)  │     │ (本地数据)   │     │ (搜索文章池) │
└─────────────┘     └─────────────┘     └─────────────┘
```

| 模式 | 特点 | 适用场景 | 成本 |
|------|------|----------|------|
| **数据库模式** | 搜索历史数据库，数据全、价格低 | 批量采集、历史文章查找 | 0.02元/条 |
| **搜一搜模式** | 实时搜索微信客户端，数据最新 | 获取最新文章、热点追踪 | 0.5元/次 |

## 数据存储

### 本地存储

- **数据目录**: `~/.hermes/data/wechat-search/`
- **文件命名**: `search_YYYYMMDD_HHMMSS_keyword.json`
- **文件内容**: 包含搜索参数、搜索时间、文章列表

**目录结构模式**（可复用）：
```
~/.hermes/data/
├── wechat-search/          # 本Skill数据
│   ├── search_20260422_175112_暑期实习.json
│   └── search_20260422_180000_实习.json
├── wechat-articles/        # 其他Skill数据
└── ...
```

**Python实现**：
```python
from pathlib import Path

# 标准数据目录模式
DATA_DIR = Path.home() / ".hermes" / "data" / "wechat-search"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 生成文件名
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"search_{timestamp}_{keyword[:20]}.json"
filepath = DATA_DIR / filename
```

### 飞书Base表

**表名**: 搜索文章池  
**表ID**: `tblUTsHDtJ2JWEbW`

| 字段 | 类型 | 说明 |
|------|------|------|
| 文章标题 | 文本 | 文章标题 |
| 公众号名称 | 文本 | 公众号名字 |
| 微信号 | 文本 | 微信号 |
| 原始ID | 文本 | 公众号原始ID |
| 文章长链接 | 文本 | 文章完整URL |
| 短链接 | 文本 | 文章短链接 |
| 发布时间 | 日期 | 数据库: publish_time 转毫秒时间戳<br>搜一搜: timestamp 转毫秒时间戳 |
| 更新时间 | 日期 | 仅数据库模式有 |
| 搜索时间 | 日期 | 当前时间毫秒时间戳 |
| 发布时间文本 | 文本 | 搜一搜: source.dateTime (如"2小时前")<br>数据库: publish_time_str |
| 阅读数 | 数字 | 阅读量 |
| 点赞数 | 数字 | 点赞数 |
| 在看数 | 数字 | 在看数 |
| 正文内容 | 文本 | 文章正文（截断） |
| 封面图片 | 文本 | 封面图片URL |
| 搜索模式 | 文本 | 标识搜索来源："数据库模式" 或 "搜一搜模式" |
| 文章摘要 | 文本 | 搜一搜: desc (去除HTML)<br>数据库: content 前2000字 |
| 公众号来源 | 文本 | 搜一搜: source.title<br>数据库: wx_name |
| 发布时间文本 | 文本 | 搜一搜: source.dateTime (如"2小时前")<br>数据库: publish_time_str |
| 搜索关键词 | 文本 | 本次搜索使用的关键词 |
| 搜索时间 | 日期 | 搜索执行时间（毫秒时间戳） |
| 关联文章ID | 文本 | 同步到文章列表后的记录ID |
| 原始JSON | 文本 | API返回的完整原始数据 |

**字段差异说明**:

| 字段 | 数据库模式 | 搜一搜模式 |
|------|-----------|-----------|
| 文章标题 | title | title (去除HTML标签) |
| 公众号名称 | wx_name | source.title |
| 文章长链接 | url | doc_url |
| 发布时间 | publish_time (秒级时间戳) | timestamp (秒级时间戳) |
| 更新时间 | update_time | 无 |
| 阅读数 | read | 无 |
| 点赞数 | praise | 无 |
| 在看数 | looking | 无 |
| 正文内容 | content | desc (去除HTML标签) |
| 封面图片 | avatar | thumbUrl |
| 发布时间文本 | publish_time_str | source.dateTime |

## API 配置

```bash
export DAJIALA_API_KEY="your_api_key_here"
```

### 飞书配置

已内置在脚本中：
- **Base Token**: `E9y1bxjHGa9LeGs9q3Tc3J41nmf`
- **搜索文章池表ID**: `tblUTsHDtJ2JWEbW`

## 搜索模式详解

### 模式一：数据库搜索（kw_search）

**接口**: `POST /fbmain/monitor/v3/kw_search`

**特点**:
- 搜索历史数据库中的文章
- 可翻页，每页20条
- 支持关键词、包含词、排除词组合搜索
- 按返回条数计费（0.02元/条）

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kw | string | 条件必填 | 搜索关键词（与any_kw、ex_kw至少填一个） |
| any_kw | string | 条件必填 | 包含任意一个关键词（逗号分隔） |
| ex_kw | string | 条件必填 | 排除关键词（逗号分隔） |
| page | int | 否 | 页码，默认1 |
| key | string | 是 | API Key |

**响应字段**:

| 字段 | 说明 |
|------|------|
| title | 文章标题 |
| url | 文章长链接 |
| short_link | 文章原始短链接 |
| content | 正文内容 |
| avatar | 封面图片 |
| publish_time | 发布时间 |
| update_time | 更新时间 |
| wx_name | 公众号名字 |
| wx_id | 微信号 |
| ghid | 原始ID |
| read | 阅读数 |
| praise | 点赞数 |
| looking | 在看数 |

### 模式二：搜一搜实时搜索（web_search）

**接口**: `POST /fbmain/monitor/v3/web_search`

**特点**:
- 实时搜索微信客户端结果
- 与微信搜一搜结果一致
- 支持排序筛选（最新/最热/不限）
- 按次计费（0.5元/次）

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| mode | int | 是 | 固定值 2 |
| keyword | string | 是 | 搜索关键词 |
| BusinessType | int | 是 | 固定值 2（文章） |
| Sub_search_type | int | 是 | 排序：0不限 2最新 4最热 1已关注 3最近读过 |
| currentPage | int | 是 | 当前页码 |
| offset | int | 是 | 第一页0，后续页填上一页返回的offset |
| cookies_buffer | string | 条件必填 | 第2页以后需要 |
| key | string | 是 | API Key |

## 使用方法

### 命令行工具

```bash
# 数据库模式搜索并保存到本地
python3 ~/.hermes/skills/web/wechat-article-search/scripts/search.py \
  --mode database \
  --keyword "实习" \
  --any-kw "互联网,大厂"

# 搜一搜模式获取最新文章并同步到飞书
python3 ~/.hermes/skills/web/wechat-article-search/scripts/search.py \
  --mode sousuo \
  --keyword "暑期实习" \
  --sort 2 \
  --sync

# 搜索、保存JSON、同步到飞书（完整流程）
python3 ~/.hermes/skills/web/wechat-article-search/scripts/search.py \
  --keyword "校招" \
  --sync

# 筛选高阅读量文章
python3 ~/.hermes/skills/web/wechat-article-search/scripts/search.py \
  --keyword "实习" \
  --min-read 5000 \
  --max-days 7 \
  --sync
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `--mode` | 搜索模式：database（默认）或 sousuo |
| `--keyword, -k` | 搜索关键词 |
| `--any-kw` | 包含任意关键词（逗号分隔，仅数据库模式） |
| `--ex-kw` | 排除关键词（逗号分隔，仅数据库模式） |
| `--sort` | 搜一搜排序：0不限 2最新 4最热 |
| `--output, -o` | 指定输出JSON文件路径 |
| `--max` | 显示最大文章数（默认10） |
| `--min-read` | 最小阅读量筛选 |
| `--max-days` | 最大发布时间（天） |
| `--sync` | 同步到飞书Base |
| `--no-save` | 不保存到本地JSON文件 |

### Python API

```python
from scripts.search import search_database, search_sousuo, save_to_json, sync_to_feishu

# 1. 搜索文章
articles = search_database(
    keyword="实习",
    any_kw="互联网,大厂",
    ex_kw="兼职"
)

# 2. 保存到本地JSON
from pathlib import Path
json_path = save_to_json(articles, {
    "keyword": "实习",
    "mode": "database"
})
print(f"已保存到: {json_path}")

# 3. 同步到飞书Base
for article in articles:
    record_id = sync_to_feishu(article, {"keyword": "实习"})
    if record_id:
        print(f"同步成功: {record_id}")
```

## 搜索结果处理

### 文章去重

```python
from scripts.search import deduplicate_articles

unique_articles = deduplicate_articles(articles)
```

### 文章筛选

```python
from scripts.search import filter_articles

# 筛选阅读量>1000且7天内发布的文章
filtered = filter_articles(
    articles,
    min_read=1000,
    max_days=7,
    required_keywords=["大厂", "名企"]
)
```

## 数据文件格式

```json
{
  "search_params": {
    "mode": "database",
    "keyword": "实习",
    "any_kw": "互联网,大厂",
    "ex_kw": ""
  },
  "search_time": "2026-04-22T18:30:00",
  "total_count": 20,
  "articles": [
    {
      "title": "...",
      "url": "...",
      "wx_name": "...",
      "read": 10000,
      "praise": 100,
      ...
    }
  ]
}
```

## 完整工作流示例

```python
#!/usr/bin/env python3
"""搜索-保存-同步完整流程"""

from scripts.search import (
    search_database, 
    deduplicate_articles, 
    filter_articles,
    save_to_json,
    sync_to_feishu
)
from datetime import datetime

def search_and_sync(
    keyword: str,
    min_read: int = 1000,
    max_days: int = 30,
    sync: bool = True
):
    """搜索文章并同步到飞书"""
    
    print(f"🔍 搜索: {keyword}")
    
    # 1. 搜索
    articles = search_database(keyword=keyword)
    print(f"✅ 找到 {len(articles)} 篇文章")
    
    # 2. 筛选
    articles = filter_articles(articles, min_read=min_read, max_days=max_days)
    print(f"📋 筛选后: {len(articles)} 篇")
    
    # 3. 去重
    articles = deduplicate_articles(articles)
    print(f"📋 去重后: {len(articles)} 篇")
    
    # 4. 保存
    search_params = {"keyword": keyword, "mode": "database"}
    json_path = save_to_json(articles, search_params)
    print(f"💾 已保存: {json_path}")
    
    # 5. 同步
    if sync:
        print(f"🚀 同步到飞书...")
        success = 0
        for article in articles:
            record_id = sync_to_feishu(article, search_params)
            if record_id:
                success += 1
        print(f"✅ 同步完成: {success}/{len(articles)}")
    
    return articles

# 使用
if __name__ == "__main__":
    search_and_sync("暑期实习", min_read=5000, max_days=7)
```

### 日期字段格式（重要）

飞书Base的日期时间字段需要**毫秒级时间戳**（13位数字），而非秒级时间戳或字符串格式。

```python
# ❌ 错误：秒级时间戳
timestamp = 1776297448  # 显示为 1970-01-21（错误）

# ❌ 错误：字符串格式
date_str = "2026-04-16"  # 不会被识别为日期

# ✅ 正确：毫秒级时间戳
timestamp_ms = 1776297448000  # 显示为 2026-04-16 07:57:28
```

**转换函数**：
```python
def convert_timestamp_to_date(timestamp):
    """将秒级时间戳转换为飞书日期格式（毫秒级时间戳）"""
    if not timestamp:
        return None
    try:
        if isinstance(timestamp, (int, float)):
            return int(timestamp * 1000)  # 秒→毫秒
        elif isinstance(timestamp, str):
            if timestamp.isdigit():
                return int(timestamp) * 1000
    except:
        pass
    return None
```

**字段类型映射**：
| API返回 | 飞书Base字段类型 | 转换方式 |
|---------|-----------------|----------|
| 秒级时间戳 (int) | datetime | `int(ts * 1000)` |
| 日期字符串 | datetime | 先解析为datetime再转毫秒戳 |

## 错误处理

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| 0 | 成功 | - |
| -1 | 参数错误 | 检查请求参数 |
| -2 | API Key无效 | 检查环境变量 |
| -3 | 余额不足 | 充值API余额 |
| -4 | 请求过于频繁 | 降低请求频率 |
| 500 | 服务器错误 | 重试1-3次 |

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0.0 | 2026-04-22 | 初始版本，支持数据库和搜一搜两种模式 |
| v1.1.0 | 2026-04-22 | 精简版本，仅保留搜索功能 |
| v1.2.0 | 2026-04-22 | 增加本地JSON存储和飞书Base同步功能 |
| v1.2.1 | 2026-04-22 | 修复日期字段格式：秒级时间戳→毫秒级时间戳 |
| **v1.3.0** | **2026-04-22** | **支持两种搜索模式数据兼容，添加字段映射和HTML清理** |

## 相关 Skill

- **wechat-article-extraction-pro**: 负责文章提取、AI分析、同步到文章列表

## 注意事项

1. **成本控制**: 数据库模式（0.02元/条）适合批量采集，搜一搜模式（0.5元/次）适合获取最新文章
2. **翻页限制**: 搜一搜模式翻页需要使用上一页返回的offset和cookies_buffer
3. **数据目录**: 自动创建 `~/.hermes/data/wechat-search/` 存储搜索历史
4. **飞书同步**: 使用 `--sync` 参数开启，会逐条同步到"搜索文章池"表
5. **重复处理**: 飞书Base不自动去重，建议搜索前检查是否已存在

以上