#!/usr/bin/env python3
"""
OCR图片查找器
从 article-ocr.md 中找到包含投递方式的图片
"""

import re
import os
from pathlib import Path


# 图片匹配关键词
IMAGE_MATCH_KEYWORDS = [
    '二维码',
    '扫码',
    '关注',
    '进群',
    '加群',
    '添加微信',
    '微信投递',
    '扫描',
    '投递',
]


def parse_ocr_file(ocr_file_path: str) -> list:
    """
    解析 article-ocr.md 文件，提取图片和对应文字
    
    Returns:
        [
            {
                'image_file': 'img_001.png',
                'image_mark': '[图片1: xxx]',
                'text': '图片下方的文字内容...'
            },
            ...
        ]
    """
    if not os.path.exists(ocr_file_path):
        return []
    
    with open(ocr_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取 Part 2（正文识别内容）
    part2_match = re.search(
        r'## Part 2: 正文识别内容\s*\n(.*?)(?=\n## Part 3:|$)',
        content,
        re.DOTALL
    )
    
    if not part2_match:
        return []
    
    part2_content = part2_match.group(1)
    
    # 解析图片标记和文字
    # 格式：[图片N: 描述] 或 [图片N]
    image_pattern = r'\[图片(\d+)[:\s]*([^\]]*)\]'
    
    images = []
    last_end = 0
    
    for match in re.finditer(image_pattern, part2_content):
        img_num = match.group(1)
        img_desc = match.group(2).strip()
        
        # 提取该图片后的文字（直到下一个图片标记或结束）
        start = match.end()
        next_match = re.search(image_pattern, part2_content[start:])
        if next_match:
            end = start + next_match.start()
        else:
            end = len(part2_content)
        
        text = part2_content[start:end].strip()
        
        images.append({
            'image_num': int(img_num),
            'image_file': f'img_{int(img_num):03d}.png',
            'image_mark': match.group(0),
            'description': img_desc,
            'text': text
        })
    
    return images


def find_delivery_image(ocr_file_path: str) -> dict:
    """
    找到包含投递方式的图片
    
    策略：
    1. 解析 article-ocr.md
    2. 遍历所有图片，检查图片描述和后续文字
    3. 匹配到关键词则返回该图片信息
    4. 返回第一张匹配的图片
    
    Args:
        ocr_file_path: article-ocr.md 文件路径
        
    Returns:
        {
            'image_file': 'img_003.png',
            'image_num': 3,
            'matched_keyword': '二维码',
            'context': '图片上下文文字...'
        }
        或 None（未找到）
    """
    images = parse_ocr_file(ocr_file_path)
    
    if not images:
        return None
    
    # 遍历图片，找匹配
    for img_info in images:
        # 检查图片描述
        desc = img_info.get('description', '')
        text = img_info.get('text', '')
        
        # 合并检查
        check_text = desc + ' ' + text
        
        for keyword in IMAGE_MATCH_KEYWORDS:
            if keyword in check_text:
                return {
                    'image_file': img_info['image_file'],
                    'image_num': img_info['image_num'],
                    'matched_keyword': keyword,
                    'context': text[:200]  # 前200字上下文
                }
    
    # 未找到匹配，返回第一张图片（兜底）
    if images:
        return {
            'image_file': images[0]['image_file'],
            'image_num': images[0]['image_num'],
            'matched_keyword': '',
            'context': images[0]['text'][:200],
            'fallback': True  # 标记为兜底
        }
    
    return None


def get_image_full_path(article_dir: str, image_file: str) -> str:
    """
    获取图片完整路径
    
    Args:
        article_dir: 文章目录（如 ~/.hermes/output/文章标题/）
        image_file: 图片文件名（如 img_003.png）
        
    Returns:
        str: 完整路径
    """
    images_dir = os.path.join(article_dir, 'images')
    return os.path.join(images_dir, image_file)


if __name__ == '__main__':
    # 测试
    import sys
    
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        result = find_delivery_image(test_file)
        print(f"查找结果: {result}")
    else:
        print("用法: python ocr_image_finder.py <article-ocr.md路径>")
