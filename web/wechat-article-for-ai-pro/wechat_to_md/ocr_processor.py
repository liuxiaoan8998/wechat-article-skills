"""OCR processor: Generate article-ocr.md with OCR results.

Supports:
- Normal images: Direct OCR
- Long images (>2000px height): Auto-slice and OCR each segment
- Multiple OCR engines: RapidOCR (default), AI Vision
"""

from __future__ import annotations

import base64
import io
import os
import re
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from PIL import Image

from .ocr_adapter import OCRAdapter, load_config_from_env
from .qr_detector import detect_qr_codes, format_qr_results, HAS_QR_DEPS


def read_article_markdown(article_md_path: Path) -> str:
    """Read existing article.md content."""
    if not article_md_path.exists():
        return ""
    
    content = article_md_path.read_text(encoding="utf-8")
    
    # 移除 YAML frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            content = parts[2]
    
    # 移除图片引用（![...](...)）
    content = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', content)
    
    # 清理多余空行
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content.strip()


def create_ocr_markdown(
    article_dir: Path,
    article_text: str,
    image_ocr_results: List[Tuple[str, str]],
) -> None:
    """Create article-ocr.md with text + OCR results.
    
    Args:
        article_dir: 文章目录
        article_text: 原文文字内容
        image_ocr_results: 列表，每项为 (图片文件名, OCR识别结果)
    """
    
    lines = []
    
    # 头部说明
    lines.append("# 文章内容（含图片 OCR 识别）")
    lines.append("")
    lines.append("> 本文档由 wechat-article-for-ai-pro 自动生成")
    lines.append("> 包含原文文字 + 图片 OCR 识别结果")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 第一部分：原文文字
    lines.append("## 一、原文文字内容")
    lines.append("")
    if article_text.strip():
        lines.append(article_text)
    else:
        lines.append("*原文无文字内容*")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 第二部分：图片 OCR 结果
    lines.append("## 二、图片 OCR 识别内容")
    lines.append("")
    
    if not image_ocr_results:
        lines.append("*无图片*")
    else:
        for img_name, ocr_text in image_ocr_results:
            lines.append(f"### 图片: {img_name}")
            lines.append("")
            if ocr_text and ocr_text.strip():
                lines.append(ocr_text.strip())
            else:
                lines.append("*该图片未识别到文字内容*")
            lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # 第三部分：整合全文
    lines.append("## 三、完整文字内容（原文 + OCR）")
    lines.append("")
    
    full_text_parts = []
    if article_text.strip():
        full_text_parts.append(article_text)
    
    for img_name, ocr_text in image_ocr_results:
        if ocr_text and ocr_text.strip():
            full_text_parts.append(f"\n【图片 {img_name} 内容】\n{ocr_text.strip()}")
    
    if full_text_parts:
        lines.append("\n\n".join(full_text_parts))
    else:
        lines.append("*无文字内容*")
    
    lines.append("")
    
    # 写入文件
    ocr_md_path = article_dir / "article-ocr.md"
    ocr_md_path.write_text("\n".join(lines), encoding="utf-8")


def get_image_list(article_dir: Path) -> List[Path]:
    """Get list of all images in article directory."""
    images_dir = article_dir / "images"
    if not images_dir.exists():
        return []
    
    return sorted([
        f for f in images_dir.iterdir()
        if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')
    ])


def slice_long_image(image_path: Path, max_height: int = 2000, overlap: int = 100) -> List[Image.Image]:
    """Slice a long image into segments for OCR.
    
    Args:
        image_path: Path to the image file
        max_height: Maximum height of each slice
        overlap: Overlap between slices to prevent text cutoff
        
    Returns:
        List of PIL Image segments
    """
    img = Image.open(image_path)
    width, height = img.size
    
    # If image is not too long, return as-is
    if height <= max_height:
        return [img]
    
    segments = []
    top = 0
    
    while top < height:
        bottom = min(top + max_height, height)
        segment = img.crop((0, top, width, bottom))
        segments.append(segment)
        
        # Move down with overlap
        top += max_height - overlap
        
        # Avoid infinite loop on last segment
        if bottom == height:
            break
    
    return segments


def image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 string."""
    buffer = io.BytesIO()
    # Convert to RGB if necessary (for PNG with transparency)
    if image.mode in ('RGBA', 'LA', 'P'):
        image = image.convert('RGB')
    image.save(buffer, format='JPEG', quality=95)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def ocr_image_with_vision(image_path: Path) -> str:
    """OCR a single image using AI Vision.
    
    For long images, automatically slices and OCRs each segment,
    then combines results.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        OCR text result
    """
    try:
        # Slice image if too long
        segments = slice_long_image(image_path)
        
        if len(segments) == 1:
            # Normal image - direct OCR
            return _ocr_single_image(segments[0])
        else:
            # Long image - OCR each segment and combine
            results = []
            for i, segment in enumerate(segments):
                text = _ocr_single_image(segment)
                if text.strip():
                    results.append(f"[段{i+1}]\n{text}")
            return "\n\n".join(results)
            
    except Exception as e:
        return f"[OCR错误: {str(e)}]"


def _ocr_single_image(image: Image.Image) -> str:
    """Internal: OCR a single image segment using AI Vision API.
    
    Note: This is a placeholder. Actual implementation should call
    the AI Vision API. For now, returns placeholder text.
    """
    # TODO: Implement actual AI Vision API call
    # For now, return placeholder indicating this needs external processing
    return "[需要AI Vision OCR处理]"


def process_all_images(
    article_dir: Path,
    ocr_config: Optional[Dict[str, Any]] = None
) -> Tuple[List[Tuple[str, str, List[Path]]], List[Tuple[str, List[Tuple[str, str]]]]]:
    """Process all images in article directory with OCR and QR detection.
    
    For long images, saves slices to disk and performs OCR.
    
    Args:
        article_dir: Article directory containing images/ folder
        ocr_config: OCR configuration dict (optional)
        
    Returns:
        Tuple of (ocr_results, qr_results):
        - ocr_results: List of (image_filename, status_text, slice_paths) tuples
        - qr_results: List of (image_filename, qr_data_list) tuples
          where qr_data_list is [(type, content), ...]
    """
    # Load OCR config
    if ocr_config is None:
        ocr_config = load_config_from_env()
    
    # Initialize OCR adapter
    adapter = OCRAdapter(ocr_config)
    engine_status = adapter.get_engine_status()
    print(f"[OCR] Engine: {ocr_config.get('engine', 'rapidocr')}")
    print(f"[OCR] Status: {engine_status}")
    
    images = get_image_list(article_dir)
    ocr_results = []
    qr_results = []
    
    # Create slices directory for long images
    slices_dir = article_dir / "slices"
    slices_dir.mkdir(exist_ok=True)
    
    for img_path in images:
        img = Image.open(img_path)
        width, height = img.size
        
        # Detect QR codes for all images
        qr_data = detect_qr_codes(img_path)
        if qr_data:
            qr_results.append((img_path.name, qr_data))
        
        if height > 2000:
            # Long image - slice, save, and OCR
            segments = slice_long_image(img_path)
            slice_paths = []
            ocr_texts = []
            
            for i, segment in enumerate(segments):
                slice_name = f"{img_path.stem}_slice_{i+1:02d}.jpg"
                slice_path = slices_dir / slice_name
                # Convert to RGB if necessary (for PNG with transparency)
                if segment.mode in ('RGBA', 'LA', 'P'):
                    segment = segment.convert('RGB')
                segment.save(slice_path, "JPEG", quality=95)
                slice_paths.append(slice_path)
                
                # OCR the slice
                ocr_result = adapter.ocr(slice_path)
                ocr_texts.append(f"[段{i+1}]\n{ocr_result}")
            
            status = f"[超长图 {width}x{height}，已切片为 {len(segments)} 段]\n\n" + "\n\n".join(ocr_texts)
            ocr_results.append((img_path.name, status, slice_paths))
        else:
            # Normal image - OCR directly
            ocr_result = adapter.ocr(img_path)
            status = f"[普通图片 {width}x{height}]\n\n{ocr_result}"
            ocr_results.append((img_path.name, status, [img_path]))
    
    return ocr_results, qr_results


def create_ocr_markdown_v2(
    article_dir: Path,
    article_text: str,
    image_ocr_results: List[Tuple[str, str, List[Path]]],
    qr_results: List[Tuple[str, List[Tuple[str, str]]]] = None,
) -> None:
    """Create article-ocr.md with OCR processing instructions and QR code detection.
    
    Args:
        article_dir: 文章目录
        article_text: 原文文字内容
        image_ocr_results: 列表，每项为 (图片文件名, 状态, 切片路径列表)
        qr_results: 二维码识别结果，每项为 (图片文件名, [(类型, 内容), ...])
    """
    
    lines = []
    
    # 头部说明
    lines.append("# 文章内容（含图片 OCR 识别）")
    lines.append("")
    lines.append("> 本文档由 wechat-article-for-ai-pro 自动生成")
    lines.append("> 包含原文文字 + 图片 OCR 识别结果 + 二维码识别")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 第一部分：原文文字
    lines.append("## 一、原文文字内容")
    lines.append("")
    if article_text.strip():
        lines.append(article_text)
    else:
        lines.append("*原文无文字内容*")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 第二部分：二维码识别内容
    lines.append("## 二、二维码识别内容")
    lines.append("")
    
    if qr_results and len(qr_results) > 0:
        lines.append(f"检测到 **{len(qr_results)}** 张包含二维码的图片")
        lines.append("")
        
        for img_name, qr_data_list in qr_results:
            lines.append(f"### {img_name}")
            lines.append("")
            lines.append(f"**图片路径**: `images/{img_name}`")
            lines.append("")
            
            for i, (qr_type, content) in enumerate(qr_data_list, 1):
                lines.append(f"**二维码 {i}**:")
                lines.append("")
                
                # 类型标签
                type_label = {
                    'recruitment_url': '📝 招聘/报名链接',
                    'url': '🔗 链接',
                    'contact': '📞 联系方式',
                    'text': '📝 文本内容'
                }.get(qr_type, '📄 内容')
                
                lines.append(f"- **类型**: {type_label}")
                lines.append(f"- **内容**: {content}")
                lines.append("")
            
            lines.append("---")
            lines.append("")
    else:
        lines.append("*未检测到二维码*")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # 第三部分：图片 OCR 结果
    lines.append("## 三、图片 OCR 识别内容")
    lines.append("")
    lines.append("### OCR 处理说明")
    lines.append("")
    lines.append("本文档中的图片 OCR 结果需要由 Hermes Agent 完成。")
    lines.append("")
    lines.append("**处理流程：**")
    lines.append("1. 工具自动检测超长图（高度>2000px）并切片")
    lines.append("2. 切片保存在 `slices/` 目录")
    lines.append("3. Hermes Agent 使用 `vision_analyze` 识别各切片")
    lines.append("4. 结果回填到本文档对应位置")
    lines.append("")
    
    if not image_ocr_results:
        lines.append("*无图片*")
    else:
        for img_name, status, slice_paths in image_ocr_results:
            lines.append(f"#### 图片: {img_name}")
            lines.append("")
            lines.append(f"**状态**: {status}")
            lines.append("")
            
            if len(slice_paths) > 1:
                lines.append(f"**切片数量**: {len(slice_paths)} 段")
                lines.append("")
                lines.append("**切片文件**:")
                for sp in slice_paths:
                    rel_path = sp.relative_to(article_dir)
                    lines.append(f"- `{rel_path}`")
                lines.append("")
                lines.append("**OCR 结果**（待 Hermes 回填）：")
                for i, _ in enumerate(slice_paths):
                    lines.append(f"\n<!-- OCR_SLICE_{i+1}: -->\n[待识别]")
            else:
                rel_path = slice_paths[0].relative_to(article_dir)
                lines.append(f"**图片路径**: `{rel_path}`")
                lines.append("")
                lines.append("**OCR 结果**（待 Hermes 回填）：")
                lines.append("\n<!-- OCR_RESULT: -->\n[待识别]")
            
            lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # 第四部分：整合全文（原文 + OCR + 二维码有效信息）
    lines.append("## 四、完整文字内容（原文 + OCR + 二维码）")
    lines.append("")
    lines.append("*待 OCR 完成后自动更新*")
    lines.append("")
    
    # 添加二维码有效信息提示（供 AI 总结时参考）
    if qr_results and len(qr_results) > 0:
        lines.append("### 二维码关键信息（供整合参考）")
        lines.append("")
        has_recruitment = False
        for img_name, qr_data_list in qr_results:
            for qr_type, content in qr_data_list:
                if qr_type == 'recruitment_url':
                    has_recruitment = True
                    lines.append(f"- **招聘/报名链接**: `{content}`（来自 {img_name}）")
                elif qr_type == 'url':
                    lines.append(f"- **相关链接**: `{content}`（来自 {img_name}）")
                elif qr_type == 'contact':
                    lines.append(f"- **联系方式**: `{content}`（来自 {img_name}）")
        if has_recruitment:
            lines.append("")
            lines.append("> ⚠️ **注意**：检测到招聘/报名链接，请在总结中整合此信息")
        lines.append("")
        lines.append("---")
        lines.append("")
    
    # 写入文件
    ocr_md_path = article_dir / "article-ocr.md"
    ocr_md_path.write_text("\n".join(lines), encoding="utf-8")


def generate_ocr_output(article_dir: Path, image_ocr_results: List[Tuple[str, str]] = None) -> None:
    """Generate article-ocr.md for an article directory.
    
    Args:
        article_dir: 文章目录
        image_ocr_results: 预处理的 OCR 结果，如果为 None 则生成占位符
    """
    article_md = article_dir / "article.md"
    
    # 读取原文
    article_text = read_article_markdown(article_md)
    
    # 如果没有提供 OCR 结果，生成占位符
    if image_ocr_results is None:
        images = get_image_list(article_dir)
        image_ocr_results = [(img.name, "") for img in images]
    
    # 生成 OCR markdown
    create_ocr_markdown(article_dir, article_text, image_ocr_results)
