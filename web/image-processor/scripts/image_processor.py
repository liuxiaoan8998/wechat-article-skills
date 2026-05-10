#!/usr/bin/env python3
"""
通用图片处理器

核心功能：
1. 图片裁剪（按坐标、按比例、按OCR关键词定位）
2. 图片拼接（垂直、水平、网格）
3. 格式转换（WEBP→PNG/JPG，RGBA→RGB）
4. 长图切片与重新拼接

Usage:
    python image_processor.py crop --input img.jpg --output out.jpg --top 0 --bottom 100
    python image_processor.py stitch --inputs img1.jpg img2.jpg --output out.jpg --direction vertical
    python image_processor.py convert --input img.webp --output out.png
    python image_processor.py slice --input long.jpg --output-dir ./slices/ --max-height 2000
    python image_processor.py stitch-slices --input-dir ./slices/ --output out.jpg
"""

import argparse
import os
import re
import sys
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from PIL import Image
except ImportError:
    print("错误：需要安装 Pillow。运行: pip install Pillow")
    sys.exit(1)


EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_RE = re.compile(r'1[3-9]\d{9}')
DELIVERY_HINT_RE = re.compile(
    r'(投递|申请|扫码|二维码|邮箱|邮件|网申|官网|咨询|联系|简历|报名)',
    re.IGNORECASE,
)
MIN_KEEP_HEIGHT = 80
DEFAULT_DISPLAY_GAP = 0


# ============ 裁剪 ============

def crop_image(
    input_path: str,
    output_path: str,
    left: int = 0,
    top: int = 0,
    right: Optional[int] = None,
    bottom: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    ratio: Optional[float] = None,
    anchor: str = "top",
) -> str:
    """
    裁剪图片

    Args:
        input_path: 输入图片路径
        output_path: 输出图片路径
        left, top, right, bottom: 像素坐标（0-based）
        width, height: 裁剪后的宽高（与 right/bottom 互斥）
        ratio: 保留的比例（0-1），与 anchor 配合
        anchor: ratio 模式的锚点，可选 top/bottom/center

    Returns:
        输出图片路径
    """
    img = Image.open(input_path)
    w, h = img.size

    # 确定裁剪区域
    if right is not None and bottom is not None:
        # 绝对坐标模式
        box = (left, top, right, bottom)
    elif width is not None and height is not None:
        # 宽高模式
        box = (left, top, left + width, top + height)
    elif ratio is not None:
        # 比例模式
        if anchor == "top":
            box = (0, 0, w, int(h * ratio))
        elif anchor == "bottom":
            keep = int(h * ratio)
            box = (0, h - keep, w, h)
        elif anchor == "center":
            keep = int(h * ratio)
            margin = (h - keep) // 2
            box = (0, margin, w, margin + keep)
        else:
            raise ValueError(f"不支持的锚点: {anchor}")
    else:
        raise ValueError("必须指定裁剪区域（坐标/宽高/比例）")

    # 确保不超出边界
    box = (
        max(0, box[0]),
        max(0, box[1]),
        min(w, box[2]),
        min(h, box[3])
    )

    cropped = img.crop(box)

    # 保存前处理模式
    _save_image(cropped, output_path)

    print(f"✅ 已裁剪: {input_path} ({w}x{h}) → {output_path} ({cropped.size[0]}x{cropped.size[1]})")
    return output_path


def crop_by_ocr_keyword(
    input_path: str,
    output_path: str,
    keywords: List[str],
    direction: str = "above",  # above/below/between
    buffer_px: int = 20,
    fallback_ratio: Optional[float] = None,
) -> str:
    """
    使用 OCR 定位关键词位置并裁剪

    Args:
        input_path: 输入图片路径
        output_path: 输出图片路径
        keywords: 要查找的关键词列表
        direction: 裁剪方向
            - "above": 保留关键词上方的内容（裁剪掉关键词及下方）
            - "below": 保留关键词下方的内容
            - "between": 保留两个关键词之间的内容
        buffer_px: 关键词周围的缓冲像素
        fallback_ratio: OCR 失败时的回退比例

    Returns:
        输出图片路径
    """
    img = Image.open(input_path)
    w, h = img.size

    # 尝试 OCR 定位
    keyword_y = None
    try:
        import pytesseract
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, lang='chi_sim+eng')

        for i, text in enumerate(data['text']):
            for kw in keywords:
                if kw in text:
                    y = data['top'][i]
                    if keyword_y is None or y < keyword_y:
                        keyword_y = y

        if keyword_y is None:
            print(f"⚠️ OCR 未找到关键词: {keywords}")

    except ImportError:
        print("⚠️ pytesseract 未安装，使用回退策略")
    except Exception as e:
        print(f"⚠️ OCR 失败: {e}")

    # 确定裁剪区域
    if keyword_y is not None:
        if direction == "above":
            crop_y = max(0, keyword_y - buffer_px)
            box = (0, 0, w, crop_y)
        elif direction == "below":
            crop_y = min(h, keyword_y + buffer_px)
            box = (0, crop_y, w, h)
        else:
            raise ValueError(f"不支持的裁剪方向: {direction}")
    elif fallback_ratio is not None:
        print(f"  → 使用回退比例: {fallback_ratio}")
        box = (0, 0, w, int(h * fallback_ratio))
    else:
        raise ValueError("OCR 失败且未提供回退比例")

    cropped = img.crop(box)
    _save_image(cropped, output_path)

    print(f"✅ OCR 裁剪: {input_path} → {output_path} ({cropped.size[0]}x{cropped.size[1]})")
    return output_path


# ============ 拼接 ============

def stitch_images(
    input_paths: List[str],
    output_path: str,
    direction: str = "vertical",  # vertical/horizontal
    align: str = "center",  # center/left/right/top/bottom
    padding: int = 0,
    bg_color: Tuple[int, int, int] = (255, 255, 255),
    quality: int = 95,
) -> str:
    """
    拼接多张图片

    Args:
        input_paths: 输入图片路径列表
        output_path: 输出图片路径
        direction: 拼接方向（vertical/horizontal）
        align: 对齐方式
            vertical: center/left/right
            horizontal: center/top/bottom
        padding: 图片间距（像素）
        bg_color: 背景色 (R, G, B)
        quality: JPEG 质量（1-100）

    Returns:
        输出图片路径
    """
    if len(input_paths) < 2:
        raise ValueError("至少需要 2 张图片")

    # 加载所有图片
    images = []
    for path in input_paths:
        img = Image.open(path)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        images.append(img)

    if direction == "vertical":
        # 垂直拼接：宽度取最大，高度累加
        max_width = max(img.size[0] for img in images)
        total_height = sum(img.size[1] for img in images) + padding * (len(images) - 1)

        result = Image.new('RGB', (max_width, total_height), bg_color)

        y_offset = 0
        for img in images:
            if align == "center":
                x = (max_width - img.size[0]) // 2
            elif align == "right":
                x = max_width - img.size[0]
            else:  # left
                x = 0

            result.paste(img, (x, y_offset))
            y_offset += img.size[1] + padding

    elif direction == "horizontal":
        # 水平拼接：高度取最大，宽度累加
        max_height = max(img.size[1] for img in images)
        total_width = sum(img.size[0] for img in images) + padding * (len(images) - 1)

        result = Image.new('RGB', (total_width, max_height), bg_color)

        x_offset = 0
        for img in images:
            if align == "center":
                y = (max_height - img.size[1]) // 2
            elif align == "bottom":
                y = max_height - img.size[1]
            else:  # top
                y = 0

            result.paste(img, (x_offset, y))
            x_offset += img.size[0] + padding

    else:
        raise ValueError(f"不支持的拼接方向: {direction}")

    # 保存
    _save_image(result, output_path, quality=quality)

    print(f"✅ 已拼接: {len(images)} 张图片 → {output_path} ({result.size[0]}x{result.size[1]})")
    return output_path


def stitch_grid(
    input_paths: List[str],
    output_path: str,
    cols: int = 2,
    padding: int = 10,
    bg_color: Tuple[int, int, int] = (255, 255, 255),
    quality: int = 95,
) -> str:
    """
    网格拼接图片

    Args:
        input_paths: 输入图片路径列表
        output_path: 输出图片路径
        cols: 列数
        padding: 间距
        bg_color: 背景色
        quality: JPEG 质量

    Returns:
        输出图片路径
    """
    images = []
    for path in input_paths:
        img = Image.open(path)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        images.append(img)

    rows = (len(images) + cols - 1) // cols

    # 计算网格单元大小（统一缩放到最大宽度）
    max_cell_width = max(img.size[0] for img in images)
    max_cell_height = max(img.size[1] for img in images)

    total_width = max_cell_width * cols + padding * (cols - 1)
    total_height = max_cell_height * rows + padding * (rows - 1)

    result = Image.new('RGB', (total_width, total_height), bg_color)

    for i, img in enumerate(images):
        row = i // cols
        col = i % cols

        x = col * (max_cell_width + padding)
        y = row * (max_cell_height + padding)

        # 居中对齐
        x += (max_cell_width - img.size[0]) // 2
        y += (max_cell_height - img.size[1]) // 2

        result.paste(img, (x, y))

    _save_image(result, output_path, quality=quality)

    print(f"✅ 网格拼接: {len(images)} 张图片 → {output_path} ({result.size[0]}x{result.size[1]}), {cols}列x{rows}行")
    return output_path


# ============ 切片 ============

def slice_long_image(
    input_path: str,
    output_dir: str,
    max_height: int = 2000,
    overlap: int = 50,
    quality: int = 95,
) -> List[str]:
    """
    将长图切片

    Args:
        input_path: 输入长图路径
        output_dir: 输出目录
        max_height: 每片最大高度
        overlap: 相邻切片重叠像素（用于无缝拼接）
        quality: JPEG 质量

    Returns:
        切片文件路径列表
    """
    img = Image.open(input_path)
    w, h = img.size

    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    slices = []
    y = 0
    slice_idx = 0

    while y < h:
        slice_idx += 1
        bottom = min(y + max_height, h)

        # 如果不是最后一片，加上重叠
        if bottom < h:
            bottom = min(bottom + overlap, h)

        slice_img = img.crop((0, y, w, bottom))

        out_path = Path(output_dir) / f"slice_{slice_idx:03d}.jpg"
        slice_img.save(out_path, 'JPEG', quality=quality)
        slices.append(str(out_path))

        print(f"  切片 {slice_idx}: y={y}-{bottom} ({w}x{slice_img.size[1]}) → {out_path}")

        y = bottom - overlap if bottom < h else bottom

    print(f"✅ 长图切片完成: {input_path} ({w}x{h}) → {len(slices)} 片")
    return slices


def stitch_slices(
    input_dir: str,
    output_path: str,
    pattern: str = "slice_*.jpg",
    quality: int = 95,
) -> str:
    """
    将切片重新拼接为长图

    Args:
        input_dir: 切片所在目录
        output_path: 输出路径
        pattern: 切片文件匹配模式
        quality: JPEG 质量

    Returns:
        输出图片路径
    """
    input_dir = Path(input_dir)
    slice_files = sorted(input_dir.glob(pattern))

    if not slice_files:
        raise FileNotFoundError(f"未找到匹配 {pattern} 的切片文件")

    return stitch_images(
        [str(f) for f in slice_files],
        output_path,
        direction="vertical",
        align="center",
        padding=0,
        quality=quality,
    )


# ============ 格式转换 ============

def convert_image(
    input_path: str,
    output_path: str,
    target_format: Optional[str] = None,
    quality: int = 95,
) -> str:
    """
    转换图片格式

    Args:
        input_path: 输入路径
        output_path: 输出路径
        target_format: 目标格式（从扩展名推断，或显式指定）
        quality: JPEG 质量

    Returns:
        输出路径
    """
    img = Image.open(input_path)

    # 处理透明通道
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    # 推断格式
    if target_format is None:
        ext = Path(output_path).suffix.lower()
        format_map = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG', '.gif': 'GIF', '.webp': 'WEBP'}
        target_format = format_map.get(ext, 'JPEG')

    if target_format == 'JPEG':
        img.save(output_path, target_format, quality=quality)
    else:
        img.save(output_path, target_format)

    print(f"✅ 已转换: {input_path} → {output_path} (格式: {target_format})")
    return output_path


def detect_actual_format(input_path: str) -> str:
    """检测图片实际格式（不依赖扩展名）"""
    with open(input_path, 'rb') as f:
        header = f.read(16)

    if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
        return 'WEBP'
    elif header[:8] == b'\x89PNG\r\n\x1a\n':
        return 'PNG'
    elif header[:2] == b'\xff\xd8':
        return 'JPEG'
    elif header[:6] in (b'GIF87a', b'GIF89a'):
        return 'GIF'
    else:
        return 'UNKNOWN'


# ============ 工具函数 ============

def _save_image(img: Image.Image, output_path: str, quality: int = 95) -> None:
    """保存图片，自动处理格式和模式"""
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    ext = Path(output_path).suffix.lower()
    if ext in ('.jpg', '.jpeg'):
        img.save(output_path, 'JPEG', quality=quality)
    elif ext == '.png':
        img.save(output_path, 'PNG')
    elif ext == '.webp':
        img.save(output_path, 'WEBP', quality=quality)
    else:
        img.save(output_path, 'JPEG', quality=quality)


def _detect_qr_boxes(img: Image.Image) -> List[Dict[str, Any]]:
    """Detect QR code bounding boxes using pyzbar or OpenCV when available."""
    detections: List[Dict[str, Any]] = []

    # pyzbar provides the most reliable bounding boxes when installed.
    try:
        from pyzbar.pyzbar import decode
        from pyzbar.wrapper import ZBarSymbol

        for obj in decode(img, symbols=[ZBarSymbol.QRCODE]):
            rect = obj.rect
            detections.append({
                "left": int(rect.left),
                "top": int(rect.top),
                "right": int(rect.left + rect.width),
                "bottom": int(rect.top + rect.height),
                "content": obj.data.decode('utf-8', errors='ignore'),
                "source": "pyzbar",
            })
        if detections:
            return detections
    except Exception:
        pass

    try:
        import cv2
        import numpy as np

        rgb = img.convert('RGB') if img.mode != 'RGB' else img
        arr = np.array(rgb)
        img_cv = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        detector = cv2.QRCodeDetector()

        ok, decoded_info, points, _ = detector.detectAndDecodeMulti(img_cv)
        if ok and points is not None:
            for idx, box in enumerate(points):
                xs = [p[0] for p in box]
                ys = [p[1] for p in box]
                detections.append({
                    "left": int(min(xs)),
                    "top": int(min(ys)),
                    "right": int(max(xs)),
                    "bottom": int(max(ys)),
                    "content": decoded_info[idx] if decoded_info and idx < len(decoded_info) else "",
                    "source": "opencv",
                })
            if detections:
                return detections

        single_data, single_box, _ = detector.detectAndDecode(img_cv)
        if single_box is not None and len(single_box) > 0:
            xs = [p[0] for p in single_box]
            ys = [p[1] for p in single_box]
            detections.append({
                "left": int(min(xs)),
                "top": int(min(ys)),
                "right": int(max(xs)),
                "bottom": int(max(ys)),
                "content": single_data or "",
                "source": "opencv",
            })
    except Exception:
        pass

    return detections


def _extract_text_blocks(
    img: Image.Image,
    img_path: Path,
    keywords: List[str],
    ocr_engine: Any,
    ocr_engine_name: str,
) -> List[Dict[str, Any]]:
    """Extract OCR blocks with geometry and delivery/contact hints."""
    blocks: List[Dict[str, Any]] = []

    def _append_block(text: str, left: int, top: int, right: int, bottom: int, score: Optional[float] = None) -> None:
        clean = text.strip()
        if not clean:
            return
        delivery_match = any(kw in clean for kw in keywords)
        contact_match = bool(EMAIL_RE.search(clean) or PHONE_RE.search(clean))
        hint_match = bool(DELIVERY_HINT_RE.search(clean))
        blocks.append({
            "text": clean,
            "left": int(left),
            "top": int(top),
            "right": int(right),
            "bottom": int(bottom),
            "width": int(right - left),
            "height": int(bottom - top),
            "area": int(max(0, right - left) * max(0, bottom - top)),
            "delivery_match": delivery_match,
            "contact_match": contact_match,
            "hint_match": hint_match,
            "score": score,
        })

    if ocr_engine_name == "rapidocr":
        ocr_result = ocr_engine(str(img_path))
        if ocr_result.boxes is not None and ocr_result.txts is not None:
            for box, text, score in zip(ocr_result.boxes, ocr_result.txts, ocr_result.scores):
                xs = [p[0] for p in box]
                ys = [p[1] for p in box]
                _append_block(text, min(xs), min(ys), max(xs), max(ys), score)
    elif ocr_engine_name == "pytesseract":
        data = ocr_engine.image_to_data(
            img, output_type=ocr_engine.Output.DICT, lang='chi_sim+eng'
        )
        for i, text in enumerate(data['text']):
            left = data['left'][i]
            top = data['top'][i]
            width = data['width'][i]
            height = data['height'][i]
            _append_block(text, left, top, left + width, top + height)

    return blocks


def _merge_ranges(ranges: List[Tuple[int, int]], max_height: int) -> List[Tuple[int, int]]:
    """Merge overlapping vertical ranges and clamp to image bounds."""
    if not ranges:
        return []

    normalized = sorted(
        [(max(0, top), min(max_height, bottom)) for top, bottom in ranges if bottom > top],
        key=lambda item: item[0],
    )
    if not normalized:
        return []

    merged = [normalized[0]]
    for top, bottom in normalized[1:]:
        last_top, last_bottom = merged[-1]
        if top <= last_bottom:
            merged[-1] = (last_top, max(last_bottom, bottom))
        else:
            merged.append((top, bottom))
    return merged


def _compute_keep_ranges(removal_ranges: List[Tuple[int, int]], image_height: int) -> List[Tuple[int, int]]:
    """Convert removal ranges to remaining visible vertical segments."""
    keep_ranges: List[Tuple[int, int]] = []
    cursor = 0
    for top, bottom in removal_ranges:
        if top - cursor >= MIN_KEEP_HEIGHT:
            keep_ranges.append((cursor, top))
        cursor = max(cursor, bottom)
    if image_height - cursor >= MIN_KEEP_HEIGHT:
        keep_ranges.append((cursor, image_height))
    return keep_ranges


def _write_image_segment(
    img: Image.Image,
    output_dir: Path,
    base_name: str,
    ext: str,
    index: int,
    top: int,
    bottom: int,
) -> Path:
    """Crop and save a kept image segment."""
    segment = img.crop((0, top, img.size[0], bottom))
    segment_path = output_dir / f"{base_name}_part_{index:02d}{ext}"
    _save_image(segment, str(segment_path))
    return segment_path


def _write_removed_segment(
    img: Image.Image,
    output_dir: Path,
    base_name: str,
    ext: str,
    index: int,
    top: int,
    bottom: int,
) -> Path:
    removed = img.crop((0, top, img.size[0], bottom))
    removed_path = output_dir / f"{base_name}_removed_{index:02d}{ext}"
    _save_image(removed, str(removed_path))
    return removed_path


# ============ 文章图片批量处理 ============

def process_article_images(
    article_id: str,
    keywords: List[str],
    delivery_ratio: float = 0.7,
    buffer_px: int = 30,
    qr_padding: int = 24,
    min_qr_size: int = 120,
    display_gap: int = DEFAULT_DISPLAY_GAP,
    project_root: Optional[str] = None,
) -> dict:
    """
    批量处理公众号文章的图片，识别并移除投递方式相关内容。

    新策略：
      A类（纯投递图）: 图片主体就是投递二维码/投递说明 → 整图移除
      B类（混合图）:   底部或局部存在投递块 → 切成多个可显示片段，不强制重拼成文件
      C类（正文图）:   无投递信息 → 原样保留

    Args:
        article_id: 文章ID
        keywords: 检测关键词列表
        delivery_ratio: 判定为纯投递图的面积占比阈值（0-1）
        buffer_px: 裁剪缓冲像素
        qr_padding: 二维码周围额外移除像素
        min_qr_size: 认为是主要二维码块的最小边长
        display_gap: 前端显示多个片段时建议间距
        project_root: 项目根目录，默认 ~/.hermes/output

    Returns:
        dict: 处理结果，包含 image_map、segments 和展示清单
    """
    # 确定项目路径
    if project_root is None:
        project_root = os.path.expanduser("~/.hermes/output")

    article_dir = Path(project_root) / article_id
    images_dir = article_dir / "images"
    draft_dir = article_dir / "draft"
    draft_images_dir = draft_dir / "images"
    delivery_dir = draft_images_dir / "delivery"

    result = {
        "article_id": article_id,
        "images_dir": str(images_dir),
        "total_images": 0,
        "class_a_removed": [],
        "class_b_segmented": [],
        "class_c_kept": [],
        "failed": [],
        "image_map": {},
        "display_manifest": {},
        "ocr_available": False,
        "qr_available": False,
        "display_gap": display_gap,
    }

    if not images_dir.exists():
        print(f"❌ 图片目录不存在: {images_dir}")
        result["message"] = "图片目录不存在"
        return result

    # 检查 OCR 可用性（优先 rapidocr，回退 pytesseract）
    ocr_engine = None
    ocr_engine_name = None
    try:
        from rapidocr import RapidOCR
        ocr_engine = RapidOCR()
        ocr_engine_name = "rapidocr"
        result["ocr_available"] = True
        print(f"✅ OCR 已启用 (rapidocr)")
    except Exception as e1:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            ocr_engine = pytesseract
            ocr_engine_name = "pytesseract"
            result["ocr_available"] = True
            print(f"✅ OCR 已启用 (pytesseract)")
        except Exception as e2:
            print(f"⚠️ OCR 不可用: rapidocr={e1}, pytesseract={e2}")
            print(f"   所有图片将按正文图处理（原样复制）。")
            print(f"   如需启用 OCR:")
            print(f"     pip install rapidocr")

    # 确保输出目录存在
    draft_images_dir.mkdir(parents=True, exist_ok=True)
    delivery_dir.mkdir(parents=True, exist_ok=True)

    # 扫描图片文件
    image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}
    image_files = sorted([
        f for f in images_dir.iterdir()
        if f.is_file() and f.suffix.lower() in image_extensions
    ])

    result["total_images"] = len(image_files)
    print(f"\n📁 发现 {len(image_files)} 张图片，开始处理...")
    print(f"   关键词: {keywords}")
    print(f"   纯投递图阈值: {delivery_ratio*100:.0f}%")
    print("-" * 50)

    for img_path in image_files:
        img_name = img_path.name
        print(f"\n🔍 处理: {img_name}")

        try:
            img = Image.open(img_path)
            w, h = img.size
            total_area = w * h

            base_name = img_path.stem
            ext = img_path.suffix or ".jpg"
            qr_boxes = _detect_qr_boxes(img)
            if qr_boxes:
                result["qr_available"] = True

            # 如果没有 OCR 和二维码能力，全部按 C 类处理
            if not result["ocr_available"] and not qr_boxes:
                output_path = draft_images_dir / img_name
                _save_image(img, str(output_path))
                result["class_c_kept"].append(img_name)
                result["image_map"][img_name] = {
                    "action": "kept",
                    "reason": "ocr_and_qr_unavailable",
                    "original_path": str(img_path.relative_to(article_dir)),
                    "draft_path": str(output_path.relative_to(article_dir)),
                    "display_parts": [str(output_path.relative_to(article_dir))],
                }
                print(f"   → 原样保留 (OCR 不可用)")
                continue

            text_blocks = []
            if result["ocr_available"]:
                text_blocks = _extract_text_blocks(
                    img=img,
                    img_path=img_path,
                    keywords=keywords,
                    ocr_engine=ocr_engine,
                    ocr_engine_name=ocr_engine_name,
                )

            matched_blocks = [
                block for block in text_blocks
                if block["delivery_match"] or block["contact_match"] or block["hint_match"]
            ]

            removal_ranges: List[Tuple[int, int]] = []
            keywords_found = list({block["text"] for block in matched_blocks if block["delivery_match"] or block["contact_match"]})

            if matched_blocks:
                for block in matched_blocks:
                    top = max(0, block["top"] - buffer_px)
                    bottom = min(h, block["bottom"] + buffer_px)
                    removal_ranges.append((top, bottom))

            qr_area_ratio = 0.0
            if qr_boxes:
                qr_boxes = [box for box in qr_boxes if (box["right"] - box["left"]) >= min_qr_size and (box["bottom"] - box["top"]) >= min_qr_size]
                for box in qr_boxes:
                    top = max(0, box["top"] - qr_padding)
                    bottom = min(h, box["bottom"] + qr_padding)
                    removal_ranges.append((top, bottom))
                if qr_boxes:
                    qr_area_ratio = sum((box["right"] - box["left"]) * (box["bottom"] - box["top"]) for box in qr_boxes) / total_area

            if not removal_ranges:
                # C类: 无关键词/二维码，原样保留
                output_path = draft_images_dir / img_name
                _save_image(img, str(output_path))
                result["class_c_kept"].append(img_name)
                result["image_map"][img_name] = {
                    "action": "kept",
                    "reason": "no_delivery_signals_found",
                    "original_path": str(img_path.relative_to(article_dir)),
                    "draft_path": str(output_path.relative_to(article_dir)),
                    "display_parts": [str(output_path.relative_to(article_dir))],
                    "text_blocks": len(text_blocks),
                    "qr_boxes": len(qr_boxes),
                }
                print(f"   → 原样保留 (未检测到投递信息)")
                continue

            merged_ranges = _merge_ranges(removal_ranges, h)
            removed_height = sum(bottom - top for top, bottom in merged_ranges)
            removal_ratio = removed_height / h if h else 0

            print(f"   命中文本块: {len(matched_blocks)}")
            print(f"   二维码块: {len(qr_boxes)}")
            print(f"   移除高度占比: {removal_ratio*100:.1f}%")

            if removal_ratio >= delivery_ratio:
                # A类: 纯投递图，整图移除
                delivery_path = delivery_dir / img_name
                _save_image(img, str(delivery_path))
                result["class_a_removed"].append(img_name)
                result["image_map"][img_name] = {
                    "action": "removed",
                    "reason": f"delivery_content_{removal_ratio*100:.0f}%",
                    "original_path": str(img_path.relative_to(article_dir)),
                    "keywords_found": keywords_found,
                    "removal_ratio": round(removal_ratio, 3),
                    "qr_area_ratio": round(qr_area_ratio, 3),
                    "removal_ranges": merged_ranges,
                    "delivery_path": str(delivery_path.relative_to(article_dir)),
                    "display_parts": [],
                }
                print(f"   → 整图移除到 delivery/ (纯投递图)")

            else:
                keep_ranges = _compute_keep_ranges(merged_ranges, h)
                if not keep_ranges:
                    delivery_path = delivery_dir / img_name
                    _save_image(img, str(delivery_path))
                    result["class_a_removed"].append(img_name)
                    result["image_map"][img_name] = {
                        "action": "removed",
                        "reason": "no_keep_ranges_after_segmentation",
                        "original_path": str(img_path.relative_to(article_dir)),
                        "keywords_found": keywords_found,
                        "removal_ratio": round(removal_ratio, 3),
                        "removal_ranges": merged_ranges,
                        "delivery_path": str(delivery_path.relative_to(article_dir)),
                        "display_parts": [],
                    }
                    print(f"   → 整图移除到 delivery/ (无可保留正文片段)")
                    continue

                display_parts: List[str] = []
                segment_records: List[Dict[str, Any]] = []
                removed_parts: List[str] = []

                for idx, (top, bottom) in enumerate(keep_ranges, 1):
                    part_path = _write_image_segment(
                        img, draft_images_dir, base_name, ext, idx, top, bottom
                    )
                    display_parts.append(str(part_path.relative_to(article_dir)))
                    segment_records.append({
                        "path": str(part_path.relative_to(article_dir)),
                        "top": top,
                        "bottom": bottom,
                        "height": bottom - top,
                    })

                for idx, (top, bottom) in enumerate(merged_ranges, 1):
                    removed_path = _write_removed_segment(
                        img, delivery_dir, base_name, ext, idx, top, bottom
                    )
                    removed_parts.append(str(removed_path.relative_to(article_dir)))

                result["class_b_segmented"].append(img_name)
                result["image_map"][img_name] = {
                    "action": "segmented",
                    "reason": "delivery_blocks_removed",
                    "original_path": str(img_path.relative_to(article_dir)),
                    "keywords_found": keywords_found,
                    "removal_ratio": round(removal_ratio, 3),
                    "qr_area_ratio": round(qr_area_ratio, 3),
                    "removal_ranges": merged_ranges,
                    "keep_ranges": keep_ranges,
                    "segments": segment_records,
                    "display_parts": display_parts,
                    "removed_parts": removed_parts,
                    "display_mode": "stacked_segments",
                }
                result["display_manifest"][img_name] = {
                    "mode": "stacked_segments",
                    "gap": display_gap,
                    "parts": display_parts,
                }
                print(f"   → 切分为 {len(display_parts)} 个显示片段，移除 {len(merged_ranges)} 个投递块")

        except Exception as e:
            print(f"   ❌ 处理失败: {e}")
            result["failed"].append({"file": img_name, "error": str(e)})
            result["image_map"][img_name] = {
                "action": "error",
                "reason": str(e),
                "original_path": str(img_path.relative_to(article_dir)),
            }

    # 保存 image_map.json 与 display_manifest.json
    map_path = draft_dir / "image_map.json"
    with open(map_path, 'w', encoding='utf-8') as f:
        json.dump(result["image_map"], f, ensure_ascii=False, indent=2)
    display_manifest_path = draft_dir / "display_manifest.json"
    with open(display_manifest_path, 'w', encoding='utf-8') as f:
        json.dump(result["display_manifest"], f, ensure_ascii=False, indent=2)

    # 输出总结
    print("\n" + "=" * 50)
    print("📊 图片处理总结")
    print(f"   总图片数: {result['total_images']}")
    print(f"   A类 整图移除: {len(result['class_a_removed'])} 张")
    print(f"   B类 分段保留: {len(result['class_b_segmented'])} 张")
    print(f"   C类 原样保留: {len(result['class_c_kept'])} 张")
    print(f"   处理失败: {len(result['failed'])} 张")
    print(f"   映射表: {map_path}")
    print(f"   展示清单: {display_manifest_path}")
    print("=" * 50)

    return result


# ============ 命令行入口 ============

def main():
    parser = argparse.ArgumentParser(
        description='通用图片处理器 - 裁剪、拼接、切片、转换',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 裁剪（保留上半部分60%）
    python image_processor.py crop --input img.jpg --output out.jpg --ratio 0.6 --anchor top

    # 裁剪（绝对坐标）
    python image_processor.py crop --input img.jpg --output out.jpg --left 0 --top 0 --right 800 --bottom 600

    # OCR 关键词裁剪（保留"投递方式"上方的内容）
    python image_processor.py crop-ocr --input img.jpg --output out.jpg --keywords "投递方式" "简历投递" --direction above

    # 垂直拼接
    python image_processor.py stitch --inputs img1.jpg img2.jpg img3.jpg --output out.jpg --direction vertical

    # 网格拼接（2列）
    python image_processor.py grid --inputs img1.jpg img2.jpg img3.jpg img4.jpg --output out.jpg --cols 2

    # 长图切片
    python image_processor.py slice --input long.jpg --output-dir ./slices/ --max-height 2000

    # 重新拼接切片
    python image_processor.py stitch-slices --input-dir ./slices/ --output out.jpg

    # 格式转换（自动检测 WEBP）
    python image_processor.py convert --input img.webp --output out.png
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # crop
    crop_parser = subparsers.add_parser('crop', help='裁剪图片')
    crop_parser.add_argument('--input', '-i', required=True)
    crop_parser.add_argument('--output', '-o', required=True)
    crop_parser.add_argument('--left', type=int, default=0)
    crop_parser.add_argument('--top', type=int, default=0)
    crop_parser.add_argument('--right', type=int)
    crop_parser.add_argument('--bottom', type=int)
    crop_parser.add_argument('--width', type=int)
    crop_parser.add_argument('--height', type=int)
    crop_parser.add_argument('--ratio', type=float)
    crop_parser.add_argument('--anchor', default='top', choices=['top', 'bottom', 'center'])

    # crop-ocr
    crop_ocr_parser = subparsers.add_parser('crop-ocr', help='OCR关键词裁剪')
    crop_ocr_parser.add_argument('--input', '-i', required=True)
    crop_ocr_parser.add_argument('--output', '-o', required=True)
    crop_ocr_parser.add_argument('--keywords', '-k', nargs='+', required=True)
    crop_ocr_parser.add_argument('--direction', default='above', choices=['above', 'below'])
    crop_ocr_parser.add_argument('--buffer', type=int, default=20)
    crop_ocr_parser.add_argument('--fallback-ratio', type=float)

    # stitch
    stitch_parser = subparsers.add_parser('stitch', help='拼接图片')
    stitch_parser.add_argument('--inputs', nargs='+', required=True)
    stitch_parser.add_argument('--output', '-o', required=True)
    stitch_parser.add_argument('--direction', default='vertical', choices=['vertical', 'horizontal'])
    stitch_parser.add_argument('--align', default='center', choices=['center', 'left', 'right', 'top', 'bottom'])
    stitch_parser.add_argument('--padding', type=int, default=0)
    stitch_parser.add_argument('--quality', type=int, default=95)

    # grid
    grid_parser = subparsers.add_parser('grid', help='网格拼接')
    grid_parser.add_argument('--inputs', nargs='+', required=True)
    grid_parser.add_argument('--output', '-o', required=True)
    grid_parser.add_argument('--cols', type=int, default=2)
    grid_parser.add_argument('--padding', type=int, default=10)
    grid_parser.add_argument('--quality', type=int, default=95)

    # slice
    slice_parser = subparsers.add_parser('slice', help='长图切片')
    slice_parser.add_argument('--input', '-i', required=True)
    slice_parser.add_argument('--output-dir', '-d', required=True)
    slice_parser.add_argument('--max-height', type=int, default=2000)
    slice_parser.add_argument('--overlap', type=int, default=50)
    slice_parser.add_argument('--quality', type=int, default=95)

    # stitch-slices
    stitch_slices_parser = subparsers.add_parser('stitch-slices', help='拼接切片')
    stitch_slices_parser.add_argument('--input-dir', '-d', required=True)
    stitch_slices_parser.add_argument('--output', '-o', required=True)
    stitch_slices_parser.add_argument('--pattern', default='slice_*.jpg')
    stitch_slices_parser.add_argument('--quality', type=int, default=95)

    # convert
    convert_parser = subparsers.add_parser('convert', help='格式转换')
    convert_parser.add_argument('--input', '-i', required=True)
    convert_parser.add_argument('--output', '-o', required=True)
    convert_parser.add_argument('--format')
    convert_parser.add_argument('--quality', type=int, default=95)

    # info
    info_parser = subparsers.add_parser('info', help='查看图片信息')
    info_parser.add_argument('--input', '-i', required=True)

    # process-article-images
    pai_parser = subparsers.add_parser('process-article-images', help='批量处理公众号文章图片（识别并移除投递方式/二维码块）')
    pai_parser.add_argument('--article-id', '-a', required=True, help='文章ID')
    pai_parser.add_argument('--keywords', '-k', nargs='+', default=["投递方式", "网申通道", "简历投递", "扫码投递", "申请方式", "网申", "二维码", "扫码申请", "投递邮箱", "咨询邮箱"], help='检测关键词列表')
    pai_parser.add_argument('--delivery-ratio', type=float, default=0.7, help='纯投递图面积占比阈值（默认0.7）')
    pai_parser.add_argument('--buffer', type=int, default=30, help='裁剪缓冲像素（默认30）')
    pai_parser.add_argument('--qr-padding', type=int, default=24, help='二维码上下扩展移除像素（默认24）')
    pai_parser.add_argument('--min-qr-size', type=int, default=120, help='识别为主要二维码块的最小边长（默认120）')
    pai_parser.add_argument('--display-gap', type=int, default=0, help='多个显示片段堆叠时建议的间距（默认0）')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'crop':
        crop_image(
            args.input, args.output,
            left=args.left, top=args.top,
            right=args.right, bottom=args.bottom,
            width=args.width, height=args.height,
            ratio=args.ratio, anchor=args.anchor
        )

    elif args.command == 'crop-ocr':
        crop_by_ocr_keyword(
            args.input, args.output,
            keywords=args.keywords,
            direction=args.direction,
            buffer_px=args.buffer,
            fallback_ratio=args.fallback_ratio
        )

    elif args.command == 'stitch':
        stitch_images(
            args.inputs, args.output,
            direction=args.direction,
            align=args.align,
            padding=args.padding,
            quality=args.quality
        )

    elif args.command == 'grid':
        stitch_grid(
            args.inputs, args.output,
            cols=args.cols,
            padding=args.padding,
            quality=args.quality
        )

    elif args.command == 'slice':
        slice_long_image(
            args.input, args.output_dir,
            max_height=args.max_height,
            overlap=args.overlap,
            quality=args.quality
        )

    elif args.command == 'stitch-slices':
        stitch_slices(
            args.input_dir, args.output,
            pattern=args.pattern,
            quality=args.quality
        )

    elif args.command == 'convert':
        convert_image(
            args.input, args.output,
            target_format=args.format,
            quality=args.quality
        )

    elif args.command == 'info':
        img = Image.open(args.input)
        actual = detect_actual_format(args.input)
        print(f"文件: {args.input}")
        print(f"扩展名: {Path(args.input).suffix}")
        print(f"实际格式: {actual}")
        print(f"尺寸: {img.size[0]}x{img.size[1]}")
        print(f"模式: {img.mode}")
        print(f"格式: {img.format}")

    elif args.command == 'process-article-images':
        process_article_images(
            article_id=args.article_id,
            keywords=args.keywords,
            delivery_ratio=args.delivery_ratio,
            buffer_px=args.buffer,
            qr_padding=args.qr_padding,
            min_qr_size=args.min_qr_size,
            display_gap=args.display_gap,
        )


if __name__ == '__main__':
    main()
