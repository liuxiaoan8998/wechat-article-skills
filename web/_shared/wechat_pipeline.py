"""
微信公众号流水线共享模块
提供提取、验证、上传等步骤的通用工具函数
"""

import re
import json
from pathlib import Path
from typing import Tuple, List, Set

from bs4 import BeautifulSoup


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
    soup = BeautifulSoup(html_content, "html.parser")
    js_content = soup.find(id="js_content")
    if js_content:
        return _clean_fragment("".join(str(child) for child in js_content.contents)), "js_content"

    body = soup.find("body")
    if body:
        return _clean_fragment("".join(str(child) for child in body.contents)), "body"

    return _clean_fragment(html_content), "raw"


def _clean_fragment(content: str) -> str:
    """清理 HTML 片段中的脚本、样式和文档外壳。"""
    soup = BeautifulSoup(content, "html.parser")
    for tag in soup(["script", "style", "head"]):
        tag.decompose()
    cleaned = str(soup)
    cleaned = re.sub(r'<!DOCTYPE[^>]*>', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'</?html[^>]*>', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'</?body[^>]*>', '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


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


def ensure_img_srcs(content: str) -> str:
    """
    确保所有含 data-src 的图片都有真实 src。

    微信原文常用 data-src 懒加载。草稿箱上传 API 通常只识别 src，
    因此只保留 data-src 会导致上传后无图。
    """
    soup = BeautifulSoup(content, "html.parser")
    for img in soup.find_all("img"):
        data_src = img.get("data-src")
        src = img.get("src")
        if data_src and (not src or src.startswith("data:")):
            img["src"] = data_src
    return str(soup)


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
