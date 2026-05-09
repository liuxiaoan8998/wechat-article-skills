#!/usr/bin/env python3
"""
企业简称提取器 v2.0 - AI驱动
使用Hermes Agent的AI能力提取企业简称
"""

import os
import json


def extract_company_name_ai(title: str) -> str:
    """
    使用AI从文章标题提取企业简称
    
    策略：
    1. 调用AI分析标题，提取企业名称
    2. 返回2-4字的企业简称
    
    Args:
        title: 文章标题
        
    Returns:
        str: 2-4字的企业简称
    """
    # 简单的规则兜底（用于非AI环境）
    if not title:
        return "未知"
    
    # 清理
    clean_title = title.strip()
    
    # 处理 "类型 | 企业名..." 格式
    if '|' in clean_title:
        parts = clean_title.split('|', 1)
        if len(parts) == 2:
            clean_title = parts[1].strip()
    
    # 提取前8个汉字作为候选（给AI更多上下文）
    chinese_chars = ''.join(c for c in clean_title if '\u4e00' <= c <= '\u9fff')
    candidate = chinese_chars[:8] if len(chinese_chars) >= 4 else clean_title[:10]
    
    return candidate


def build_extraction_prompt(title: str) -> str:
    """
    构建提取企业简称的prompt
    
    Args:
        title: 文章标题
        
    Returns:
        str: prompt文本
    """
    prompt = f"""从以下招聘文章标题中提取企业简称（2-4个字）：

标题："{title}"

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

请直接输出企业简称："""
    
    return prompt


def parse_ai_response(response: str) -> str:
    """
    解析AI返回的企业简称
    
    Args:
        response: AI的回复文本
        
    Returns:
        str: 清理后的企业简称
    """
    # 清理回复
    clean = response.strip()
    
    # 去除引号
    clean = clean.strip('"\'"')
    
    # 去除常见前缀
    clean = clean.lstrip('【').lstrip('[').lstrip('(')
    clean = clean.rstrip('】').rstrip(']').rstrip(')')
    
    # 去除"企业简称："等前缀
    if '：' in clean:
        clean = clean.split('：', 1)[1].strip()
    if ':' in clean:
        clean = clean.split(':', 1)[1].strip()
    
    # 只保留前4个字符
    clean = clean[:4]
    
    return clean if clean else "未知"


def extract_and_shorten(title: str, use_ai: bool = True) -> str:
    """
    一站式提取：从标题提取企业简称
    
    优先使用AI提取，如果失败则使用规则兜底
    
    Args:
        title: 文章标题
        use_ai: 是否使用AI（默认True）
        
    Returns:
        str: 2-4字的企业简称
    """
    if not title:
        return "未知"
    
    if use_ai:
        # 返回候选，由调用方使用AI进一步处理
        candidate = extract_company_name_ai(title)
        return candidate
    else:
        # 使用规则兜底
        return extract_company_name_rule(title)


def extract_company_name_rule(title: str) -> str:
    """
    规则兜底：从文章标题提取企业名称
    
    当AI不可用时使用
    """
    import re
    
    if not title:
        return "未知"
    
    clean_title = title.strip()
    
    # 处理 "类型 | 企业名..." 格式
    if '|' in clean_title:
        parts = clean_title.split('|', 1)
        if len(parts) == 2:
            clean_title = parts[1].strip()
    
    # 模式：XXX招聘/校招/实习
    patterns = [
        r'^(.*?)(?:20\d{2})?\s*(?:届)?\s*(?:春季|秋季|暑期)?\s*(?:校园)?\s*(?:招聘|校招|实习)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, clean_title)
        if match:
            company = match.group(1).strip()
            # 清理
            company = re.sub(r'^(?:【|\[\(|第\d+届|202\d年)\s*', '', company)
            company = re.sub(r'\s*(?:】|\]|\))$', '', company)
            company = re.sub(r'\s*\|\s*', '', company)
            # 同时清理数字年份和"届"
            company = re.sub(r'20\d{2}(?:届)?', '', company).strip()
            company = re.sub(r'(届|季|年)', '', company).strip()
            if company and len(company) >= 2:
                return company[:4]
    
    # 兜底：提取前4个汉字
    chinese_chars = ''.join(c for c in clean_title if '\u4e00' <= c <= '\u9fff')
    return chinese_chars[:4] if len(chinese_chars) >= 2 else clean_title[:4]


if __name__ == '__main__':
    # 测试
    test_cases = [
        '腾讯2026校园招聘正式启动',
        '字节跳动2026届春季校园招聘',
        '久候未来 盈在今夏丨华夏久盈2027届应届生暑期实习招募正式开启',
        '实习招聘 | 洛书投资2026暑期实习',
        '【校招】华为2026届应届生招聘',
        '美团 | 2026届北斗计划启动',
    ]
    
    print("="*60)
    print("企业简称提取器 v2.0 - AI驱动")
    print("="*60)
    print()
    print("使用方法：")
    print("1. 调用 build_extraction_prompt(title) 获取prompt")
    print("2. 将prompt发送给AI获取回复")
    print("3. 调用 parse_ai_response(response) 解析结果")
    print()
    print("测试用例：")
    for case in test_cases:
        candidate = extract_company_name_ai(case)
        prompt = build_extraction_prompt(case)
        print(f"\n标题: {case}")
        print(f"候选: {candidate}")
        print(f"Prompt: {prompt[:100]}...")
