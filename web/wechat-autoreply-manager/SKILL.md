---
name: wechat-autoreply-manager
description: >
  微信公众号自动回复规则管理 Skill。
  在文章上传草稿完成后，自动分析【投递方式】字段，
  询问用户是否创建自动回复规则。
  支持文字回复（日期关键词）和图片回复（企业简称关键词）。
required_env_vars:
  - JIANLIZHIZUO_API_KEY  # 简立制作平台 API Key
---

# 微信公众号自动回复规则管理 Skill

## 功能概述

在 `wechat-mp-draft-uploader` 上传草稿完成后，自动：
1. 读取【投递方式】字段
2. 判断是文字投递还是图片投递
3. 询问用户是否创建自动回复规则
4. 批量创建到所有成功上传的账号

## 触发时机

上传脚本 `upload_from_feishu.py` 执行完成后，自动检查并询问。

## 快速使用（命令行）

### 预览模式（推荐）

```bash
# 先预览计划内容
python ~/.hermes/skills/web/wechat-autoreply-manager/scripts/create_autoreply.py <article_id> --preview
```

### 执行创建（确认后）

```bash
# 用户确认后执行
python ~/.hermes/skills/web/wechat-autoreply-manager/scripts/create_autoreply.py <article_id> --execute
```

### 手动指定企业简称（当自动提取不准时）

```bash
# 使用 --company 参数强制指定企业简称，优先级最高，跳过AI提取和自检
python ~/.hermes/skills/web/wechat-autoreply-manager/scripts/create_autoreply.py <article_id> --execute --company "上海电气"
```

**适用场景**：
- 标题含有招趣号、宣传语，AI提取偏离企业名如"年优秀实"、"立足上海"、"以梦为弦"
- 多个品牌名组合标题，需要指定特定部分（如 "邮储银行" 而非 "天津分行"）

**v2.0 新增功能：**
- **预览确认**：创建先展示计划内容（关键词、回复内容），用户确认后才执行
- **企业简称自检**：AI提取简称后自动检查，含有"校招"、"招聘"等无效词时自动修正
- **--company 手动覆盖**：命令行直接指定企业简称，强制覆盖自动提取结果

**示例：**
```bash
# 展示计划内容
python ~/.hermes/skills/web/wechat-autoreply-manager/scripts/create_autoreply.py 94a8aacd --preview

# 确认后执行
python ~/.hermes/skills/web/wechat-autoreply-manager/scripts/create_autoreply.py 94a8aacd --execute

# 自动提取失败时手动指定
python ~/.hermes/skills/web/wechat-autoreply-manager/scripts/create_autoreply.py 94a8aacd --execute --company "薯片公司"
```

脚本会自动执行：查询文章 → 提取企业简称 → 自检修正 → 判断投递类型 → 检查现有规则 → 创建/追加规则 → 更新Base状态

## 交互流程（v2.0 预览确认）

```
upload_from_feishu.py 执行完成（所有账号上传成功）
    ↓
调用 create_autoreply.py --preview 获取计划内容
    ↓
展示预览：
   【企业简称】原始提取: xxx → 自动修正: yyy → 最终使用: zzz
   【投递方式】类型: 文字/图片
   【即将创建的规则】关键词: xxx ，回复内容: xxx
    ↓
询问用户确认
    ↓
用户响应：
    ├── "是" → 运行 create_autoreply.py --execute 批量创建到所有账号
    ├── "否" → 跳过
    └── "修改 xxx" → 使用自定义关键词/企业简称创建
```

## 多条内容格式

当同一关键词有多篇文章时，使用优化格式（无"投递方式："前缀，双换行分隔保留空行）：

```
洛书投资
官网直投：https://www.luoshu.com/join-us；投递邮箱：recruit@luoshu.com（标题：简历-暑期实习-姓名-学校）

恒丰银行
邮箱投递: whzhaopin@hfbank.com.cn
```

**格式特点**：
- 无"投递方式："前缀，更简洁
- 无分隔线（---）
- 使用双换行符（`\n\n`）分隔不同文章，保留一个空行
- 阅读更清晰

## 文字回复特殊处理（v1.6）

**追加逻辑**：

创建文字回复前，系统会：
1. 查询该账号的关键词回复列表
2. 检查是否已有相同关键词的规则
3. 如果有且是**2天内创建**的 → **追加内容**到现有规则
4. 否则 → **创建新规则**

**追加格式**：
```
企业A
投递方式: xxx

企业B
投递方式: xxx
```

**示例**：
- 4月24日创建了关键词"0424"的规则：腾讯招聘
- 4月25日再创建"0424"规则 → 自动追加到4月24日的规则中
- 4月27日再创建"0424"规则 → 创建新规则（超过2天）

**图片回复**：始终创建新规则（不追加）

## 企业简称提取 v2.0（自检+修正）

### 自检机制

v2.0 新增自动检查机制，确保企业简称合理：

1. **提取后检查**：AI提取简称后，系统自动检查是否包含无效词
2. **无效词库**：校招、招聘、实习、校园、暑期、春季、秋季、2026、2027、2025、岗位、正式、启动、届
3. **自动修正**：检测到无效词时，按以下优先级修正：
   - **策略0**：缩短原始提取结果（如"南航届校"→"南航"）
   - **策略1**：滑动窗口查找不含无效词的4个字
   - **策略2**：找企业名后缀（公司/集团/银行/证券等）
   - **策略3**：取第一个无效词之前的所有字
4. **用户确认**：修正结果在预览中展示，用户确认后才使用

### 修正示例

| 标题 | 原始提取 | 自检结果 | 自动修正 | 最终使用 |
|---------|-----------|---------|---------|---------|
| 校招｜中国电子2026届春季校园招聘 | 校招中国 | ❌ 含无效词 | 校招中国 | 中国电子 |
| 南航2026届校园招聘热招岗位合集 | 南航届校 | ❌ 含无效词 | 南航届校 → 南航 | 南航 |
| 三一集团【星辰计划】2027届... | 三一集团 | ✅ 通过 | - | 三一集团 |
| 洛书投资Summer Intern火热招聘中 | 洛书投资 | ✅ 通过 | - | 洛书投资 |

### 与上传脚本的集成

`upload_from_feishu.py` 上传完成后，会自动调用 `--preview` 模式获取计划内容，然后展示给用户：

```
🤖 询问: 是否创建自动回复规则？

文章: 南航2026届校园招聘热招岗位合集
适配账号: 研究生求职圈

--- 预览内容 ---
自动回复规则: 5da320d5 [preview模式]

【企业简称】
   原始提取: 南航届校
   自动修正: 南航
   最终使用: 南航
   自检状态: ⚠️ 原始提取'南航届校'自检不通过（含有'届'），已自动修正为'南航'

【即将创建的规则】
   关键词: 0427
   回复类型: 文字
   回复内容:
   南航
   官网 https://job.csair.cn
---

回复 '是' 自动创建，回复 '否' 跳过
```

用户确认后，Hermes 运行 `create_autoreply.py --execute` 执行创建。

### 手动修正（当自动修正不满意时）

当自动修正结果仍不理想时，有两种方式手动覆盖：

**1. 对话式修正**：用户回复 `"xxx"` 使用自定义企业简称。

**2. 命令行修正**（批量/脚本场景推荐）：
```bash
# 使用 --company 参数强制指定，优先级最高
python ~/.hermes/skills/web/wechat-autoreply-manager/scripts/create_autoreply.py <article_id> --execute --company "上海电气"
```

**--company 使用示例**：
```bash
# 标题含宣传语，自动提取偏离企业名
# 原标题: "芯光汇聚，筑梦未来 | 2026年优秀实习生计划正式启动"
# 自动提取: "年优秀实" → 手动修正: --company "芯朋微"

# 标题以地理位置开头
# 原标题: "立足上海，奔赴全球：上海电气国际化业务实习生招募"
# 自动提取: "立足上海" → 手动修正: --company "上海电气"

python ~/.hermes/skills/web/wechat-autoreply-manager/scripts/create_autoreply.py 1b50ce19 --execute --company "上海电气"
python ~/.hermes/skills/web/wechat-autoreply-manager/scripts/create_autoreply.py d4b5be71 --execute --company "邮储银行"
python ~/.hermes/skills/web/wechat-autoreply-manager/scripts/create_autoreply.py 272090a8 --execute --company "CVTE"
```

## 关键词使用规则

| 回复类型 | 默认关键词 | 说明 |
|---------|-----------|------|
| **文字回复** | 当天日期（如`0424`） | 日期唯一，避免冲突 |
| **图片回复** | 企业简称（如`华夏久盈`） | 直观好记，用户输入企业名即可 |

### 文字回复使用日期关键词的原因

1. **避免冲突**：同一日期可能有多篇文章，使用日期作为关键词统一管理
2. **简洁易记**：4位数字，用户容易输入
3. **时效性**：日期与文章发布时间对应，符合阅读习惯

### 图片回复使用企业简称的原因

1. **直观好记**：用户看到企业名就能想到回复
2. **品牌识别**：企业简称通常具有品牌辨识度
3. **长期有效**：企业简称不会随时间变化

### 示例

| 文章 | 投递方式 | 回复类型 | 关键词 |
|------|---------|---------|--------|
| 腾讯2026校园招聘 | 邮箱投递 | 文字 | `0424` |
| 华夏久盈实习招聘 | 扫码投递 | 图片 | `华夏久盈` |
| 敦和资管春季招聘 | 邮箱投递 | 文字 | `0425` |

## 询问示例

### 文字投递

```
📄 文章：《腾讯2026校园招聘》
📮 投递方式：文字（邮箱/链接）
━━━━━━━━━━━━━━
原文：发送简历至 campus@tencent.com

💡 建议创建自动回复（将应用到3个账号）：
   关键词：0424（当天日期）
   回复内容：
   ──────────────
   腾讯
   邮箱投递: campus@tencent.com
   ──────────────

是否创建？（是 / 否 / 修改）
```

**说明**：文字回复使用**当天日期**（如0424）作为关键词，避免企业名称冲突，统一管理。

### 图片投递

```
📄 文章：《腾讯2026校园招聘》
📮 投递方式：图片（二维码）
━━━━━━━━━━━━━━
从 article-ocr.md 找到匹配图片：img_003.png

💡 建议创建自动回复（将应用到3个账号）：
   关键词：腾讯（企业简称）
   回复内容：该二维码图片

是否创建？（是 / 否 / 修改关键词）
```

## 核心模块

| 模块 | 功能 |
|------|------|
| `create_autoreply.py` | **一键创建脚本**（新增） |
| `delivery_classifier.py` | 判断投递方式类型（文字/图片） |
| `company_extractor.py` | 从标题提取企业简称（优先2字） |
| `ocr_image_finder.py` | 从 article-ocr.md 找投递图片 |
| `autoreply_api.py` | 简立制作 API 封装 |
| `ask_autoreply.py` | 主询问逻辑和执行 |
| `feishu_base_updater.py` | 飞书Base状态更新 |

## 图片类型判断规则

**优先级（从高到低）：**

1. **文字类型优先**：包含有效链接（非公众号链接）或邮箱 → 文字类型
2. **图片类型**：包含图片关键词 → 图片类型
3. **默认**：文字类型

**图片关键词**（满足则判定为图片类型）：
- `关注公众号`（但如果只有公众号链接，不算）
- `扫码`
- `二维码`
- `扫描`
- `添加微信`
- `微信投递`
- `进群`
- `加群`

**文字类型特征**（优先判定）：
- 包含 `http/https` 链接（非 `mp.weixin.qq.com`）
- 包含邮箱地址 `@xxx.com`

**示例**：
- `扫码投递或访问 https://xxx.com` → **文字类型**（链接优先）
- `关注公众号或发送简历至 hr@xxx.com` → **文字类型**（邮箱优先）
- `扫码关注公众号` → **图片类型**
- `关注公众号 https://mp.weixin.qq.com` → **图片类型**（只有公众号链接）

## 企业简称提取规则 v2.0（AI驱动）

**提取方式**：优先使用AI提取，规则兜底

### AI提取Prompt

当需要提取企业简称时，系统会生成如下Prompt供AI处理：

```
从以下招聘文章标题中提取企业简称（2-4个字）：

标题："久候未来 盈在今夏丨华夏久盈2027届应届生暑期实习招募正式开启"

要求：
1. 只返回企业简称，不要解释
2. 简称应该是人们熟知的品牌名或公司名
3. 长度2-4个字
4. 不要包含"招聘"、"校招"、"实习"等字样
5. 不要包含年份、届数

示例：
- "腾讯2026校园招聘" → "腾讯"
- "字节跳动2026届春季校园招聘" → "字节跳动"
- "久候未来 盈在今夏丨华夏久盈2027届应届生暑期实习招募" → "华夏久盈"
- "实习招聘 | 洛书投资2026暑期实习" → "洛书投资"
- "【校招】华为2026届应届生招聘" → "华为"

请直接输出企业简称：
```

### 使用方式

**方式1：AI提取（推荐）**
```python
result = ask_create_autoreply(record_id, title, delivery, accounts)

if result['action'] == 'need_ai_extraction':
    # 使用AI提取企业简称
    ai_prompt = result['prompt']
    # 将prompt发送给AI获取回复
    company_short = ai_response.strip()
    
    # 再次调用，传入企业简称
    result = ask_create_autoreply(
        record_id, title, delivery, accounts, 
        company_short=company_short
    )
```

**方式2：规则兜底**
```python
from company_extractor import extract_and_shorten

company_short = extract_and_shorten(title, use_ai=False)
```

### 提取示例

| 标题 | AI提取 | 规则提取 |
|------|--------|----------|
| 腾讯2026校园招聘 | 腾讯 | 腾讯 |
| 字节跳动2026届春季校园招聘 | 字节跳动 | 字节跳动 |
| 久候未来 盈在今夏丨华夏久盈2027届... | 华夏久盈 | 久候未来 ❌ |
| 实习招聘 \| 洛书投资2026暑期实习 | 洛书投资 | 洛书投资 |
| 【校招】华为2026届应届生招聘 | 华为 | 华为 |

## API 依赖

基于简立制作 API 平台：
- `GET /v1/accounts/{appid}/autoreplies/keywords` - 查询规则
- `POST /v1/accounts/{appid}/autoreplies/keywords` - 创建规则
- `PUT /v1/accounts/{appid}/autoreplies/keywords/{ruleId}` - 更新规则
- `DELETE /v1/accounts/{appid}/autoreplies/keywords/{ruleId}` - 删除规则
- `POST /v1/accounts/{appid}/materials` - 上传图片素材

## 与上传脚本的集成

修改 `upload_from_feishu.py`，在上传完成后调用：

```python
# 10. 自动回复规则创建询问（如果上传成功）
if success_count > 0:
    print(f"\n💬 步骤 9: 检查自动回复规则创建")
    try:
        # 导入自动回复询问模块
        autoreply_script_dir = os.path.expanduser('~/.hermes/skills/web/wechat-autoreply-manager/scripts')
        if os.path.exists(autoreply_script_dir):
            sys.path.insert(0, autoreply_script_dir)
            from ask_autoreply import ask_create_autoreply
            
            # 获取投递方式字段
            delivery_method = fields.get('投递方式', '')
            
            # 准备成功上传的账号信息
            successful_accounts = [r for r in upload_results if r['success']]
            
            # 调用询问函数
            ask_result = ask_create_autoreply(
                record_id=record_id,
                article_title=title,
                delivery_method=delivery_method,
                successful_accounts=successful_accounts
            )
            
            # 将询问结果附加到返回值中
            return {
                "results": upload_results,
                "success_count": success_count,
                "failed_count": failed_count,
                "total_count": len(account_configs),
                "autoreply_ask": ask_result
            }
        else:
            print(f"   ⚠️ 自动回复模块未安装，跳过")
    except Exception as e:
        print(f"   ⚠️ 自动回复询问失败: {e}")
```

## 使用方式

无需手动调用，上传草稿后自动触发询问。

Hermes 会捕获询问输出并展示给用户，用户回复后调用 `execute_create()` 执行创建。

## 文件结构

```
~/.hermes/skills/web/wechat-autoreply-manager/
├── SKILL.md                          # 本文档
└── scripts/
    ├── create_autoreply.py           # 一键创建脚本（新增）
    ├── delivery_classifier.py        # 投递方式分类
    ├── company_extractor.py          # 企业简称提取
    ├── company_extractor_v2.py       # AI驱动企业简称提取
    ├── ocr_image_finder.py           # OCR图片查找
    ├── autoreply_api.py              # API封装
    ├── ask_autoreply.py              # 主询问逻辑
    ├── feishu_base_updater.py        # 飞书Base状态更新
    └── test_autoreply.py             # 测试脚本
```

## 已知问题与限制

### 1. API 域名

**正确域名**: `https://mp.jianlizhizuo.cn`

**错误域名**: `www.jianlizhizuo.com`（已废弃，会连接超时）

### 2. 图片上传参数

必须提供三个参数：
- `type`: `IMAGE`（必填）
- `name`: 素材名称（必填）
- `media`: 文件（必填）

错误示例（缺少type/name）：
```python
files = {'file': f}  # ❌ 错误
```

正确示例：
```python
files = {'media': f}
data = {'type': 'IMAGE', 'name': '素材名称'}
```

### 3. 自动回复字段名

**必填字段**：
- `ruleName`: 规则名称（1-50字符）
- `keyword`: 关键词（1-50字符）
- `replyContent`: 数组格式 `[{"type": "IMAGE/TEXT", "content": "..."}]`

**注意**：图片类型使用 `mediaId` 字段存放 mediaId，不是 `content` 字段。

正确示例：
```python
{
    "ruleName": "自动回复-Apple",
    "keyword": "Apple",
    "matchMode": "EXACT",  # EXACT(精确匹配) / FUZZY(模糊匹配)
    "replyType": "IMAGE",
    "replyContent": [
        {"type": "IMAGE", "mediaId": "mediaId_xxx"}  # 注意：使用mediaId字段
    ]
}
```

### 4. 获取正确的 AppID

不要硬编码 appid，应该从 API 查询：

```python
api = WechatAutoreplyAPI()
result = api.list_accounts()
# 从 result['data']['list'] 中找到目标账号
```

Joblinker 的正确 appid 示例：`wxYOUR_APPID_HERE`

### 5. API 权限问题

**现象**：自动回复端点返回 `40400 账号不存在`

**原因**：简立制作平台的自动回复功能可能需要单独开通权限，或仅对部分账号启用

**验证方法**：
```python
api = WechatAutoreplyAPI()
result = api.list_rules(appid)
if result.get('code') == 40400:
    print("该账号不支持自动回复功能")
```

**解决方案**：
- 联系简立制作平台客服开通自动回复权限
- 或在公众号后台手动创建自动回复规则

### 6. 标题格式处理

**问题**：标题格式为"实习招聘 | 洛书投资..."时，企业简称提取错误

**修复**：已更新 `company_extractor.py`，支持处理 `|` 分隔的标题格式

```python
# 处理 "类型 | 企业名..." 格式
if '|' in clean_title:
    parts = clean_title.split('|', 1)
    if len(parts) == 2:
        clean_title = parts[1].strip()
```

### 7. 环境变量设置

**必须设置**：`JIANLIZHIZUO_API_KEY`

```bash
# 添加到 ~/.hermes/.env
export JIANLIZHIZUO_API_KEY=sk-xxxxxxxxxxxxxxxx
```

## 手动创建规则模板

当 API 创建失败时，可使用以下模板在公众号后台手动创建：

### 文字回复模板

| 字段 | 值 |
|------|-----|
| 规则名称 | 自动回复-0424 |
| 关键词 | 0424 |
| 匹配模式 | 精确匹配 |
| 回复内容 | 洛书投资<br>投递方式：官网直投：https://www.luoshu.com/join-us；投递邮箱：recruit@luoshu.com |

### 图片回复模板

| 字段 | 值 |
|------|-----|
| 规则名称 | 自动回复-腾讯 |
| 关键词 | 腾讯 |
| 匹配模式 | 精确匹配 |
| 回复类型 | 图片 |
| 回复内容 | [上传二维码图片] |

## 故障排查清单

### 问题1: API连接超时

**现象**: `HTTPSConnectionPool Read timed out`

**原因**: 使用了错误的API域名

**解决**:
```python
# ❌ 错误
base_url = 'https://www.jianlizhizuo.com/v1'  # 会超时

# ✅ 正确
base_url = 'https://mp.jianlizhizuo.cn/v1'
```

### 问题2: 图片上传返回400

**现象**: `{"code":40000,"message":"String must contain at least 1 character(s)"}`

**原因**: 缺少 `type` 和 `name` 参数

**解决**:
```python
# ❌ 错误
files = {'file': open('image.png', 'rb')}

# ✅ 正确
files = {'media': open('image.png', 'rb')}
data = {'type': 'IMAGE', 'name': '素材名称'}
```

### 问题3: 创建规则返回400 "Required"

**现象**: `{"code":40000,"message":"Required"}`

**原因**: 缺少必填字段 `ruleName`

**解决**:
```python
# ❌ 错误
payload = {
    'keyword': 'Apple',
    'replyContent': [...]
}

# ✅ 正确
payload = {
    'ruleName': '自动回复-Apple',  # 必填！
    'keyword': 'Apple',
    'matchMode': 'EXACT',
    'replyType': 'IMAGE',
    'replyContent': [...]
}
```

### 问题4: 图片回复不生效

**现象**: 规则创建成功，但回复的不是图片

**原因**: 使用了错误的字段名 `content` 而不是 `mediaId`

**解决**:
```python
# ❌ 错误
'replyContent': [{'type': 'IMAGE', 'content': 'mediaId_xxx'}]

# ✅ 正确
'replyContent': [{'type': 'IMAGE', 'mediaId': 'mediaId_xxx'}]
```

### 问题5: 删除规则返回400

**现象**: `{"code":"FST_ERR_CTP_EMPTY_JSON_BODY"}`

**原因**: DELETE请求不需要body，但设置了Content-Type: application/json

**解决**:
```python
# ❌ 错误
requests.delete(url, headers={'Content-Type': 'application/json'})

# ✅ 正确
requests.delete(url, headers={'Authorization': 'Bearer xxx'})  # 不要Content-Type
```

**注意**: `autoreply_api.py` 中 `delete_rule()` 方法已修复，仅保留 `Authorization` header。

---

## 图片素材获取：从草稿内容提取（备用方案）

当本地没有 article-ocr 图片文件时，可以从已上传的公众号草稿中提取图片：

### 适用场景
- 文章上传草稿后，本地 `article-ocr.md` 或图片目录已被清理
- 需要为图片投递类型的文章创建自动回复规则
- 投递方式字段包含 `img_xxx` 引用但本地找不到对应文件

### 提取步骤

**Step 1: 获取草稿内容**
```python
import requests

headers = {'Authorization': f'Bearer {API_KEY}'}
resp = requests.get(
    f'{BASE_URL}/accounts/{appid}/drafts?page=1&pageSize=100',
    headers=headers
)
drafts = resp.json()['data']['list']
```

**Step 2: 提取图片URL**
```python
import re

for d in drafts:
    items = d.get('content', {}).get('news_item', [])
    for item in items:
        title = item.get('title', '')
        content = item.get('content', '')
        # 提取 data-src 中的图片URL
        urls = re.findall(r'data-src="([^"]+)"', content)
```

**Step 3: 下载并识别二维码图片**
```python
for url in urls:
    img_resp = requests.get(url, timeout=30)
    # 保存到临时目录
    with open(f'/tmp/{name}.jpg', 'wb') as f:
        f.write(img_resp.content)
    # 使用 vision 工具识别哪张包含二维码
```

**Step 4: 上传素材并创建规则**
```python
# 上传图片素材
with open(image_path, 'rb') as f:
    files = {'media': f}
    data = {'type': 'IMAGE', 'name': 'qrcode.jpg'}
    resp = requests.post(f'{BASE_URL}/accounts/{appid}/materials',
                        files=files, data=data,
                        headers={'Authorization': f'Bearer {API_KEY}'})
media_id = resp.json()['data']['mediaId']

# 创建图片规则
payload = {
    'ruleName': f'自动回复-{keyword}',
    'keyword': keyword,
    'matchMode': 'EXACT',
    'replyType': 'IMAGE',
    'replyContent': [{'type': 'IMAGE', 'mediaId': media_id}],
    'isActive': True
}
requests.post(f'{BASE_URL}/accounts/{appid}/autoreplies/keywords',
             json=payload, headers=headers)
```

---

## 日期关键词规则清理

当使用日期（如 `0429`）作为关键词时，同一日期的多篇文章会追加到同一个规则中。长期运行后可能出现：
- 企业简称提取错误的内容被追加
- 过期文章内容累积导致规则过长

### 检查和清理方法

**查看规则当前内容：**
```python
resp = requests.get(f'{BASE_URL}/accounts/{appid}/autoreplies/keywords?pageSize=100',
                    headers=headers)
for rule in resp.json()['data']['list']:
    if rule['keyword'] == '0429':
        content = rule['replyContent'][0]['content']
        print(content)
```

**清理并重建（保留正确条目）：**
```python
# 1. 获取规则ID
rule_id = rule['id']

# 2. 构建新内容（只保留正确的条目）
new_content = '企业A\n投递方式A\n\n企业B\n投递方式B'

# 3. 使用 PUT 直接替换
payload = {
    'ruleName': rule['ruleName'],
    'keyword': rule['keyword'],
    'matchMode': rule['matchMode'],
    'replyType': 'TEXT',
    'replyContent': [{'type': 'TEXT', 'content': new_content}],
    'isActive': True
}
requests.put(f'{BASE_URL}/accounts/{appid}/autoreplies/keywords/{rule_id}',
             json=payload, headers=headers)
```

### 建议
- 每月检查一次日期关键词规则的累积情况
- 发现错误简称时，及时清理并重新创建正确的 IMAGE 规则（企业简称关键词）
- 文字日期规则中的错误条目可通过 PUT 直接替换内容修正

---

## 手动修正 Base 状态（绕过脚本）

当通过脚本流程之外的方式（如手动 API 调用）创建了规则，需要更新飞书 Base 状态时，可直接使用 Lark CLI：

```bash
lark-cli base +record-upsert \
  --app E9y1bxjHGa9LeGs9q3Tc3J41nmf \
  --table tblYIqHtHrWUlVnP \
  --record xxx \
  --field '文章状态=已配置自动回复'
```

**参数说明**：
- `--app`: Base Token
- `--table`: 文章素材表 ID
- `--record`: 记录 ID（不是文章 ID）
- `--field`: 要更新的字段及值

---

## 版本历史

| 版本 | 变更 |
|------|------|
| v1.0 | 初始版本，支持文字/图片自动回复创建，集成上传流程 |
| v1.1 | 修复企业简称提取逻辑，支持 `\|` 分隔的标题格式；添加 API 权限问题说明 |
| v1.2 | 修正API字段名：图片回复使用 `mediaId` 而不是 `content`；添加故障排查清单 |
| v1.3 | 新增飞书Base状态更新：创建成功后自动将文章状态更新为"已配置自动回复" |
| v1.4 | 优化投递方式分类逻辑：优先检测链接/邮箱，存在则创建文字回复 |
| v1.5 | 企业简称提取改为AI驱动：新增company_extractor_v2.py，使用AI提取更准确 |
| v1.6 | 文字回复特殊处理：2天内相同关键词自动追加内容，超过2天创建新规则 |
| v1.7 | 新增一键创建脚本：create_autoreply.py，支持命令行快速创建 |
| v1.8 | 记录AI企业简称提取准确率问题及手动修正工流；文档化PUT API直接替换内容的方法 |
| **v2.0** | **预览确认模式**：上传前先展示计划内容，用户确认后才执行；**企业简称自检**：自动检测无效词并修正，修正后再展示给用户 |
| **v2.1** | 修复 `delete_rule()` 方法：DELETE 请求移除 `Content-Type` header；新增"从草稿提取图片"备用方案文档；新增"日期关键词规则清理"指南；新增手动更新 Base 状态命令 |
