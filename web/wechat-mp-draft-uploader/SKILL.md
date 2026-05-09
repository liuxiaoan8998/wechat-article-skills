---
name: wechat-mp-draft-uploader
description: >
  微信公众号草稿箱上传 Skill。基于简立制作 API 平台，
  实现从飞书 Base 选题后的文章自动上传到微信公众号草稿箱。
  支持单图文/多图文、封面素材上传、原文链接保留等功能。
required_env_vars:
  - JIANLIZHIZUO_API_KEY  # 简立制作平台 API Key
---

# Skill 输入参数

## 必需参数

| 参数名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `appid` | string | 公众号 AppID | `wx1234567890abcdef` |
| `article_source` | string | 文章来源类型 | `feishu` / `local` |

## 条件参数（根据 article_source）

### 当 article_source = "feishu" 时

| 参数名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `feishu_base_token` | string | 飞书 Base Token | `"$FEISHU_BASE_TOKEN"` |
| `feishu_table_id` | string | 飞书表 ID | `"$FEISHU_ARTICLE_TABLE_ID"` |
| `record_id` | string | 文章记录 ID | `recvhq1MWUhyc5` |

### 当 article_source = "local" 时

| 参数名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `article_dir` | string | 文章本地目录路径 | `~/.hermes/output/文章标题/` |

## 可选参数

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `cover_image` | string | 指定封面图片文件名 | 自动使用第一张图片 |
| `author` | string | 文章作者 | 从飞书 Base 读取 |
| `digest` | string | 文章摘要 | 从飞书 Base 读取 |
| `need_open_comment` | number | 是否开启评论 | `1`（开启）|

---

# 微信公众号草稿上传 Skill

## 功能概述

将飞书 Base 中已选题的文章自动上传到微信公众号草稿箱，支持：
- 单图文/多图文上传（最多8篇）
- 自动上传封面图片获取 thumbMediaId
- 保留原文链接
- 设置作者、摘要、评论开关

## 前置条件

1. **简立制作平台账号**
   - 注册地址：https://mp.jianlizhizuo.cn
   - 获取 API Key
   - 绑定需要管理的公众号

2. **环境变量配置（必需）**
```bash
# 添加到 ~/.hermes/.env
export JIANLIZHIZUO_API_KEY=sk-xxxxxxxxxxxxxxxx  # 简立制作平台 API Key
```

**验证环境变量**:
```bash
echo $JIANLIZHIZUO_API_KEY
# 应输出: sk-xxxxxxxxxxxxxxxx
```

3. **环境检查**
```bash
# 运行环境检查
source ~/.hermes/skills/web/wechat-mp-draft-uploader/scripts/check_env.sh
```

## 工作流集成

### 与文章提取工作流集成

**完整流程**:
```
1. 提取文章
   wechat-article-extraction-pro → /tmp/test_output/{article_id}/
   
2. 复制到上传目录
   cp -r /tmp/test_output/{article_id} ~/.hermes/output/
   
3. 草稿处理（自动或手动）
   process.py {article_id} --account {account_name}
   → 生成 draft/draft.html（含推广模板、关键词回复）

4. 上传到草稿箱
   upload_from_feishu.py --record-id {record_id}
```

> **自动草稿处理器前置检查**：
> 上传脚本已内置自动检查。如果 `draft/draft.html` 不存在，上传脚本会**自动调用草稿处理器** `process.py` 生成处理后的草稿，然后继续上传。这确保每次上传都会自动经过草稿处理步骤，避免因为忘记运行处理器而导致上传的文章缺少推广模板。
>
> 但是，如果希望对标题、摘要、关键词回复等做细节调整，建议先手动运行处理器，确认 `draft.json` 内容无误后再上传。

**自动化脚本**:
```python
import shutil
import subprocess
import os

def extract_and_upload(article_url: str):
    """提取文章并自动上传到草稿箱"""
    
    # 1. 提取文章
    result = subprocess.run(
        f'cd /tmp/wechat-article-for-ai-pro && /usr/bin/python3 main.py "{article_url}"',
        shell=True, capture_output=True, text=True
    )
    
    # 2. 获取 article_id（从输出或metadata）
    # ...
    
    # 3. 复制到上传目录
    shutil.copytree(
        f"/tmp/test_output/{article_id}",
        f"~/.hermes/output/{article_id}"
    )
    
    # 4. 上传
    env = os.environ.copy()
    env['JIANLIZHIZUO_API_KEY'] = 'sk-xxxxxxxxxxxxxxxx'
    subprocess.run(
        f'python upload_from_feishu.py --article-id {article_id}',
        shell=True, env=env
    )
```

## API 端点

**Base URL**: `https://mp.jianlizhizuo.cn/v1`

### 1. 创建草稿

```http
POST /accounts/{appid}/drafts
```

**请求参数**:
| 名称 | 类型 | 必填 | 说明 |
|------|------|------|------|
| articles | array | 是 | 文章列表，最多8篇 |
| articles[].title | string | 是 | 标题（最长64字符）|
| articles[].content | string | 是 | 正文 HTML |
| articles[].thumbMediaId | string | 条件 | 封面素材ID（article_type=news 时必填）|
| articles[].articleType | string | 否 | news（图文，默认）/ newspic（图片）|
| articles[].author | string | 否 | 作者（最长16字符）|
| articles[].digest | string | 否 | 摘要（最长128字符）|
| articles[].contentSourceUrl | string | 否 | 原文链接 |
| articles[].needOpenComment | number | 否 | 0否（默认）1是 |

**响应参数**:
| 名称 | 类型 | 说明 |
|------|------|------|
| code | number | 状态码，0为成功 |
| data.mediaId | string | 草稿 MediaID |
| data.title | string | 第一篇文章标题 |
| data.articleCount | number | 文章数量 |

### 2. 上传图文消息内的图片获取 URL

```http
POST /accounts/{appid}/media/uploadimg
```

用于上传正文中引用的图片，返回永久 URL。

### 3. 上传永久素材（封面/正文图片）

```http
POST /accounts/{appid}/materials
Content-Type: multipart/form-data
```

用于上传封面图或正文图片，返回永久素材 mediaId 和 URL。

**请求参数**:
| 名称 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string | 是 | 素材类型：IMAGE / VOICE / VIDEO / THUMB |
| name | string | 是 | 素材名称 |
| media | file | 是 | 文件（图片≤10M，语音≤2M，视频≤10M，缩略图≤64KB）|
| description | string | 否 | 视频素材简介（VIDEO 类型时使用）|

**响应参数**:
| 名称 | 类型 | 说明 |
|------|------|------|
| code | number | 状态码，0为成功 |
| data.mediaId | string | 永久素材 MediaID（可用于 thumbMediaId）|
| data.url | string | 图片素材访问 URL（仅图片类型返回）|
| data.name | string | 素材名称 |
| data.type | string | 素材类型 |

### 4. 上传图文消息内的图片获取 URL

```http
POST /accounts/{appid}/media/uploadimg
```

用于上传正文中引用的图片，返回永久 URL。

## 使用流程

### 完整上传流程

```
从飞书 Base 获取已选题文章
    ↓
读取 article-ocr.md 中的结构化内容
    ↓
提取/处理正文 HTML
    ↓
上传正文图片 → 获取永久 URL（只上传一次）
    ↓
循环处理每个适配账号：
    ├── 上传封面 → 获取 thumbMediaId（每个账号独立）
    └── 创建草稿 → 获取 MediaID
    ↓
更新【文章素材表】→ 状态"已上传草稿"、记录所有草稿ID
```

## 使用方式（简化版）

**只需提供飞书 Base 文章记录 ID，自动完成全部流程**

### Python API

```python
from upload_from_feishu import upload_from_feishu

# 极简调用 - 只需记录 ID
result = upload_from_feishu(record_id="recvhq1MWUhyc5")

# 返回结果
{
    "results": [
        {"account_name": "Joblinker", "appid": "wx...", "mediaId": "DRAFT_MEDIA_ID_1", "success": True},
        {"account_name": "行研实习", "appid": "wx...", "mediaId": "DRAFT_MEDIA_ID_2", "success": True}
    ],
    "success_count": 2,
    "failed_count": 0,
    "total_count": 2
}
```

**自动流程**:
1. 读取飞书 Base 文章记录（标题、摘要、原文链接、适配账号）
2. **根据【适配账号】自动查询【账号配置表】获取所有有效 AppID**
3. 查找本地文章目录（`~/.hermes/output/`）
4. **读取文章正文（优先级：article_original.html > article.html > article.md）**
   - `article_original.html`: 微信原始 HTML，保留完整结构和样式（推荐）
   - `article.html`: 本地查看用的 HTML（兼容性备选）
   - `article.md`: Markdown 格式（降级方案）
5. **上传正文图片到微信素材库（只上传一次，所有账号复用）**
6. **循环上传到所有适配账号**（每个账号独立上传封面获取 thumbMediaId）
7. 更新飞书 Base 状态为"已上传草稿"，记录所有草稿ID

### 命令行

```bash
# 方式1: 使用文章编号（推荐）
python upload_from_feishu.py --no NO.008
python upload_from_feishu.py -n 008

# 方式2: 使用记录 ID
python upload_from_feishu.py --record-id recvhq1MWUhyc5

# 方式3: 使用文章ID（如 7907d7cb）⭐ 新增
python upload_from_feishu.py --article-id 7907d7cb
python upload_from_feishu.py -aid 7907d7cb

# 方式4: 自动检测上下文（最近同步的文章）⭐ 新增
python upload_from_feishu.py --context
python upload_from_feishu.py -ctx

# 指定封面图片
python upload_from_feishu.py -n 008 --cover img_001.jpg

# 覆盖作者
python upload_from_feishu.py -n 008 --author "Joblinker官方"

# 启用图片压缩
python upload_from_feishu.py -n 008 --compress

# 使用原始HTML上传（跳过草稿处理器和推广模板）⭐ 新增
python upload_from_feishu.py -n 008 --raw
```

### 完整参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `--no` / `-n` | string | ✅(四选一) | 文章编号 | `008` 或 `NO.008` |
| `--record-id` / `-r` | string | ✅(四选一) | 飞书 Base 记录 ID | `recvhq1MWUhyc5` |
| `--article-id` / `-aid` | string | ✅(四选一) ⭐ | 文章ID（从提取工具生成） | `7907d7cb` |
| `--context` / `-ctx` | flag | ✅(四选一) ⭐ | 自动检测上下文 | 使用最近同步的文章 |
| `--base-token` / `-b` | string | ❌ | 飞书 Base Token | 默认使用配置 |
| `--cover` / `-c` | string | ❌ | 指定封面图片 | `img_001.jpg` |
| `--author` / `-a` | string | ❌ | 覆盖作者 | `Joblinker` |
| `--no-comment` | flag | ❌ | 关闭评论 | 默认开启 |
| `--compress` / `-z` | flag | ❌ | 启用图片压缩 | 默认不压缩 |
| `--raw` | flag | ❌ | 使用原始HTML上传 | 默认使用 draft.html |

## 数据流转

```
输入: record_id
    ↓
【文章素材表】→ 标题、摘要、原文链接、适配账号
    ↓
【账号配置表】→ 根据适配账号查询 → 获取所有有效 AppID
    ↓
本地目录 → 读取 article_original.html（优先）或 article.html
    ↓
上传正文图片 → 获取永久 URL（只上传一次，所有账号复用）
    ↓
循环处理每个适配账号：
    ├── 上传封面 → 获取 thumbMediaId（每个账号独立）
    └── 创建草稿 → MediaID
    ↓
更新【文章素材表】→ 状态"已上传草稿"、记录所有草稿ID
```

## 前置配置要求

### 1. 环境变量

```bash
# 添加到 ~/.hermes/.env
JIANLIZHIZUO_API_KEY=sk-xxxxxxxxxxxxxxxx  # 简立制作平台 API Key
```

### 2. 账号配置表字段

| 字段名 | 说明 | 示例 |
|--------|------|------|
| `账号名称` | 适配账号名称 | `Joblinker` |
| `公众号ID` | 微信公众号 AppID | `wx1234567890abcdef` |
| `AppSecret` | 公众号密钥 | `***` |
| `作者` | 默认作者名称（用于草稿 author 字段）| `Lily学姐` |
| `授权状态` | 是否已授权 | `已授权` |

**作者优先级**:
1. 传入参数（`--author` 命令行参数）
2. 账号配置【作者】字段
3. 账号名称（兜底）

### 3. 文章素材表字段

| 字段名 | 说明 | 可选值 |
|--------|------|--------|
| `文章标题` | 文章标题 | - |
| `文章链接` | 原文链接（支持 Markdown 格式） | - |
| `文章概要` | 文章摘要 | - |
| `适配账号` | 多选，如 `["Joblinker"]` | Joblinker / 行研实习 / 研究生求职圈 |
| `文章状态` | 文章状态字段 | **待选题** / **已选题** / **已上传草稿** / 待二创 / 待排版 / 待发布 / 已发布 / 已取消 |

**状态流转**:
```
待选题 → 已选题 → 已上传草稿 → 待二创 → 待排版 → 待发布 → 已发布
```

```python
import requests
import os
import json
from pathlib import Path

class WechatDraftUploader:
    def __init__(self, api_key: str = None, appid: str = None):
        self.api_key = api_key or os.getenv("JIANLIZHIZUO_API_KEY")
        self.appid = appid or os.getenv("WECHAT_APPID")
        self.base_url = "https://mp.jianlizhizuo.cn/v1"
        
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def upload_cover_image(self, image_path: str) -> str:
        """上传封面图片，返回 thumbMediaId"""
        url = f"{self.base_url}/accounts/{self.appid}/media/uploadnews"
        
        with open(image_path, 'rb') as f:
            files = {'media': f}
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.post(url, files=files, headers=headers)
        
        if response.json().get('code') == 0:
            return response.json()['data']['mediaId']
        else:
            raise Exception(f"封面上传失败: {response.json()}")
    
    def upload_content_image(self, image_path: str) -> str:
        """上传正文图片，返回永久 URL"""
        url = f"{self.base_url}/accounts/{self.appid}/media/uploadimg"
        
        with open(image_path, 'rb') as f:
            files = {'media': f}
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.post(url, files=files, headers=headers)
        
        if response.json().get('code') == 0:
            return response.json()['data']['url']
        else:
            raise Exception(f"图片上传失败: {response.json()}")
    
    def create_draft(self, articles: list) -> dict:
        """
        创建草稿
        
        Args:
            articles: 文章列表，每项为 dict 包含 title, content, thumbMediaId 等
        
        Returns:
            dict: 包含 mediaId, title, articleCount
        """
        url = f"{self.base_url}/accounts/{self.appid}/drafts"
        
        payload = {"articles": articles}
        response = requests.post(url, json=payload, headers=self._headers())
        
        result = response.json()
        if result.get('code') == 0:
            return result['data']
        else:
            raise Exception(f"创建草稿失败: {result}")

# 使用示例
def upload_article_from_feishu(record_id: str):
    """从飞书 Base 记录上传文章到草稿箱"""
    
    # 1. 从飞书 Base 获取文章数据
    # ... 调用 lark-cli 获取记录 ...
    
    # 2. 读取本地 article-ocr.md
    article_dir = f"~/.hermes/output/{article_title}/"
    
    # 3. 处理封面图片
    uploader = WechatDraftUploader()
    thumb_media_id = uploader.upload_cover_image(f"{article_dir}/images/cover.jpg")
    
    # 4. 组装文章数据
    articles = [{
        "title": "文章标题",
        "content": "<p>正文 HTML</p>",
        "thumbMediaId": thumb_media_id,
        "author": "Joblinker",
        "digest": "文章摘要",
        "contentSourceUrl": "https://mp.weixin.qq.com/s/xxx",
        "needOpenComment": 1
    }]
    
    # 5. 创建草稿
    result = uploader.create_draft(articles)
    print(f"草稿创建成功: {result['mediaId']}")
    
    return result
```

## 参数映射表

### 数据来源映射

| 草稿参数 | 数据来源 | 说明 |
|----------|----------|------|
| `title` | `metadata.json` → `title` | 文章标题，≤64字符 |
| `content` | `article.html` | 正文 HTML |
| `thumbMediaId` | 上传 `images/` 图片 → `/materials` API | 返回的 `mediaId` |
| `author` | 飞书 Base → `适配账号` | ≤16字符 |
| `digest` | 飞书 Base → `文章概要` | ≤128字符 |
| `contentSourceUrl` | `metadata.json` → `url` | 原文链接 |
| `needOpenComment` | 固定值 | 1（开启评论）|

### API 参数速查

**上传永久素材 `/materials`**:
| 参数 | 值 | 说明 |
|------|-----|------|
| `type` | `IMAGE` | 素材类型 |
| `name` | 文件名或自定义 | 素材名称 |
| `media` | 文件内容 | 本地图片路径（≤10MB）|

**创建草稿 `/drafts`**:
| 参数 | 限制 | 必填 |
|------|------|------|
| `title` | ≤64字符 | ✅ |
| `content` | HTML格式 | ✅ |
| `thumbMediaId` | - | ✅（news类型）|
| `author` | ≤16字符 | ❌ |
| `digest` | ≤120字符 | ❌ |
| `contentSourceUrl` | URL格式 | ❌ |
| `needOpenComment` | 0/1 | ❌ |

## 与飞书 Base 集成

### 从 Base 读取已选题文章

```bash
# 查询素材状态为"已选题"的记录
lark-cli base +record-list \
  --base-token "$FEISHU_BASE_TOKEN" \
  --table-id "$FEISHU_ARTICLE_TABLE_ID" \
  --filter '{"material_status": "已选题"}' \
  --as bot
```

### 上传成功后更新 Base 状态

```bash
# 更新素材状态为"已上传草稿"
lark-cli api PUT /open-apis/bitable/v1/apps/{base_token}/tables/{table_id}/records/{record_id} \
  --data '{"fields": {"素材状态": "已上传草稿", "草稿ID": "MEDIA_ID"}}' \
  --as bot
```

## 注意事项

### 封面图片获取逻辑

**默认行为**（未指定 `--cover` 参数时）：
1. 扫描 `images/` 目录下所有图片文件
2. 支持的格式：`.jpg`, `.jpeg`, `.png`, `.gif`
3. 按文件名排序（字母顺序）
4. 取排序后的**第一张图片**作为封面

**示例**：
```
images/
  ├── img_001.png    ← 默认选中（文件名排序第一）
  ├── img_002.png
  ├── img_003.gif
  └── banner.jpg
```

**手动指定封面**：
```bash
python upload_from_feishu.py -n 008 --cover img_003.gif
```

**注意事项**：
- 封面建议尺寸：900×500 像素
- 封面文件大小 ≤10MB（API 限制）
- GIF 动图可以作为封面，但微信可能只显示第一帧

### 1. 封面图片要求
   - 支持 JPG、PNG 格式
   - 建议尺寸：900×500 像素
   - 大小不超过 2MB

2. **正文 HTML 要求**
   - 必须使用微信支持的 HTML 标签
   - 图片必须使用 uploadimg 接口上传后的永久 URL
   - 不支持外部 CSS，需使用内联样式

3. **HTML 文件优先级（重要！）**
   上传脚本按以下优先级选择正文源文件：
   
   | 优先级 | 文件名 | 说明 | 处理方式 |
   |--------|--------|------|----------|
   | 1 | `draft/draft.html` | 草稿处理器输出（推荐）| 含标题转换、摘要生成、推广模板、投递方式隐藏等完整加工 |
   | 2 | `article_original.html` | 微信原始 HTML | 优先提取 `js_content`，回退 body |
   | 3 | `article.html` | 本地查看 HTML | 提取 body，清理多余元素 |
   | 4 | `article.md` | Markdown | 简单包裹为 pre 标签 |
   
   **⚠️ article_original.html 提取逻辑（重要！）**
   
   上传脚本对 `article_original.html` 的处理顺序：
   1. **优先提取 `<div id="js_content">` 内的内容** — 这是微信文章的实际正文容器，只包含用户可见的文章内容
   2. 如果找不到 `js_content`，回退到提取整个 `<body>`
   3. 最后移除 `<script>` 和 `<style>` 标签
   
   **为什么优先提取 js_content？**
   - 原始微信 HTML 通常包含大量无关内容：底部弹窗框架、标签预览区、脚本代码、对话框 DOM 等
   - 提取整个 `body` 会把这些垃圾标签一起上传，导致草稿内容异常
   - `js_content` 是微信官方定义的正文容器，精确包含文章图文内容
   
   **两种文章模式的差异**：
   - **正常图文模式**：`article_original.html` 很大（>100KB，甚至 1MB+），`js_content` 内含丰富段落、图片、样式
   - **长图模式**：`article_original.html` 很小（<5KB），`js_content` 内只有一张 `<img>` 标签（公众号直接以长图形式发布，无传统文字排版）
   
   **⚠️ 重要提示**：
   - `draft/draft.html` 是**草稿处理器**（`wechat-mp-draft-processor`）的输出，包含账号化加工后的完整内容（标题前缀、摘要、推广模板、投递方式隐藏），**有 draft 时优先使用**
   - 使用 `draft/draft.html` 时，脚本会自动读取同目录的 `draft/draft.json` 获取元数据（标题、摘要、作者、关键词等）
   - 图片路径自动适配：`draft.html` 中的本地图片（如 `src="images/xxx.jpg"`）实际位于 `draft/images/` 子目录，脚本会自动修正查找路径
   - `article_original.html` 是微信页面的原始 HTML，保留所有格式和样式
   - `article.html` 在部分提取版本中仅为**图片查看器**（仅含标题+图片+页脚，无任何正文文字），上传后会导致草稿只有图片没有文字
   - 如果提取工具未生成 `article_original.html`，脚本会自动回退到 `article.html`
   - 避免使用 Markdown 转换的 HTML，会导致格式丢失

4. **API 限制**
   - 单图文/多图文最多8篇
   - 标题最长64字符
   - 作者最长16字符
   - 摘要最长128字符

## 版本历史

| 版本 | 变更 |
|------|------|
| v1.0 | 初始版本，支持基础草稿创建 |
| v1.1 | 更新素材上传 API，使用 `/materials` 端点上传永久素材 |
| v1.2 | **完整流程自动化**：<br>• 自动根据【适配账号】查询【账号配置表】获取 AppID<br>• 自动处理正文图片，上传本地图片并替换为微信永久 URL<br>• 自动提取纯 URL（处理 Markdown 格式链接）<br>• 自动更新飞书 Base【文章状态】为"已上传草稿"<br>• 修复 lark-cli 文件路径问题 |
| v1.3 | **新增作者字段支持**：<br>• 从【账号配置表】读取【作者】字段作为默认作者<br>• 作者优先级：传入参数 > 账号配置 > 账号名称<br>• 优化正文内容清理：移除标题、meta信息、footer |
| v1.4 | **修复图片间距问题**：<br>• 清理图片 margin 样式，保持原文章连续布局<br>• 优化 contentSourceUrl 默认为空<br>• 优化 needOpenComment 默认为 1（开启） |
| v1.5 | **新增图片压缩功能**：<br>• 自动压缩超过 1MB 的图片<br>• 使用 macOS sips 命令行工具<br>• 支持 PNG/JPG 格式自动转换和压缩<br>• 添加调试输出检查图片替换状态 |
| v1.7 | **图片压缩改为可选参数**：<br>• 添加 `--compress` / `-z` CLI 参数<br>• 默认不压缩图片（compress=False）<br>• 需要压缩时显式添加参数启用<br>• 修改 `upload_material()` 和 `upload_from_feishu()` 函数签名 |
| v1.8 | **智能编号查询**：<br>• 支持 `--no` / `-n` 参数使用文章编号（如 NO.008）<br>• 自动根据 `ID` 字段查询 record_id<br>• 支持简写格式（008 自动转为 NO.008）<br>• `--record-id` 和 `--no` 互斥，二选一即可 |
| v1.9 | **智能封面选择**：<br>• 基于 OCR 内容自动选择最佳封面<br>• 排除 GIF 动图、超长图、纯文字图<br>• 关键词匹配：招聘/校招/公司/Logo 加分<br>• 尺寸优化：优先 900x500 比例<br>• 兜底：第一张非动图<br>• 支持 `--cover` 参数手动指定 |
| v1.10 | **API 限制修正**：<br>• 摘要长度限制从 128 修正为 **120 字符**（微信 API 实际限制）<br>• 文件大小限制提升为 **10MB**（API 已优化） |
| v1.11 | **新增 article_original.html 支持**，优先使用微信原始 HTML<br>• 修复 `article.html` 被 Markdown 转换版本覆盖的问题<br>• 上传脚本优先读取 `article_original.html`，保留完整格式<br>• 提取工具修复调用顺序，确保原始 HTML 先生成 |
| v1.12 | **新增 article_id 精确匹配**：<br>• `find_article_directory()` 新增 `article_id` 参数<br>• 优先通过文章ID精确匹配本地目录（8位UUID）<br>• 回退到标题匹配（兼容旧版本数据）<br>• 改进引号处理，支持中英文引号差异匹配<br>• 解决标题特殊字符导致的目录查找失败问题 |
| v1.13 | **⭐ 新增文章ID和上下文检测支持**：<br>• 支持 `--article-id` / `-aid` 参数直接使用文章ID（如 `7907d7cb`）<br>• 支持 `--context` / `-ctx` 参数自动检测上下文（最近同步的文章）<br>• 新增 `find_record_by_article_id()` 函数通过文章ID查找飞书记录<br>• 新增 `find_latest_article_in_context()` 函数智能检测最近有效文章<br>• 四种定位方式互斥：文章编号 / 记录ID / 文章ID / 上下文检测<br>• 简化用户操作：提取文章后可直接用 `--context` 上传，无需记住ID |
| **v1.14** | **⭐ 支持多账号上传**：<br>• 自动上传到【适配账号】中所有配置有效的公众号<br>• 正文图片只上传一次（第一个账号），后续账号复用 URL<br>• 每个账号独立上传封面获取 thumbMediaId<br>• 飞书 Base【草稿ID】字段记录所有账号的草稿ID<br>• 输出格式更新：显示成功/失败统计和各账号结果 |
| **v1.16** | **⭐ 新增常见问题解决方案**：<br>• 添加"找不到文章目录"问题的诊断和解决<br>• 添加"缺少 API Key"问题的诊断和解决<br>• 添加工作流集成指南（提取→复制→上传）<br>• 强调环境变量必须使用 `export` 导出 |
| **v1.17** | **⭐ 修复 article_original.html 提取逻辑**：<br>• 优先从 `<div id="js_content">` 提取正文，而不是整个 `body`<br>• 解决了提取 `body` 时连带上传底部弹窗框架、脚本代码等垃圾标签的问题<br>• 识别长图模式文章（`article_original.html` <5KB，`js_content` 内只有一张图片）<br>• 无 `js_content` 时自动回退到 `body` 提取 |
| **v1.18** | **⭐ 修复图片上传三大严重bug**（通过与已发布文章 diff 定位）：<br>• **Bug 1**: 步骤5正则只替换 `src` 属性，漏掉 `data-src` 属性，导致微信懒加载/预览时图片无法显示<br>• **Bug 2**: 远程CDN图片（GIF动图、推广模板GIF）被当作"已有远程URL"跳过处理，但微信草稿API**不会自动保留外部域名图片**，导致发布后这些图片完全丢失<br>• **Bug 3**: `data-src` 和 `src` 不一致的图片（如 `http://` vs `https://`）需统一处理<br>• **修复方案**: ① 替换 `src` 时同时替换 `data-src`；② 将所有远程图片（包括GIF）下载为本地文件后再上传；③ 推广模板图片使用 mediaId 方式引用 |
| **v1.19** | **⭐ 修复远程图片下载与格式兼容性问题**：<br>• 添加 `Referer: https://mp.weixin.qq.com/` header，解决微信CDN图片下载被62d拒问题<br>• 自动检测并转换 webp 格式为 PNG（微信 `/materials` 接口不支持 webp）<br>• 优化错误提示，区分"积分不足"和"文件格式不支持"<br>• **依赖**: 需要安装 Pillow 库以支持 webp 自动转换 (`pip install Pillow`) |
| **v1.20** | **⭐ 修复远程图片格式识别错误导致上传失败**：<br>• 微信CDN远程图片URL无路径扩展名，脚本默认保存为 `.jpg`，导致实际格式（GIF/PNG/WEBP）与声明格式不匹配<br>• 优先从 `wx_fmt=gif|png|jpg|jpeg|webp` URL参数推断正确扩展名<br>• 下载后用 Pillow `Image.open().format` 检测真实格式，不匹配则自动重命名<br>• `upload_material` 中增加文件头签名兜底：用 magic bytes 覆盖 `mimetypes.guess_type()` 结果<br>• 清理旧的错误临时文件后重新下载即可生效 |
| **v1.22** | **⭐ 修复多账号上传时推广模板错乱问题**（重要！）：<br>• **Bug**: 上传多个账号时所有账号共用第一份草稿的 `content`，导致第二个及以后账号错误使用第一个账号的推广模板<br>• **根因**: `draft/draft.html` 只生成/读取一次，循环上传时未按账号重新生成<br>• **修复**: ① 添加 `ACCOUNT_NAME_MAP` 将飞书显示名映射为 `process.py` 账号 key；② 上传循环中对第2+个账号删除旧 draft 并重新运行 `process.py --account {key}` 生成独立草稿；③ 独立处理每个账号的新增图片并替换 URL<br>• 确保 Joblinker、行研实习等不同账号各自使用正确的推广模板 |
| **v1.21** | **⭐ 自动草稿处理器前置检查**（本次更新）：<br>• 上传脚本在读取正文前，自动检测 `draft/draft.html` 是否存在<br>• 不存在时**自动调用草稿处理器** `process.py` 生成处理后的草稿<br>• 解决了"忘记运行处理器导致上传文章缺少推广模板"的潜在风险<br>• 处理失败时回退到原始HTML上传，并提示可能缺少推广模板 |

---

## Troubleshooting

### 常见错误

#### 1. "未找到记录" 或字段值为空

**原因**: lark-cli 返回的数据格式特殊，字段名和记录数据是分开的数组。

**解决**: 代码已处理此格式，确保 `query_records()` 正确映射字段名到值。

#### 2. "找不到账号配置"

**原因**: 字段名不匹配。飞书 Base 使用中文字段名。

**检查**: 确认【账号配置表】字段名为：
- `公众号ID` (不是 `AppID`)
- `作者` (不是 `author`)

#### 3. "Invalid url" 错误

**原因**: `contentSourceUrl` 包含 Markdown 格式或特殊字符。

**解决**: 代码已自动提取纯 URL：
```python
url_match = re.search(r'https?://[^\s\[\]()<>"{}|\\^`\[\]]+', article_url_raw)
article_url = url_match.group(0) if url_match else article_url_raw
```

#### 7. 上传后草稿只有图片没有文字（严重！）

**现象**:
- 上传的草稿只有标题和图片，正文区域空白或只有"提取自微信公众号"字样
- 文章字符数极少（可能只有 1-2KB，正常应该几十到几百 KB）

**原因**: `upload_draft.py` 读取了错误的 HTML 文件。提取工具生成的 `article.html` 在某些版本中仅为**图片查看器**（展示图片的 HTML 页面），不含任何正文文字内容。真正的微信原始 HTML 保存在 `article_original.html` 中。

**诊断**: 检查文章目录下的文件大小：
```bash
ls -lh ~/.hermes/output/文章标题/
# 异常：article.html 只有 2KB，article_original.html 有 3.7MB
```

**解决**:
1. **修复上传脚本**（已修复）：`upload_draft.py` 现已优先检查 `article_original.html`：
   ```python
   html_path = article_path / "article_original.html"
   if not html_path.exists():
       html_path = article_path / "article.html"
   ```
2. **临时解决**：手动指定 `article_original.html` 作为内容源
3. **重新提取**：确保提取工具生成了 `article_original.html`

**预防**:
- `upload_from_feishu.py` 主脚本已正确处理（优先 `article_original.html`）
- 如果直接使用 `upload_draft.py`，请确保版本 >= v1.17（包含此修复）
- 每次提取后检查 `article_original.html` 是否存在且大小合理（通常 >100KB）

#### 8. "找不到文章目录"或"未找到编号为 NO.xxx 的文章"

**原因**: 提取工具输出目录与上传脚本查找目录不一致。
- 提取工具默认输出到: `/tmp/test_output/`
- 上传脚本默认查找: `~/.hermes/output/`

**解决**: 将文章从提取目录复制到上传目录：
```bash
# 复制文章目录
cp -r /tmp/test_output/{article_id} ~/.hermes/output/

# 或使用 Python
import shutil
shutil.copytree(f"/tmp/test_output/{article_id}", f"~/.hermes/output/{article_id}")
```

**预防**: 在提取文章后立即复制到 `~/.hermes/output/` 目录。

#### 9. 文章上传到了错误的账号（适配账号与预期不符）

**现象**:
- 运行上传脚本后发现草稿出现在错误的公众号（如 Joblinker 而不是 行研实习）
- `--author` 参数无法改变目标账号，只会改变显示的作者名

**原因**: 上传脚本的目标账号**严格由飞书 Base【适配账号】字段决定**，脚本会通过该字段查询【账号配置表】获取 AppID。`--author` 参数仅覆盖草稿的 `author` 显示字段，不影响上传到哪个公众号。

**解决 — 手动切换目标账号**:

如果 Base 中的【适配账号】设置错误，需要先用 `lark-cli` 更新记录，再重新上传：

```bash
# 1. 更新【适配账号】和【文章状态】
cd ~/.hermes/skills/web/wechat-mp-draft-uploader
cat > update_account.json << 'EOF'
{
  "适配账号": ["目标账号名称"],
  "文章状态": ["待上传"]
}
EOF

lark-cli base +record-upsert \
  --base-token <base_token> \
  --table-id <文章素材表ID> \
  --record-id <record_id> \
  --json @update_account.json \
  --as bot

# 2. 重新执行上传
python scripts/upload_from_feishu.py --article-id <article_id> --compress
```

**注意**:
- JSON 文件必须使用**相对路径**（如 `@update_account.json`），不能是绝对路径（如 `@/tmp/xxx.json`）
- `lark-cli` 必须在 JSON 文件所在目录下执行
- 同时需要将【文章状态】改回 "待上传"，否则脚本会跳过已上传的记录

**预防**:
- 上传前务必确认 Base 中【适配账号】字段是否正确
- 若需同一篇文章上传到多个账号，应先在 Base 中将【适配账号】设为多选包含所有目标账号，再执行一次上传
- 目前脚本不支持 `--account` 参数覆盖目标账号，必须通过修改 Base 记录来切换

#### 5. "缺少 API Key" 或 "JIANLIZHIZUO_API_KEY not set"

**原因**: 环境变量未设置。

**解决**: 设置环境变量后重新运行：
```bash
export JIANLIZHIZUO_API_KEY=sk-xxxxxxxxxxxxxxxx
python upload_from_feishu.py -n 008
```

或在 Python 中设置：
```python
import os
os.environ['JIANLIZHIZUO_API_KEY'] = 'sk-xxxxxxxxxxxxxxxx'
```

#### 6. 图片之间有间距（不连续）

**原因**: 提取的 HTML 中图片有 `margin: 10px 0` 样式。

**解决**: 代码已清理 margin：
```python
# 清理图片间距：移除图片的 margin 样式，保持图片紧密连续
content = re.sub(r'<img([^>]*?)\s*margin:\s*[^;"]*;?\s*', r'<img\1', content, flags=re.IGNORECASE)
content = re.sub(r'<img([^>]*?)style=["\']([^"\']*?)\s*margin:\s*[^;"]*;?\s*([^"\']*?)["\']', r'<img\1style="\2\3"', content, flags=re.IGNORECASE)
content = re.sub(r'<img([^>]*?)style=["\']\s*["\']', r'<img\1', content, flags=re.IGNORECASE)
```

#### 6. "413 Request Entity Too Large" 图片上传失败

**原因**: 图片文件超过 API 限制（通常 >1MB）。

**解决**: 代码已自动压缩超过 1MB 的图片（详见上方代码）。

#### 7. 上传后文章格式丢失/错乱

**现象**: 
- 上传的草稿只有几千字符（正常应该几万字符）
- 文章结构丢失，只有纯文本
- 图片显示正常但文字格式错乱

**原因**: `article.html` 被 Markdown 转换版本覆盖，而非微信原始 HTML。

**诊断**: 检查文章目录下的文件：
```bash
ls -la ~/.hermes/output/文章标题/
```

**正常情况**:
```
article.html              # 微信原始 HTML（6万+ 字符）
article.md                # Markdown 版本
metadata.json             # 元数据
images/                   # 图片目录
```

**异常情况**:
```
article.html              # Markdown 转换的 HTML（2千字符）⚠️
article.md                # Markdown 版本
...
```

**解决**: 
1. **重新提取文章**（推荐）：使用修复后的提取工具重新抓取
2. **手动修复**（应急）：从微信页面重新抓取原始 HTML 替换

**预防**: 
- 确保提取工具版本 ≥ v1.11
- 上传脚本会自动优先使用 `article_original.html`（如果存在）
- 定期检查 `article.html` 文件大小（原始 HTML 通常 >30KB）

---

#### 10. "找到多个文章ID为 xxx 的文章，请使用 record_id 直接指定"

**现象**:
- 使用 `--article-id aeb220f3` 上传时，脚本报错并拒绝执行
- 同一篇原始微信文章可能包含多个招聘岗位，在 Base 中被拆分为多条记录

**原因**: 飞书 Base 中【文章ID】字段对应原始微信文章的 URL hash，多条记录（不同岗位）可能共享同一个 `article_id`。

**解决**: 改用 `--record-id` 精确指定单条记录：
```bash
# 先查询对应的 record_id
lark-cli api GET /open-apis/bitable/v1/apps/{base_token}/tables/{table_id}/records --page-size 500 --as bot | jq '.data.items[] | select(.fields."文章ID"=="aeb220f3") | {record_id, title}'

# 再用 record_id 上传
python upload_from_feishu.py --record-id recvifXrBg7PEA
```

**预防**:
- 当一篇文章包含多个岗位时，优先使用 `--record-id` 而非 `--article-id`
- 在飞书 Base 中通过【文章标题】区分不同岗位记录

---

#### 11. "找不到图片目录: /xxx/images" 导致上传失败

**现象**:
- 步骤 6 "处理封面图片" 报错：`找不到图片目录: ~/.hermes/output/{article_id}/images`
- 文章正文中有图片（`draft.html` 包含 `<img src="http://mmbiz.qpic.cn/...">`），但本地没有 `images/` 文件夹

**原因**: 
- 原始微信文章使用了远程图片 URL（`mmbiz.qpic.cn`），提取工具未生成本地 `images/` 目录
- 草稿处理器（`wechat-mp-draft-processor-pro`）检测到无本地图片后跳过了图片处理步骤
- 但上传脚本仍需要本地图片文件来上传封面

**解决**: 手动从 `draft.html` 中提取远程图片 URL 并下载为封面：
```python
import re, requests
from pathlib import Path

article_dir = Path.home() / ".hermes/output/aeb220f3"
draft_html = (article_dir / "draft" / "draft.html").read_text(encoding='utf-8')

# 提取所有 mmbiz 图片 URL
urls = re.findall(r'https?://[^\s"\'<>]+mmbiz[^\s"\'<>]*\.png', draft_html)

# 下载第一张作为封面
images_dir = article_dir / "images"
images_dir.mkdir(exist_ok=True)
resp = requests.get(urls[0].replace("&amp;", "&"))
(images_dir / "cover.png").write_bytes(resp.content)
```

然后重新执行上传命令。

**长期修复建议**:
- 上传脚本应增强：当 `images/` 不存在但 `draft.html` 含远程图片时，自动下载一张作为封面
- 或在草稿处理器中增加"无本地图片时下载远程封面"的兜底逻辑

**预防**:
- 上传前检查 `images/` 目录是否存在：`ls ~/.hermes/output/{article_id}/images/`
- 若不存在，提前从 `draft.html` 中的远程 URL 下载备用封面
```python
def _compress_image(self, file_path: str, max_size: int = 1024 * 1024) -> str:
    """压缩图片到指定大小以下"""
    import subprocess
    
    temp_path = file_path + ".compressed.jpg"
    width = 1200  # 初始宽度
    quality = 80
    
    while width > 400:
        cmd = [
            'sips', '-Z', str(width),
            '-s', 'format', 'jpeg',
            '-s', 'formatOptions', str(quality),
            file_path,
            '--out', temp_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(temp_path):
            if os.path.getsize(temp_path) <= max_size:
                return temp_path
            
            # 如果还是太大，降低质量或尺寸
            if quality > 50:
                quality -= 10
            else:
                width = int(width * 0.8)
                quality = 80
    
    return None
```

**特点**:
- 使用 macOS 原生 `sips` 命令，无需额外依赖
- 自动转换为 JPEG 格式（处理 PNG 透明通道）
- 逐步降低质量和尺寸直到符合大小限制
- 保持图片比例

### 调试技巧

1. **查看字段列表**:
```python
feishu = FeishuClient(base_token)
items = feishu.query_records(table_id, limit=10)
print(f"字段: {list(items[0].keys())}")
```

2. **测试单个 API 调用**:
```python
import requests
url = f"https://mp.jianlizhizuo.cn/v1/accounts/{appid}/drafts"
response = requests.post(url, json={"articles": articles}, headers=headers)
print(f"状态码: {response.status_code}")
print(f"响应: {response.text}")
```

3. **检查本地文章目录**:
```python
from upload_from_feishu import find_article_directory
dir = find_article_directory("文章标题")
print(f"目录: {dir}")
```

---

#### 12. "积分不足，需要 1 积分，当前余额 0" 或 "unsupported file type"

**现象**:
- 远程图片处理失败，提示"积分不足"或"文件格式不支持"
- 上传的草稿中某些图片保留了原始远程URL（mmbiz.qpic.cn），未替换为微信永久URL
- 发布后这些图片可能无法显示

**原因**:
- **积分不足**: 简立制作平台的API调用需要消耗积分，积分耗尽后无法继续上传
- **文件格式不支持**: 微信CDN返回的图片实际为 **webp 格式**（即使URL参数写着 `wx_fmt=png`），但微信 `/materials` 接口不支持 webp 格式
- 缺少 `Referer` header: 某些微信CDN图片需要 `Referer: https://mp.weixin.qq.com/` 才能下载

**解决**:

1. **充值积分**:
   - 登录简立制作平台: https://mp.jianlizhizuo.cn
   - 进入"我的账户" → "充值"
   - 充值完成后重新执行上传

2. **安装 Pillow 库** (处理 webp 转换):
   ```bash
   pip install Pillow
   ```

3. **修复后重新上传**:
   修复后的脚本会自动处理 webp 转换和 Referer header，重新执行即可：
   ```bash
   python upload_from_feishu.py --article-id <article_id>
   ```

**预防**:
- 定期检查简立制作平台积分余额
- 确保环境已安装 Pillow: `python -c "from PIL import Image; print('Pillow OK')"`
- 上传前检查日志中是否有"检测到 WEBP 格式，已转换为 PNG"提示

---

#### 14. 多账号上传时各账号推广模板一样（错误使用同一套模板）

**现象**:
- 同一篇文章上传到多个公众号（如 Joblinker 和 行研实习）
- 两个账号的草稿都显示同一套推广模板（如都显示"回复关键词"或都显示"点击名片"）
- 实际上两个账号的模板应该不同（如 Joblinker 用"点击名片"，行研实习用"回复关键词"）

**根因**:
- `draft/draft.html` 只在第一个账号上传前生成一次
- 上传循环中第二个及以后账号复用了第一个账号的 `content`
- `飞书 Base 适配账号名称`（如 "行研实习"）与 `process.py` 的账号 key（如 "xingyan_shixi"）不匹配，导致第一次自动调用 process.py 时传递了错误的 --account 参数

**解决** (v1.22+ 自动处理):
- 上传脚本已修复，为每个账号独立重新生成 draft.html
- 确保脚本版本 >= v1.22，然后重新上传即可

**手动修复**（若脚本未更新）:
```bash
# 1. 分别为每个账号单独生成 draft
python process.py ARTICLE_ID --account joblinker
# 拷贝第一个账号的结果备份
cp draft/draft.html draft/draft_joblinker.html

cp -r draft/images draft/images_joblinker

# 清除旧 draft
rm draft/draft.html draft/draft.json

# 生成第二个账号的 draft
python process.py ARTICLE_ID --account xingyan_shixi
cp draft/draft.html draft/draft_xingyan.html
cp -r draft/images draft/images_xingyan
```

**预防**:
- 确保 `upload_from_feishu.py` 版本 >= v1.22（包含 `ACCOUNT_NAME_MAP` 和每账号独立重新生成 draft 的逻辑）
- 上传前检查日志中是否有 "正在为 XXX 重新生成草稿..." 提示
- 若添加了新账号，请在 `ACCOUNT_NAME_MAP` 中补充映射关系

---

#### 13. 草稿箱内容缺少图片（特别是 GIF 动图）

**现象**:
- 上传的草稿正文缺少部分图片（如 GIF 动图、部分 PNG）
- 本地 `images/` 目录下图片存在且大小正常
- 同篇文章部分图片能显示，部分不能

**根因**: 微信 CDN 远程图片 URL 格式与**实际返回的文件格式不一致**。微信 CDN URL 的路径中没有文件扩展名（如 `mmbiz.qpic.cn/mmbiz_gif/xxx`），脚本从 URL 路径提取扩展名得到空字符串，默认回退为 `.jpg`。上传时 `mimetypes.guess_type('.jpg')` 推断 MIME 为 `image/jpeg`，但实际下载的文件可能是 GIF/PNG/WEBP，MIME 与文件内容严重不匹配，微信 `/materials` API 拒绝上传或上传后无法渲染。

**诊断**: 检查临时下载的远程图片格式是否与扩展名匹配：
```python
from pathlib import Path

temp_dir = Path.home() / ".hermes/output/ARTICLE_ID/.temp_remote_images"
for f in sorted(temp_dir.glob("remote_*")):
    header = f.read_bytes()[:12]
    if header[:6] in (b'GIF89a', b'GIF87a'):
        actual = 'GIF'
    elif header[:8] == b'\x89PNG\r\n\x1a\n':
        actual = 'PNG'
    elif header[:2] == b'\xff\xd8':
        actual = 'JPEG'
    elif header[:4] == b'RIFF' and header[8:12] == b'WEBP':
        actual = 'WEBP'
    else:
        actual = 'UNKNOWN'
    match = "✅" if f.suffix.upper() == f".{actual}" else "❌ 不匹配!"
    print(f"{f.name}: 声明={f.suffix} 实际={actual} {match}")
```

**解决** (v1.20+ 自动处理)：
修复后的脚本自动处理步骤：
1. 优先从 URL 参数 `wx_fmt=gif|png|jpg|jpeg|webp` 推断正确扩展名
2. 下载后用 Pillow `Image.open().format` 检测真实格式，不匹配则自动重命名
3. `upload_material` 中增加文件头签名（magic bytes）兜底，覆盖 `mimetypes.guess_type()` 结果
4. WEBP 格式自动转换为 PNG

**即刻恢复**: 
```bash
# 1. 清理旧的错误临时文件
rm -rf ~/.hermes/output/ARTICLE_ID/.temp_remote_images

# 2. 重新执行上传（会重新下载并使用正确格式）
python upload_from_feishu.py --article-id ARTICLE_ID
```

**预防**:
- 确保脚本版本 >= v1.20（包含格式修正逻辑）
- 上传前检查日志中是否有"格式修正: XXX -> remote_xxx.ext"提示
- 微信 CDN 图片实际格式与 URL 路径标记不一致是常见现象，不要依赖路径标记判断格式

## 相关资源

- 简立制作平台：https://mp.jianlizhizuo.cn
- 微信公众号官方文档：https://developers.weixin.qq.com/doc/offiaccount/
