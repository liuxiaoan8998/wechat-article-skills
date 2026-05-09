#!/usr/bin/env python3
"""
投递方式分类器 v2.0
判断投递方式是文字类型还是图片类型

规则优先级（从高到低）：
1. 包含有效链接（非公众号链接）或邮箱 → 文字类型
2. 包含图片关键词（扫码/二维码/关注公众号等） → 图片类型
3. 默认文字类型
"""

import re

# 图片类型关键词
IMAGE_KEYWORDS = [
    '关注公众号',
    '扫码',
    '二维码',
    '扫描',
    '添加微信',
    '微信投递',
    '进群',
    '加群',
]

# 公众号链接特征（这些链接不算有效投递链接）
MP_URL_PATTERNS = [
    r'mp\.weixin\.qq\.com',
    r'weixin\.qq\.com',
]


def extract_urls(text: str) -> list:
    """
    提取文本中的所有URL
    
    Returns:
        list of urls
    """
    # 匹配http/https链接
    url_pattern = r'https?://[^\s<>"\')\]]+[^\s<>"\')\].,;!?]'
    return re.findall(url_pattern, text)


def is_mp_url(url: str) -> bool:
    """
    判断是否为公众号链接
    
    Args:
        url: URL字符串
        
    Returns:
        bool: True=公众号链接, False=其他链接
    """
    url_lower = url.lower()
    for pattern in MP_URL_PATTERNS:
        if re.search(pattern, url_lower):
            return True
    return False


def contains_email(text: str) -> bool:
    """
    检查是否包含邮箱地址
    
    Args:
        text: 文本内容
        
    Returns:
        bool: True=包含邮箱
    """
    # 邮箱正则
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return bool(re.search(email_pattern, text))


def is_image_delivery(delivery_method: str) -> bool:
    """
    判断是否为图片投递方式（简化版）
    
    规则：
    1. 包含有效链接（非公众号）或邮箱 → 文字类型
    2. 包含图片关键词 → 图片类型
    3. 默认文字类型
    
    Args:
        delivery_method: 投递方式字段内容
        
    Returns:
        bool: True=图片类型, False=文字类型
    """
    result = classify_delivery(delivery_method)
    return result['type'] == 'image'


def classify_delivery(delivery_method: str) -> dict:
    """
    分类投递方式并返回详细信息
    
    优先级：
    1. 有效链接/邮箱 → 文字类型（高优先级）
    2. 图片关键词 → 图片类型
    3. 默认文字类型
    
    Returns:
        {
            'type': 'text' | 'image',
            'confidence': 'high' | 'medium' | 'low',
            'matched_keyword': str,
            'reason': str,
            'raw': str
        }
    """
    if not delivery_method:
        return {
            'type': 'text',
            'confidence': 'low',
            'matched_keyword': '',
            'reason': '空内容，默认文字类型',
            'raw': delivery_method
        }
    
    # 第一步：检查是否包含有效链接或邮箱（最高优先级）
    urls = extract_urls(delivery_method)
    valid_urls = [url for url in urls if not is_mp_url(url)]
    
    if valid_urls:
        return {
            'type': 'text',
            'confidence': 'high',
            'matched_keyword': valid_urls[0][:50],  # 截取前50字符
            'reason': f'包含有效链接: {len(valid_urls)}个',
            'raw': delivery_method
        }
    
    # 检查邮箱
    if contains_email(delivery_method):
        # 提取邮箱
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, delivery_method)
        return {
            'type': 'text',
            'confidence': 'high',
            'matched_keyword': emails[0] if emails else '邮箱',
            'reason': f'包含邮箱地址: {len(emails)}个',
            'raw': delivery_method
        }
    
    # 第二步：检查图片关键词（但要排除"关注公众号"如果后面跟的是公众号链接）
    for keyword in IMAGE_KEYWORDS:
        if keyword in delivery_method:
            # 特殊处理：如果包含"关注公众号"且只有公众号链接，不算图片类型
            if keyword == '关注公众号':
                # 检查是否只有公众号链接
                if urls and all(is_mp_url(url) for url in urls):
                    continue  # 跳过，继续检查其他关键词或视为文字类型
            return {
                'type': 'image',
                'confidence': 'high',
                'matched_keyword': keyword,
                'reason': f'包含图片关键词: {keyword}',
                'raw': delivery_method
            }
    
    # 第三步：检查是否只有公众号链接（不算有效投递链接）
    if urls and all(is_mp_url(url) for url in urls):
        return {
            'type': 'image',
            'confidence': 'medium',
            'matched_keyword': '公众号链接',
            'reason': '仅包含公众号链接，视为图片类型',
            'raw': delivery_method
        }
    
    # 默认文字类型
    return {
        'type': 'text',
        'confidence': 'low',
        'matched_keyword': '',
        'reason': '未匹配到特定规则，默认文字类型',
        'raw': delivery_method
    }


def get_reply_content(delivery_method: str, company_short: str = '') -> str:
    """
    生成回复内容
    
    根据投递方式类型生成合适的回复内容
    
    Args:
        delivery_method: 投递方式原文
        company_short: 企业简称
        
    Returns:
        str: 回复内容
    """
    result = classify_delivery(delivery_method)
    
    if result['type'] == 'text':
        # 文字类型：提取链接和邮箱
        urls = extract_urls(delivery_method)
        valid_urls = [url for url in urls if not is_mp_url(url)]
        
        content_parts = []
        if company_short:
            content_parts.append(company_short)
        
        if valid_urls:
            content_parts.append(f"官网投递: {valid_urls[0]}")
        
        if contains_email(delivery_method):
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = re.findall(email_pattern, delivery_method)
            if emails:
                content_parts.append(f"邮箱投递: {emails[0]}")
        
        # 如果没有提取到有效信息，使用原文
        if len(content_parts) <= 1:  # 只有公司名或什么都没有
            if company_short:
                return f"{company_short}\n{delivery_method}"
            return delivery_method
        
        return '\n'.join(content_parts)
    
    else:
        # 图片类型：返回空，需要配合图片
        return ''


if __name__ == '__main__':
    # 测试用例
    test_cases = [
        # 应该识别为文字类型（有有效链接）
        ('扫码投递或访问 https://hxjyam.zhaopin.com', '华夏久盈'),
        ('发送简历至 campus@tencent.com', '腾讯'),
        ('官网投递 https://careers.meituan.com 或邮箱 hr@meituan.com', '美团'),
        
        # 应该识别为图片类型（只有二维码/关注公众号）
        ('扫码关注公众号投递', '某企业'),
        ('添加微信：hr123', '某企业'),
        ('扫描二维码进群', '某企业'),
        
        # 混合情况（优先文字类型）
        ('关注公众号或访问 https://example.com', '某企业'),
        ('扫码投递或发送简历至 hr@company.com', '某企业'),
        
        # 只有公众号链接
        ('关注公众号 https://mp.weixin.qq.com/s/xxx', '某企业'),
    ]
    
    print("="*60)
    print("投递方式分类器测试")
    print("="*60)
    print()
    
    for delivery, company in test_cases:
        result = classify_delivery(delivery)
        reply = get_reply_content(delivery, company)
        
        print(f"📄 输入: {delivery}")
        print(f"🏢 公司: {company}")
        print(f"📊 类型: {result['type']} (置信度: {result['confidence']})")
        print(f"🔍 原因: {result['reason']}")
        print(f"💬 回复内容:\n{reply}")
        print("-"*60)
        print()
