# 飞书 Base 同步方法总结

> 基于实际同步经验的标准化流程

## 核心命令

```bash
lark-cli base +record-upsert \
  --base-token "E9y1bxjHGa9LeGs9q3Tc3J41nmf" \
  --table-id "tblYIqHtHrWUlVnP" \
  --json @data.json \
  --as bot
```

## 关键要点

### 1. 数据文件必须使用相对路径

```python
# ❌ 错误：绝对路径
"/tmp/data.json"

# ✅ 正确：相对路径
"./data.json" 或 "data.json"
```

### 2. 单选字段格式

```python
# ❌ 错误：不要包装成对象
{"行业": {"text": "消费品"}}

# ✅ 正确：直接使用字符串
{"行业": "消费品"}
```

### 3. 空字段填充

信息未获取到的字段，统一填充 `"/"`：

```python
{"截止日期": "/", "工作地点": "/"}
```

### 4. 多选字段格式

```python
{"岗位类型": ["实习"], "标签": ["大厂", "国企"]}
```

## Python 同步函数（含字段填充率反馈）

```python
import subprocess
import json
import os

def sync_to_feishu(record_data: dict) -> dict:
    """同步单条记录到飞书Base"""
    base_token = "E9y1bxjHGa9LeGs9q3Tc3J41nmf"
    table_id = "tblYIqHtHrWUlVnP"
    
    # 计算字段填充率
    total_fields = 23  # 基础10个 + AI分析13个
    filled_fields = sum(1 for v in record_data.values() if v and v != "/" and v != ["/"])
    fill_rate = int(filled_fields / total_fields * 100)
    
    # 写入临时文件（必须使用相对路径）
    with open('sync_data.json', 'w', encoding='utf-8') as f:
        json.dump(record_data, f, ensure_ascii=False)
    
    try:
        result = subprocess.run(
            f'lark-cli base +record-upsert --base-token {base_token} --table-id {table_id} --json @sync_data.json --as bot',
            shell=True, capture_output=True, text=True
        )
        
        if result.returncode == 0:
            response = json.loads(result.stdout)
            if response.get('ok'):
                record_id = response['data']['record']['record_id_list'][0]
                return {
                    'success': True, 
                    'record_id': record_id,
                    'fill_rate': f"{filled_fields}/{total_fields} ({fill_rate}%)"
                }
            else:
                return {'success': False, 'error': response.get('error')}
        else:
            return {'success': False, 'error': result.stderr}
    finally:
        if os.path.exists('sync_data.json'):
            os.remove('sync_data.json')

# 使用示例
result = sync_to_feishu(record_data)
if result['success']:
    print(f"✅ 同步成功！")
    print(f"   记录ID: {result['record_id']}")
    print(f"   字段填充: {result['fill_rate']}")  # 例如: 23/23 (100%)
```

## 标准反馈格式

每次同步完成后，必须按照以下格式反馈：

```
✅ 同步成功！
   记录ID: recvhC4o1aT1TP
   字段填充: 23/23 (100%)
```

**格式规范**: `字段填充: {已填充}/{总字段数} ({百分比}%)`

## 本次同步结果

| 文章 | 记录ID | 文章ID | 状态 |
|------|--------|--------|------|
| 招贤纳士丨环境政策研究实习生招聘 | recvhC4o1aT1TP | fa70b413 | ✅ 成功 |

## 相关 Skill

- `wechat-article-extraction-pro` - 微信文章提取完整流程
- `feishu-base-sync` - 飞书Base同步标准方法
