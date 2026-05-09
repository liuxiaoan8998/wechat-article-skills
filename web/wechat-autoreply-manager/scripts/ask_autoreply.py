#!/usr/bin/env python3
"""
主询问逻辑
在上传草稿完成后，询问用户是否创建自动回复规则
"""

import os
import sys
import json
from datetime import datetime
from typing import List, Dict

# 添加脚本目录到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from delivery_classifier import classify_delivery, is_image_delivery
from company_extractor import extract_and_shorten
from company_extractor_v2 import build_extraction_prompt
from ocr_image_finder import find_delivery_image, get_image_full_path
from autoreply_api import WechatAutoreplyAPI
from feishu_base_updater import FeishuBaseUpdater


def find_article_directory(article_title: str, base_dir: str = None) -> str:
    """
    查找文章本地目录
    
    搜索路径：
    1. ~/.hermes/output/文章标题/
    2. /tmp/test_output/文章标题/
    """
    if base_dir:
        candidate = os.path.join(base_dir, article_title)
        if os.path.exists(candidate):
            return candidate
    
    search_paths = [
        os.path.expanduser('~/.hermes/output'),
        '/tmp/test_output',
    ]
    
    for path in search_paths:
        candidate = os.path.join(path, article_title)
        if os.path.exists(candidate):
            return candidate
    
    return None


def build_text_prompt(article_title: str, company_short: str, 
                      delivery_method: str, keyword: str,
                      account_count: int) -> str:
    """
    构建文字投递的询问提示（优化格式）
    """
    # 新格式：去掉"投递方式："前缀，更简洁
    reply_content = f"{company_short}\n{delivery_method}"
    
    prompt = f"""📄 文章：《{article_title}》
📮 投递方式：文字
━━━━━━━━━━━━━━
原文：{delivery_method}

💡 建议创建自动回复（将应用到{account_count}个账号）：
   关键词：{keyword}
   回复内容：
   ──────────────
   {reply_content}
   ──────────────

是否创建？（是 / 否 / 修改）"""
    
    return prompt


def build_image_prompt(article_title: str, company_short: str,
                       image_info: dict, keyword: str,
                       account_count: int) -> str:
    """
    构建图片投递的询问提示
    """
    image_file = image_info.get('image_file', '未知')
    matched = image_info.get('matched_keyword', '')
    fallback = image_info.get('fallback', False)
    
    match_info = f"（匹配关键词：{matched}）" if matched else ""
    if fallback:
        match_info = "（未匹配到关键词，使用第一张图片）"
    
    prompt = f"""📄 文章：《{article_title}》
📮 投递方式：图片（二维码）
━━━━━━━━━━━━━━
从 article-ocr.md 找到匹配图片：{image_file} {match_info}

💡 建议创建自动回复（将应用到{account_count}个账号）：
   关键词：{keyword}（企业简称）
   回复内容：该二维码图片

是否创建？（是 / 否 / 修改关键词）"""
    
    return prompt


def ask_create_autoreply(record_id: str, article_title: str, 
                         delivery_method: str, successful_accounts: List[dict],
                         company_short: str = None) -> dict:
    """
    询问用户是否创建自动回复规则
    
    Args:
        record_id: 飞书记录ID
        article_title: 文章标题
        delivery_method: 投递方式字段内容
        successful_accounts: 上传成功的账号列表 [{'appid': 'xxx', 'name': 'Joblinker'}, ...]
        company_short: 企业简称（可选，如未提供将返回AI提取prompt）
        
    Returns:
        {'action': 'create'/'skip'/'modify', 'keyword': 'xxx', ...}
        或 {'action': 'need_ai_extraction', 'prompt': '...', ...} 需要AI提取企业简称
    """
    if not successful_accounts:
        print("⚠️ 没有成功上传的账号，跳过自动回复创建")
        return {'action': 'skip', 'reason': 'no_successful_accounts'}
    
    # 分类投递方式
    delivery_info = classify_delivery(delivery_method)
    is_image = delivery_info['type'] == 'image'
    
    # 生成日期关键词
    today_keyword = datetime.now().strftime("%m%d")  # "0424"
    
    # 如果没有提供企业简称，返回AI提取prompt
    if not company_short:
        ai_prompt = build_extraction_prompt(article_title)
        return {
            'action': 'need_ai_extraction',
            'prompt': ai_prompt,
            'article_title': article_title,
            'delivery_method': delivery_method,
            'delivery_info': delivery_info,
            'is_image': is_image,
            'today_keyword': today_keyword,
            'successful_accounts': successful_accounts,
            'record_id': record_id
        }
    
    # 查找文章目录
    article_dir = find_article_directory(article_title)
    
    account_count = len(successful_accounts)
    
    if is_image:
        # 图片类型
        if not article_dir:
            print(f"⚠️ 未找到文章本地目录：{article_title}")
            return {'action': 'skip', 'reason': 'article_dir_not_found'}
        
        ocr_file = os.path.join(article_dir, 'article-ocr.md')
        image_info = find_delivery_image(ocr_file)
        
        if not image_info:
            print(f"⚠️ 未在 article-ocr.md 中找到投递图片")
            return {'action': 'skip', 'reason': 'image_not_found'}
        
        # 使用企业简称作为关键词
        keyword = company_short
        prompt = build_image_prompt(article_title, company_short, 
                                    image_info, keyword, account_count)
        
        context = {
            'type': 'image',
            'image_info': image_info,
            'article_dir': article_dir,
            'keyword': keyword
        }
    else:
        # 文字类型
        keyword = today_keyword
        prompt = build_text_prompt(article_title, company_short,
                                   delivery_method, keyword, account_count)
        
        context = {
            'type': 'text',
            # 新格式：去掉"投递方式："前缀
            'reply_content': f"{company_short}\n{delivery_method}",
            'keyword': keyword
        }
    
    # 输出询问（这里会被 Hermes 捕获并展示给用户）
    print("\n" + "="*50)
    print(prompt)
    print("="*50 + "\n")
    
    # 返回上下文信息，供后续处理使用
    return {
        'action': 'ask',
        'prompt': prompt,
        'context': context,
        'successful_accounts': successful_accounts,
        'record_id': record_id
    }


def execute_create(user_response: str, ask_context: dict) -> dict:
    """
    根据用户响应执行创建操作
    
    文字回复特殊逻辑：
    1. 先查询关键词回复列表
    2. 如果已有该关键词规则且是2天内创建的，则追加内容
    3. 否则创建新规则
    
    Args:
        user_response: 用户输入（是/否/修改 xxx）
        ask_context: ask_create_autoreply 返回的上下文
        
    Returns:
        执行结果
    """
    import requests
    from datetime import datetime, timedelta
    
    response = user_response.strip().lower()
    context = ask_context['context']
    successful_accounts = ask_context['successful_accounts']
    
    # 解析用户响应
    if response in ['否', 'no', 'n', '不', '跳过', 'skip']:
        return {'action': 'skip', 'reason': 'user_cancelled'}
    
    # 检查是否修改关键词
    keyword = context['keyword']
    if response.startswith('修改') or ' ' in response:
        # 提取新关键词
        parts = response.split(maxsplit=1)
        if len(parts) > 1:
            keyword = parts[1].strip()
    
    # 执行创建
    api = WechatAutoreplyAPI()
    results = []
    
    for account in successful_accounts:
        appid = account['appid']
        account_name = account.get('name', '未知账号')
        
        try:
            if context['type'] == 'text':
                # 文字类型：先查询现有规则
                print(f"查询 {account_name} 的现有规则...")
                
                list_result = api.list_rules(appid, page_size=100)
                existing_rule = None
                should_append = False
                
                if list_result.get('code') == 0:
                    rules = list_result.get('data', {}).get('list', [])
                    for rule in rules:
                        if rule.get('keyword') == keyword:
                            existing_rule = rule
                            break
                
                if existing_rule:
                    # 检查创建时间是否在2天内
                    created_at_str = existing_rule.get('createdAt', '')
                    if created_at_str:
                        try:
                            # 解析ISO格式时间
                            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                            now = datetime.now(created_at.tzinfo)
                            days_diff = (now - created_at).days
                            
                            if days_diff <= 2:
                                should_append = True
                                print(f"   找到2天内创建的规则（{days_diff}天前），将追加内容")
                            else:
                                print(f"   找到规则但已创建{days_diff}天，将创建新规则")
                        except Exception as e:
                            print(f"   时间解析失败，默认创建新规则: {e}")
                    
                    if should_append:
                        # 追加到现有规则
                        rule_id = existing_rule['id']
                        result = api.update_text_rule(
                            appid, rule_id, context['reply_content'], append=True
                        )
                        action = 'appended'
                    else:
                        # 创建新规则（关键词已存在但超过2天）
                        result = api.create_text_rule(
                            appid, keyword, context['reply_content']
                        )
                        action = 'created'
                else:
                    # 创建新规则
                    result = api.create_text_rule(
                        appid, keyword, context['reply_content']
                    )
                    action = 'created'
            else:
                # 图片类型（保持原有逻辑）
                image_path = get_image_full_path(
                    context['article_dir'], 
                    context['image_info']['image_file']
                )
                
                # 上传图片获取 mediaId
                upload_result = api.upload_image(appid, image_path)
                
                if upload_result.get('code') != 0:
                    results.append({
                        'account': account_name,
                        'appid': appid,
                        'success': False,
                        'error': f"图片上传失败: {upload_result.get('message')}"
                    })
                    continue
                
                media_id = upload_result['data']['mediaId']
                
                # 创建图片规则
                result = api.create_image_rule(appid, keyword, media_id)
                action = 'created'
            
            if result.get('code') == 0:
                results.append({
                    'account': account_name,
                    'appid': appid,
                    'success': True,
                    'action': action,
                    'rule_id': result.get('data', {}).get('ruleId') or result.get('data', {}).get('id')
                })
            else:
                results.append({
                    'account': account_name,
                    'appid': appid,
                    'success': False,
                    'error': result.get('message', '未知错误')
                })
                
        except Exception as e:
            results.append({
                'account': account_name,
                'appid': appid,
                'success': False,
                'error': str(e)
            })
    
    # 统计结果
    success_count = sum(1 for r in results if r['success'])
    
    # 如果全部成功，更新Base文章状态
    if success_count == len(results) and success_count > 0:
        try:
            base_updater = FeishuBaseUpdater()
            record_id = ask_context.get('record_id')
            if record_id:
                update_result = base_updater.update_article_status(
                    record_id, 
                    '已配置自动回复'
                )
                if update_result.get('success'):
                    print(f"✅ Base文章状态已更新为'已配置自动回复'")
                else:
                    print(f"⚠️ Base状态更新失败: {update_result.get('error')}")
        except Exception as e:
            print(f"⚠️ Base状态更新异常: {e}")
    
    return {
        'action': 'executed',
        'keyword': keyword,
        'type': context['type'],
        'results': results,
        'success_count': success_count,
        'total_count': len(results)
    }


if __name__ == '__main__':
    # 测试
    print("这是一个模块，请通过其他脚本调用")
    print("用法：")
    print("  from ask_autoreply import ask_create_autoreply, execute_create")
    print("  result = ask_create_autoreply(record_id, title, delivery, accounts)")
