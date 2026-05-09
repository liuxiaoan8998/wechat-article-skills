"""QR Code detector for extracting QR codes from images.

This module provides functionality to detect and decode QR codes in images,
which is useful for extracting application links, contact info, etc. from
WeChat article images.

Uses OpenCV as fallback if pyzbar is not available (requires zbar system library).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple, Optional
from urllib.parse import urlparse

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Try pyzbar first (better accuracy), fallback to OpenCV
try:
    from pyzbar.pyzbar import decode
    from pyzbar.wrapper import ZBarSymbol
    HAS_PYZBAR = True
    HAS_CV2 = False
except ImportError:
    HAS_PYZBAR = False
    try:
        import cv2
        import numpy as np
        HAS_CV2 = True
    except ImportError:
        HAS_CV2 = False


def is_url(text: str) -> bool:
    """Check if text is a valid URL."""
    try:
        result = urlparse(text)
        return all([result.scheme, result.netloc])
    except:
        return False


def is_recruitment_url(url: str) -> bool:
    """Check if URL is likely a recruitment/application link."""
    recruitment_keywords = [
        'apply', 'job', 'career', 'hire', 'recruit', 'position',
        'campus', '校招', '招聘', '应聘', '报名', '投递',
        'join', 'talent', 'opportunity', 'intern',
        'weixin.qq.com', 'mp.weixin.qq.com', 'forms', 'survey',
        'wj.qq.com', 'jinshuju', 'shimo', 'feishu.cn', 'larksuite'
    ]
    url_lower = url.lower()
    return any(keyword in url_lower for keyword in recruitment_keywords)


def detect_qr_codes_opencv(image: Image.Image) -> List[Tuple[str, str]]:
    """Detect QR codes using OpenCV.
    
    Args:
        image: PIL Image object
        
    Returns:
        List of (data_type, content) tuples
    """
    if not HAS_CV2 or not HAS_PIL:
        return []
    
    try:
        import cv2
        import numpy as np
        
        # Convert PIL to OpenCV format
        if image.mode != 'RGB':
            image = image.convert('RGB')
        img_array = np.array(image)
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Create QR detector
        detector = cv2.QRCodeDetector()
        
        # Detect and decode
        data, bbox, _ = detector.detectAndDecode(img_cv)
        
        results = []
        if data:
            if is_url(data):
                if is_recruitment_url(data):
                    results.append(('recruitment_url', data))
                else:
                    results.append(('url', data))
            elif re.match(r'^\d{11}$', data):
                results.append(('contact', f"电话: {data}"))
            elif '@' in data and '.' in data:
                results.append(('contact', f"邮箱: {data}"))
            else:
                results.append(('text', data))
        
        return results
        
    except Exception as e:
        return []


def detect_qr_codes_pyzbar(image: Image.Image) -> List[Tuple[str, str]]:
    """Detect QR codes using pyzbar.
    
    Args:
        image: PIL Image object
        
    Returns:
        List of (data_type, content) tuples
    """
    if not HAS_PYZBAR or not HAS_PIL:
        return []
    
    try:
        from pyzbar.pyzbar import decode
        from pyzbar.wrapper import ZBarSymbol
        
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        # Decode QR codes
        decoded_objects = decode(image, symbols=[ZBarSymbol.QRCODE])
        
        results = []
        for obj in decoded_objects:
            data = obj.data.decode('utf-8', errors='ignore')
            
            if is_url(data):
                if is_recruitment_url(data):
                    results.append(('recruitment_url', data))
                else:
                    results.append(('url', data))
            elif re.match(r'^\d{11}$', data):
                results.append(('contact', f"电话: {data}"))
            elif '@' in data and '.' in data:
                results.append(('contact', f"邮箱: {data}"))
            else:
                results.append(('text', data))
        
        return results
        
    except Exception as e:
        return []


def detect_qr_codes(image_path: Path) -> List[Tuple[str, str]]:
    """Detect and decode QR codes in an image.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        List of (data_type, content) tuples:
        - ('recruitment_url', 'https://...') - Recruitment links
        - ('url', 'https://...') - Other URL links
        - ('text', 'plain text') - Plain text
        - ('contact', '...') - Contact info
        
    Returns empty list if no QR codes found or dependencies missing.
    """
    if not HAS_PIL:
        return []
    
    try:
        img = Image.open(image_path)
        
        # Try pyzbar first, fallback to OpenCV
        if HAS_PYZBAR:
            results = detect_qr_codes_pyzbar(img)
            if results:
                return results
        
        if HAS_CV2:
            results = detect_qr_codes_opencv(img)
            return results
        
        return []
        
    except Exception as e:
        return []


def format_qr_results(qr_results: List[Tuple[str, str]]) -> str:
    """Format QR code detection results for display.
    
    Args:
        qr_results: List of (type, content) tuples from detect_qr_codes
        
    Returns:
        Formatted string for markdown output
    """
    if not qr_results:
        return ""
    
    lines = []
    for data_type, content in qr_results:
        if data_type == 'recruitment_url':
            lines.append(f"📝 **招聘/报名链接**: {content}")
        elif data_type == 'url':
            lines.append(f"🔗 **链接**: {content}")
        elif data_type == 'contact':
            lines.append(f"📞 **联系方式**: {content}")
        else:
            lines.append(f"📝 **内容**: {content}")
    
    return "\n".join(lines)


# Export availability flags
HAS_QR_DEPS = HAS_PIL and (HAS_PYZBAR or HAS_CV2)
