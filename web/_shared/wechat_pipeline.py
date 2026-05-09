"""
微信公众号流水线共享模块
提供提取、验证、上传等步骤的通用工具函数
"""

import re
import json
from pathlib import Path
from typing import Tuple, List, Set


class PipelineValidationError(Exception):
    """流水线验证错误，用于阻断后续步骤"""
    pass


def extract_article_content(html_content: str) -> Tuple[str, str]:
    """
    从原始微信HTML中提取文章正文内容
    
    优先级：
    1. 提取 js_content 区域
    2. 提取 body 内容
    3. 返回整体HTML
    
    Returns:
        (content, source_label) - 内容和来源标签
    """
    # 尝试提取 js_content
    match = re.search(r'id="js_content"[^>]*>(.*?)</div>', html_content, re.DOTALL)
    if match:
        return match.group(1).strip(), "js_content"
    
    # 尝试提取 body
    match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip(), "body"
    
    # 回退：清理基本HTML结构后返回
    content = re.sub(r'<!DOCTYPE[^>]*>', '', html_content, flags=re.IGNORECASE)
    content = re.sub(r'<html[^>]*>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'</html>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'<head>.*?</head>', '', content, flags=re.IGNORECASE | re.DOTALL)
    return content.strip(), "raw"


def collect_img_refs(content: str) -> List[str]:
    """
    从HTML内容中收集所有图片引用
    
    提取 <img> 标签的 src 和 data-src 属性
    过滤掉 data URI 格式的内联图片
    
    Returns:
        图片URL或路径列表
    """
    refs = set()
    
    # 提取 src
    for match in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE):
        ref = match.group(1)
        if not ref.startswith("data:"):
            refs.add(ref)
    
    # 提取 data-src
    for match in re.finditer(r'<img[^>]+data-src=["\']([^"\']+)["\']', content, re.IGNORECASE):
        ref = match.group(1)
        if not ref.startswith("data:"):
            refs.add(ref)
    
    return sorted(list(refs))


def validate_draft_local_images(article_dir: Path, content: str) -> List[str]:
    """
    验证草稿HTML中引用的本地图片是否存在
    
    检查非http开头的图片引用，在以下目录查找：
    - article_dir/draft/images/
    - article_dir/images/
    
    Returns:
        缺失的本地图片路径列表
    """
    refs = collect_img_refs(content)
    missing = []
    
    draft_images_dir = article_dir / "draft" / "images"
    original_images_dir = article_dir / "images"
    
    for ref in refs:
        if ref.startswith(("http://", "https://", "//", "data:")):
            continue
        
        # 去掉前导路径的 /
        ref_path = ref.lstrip("/")
        
        # 检查 draft/images/
        if draft_images_dir.exists():
            if (draft_images_dir / ref_path).exists():
                continue
        
        # 检查 images/
        if original_images_dir.exists():
            if (original_images_dir / ref_path).exists():
                continue
        
        missing.append(ref)
    
    return missing


def write_manifest(article_dir: Path, data: dict) -> None:
    """
    写入文章清单文件
    """
    manifest_path = article_dir / "manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def validate_required_fields(fields: dict, required: list) -> None:
    """
    验证字段是否完整
    """
    missing = [f for f in required if not fields.get(f)]
    if missing:
        raise PipelineValidationError(f"缺少字段: {', '.join(missing)}")
