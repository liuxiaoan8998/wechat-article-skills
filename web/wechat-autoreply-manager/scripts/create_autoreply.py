#!/usr/bin/env python3
"""
自动回复规则创建完整流程（v2.1 - 预览确认+手动简称覆盖）

使用方式:
    # 预览模式（展示计划内容，等待用户确认）
    python create_autoreply.py <article_id> --preview
    
    # 执行模式（实际创建规则）
    python create_autoreply.py <article_id> --execute
    
    # 手动指定企业简称（强制覆盖自动提取，优先级最高）
    python create_autoreply.py <article_id> --execute --company "上海电气"
    
    # 简写（默认预览模式）
    python create_autoreply.py <article_id>

示例:
    python create_autoreply.py 94a8aacd --preview
    python create_autoreply.py 94a8aacd --execute
    python create_autoreply.py 94a8aacd --execute --company "薯片公司"
"""

import os
import sys
import json
import subprocess
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict

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

# 账号映射
ACCOUNT_MAP = {
    "Joblinker": "wxYOUR_APPID_HERE",
    "研究生求职圈": "wxYOUR_APPID_HERE",
    "行研实习": "wxYOUR_APPID_HERE"
}

# 企业简称自检：这些词不应出现在简称中
INVALID_KEYWORDS = ['校招', '招聘', '实习', '校园', '暑期', '春季', '秋季', '2026', '2027', '2025', '岗位', '正式', '启动', '届', '等你', '未来']


def query_feishu_record(article_id: str) -> Optional[dict]:
    """从飞书Base查询文章信息"""
    cmd = f'lark-cli base +record-list --base-token {BASE_TOKEN} --table-id {TABLE_ID} --limit 500 --as bot'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ 查询Base失败: {result.stderr}")
        return None
    
    try:
        response = json.loads(result.stdout)
        if not response.get('ok'):
            print(f"❌ API错误: {response.get('error')}")
            return None
        
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
        
        print(f"❌ 未找到文章ID: {article_id}")
        return None
        
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        return None


def _extract_raw(title: str) -> str:
    """原始提取：取标题前4个连续汉字"""
    # 处理 | 分隔
    if '|' in title:
        parts = title.split('|', 1)
        if len(parts) == 2:
            title = parts[1].strip()
    
    # 提取连续汉字
    chinese_chars = ''.join(c for c in title if '\u4e00' <= c <= '\u9fff')
    return chinese_chars[:4] if len(chinese_chars) >= 4 else chinese_chars


def _validate_company_name(name: str) -> list:
    """验证企业简称是否合理"""
    issues = []
    for kw in INVALID_KEYWORDS:
        if kw in name:
            issues.append(f"包含'{kw}'")
    return issues


def _try_fix_company_name(title: str, raw: str) -> str:
    """尝试修正企业简称
    
    优先级:
    1. 尝试缩短 raw，看是否能移除无效词
    2. 滑动窗口找4个字不含无效词
    3. 找企业名后缀（公司/集团/银行/证券等）
    4. 取第一个无效词之前的所有字
    """
    full_chars = ''.join(c for c in title if '\u4e00' <= c <= '\u9fff')
    
    # 策略0: 缩短 raw，看是否能移除无效词
    # 例如 "南航届校" → "南航"
    if raw:
        for length in [3, 2, 1]:
            if length <= len(raw):
                candidate = raw[:length]
                if not any(kw in candidate for kw in INVALID_KEYWORDS):
                    return candidate
    
    # 策略1: 滑动窗口，找4个字不含无效词
    for i in range(len(full_chars) - 3):
        candidate = full_chars[i:i+4]
        if not any(kw in candidate for kw in INVALID_KEYWORDS):
            return candidate
    
    # 策略2: 找企业名后缀
    company_suffixes = ['公司', '集团', '银行', '证券', '基金', '投资', '保险', '信托', 
                        '期货', '租赁', '资管', '资本', '企业', '大学', '学院', '研究院',
                        '科技', '网络', '软件', '智能', '文化', '传媒', '能源', '电力',
                        '五环', '三一', '中海', '中交', '交通']
    for suffix in company_suffixes:
        idx = full_chars.find(suffix)
        if idx >= 2:
            # 取后缀及前面2-4个字
            start = max(0, idx - 2)
            candidate = full_chars[start:idx+len(suffix)]
            if not any(kw in candidate for kw in INVALID_KEYWORDS):
                return candidate[:4]
    
    # 策略3: 取第一个无效词之前的所有字
    first_invalid_idx = len(full_chars)
    for kw in INVALID_KEYWORDS:
        idx = full_chars.find(kw)
        if idx >= 0 and idx < first_invalid_idx:
            first_invalid_idx = idx
    
    if first_invalid_idx > 0:
        candidate = full_chars[:first_invalid_idx]
        if len(candidate) >= 2:
            return candidate[:4]
    
    return raw


def extract_company_name(title: str) -> dict:
    """
    提取企业简称，带自检和自动修正
    
    Returns:
        {
            'raw': '原始提取结果',
            'fixed': '修正后结果',
            'issues': ['问题1', '问题2'],
            'passed': True/False,
            'company': '最终使用的简称',
            'message': '人类可读说明'
        }
    """
    # Step 1: 原始提取
    raw = _extract_raw(title)
    
    # Step 2: 自检
    issues = _validate_company_name(raw)
    
    # Step 3: 如果未通过，尝试自动修正
    if issues:
        fixed = _try_fix_company_name(title, raw)
        fixed_issues = _validate_company_name(fixed)
        
        if not fixed_issues:
            return {
                'raw': raw,
                'fixed': fixed,
                'issues': issues,
                'passed': True,  # 修正后通过
                'company': fixed,
                'message': f"⚠️ 原始提取'{raw}'自检不通过（{', '.join(issues)}），已自动修正为'{fixed}'"
            }
        else:
            # 修正后仍有 issue，标记为待人工确认
            return {
                'raw': raw,
                'fixed': fixed,
                'issues': issues + fixed_issues,
                'passed': False,
                'company': fixed,  # 使用修正版，但标记为未通过
                'message': f"❌ 原始提取'{raw}'和修正版'{fixed}'均不通过，建议人工确认"
            }
    
    return {
        'raw': raw,
        'fixed': raw,
        'issues': [],
        'passed': True,
        'company': raw,
        'message': f"✅ 自检通过：'{raw}'"
    }


def classify_delivery(delivery_method: str) -> dict:
    """判断投递方式类型"""
    import re
    
    if not delivery_method:
        return {'type': 'text', 'reason': '空内容'}
    
    # 检查有效链接
    urls = re.findall(r'https?://[^\s<>"\')\]]+[^\s<>"\')\].,;!?]', delivery_method)
    valid_urls = [url for url in urls if 'mp.weixin.qq.com' not in url.lower()]
    
    if valid_urls:
        return {'type': 'text', 'reason': f'包含有效链接: {len(valid_urls)}个'}
    
    # 检查邮箱
    if re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', delivery_method):
        return {'type': 'text', 'reason': '包含邮箱'}
    
    # 检查图片关键词
    image_keywords = ['扫码', '二维码', '扫描', '添加微信', '微信投递', '进群', '加群']
    for kw in image_keywords:
        if kw in delivery_method:
            return {'type': 'image', 'reason': f'包含图片关键词: {kw}'}
    
    # 默认文字
    return {'type': 'text', 'reason': '默认文字类型'}


def list_rules(appid: str, keyword: str) -> Optional[dict]:
    """查询关键词规则"""
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    try:
        resp = requests.get(
            f"{BASE_URL}/accounts/{appid}/autoreplies/keywords",
            headers=headers,
            params={"pageSize": 100},
            timeout=30
        )
        
        if resp.status_code == 200:
            result = resp.json()
            if result.get('code') == 0:
                rules = result.get('data', {}).get('list', [])
                for rule in rules:
                    if rule.get('keyword') == keyword:
                        return rule
        return None
    except Exception as e:
        print(f"⚠️ 查询规则失败: {e}")
        return None


def check_rule_age(rule: dict) -> int:
    """检查规则创建天数"""
    created_at = rule.get('createdAt', '')
    if not created_at:
        return 999
    
    try:
        created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        now = datetime.now(created.tzinfo)
        return (now - created).days
    except:
        return 999


def create_text_rule(appid: str, keyword: str, content: str) -> dict:
    """创建文字规则"""
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
    return resp.json()


def update_text_rule(appid: str, rule_id: str, existing_content: str, new_content: str) -> dict:
    """更新文字规则（追加）"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    combined = f"{existing_content}\n\n{new_content}"
    
    # 先获取现有规则
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
        return {'code': -1, 'message': '规则不存在'}
    
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
    return resp.json()


def update_base_status(record_id: str) -> bool:
    """更新Base文章状态"""
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


def build_preview(record: dict) -> dict:
    """
    构建预览信息，不执行任何API调用
    
    Returns:
        {
            'article_id': '...',
            'title': '...',
            'company_result': {...},
            'delivery_info': {...},
            'keyword': '...',
            'content': '...',
            'accounts': [...],
            'is_image': False,
            'record_id': '...'
        }
    """
    title = record.get('文章标题', '')
    delivery = record.get('投递方式', '')
    accounts_field = record.get('适配账号', [])
    record_id = record.get('record_id')
    article_id = record.get('文章ID', '')
    
    # 解析账号
    accounts = []
    for acc_name in accounts_field:
        if acc_name in ACCOUNT_MAP:
            accounts.append({'name': acc_name, 'appid': ACCOUNT_MAP[acc_name]})
    
    # 提取企业简称（带自检）
    company_result = extract_company_name(title)
    
    # 判断投递类型
    delivery_info = classify_delivery(delivery)
    is_image = delivery_info['type'] == 'image'
    
    # 确定关键词和内容
    if is_image:
        keyword = company_result['company']
        content = f"[图片回复] 关键词: {keyword}"
    else:
        keyword = datetime.now().strftime("%m%d")
        content = f"{company_result['company']}\n{delivery}"
    
    return {
        'article_id': article_id,
        'title': title,
        'company_result': company_result,
        'delivery_info': delivery_info,
        'keyword': keyword,
        'content': content,
        'accounts': accounts,
        'is_image': is_image,
        'record_id': record_id
    }


def print_preview(preview: dict):
    """打印预览内容"""
    print("=" * 60)
    print("📋 自动回复规则预览")
    print("=" * 60)
    print(f"文章: {preview['title']}")
    print(f"文章ID: {preview['article_id']}")
    print()
    
    # 企业简称自检结果
    cr = preview['company_result']
    print("【企业简称】")
    print(f"   原始提取: {cr['raw']}")
    if cr['raw'] != cr['fixed']:
        print(f"   自动修正: {cr['fixed']}")
    print(f"   最终使用: {cr['company']}")
    print(f"   自检状态: {cr['message']}")
    if not cr['passed']:
        print(f"   ⚠️ 建议人工确认后使用")
    print()
    
    # 投递方式
    di = preview['delivery_info']
    print("【投递方式】")
    print(f"   类型: {di['type']}")
    print(f"   原因: {di['reason']}")
    print()
    
    # 规则内容
    print("【即将创建的规则】")
    print(f"   关键词: {preview['keyword']}")
    print(f"   回复类型: {'图片' if preview['is_image'] else '文字'}")
    print(f"   目标账号: {', '.join(a['name'] for a in preview['accounts'])}")
    print()
    print("   回复内容:")
    print("   " + "-" * 50)
    for line in preview['content'].split('\n'):
        print(f"   {line}")
    print("   " + "-" * 50)
    print()
    print("=" * 60)


def execute_create(preview: dict) -> dict:
    """
    执行创建规则（基于预览信息）
    
    Returns:
        {'success': True/False, 'results': [...]}
    """
    keyword = preview['keyword']
    content = preview['content']
    accounts = preview['accounts']
    record_id = preview['record_id']
    is_image = preview['is_image']
    company = preview['company_result']['company']
    
    print("\n步骤: 创建/更新规则...")
    results = []
    
    for account in accounts:
        appid = account['appid']
        name = account['name']
        
        print(f"\n   {name}:")
        
        if is_image:
            print(f"      ⚠️ 图片类型暂不支持自动创建")
            results.append({'account': name, 'success': False, 'error': '图片类型暂不支持'})
            continue
        
        # 文字类型：检查现有规则
        existing = list_rules(appid, keyword)
        
        if existing:
            days = check_rule_age(existing)
            print(f"      找到现有规则（{days}天前）")
            
            if days <= 2:
                rule_id = existing['id']
                existing_content = existing.get('replyContent', [{}])[0].get('content', '')
                
                # 检查是否已存在该企业
                if company in existing_content:
                    print(f"      ⏭️ 已存在该企业，跳过")
                    results.append({'account': name, 'success': True, 'action': 'skipped'})
                    continue
                
                print(f"      📝 追加内容...")
                result = update_text_rule(appid, rule_id, existing_content, content)
                
                if result.get('code') == 0:
                    print(f"      ✅ 追加成功")
                    results.append({'account': name, 'success': True, 'action': 'appended'})
                else:
                    print(f"      ❌ 追加失败: {result.get('message')}")
                    results.append({'account': name, 'success': False, 'error': result.get('message')})
            else:
                print(f"      📝 创建新规则...")
                result = create_text_rule(appid, keyword, content)
                
                if result.get('code') == 0:
                    print(f"      ✅ 创建成功")
                    results.append({'account': name, 'success': True, 'action': 'created'})
                else:
                    print(f"      ❌ 创建失败: {result.get('message')}")
                    results.append({'account': name, 'success': False, 'error': result.get('message')})
        else:
            print(f"      📝 创建新规则...")
            result = create_text_rule(appid, keyword, content)
            
            if result.get('code') == 0:
                print(f"      ✅ 创建成功")
                results.append({'account': name, 'success': True, 'action': 'created'})
            else:
                print(f"      ❌ 创建失败: {result.get('message')}")
                results.append({'account': name, 'success': False, 'error': result.get('message')})
    
    # 更新Base状态
    print("\n步骤: 更新Base状态...")
    success_count = sum(1 for r in results if r['success'])
    
    if success_count > 0:
        if update_base_status(record_id):
            print("   ✅ Base状态已更新")
        else:
            print("   ⚠️ Base状态更新失败")
    
    print()
    print("=" * 60)
    print(f"完成: {success_count}/{len(results)} 成功")
    print("=" * 60)
    
    return {
        'success': success_count > 0,
        'results': results
    }


def create_autoreply(article_id: str, mode: str = 'preview', manual_company: str = None) -> dict:
    """
    创建自动回复规则的完整流程
    
    Args:
        article_id: 文章ID
        mode: 'preview' 只展示计划内容 / 'execute' 执行创建
        manual_company: 手动指定企业简称（优先级最高）
        
    Returns:
        执行结果
    """
    print("=" * 60)
    print(f"自动回复规则: {article_id} [{mode}模式]")
    print("=" * 60)
    print()
    
    # 1. 查询文章信息
    print("步骤1: 查询文章信息...")
    record = query_feishu_record(article_id)
    if not record:
        return {'success': False, 'error': '文章未找到'}
    
    print(f"   标题: {record.get('文章标题', '')}")
    print(f"   投递方式: {record.get('投递方式', '')}")
    print()
    
    # 2. 构建预览
    print("步骤2: 提取企业简称并自检...")
    preview = build_preview(record)
    
    # 如果手动指定了企业简称，直接覆盖
    if manual_company:
        preview['company_result'] = {
            'raw': manual_company,
            'fixed': manual_company,
            'passed': True,
            'issues': [],
            'company': manual_company,
            'message': f'✅ 手动指定：{manual_company}'
        }
        # 重新构建内容
        if not preview['is_image']:
            preview['content'] = f"{manual_company}\n{record.get('投递方式', '')}"
        print(f"   手动指定: {manual_company}")
    
    # 3. 打印预览
    print()
    print_preview(preview)
    
    # 4. 如果是预览模式，直接返回
    if mode == 'preview':
        print("🔍 预览模式完成。请确认后继续。")
        return {
            'success': True,
            'mode': 'preview',
            'preview': preview,
            'message': '请确认上述预览内容后，使用 --execute 执行创建'
        }
    
    # 5. 执行模式：检查未通过的情况
    if not preview['company_result']['passed']:
        print("⚠️ 企业简称自检未通过，请人工确认后继续。")
        print(f"   建议：将企业简称修正为更合理的名称后再执行。")
        return {
            'success': False,
            'error': '企业简称自检未通过',
            'preview': preview
        }
    
    # 6. 执行创建
    return execute_create(preview)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法:")
        print("  python create_autoreply.py <article_id> --preview    # 预览模式（默认）")
        print("  python create_autoreply.py <article_id> --execute    # 执行模式")
        print("示例:")
        print("  python create_autoreply.py 94a8aacd --preview")
        print("  python create_autoreply.py 94a8aacd --execute")
        sys.exit(1)
    
    article_id = sys.argv[1]
    
    if '--execute' in sys.argv:
        mode = 'execute'
    elif '--preview' in sys.argv:
        mode = 'preview'
    else:
        mode = 'preview'
    
    # 手动指定企业简称
    manual_company = None
    for i, arg in enumerate(sys.argv):
        if arg == '--company' and i + 1 < len(sys.argv):
            manual_company = sys.argv[i + 1]
            break
    
    result = create_autoreply(article_id, mode=mode, manual_company=manual_company)
    
    if not result['success']:
        print(f"\n❌ 失败: {result.get('error', '未知错误')}")
        sys.exit(1)
    
    print(f"\n✅ {result.get('mode', '完成')}")
