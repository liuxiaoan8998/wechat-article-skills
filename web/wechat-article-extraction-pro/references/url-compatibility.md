# URL格式兼容性修复指南

> 解决极致了API返回URL格式与提取工具验证逻辑不兼容的问题

## 问题描述

**现象**：批量处理极致了API返回的文章时，提取工具报错 `No valid WeChat URLs found`

**原因**：极致了API返回的URL格式为 `http://mp.weixin.qq.com/s?__biz=xxx`（带查询参数），而提取工具原验证逻辑只支持 `/s/xxx` 路径格式。

| URL格式 | 示例 | 原工具支持 |
|---------|------|-----------|
| 标准路径格式 | `https://mp.weixin.qq.com/s/nJ-MZGEiYGM-epQVGKaLCA` | ✅ 支持 |
| 查询参数格式 | `https://mp.weixin.qq.com/s?__biz=MzkwMTI4MzE1OQ==&mid=...` | ❌ 不支持 |

## 修复方案

### 1. 修改URL验证逻辑

**文件**：`/tmp/wechat-article-for-ai-pro/wechat_to_md/cli.py`

**原代码**（第77-80行）：
```python
def validate_url(url: str) -> bool:
    """Check that URL is a WeChat article URL."""
    # 支持带参数的 URL，如 ?scene=1&click_id=12
    return url.startswith("https://mp.weixin.qq.com/s/")
```

**修复后代码**：
```python
def validate_url(url: str) -> bool:
    """Check that URL is a WeChat article URL."""
    # 支持带参数的 URL，如 ?scene=1&click_id=12
    # 支持两种格式: /s/xxx 或 /s?__biz=xxx
    return url.startswith("https://mp.weixin.qq.com/s/") or url.startswith("https://mp.weixin.qq.com/s?")
```

### 2. 批量处理注意事项

#### 协议转换

API返回的URL可能是 `http://` 协议，需转换为 `https://`：

```python
def extract_article(url):
    """提取单篇文章"""
    # 转换为https
    if url.startswith('http://'):
        url = url.replace('http://', 'https://', 1)
    
    cmd = f'cd /tmp/wechat-article-for-ai-pro && /usr/bin/python3 main.py "{url}" -o /tmp/test_output -v --force'
    # ...
```

#### 标题截断问题

文章标题中的特殊字符（如 `|`）可能导致提取的文件夹名称被截断，需要通过URL匹配查找正确目录：

```python
def find_article_dir_by_url(url, output_dir):
    """通过URL查找文章目录（处理标题截断问题）"""
    for item in os.listdir(output_dir):
        full_path = os.path.join(output_dir, item)
        if os.path.isdir(full_path):
            metadata_path = os.path.join(full_path, 'metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                if metadata.get('url') == url:
                    return full_path
    return None

# 使用示例
article_dir = extract_article(url)
if not article_dir:
    # 尝试通过URL查找（处理标题截断）
    https_url = url.replace('http://', 'https://', 1)
    article_dir = find_article_dir_by_url(https_url, '/tmp/test_output')
```

## 完整批量处理示例

```python
import json
import subprocess
import os
import time
from datetime import datetime

# 配置
OUTPUT_DIR = "/tmp/test_output"
WECHAT_TOOL_PATH = "/tmp/wechat-article-for-ai-pro"
LARK_CLI_PATH = "/Users/gaolinmac/.npm-global/lib/node_modules/@larksuite/cli/bin/lark-cli"
BASE_TOKEN = "E9y1bxjHGa9LeGs9q3Tc3J41nmf"
TABLE_ID = "tblYIqHtHrWUlVnP"

def extract_article(url):
    """提取单篇文章"""
    # 转换为https
    if url.startswith('http://'):
        url = url.replace('http://', 'https://', 1)
    
    cmd = f'cd {WECHAT_TOOL_PATH} && /usr/bin/python3 main.py "{url}" -o {OUTPUT_DIR} -v --force'
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        stderr = result.stderr
        
        # 从stderr解析保存路径
        for line in stderr.split('\n'):
            if 'Saved:' in line:
                saved_path = line.split('Saved:')[1].strip().split()[0]
                return saved_path
            if 'Skipping (already exists):' in line:
                path = line.split('Skipping (already exists):')[1].strip()
                return path
        return None
    except Exception as e:
        print(f"提取异常: {e}")
        return None

def find_article_dir_by_url(url):
    """通过URL查找文章目录"""
    for item in os.listdir(OUTPUT_DIR):
        full_path = os.path.join(OUTPUT_DIR, item)
        if os.path.isdir(full_path):
            metadata_path = os.path.join(full_path, 'metadata.json')
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    if metadata.get('url') == url:
                        return full_path
                except:
                    pass
    return None

def sync_to_feishu(record_data):
    """同步到飞书Base"""
    with open('sync_data.json', 'w', encoding='utf-8') as f:
        json.dump(record_data, f, ensure_ascii=False)
    
    try:
        cmd = f'{LARK_CLI_PATH} base +record-upsert --base-token {BASE_TOKEN} --table-id {TABLE_ID} --json @sync_data.json --as bot'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout:
            try:
                response = json.loads(result.stdout)
                if response.get('ok'):
                    return response['data']['record']['record_id_list'][0]
            except:
                pass
        return None
    except Exception as e:
        print(f"同步异常: {e}")
        return None
    finally:
        if os.path.exists('sync_data.json'):
            os.remove('sync_data.json')

# 批量处理
results = []
for i, item in enumerate(api_results[:5], 1):
    title = item.get('title', '').replace('<em class="highlight">', '').replace('</em>', '')
    url = item.get('doc_url', '')
    
    print(f"\n【{i}/5】{title[:50]}")
    
    # 提取
    article_dir = extract_article(url)
    
    if not article_dir:
        # 尝试通过URL查找
        if url.startswith('http://'):
            https_url = url.replace('http://', 'https://', 1)
        else:
            https_url = url
        article_dir = find_article_dir_by_url(https_url)
    
    if not article_dir:
        print("❌ 提取失败")
        results.append({"title": title, "status": "提取失败"})
        continue
    
    # 读取metadata
    try:
        with open(os.path.join(article_dir, 'metadata.json'), 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    except Exception as e:
        print(f"❌ 读取失败: {e}")
        results.append({"title": title, "status": "读取失败"})
        continue
    
    # 构建记录并同步
    pub_time = metadata.get('published_at', '')
    pub_time = pub_time.split()[0].replace('-', '/') if pub_time else '/'
    
    record_data = {
        "文章标题": metadata.get('title', ''),
        "公众号": metadata.get('author', ''),
        "发布时间": pub_time,
        "文章链接": metadata.get('url', ''),
        "文章状态": "待选题",
        "文章来源": "链接",
        "采集时间": int(datetime.now().timestamp() * 1000),
        "行业": "/",
        "领域": "/",
        "岗位类型": ["/"],
        "工作地点": "/",
        "学历要求": "/",
        "截止日期": "/",
        "投递方式": "/",
        "原文亮点": "/",
        "文章概要": "/",
        "选题方向": "/",
        "适配账号": ["/"],
        "优先级": "中",
        "标签": ["/"]
    }
    
    record_id = sync_to_feishu(record_data)
    if record_id:
        print(f"✅ 同步成功: {record_id}")
        results.append({"title": title, "status": "成功", "record_id": record_id})
    else:
        print("❌ 同步失败")
        results.append({"title": title, "status": "同步失败"})
    
    time.sleep(1)

# 汇总
success_count = sum(1 for r in results if r["status"] == "成功")
print(f"\n总计: {success_count}/{len(results)} 篇成功")
```

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-04-22 | 初始版本，记录URL格式兼容性修复方案 |

## 字段填充率反馈规范

用户明确要求每次同步完成后，按照以下格式反馈字段填充率：

```
✅ 同步成功！
   记录ID: {record_id}
   字段填充: 22/22 (100%)
```

**标准格式**: `字段填充: {已填充字段数}/{总字段数} ({百分比}%)`

**示例**:
- 完整填充: `字段填充: 22/22 (100%)`
- 部分缺失: `字段填充: 19/22 (86%)`
