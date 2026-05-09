#!/usr/bin/env python3
"""
企业简称提取器
从文章标题提取企业简称（优先2字）
"""

import re


def extract_company_name(title: str) -> str:
    """
    从文章标题提取企业名称
    
    策略：
    1. 匹配"XXX招聘"、"XXX校招"、"XXX实习"等模式
    2. 提取XXX部分作为企业名
    3. 如果没有匹配，取标题前4个字
    
    Args:
        title: 文章标题
        
    Returns:
        str: 企业名称
    """
    if not title:
        return "未知"
    
    # 清理标题中的特殊字符
    clean_title = title.strip()
    
    # 处理 "类型 | 企业名..." 格式（如"实习招聘 | 洛书投资..."）
    if '|' in clean_title:
        parts = clean_title.split('|', 1)
        if len(parts) == 2:
            # 取 | 后面的内容
            clean_title = parts[1].strip()
    
    # 模式1：XXX招聘/校招/实习/校园招聘（优先匹配）
    patterns = [
        r'^(.*?)(?:20\d{2})?\s*(?:届)?\s*(?:春季|秋季|暑期)?\s*(?:校园)?\s*(?:招聘|校招|实习)',
        r'^(.*?)(?:招聘|校招|实习)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, clean_title)
        if match:
            company = match.group(1).strip()
            # 清理常见前缀后缀
            company = re.sub(r'^(?:【|\[\(|第\d+届|202\d年)\s*', '', company)
            company = re.sub(r'\s*(?:】|\]|\))$', '', company)
            # 清理 | 后面的内容
            company = re.split(r'\s*\|\s*', company)[0].strip()
            # 清理数字年份（如"美团2026" → "美团"）
            company = re.sub(r'20\d{2}.*$', '', company).strip()
            if company and len(company) >= 2:
                return company
    
    # 兜底：尝试提取前2-4个汉字
    # 清理非汉字字符，保留汉字
    clean = re.sub(r'[^\u4e00-\u9fa5]', '', clean_title).strip()
    # 清理常见无意义词（在任何位置）
    clean = re.sub(r'(届|季|年|月|日|第|校|招)', '', clean)
    if len(clean) >= 2:
        # 取前2-4个汉字
        return clean[:4] if len(clean) >= 4 else clean
    
    # 最后兜底：取原始标题前4个字符
    return clean_title[:4] if len(clean_title) >= 2 else clean_title


def get_short_name(company_name: str, max_len: int = 4, prefer_len: int = 2) -> str:
    """
    从企业名称提取简称（优先2字，最多4字）
    
    策略：
    1. 如果名称<=4字，直接使用
    2. 如果名称>4字，取前2字（优先）或前4字
    
    Args:
        company_name: 企业全称
        max_len: 最大长度
        prefer_len: 优先长度
        
    Returns:
        str: 企业简称
    """
    if not company_name:
        return "未知"
    
    # 清理
    name = company_name.strip()
    
    # 如果本身就很短，直接返回
    if len(name) <= max_len:
        return name
    
    # 优先取前2字
    short = name[:prefer_len]
    
    # 如果2字太短（比如"北京"、"上海"），尝试取4字
    if len(short) < prefer_len or short in ['北京', '上海', '广州', '深圳', '中国']:
        short = name[:max_len]
    
    return short


def extract_and_shorten(title: str) -> str:
    """
    一站式提取：从标题提取企业简称
    
    Args:
        title: 文章标题
        
    Returns:
        str: 2-4字的企业简称
    """
    company = extract_company_name(title)
    return get_short_name(company)


if __name__ == '__main__':
    # 测试
    test_cases = [
        '腾讯2026校园招聘正式启动',
        '字节跳动2026届春季校园招聘',
        '阿里巴巴实习生招聘',
        '【校招】华为2026届应届生招聘',
        '美团 | 2026届北斗计划启动',
        '京东2026校园招聘',
        '小红书2026届春季校招',
    ]
    
    for case in test_cases:
        company = extract_company_name(case)
        short = get_short_name(company)
        print(f"标题: {case}")
        print(f"  企业名: {company}")
        print(f"  简称: {short}")
        print()
