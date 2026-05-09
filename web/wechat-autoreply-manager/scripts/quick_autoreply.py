#!/usr/bin/env python3
"""
自动回复规则快速创建
在上传完成后自动调用，无需手动执行

使用方式:
    python quick_autoreply.py <article_id>
    
示例:
    python quick_autoreply.py 94a8aacd
"""

import os
import sys
import json
import subprocess
import requests
from datetime import datetime, timedelta

# 自动加载 .env 文件（如果存在）
_env_path = Path(__file__).resolve().parents[3] / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value.strip())

# 自动加载 .env 文件（如果存在）
_env_path = Path(__file__).resolve().parents[3] / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value.strip())

# 配置
API_KEY = os.getenv("JIANLIZHIZUO_API_KEY")
BASE_URL = "https://mp.jianlizhizuo.cn/v1"
BASE_TOKEN = os.getenv("FEISHU_BASE_TOKEN")
TABLE_ID = os.getenv("FEISHU_ARTICLE_TABLE_ID")

ACCOUNT_MAP = {
    "Joblinker": "wxYOUR_APPID_HERE",
    "研究生求职圈": "wxYOUR_APPID_HERE",
    "行研实习": "wxYOUR_APPID_HERE"
}


def query_article(article_id: str) -> dict:
    """查询文章信息"""
    cmd = f'lark-cli base +record-list --base-token {BASE_TOKEN} --table-id {TABLE_ID} --limit 500 --as bot'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise Exception(f"查询失败: {result.stderr}")
    
    response = json.loads(result.stdout)
    if not response.get('ok'):
        raise Exception(f"API错误: {response.get('error')}")
    
    records_data = response['data']['data']
    field_names = response['data']['fields']
    record_ids = response['data']['record_id_list']
    
    for i, record_values in enumerate(records_data):
        record = {'record_id': record_ids[i]}
        for j, field_name in enumerate(field_names):
            if j < len(record_values):
                record[field_name] = record_values[j]
        
        if record.get('文章ID') == article_id:
            return record
    
    raise ValueError(f"未找到文章: {article_id}")


def extract_company(title: str) -> str:
    """提取企业简称"""
    chinese_chars = ''.join(c for c in title if '\u4e00' <= c <= '\u9fff')
    if '|' in title:
        parts = title.split('|', 1)
        if len(parts) == 2:
            chinese_chars = ''.join(c for c in parts[1] if '\u4e00' <= c <= '\u9fff')
    return chinese_chars[:4] if len(chinese_chars) >= 4 else chinese_chars


def classify_delivery(delivery: str) -> str:
    """判断投递类型"""
    import re
    if not delivery:
        return 'text'
    
    urls = re.findall(r'https?://[^\s<>"\')\]]+[^\s<>"\')\].,;!?]', delivery)
    valid_urls = [url for url in urls if 'mp.weixin.qq.com' not in url.lower()]
    
    if valid_urls:
        return 'text'
    
    if re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', delivery):
        return 'text'
    
    image_keywords = ['扫码', '二维码', '扫描', '添加微信', '微信投递', '进群', '加群']
    for kw in image_keywords:
        if kw in delivery:
            return 'image'
    
    return 'text'


def list_rules(appid: str, keyword: str) -> dict:
    """查询规则"""
    headers = {"Authorization": f"Bearer {API_KEY}"}
    resp = requests.get(
        f"{BASE_URL}/accounts/{appid}/autoreplies/keywords",
        headers=headers,
        params={"pageSize": 100},
        timeout=30
    )
    
    if resp.status_code == 200:
        result = resp.json()
        if result.get('code') == 0:
            for rule in result.get('data', {}).get('list', []):
                if rule.get('keyword') == keyword:
                    return rule
    return None


def create_rule(appid: str, keyword: str, content: str) -> bool:
    """创建规则"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    rule_data = {
        "ruleName": f"自动回复-{keyword}",
        "keyword": keyword,
        "matchMode": "EXACT",
        "replyType": "TEXT",
        "replyContent": [{"type": "TEXT", "content": content}],
        "isActive": True
    }
    
    resp = requests.post(
        f"{BASE_URL}/accounts/{appid}/autoreplies/keywords",
        headers=headers,
        json=rule_data,
        timeout=30
    )
    
    if resp.status_code == 200:
        result = resp.json()
        return result.get('code') == 0
    return False


def update_rule(appid: str, rule_id: str, existing: str, new: str) -> bool:
    """更新规则（追加）"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 获取现有规则
    list_resp = requests.get(
        f"{BASE_URL}/accounts/{appid}/autoreplies/keywords",
        headers={"Authorization": f"Bearer {API_KEY}"},
        params={"pageSize": 100},
        timeout=30
    )
    
    existing_rule = None
    if list_resp.status_code == 200:
        result = list_resp.json()
        if result.get('code') == 0:
            for rule in result.get('data', {}).get('list', []):
                if rule.get('id') == rule_id:
                    existing_rule = rule
                    break
    
    if not existing_rule:
        return False
    
    combined = f"{existing}\n\n{new}"
    
    update_data = {
        "ruleName": existing_rule.get('ruleName'),
        "keyword": existing_rule.get('keyword'),
        "matchMode": existing_rule.get('matchMode'),
        "replyType": "TEXT",
        "replyContent": [{"type": "TEXT", "content": combined}],
        "isActive": True
    }
    
    resp = requests.put(
        f"{BASE_URL}/accounts/{appid}/autoreplies/keywords/{rule_id}",
        headers=headers,
        json=update_data,
        timeout=30
    )
    
    if resp.status_code == 200:
        result = resp.json()
        return result.get('code') == 0
    return False


def update_base(record_id: str) -> bool:
    """更新Base状态"""
    json_str = json.dumps({"文章状态": "已配置自动回复"}, ensure_ascii=False)
    cmd = f"lark-cli base +record-upsert --base-token {BASE_TOKEN} --table-id {TABLE_ID} --record-id {record_id} --json '{json_str}' --as bot"
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        try:
            response = json.loads(result.stdout)
            return response.get('ok', False)
        except:
            return False
    return False


def main():
    if len(sys.argv) < 2:
        print("用法: python quick_autoreply.py <article_id>")
        sys.exit(1)
    
    article_id = sys.argv[1]
    
    print("="*60)
    print(f"自动创建自动回复规则: {article_id}")
    print("="*60)
    print()
    
    # 1. 查询文章
    print("1. 查询文章信息...")
    record = query_article(article_id)
    title = record.get('文章标题', '')
    delivery = record.get('投递方式', '')
    accounts_field = record.get('适配账号', [])
    record_id = record.get('record_id')
    
    accounts = []
    for acc_name in accounts_field:
        if acc_name in ACCOUNT_MAP:
            accounts.append({'name': acc_name, 'appid': ACCOUNT_MAP[acc_name]})
    
    print(f"   标题: {title}")
    print(f"   账号: {[a['name'] for a in accounts]}")
    print()
    
    # 2. 提取企业简称
    print("2. 提取企业简称...")
    company = extract_company(title)
    print(f"   {company}")
    print()
    
    # 3. 判断类型
    print("3. 判断投递类型...")
    dtype = classify_delivery(delivery)
    print(f"   {dtype}")
    print()
    
    if dtype == 'image':
        print("⚠️ 图片类型暂不支持自动创建")
        return
    
    # 4. 确定关键词和内容
    keyword = datetime.now().strftime("%m%d")
    content = f"{company}\n{delivery}"
    
    print(f"4. 关键词: {keyword}")
    print(f"   内容:\n{content}")
    print()
    
    # 5. 创建/更新规则
    print("5. 创建/更新规则...")
    results = []
    
    for account in accounts:
        appid = account['appid']
        name = account['name']
        
        print(f"\n   {name}:")
        
        existing = list_rules(appid, keyword)
        
        if existing:
            created_at = existing.get('createdAt', '')
            days = 999
            if created_at:
                try:
                    created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    now = datetime.now(created.tzinfo)
                    days = (now - created).days
                except:
                    pass
            
            if days <= 2:
                rule_id = existing['id']
                existing_content = existing.get('replyContent', [{}])[0].get('content', '')
                
                if company in existing_content:
                    print(f"      ⏭️ 已存在，跳过")
                    results.append({'account': name, 'success': True, 'action': 'skipped'})
                    continue
                
                print(f"      📝 追加...")
                if update_rule(appid, rule_id, existing_content, content):
                    print(f"      ✅ 成功")
                    results.append({'account': name, 'success': True, 'action': 'appended'})
                else:
                    print(f"      ❌ 失败")
                    results.append({'account': name, 'success': False})
            else:
                print(f"      📝 创建新规则...")
                if create_rule(appid, keyword, content):
                    print(f"      ✅ 成功")
                    results.append({'account': name, 'success': True, 'action': 'created'})
                else:
                    print(f"      ❌ 失败")
                    results.append({'account': name, 'success': False})
        else:
            print(f"      📝 创建新规则...")
            if create_rule(appid, keyword, content):
                print(f"      ✅ 成功")
                results.append({'account': name, 'success': True, 'action': 'created'})
            else:
                print(f"      ❌ 失败")
                results.append({'account': name, 'success': False})
    
    # 6. 更新Base
    print("\n6. 更新Base状态...")
    success_count = sum(1 for r in results if r['success'])
    if success_count > 0 and update_base(record_id):
        print("   ✅ 已更新")
    
    print()
    print("="*60)
    print(f"完成: {success_count}/{len(results)} 成功")
    print("="*60)


if __name__ == '__main__':
    main()
