"""Output formatter: Generate standard 7-file structure (md, html, json, images, ocr, original_html, slices)."""

from __future__ import annotations

import json
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

from .parser import ArticleMetadata

_SHARED_DIR = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

from wechat_pipeline import extract_article_content, write_manifest


def generate_article_id() -> str:
    """Generate an 8-character UUID for article identification."""
    return uuid.uuid4().hex[:8]


def save_original_html(article_dir: Path, html_raw: str, title: str) -> None:
    """Save the original WeChat HTML (from Camoufox scraper) to article_original.html.
    
    This preserves the full HTML including base64 images (~3-4MB).
    It is used for recovery, re-extraction, and as source for upload HTML.
    """
    original_html_path = article_dir / "article_original.html"
    original_html_path.write_text(html_raw, encoding="utf-8")


def create_upload_html(article_dir: Path, html_raw: str, title: str) -> None:
    """Extract clean js_content from raw HTML for WeChat draft upload.
    
    Reduces file size from ~3.7MB to ~17KB by removing base64 images, 
    scripts, and unused CSS while preserving article content structure.
    """
    content_html, _source = extract_article_content(html_raw)
    # Clean redundant attributes but keep essential image/content attributes.
    content_html = re.sub(r'style=["\'][^"\']*["\']', '', content_html)
    content_html = re.sub(r'class=["\'][^"\']*["\']', '', content_html)
    content_html = re.sub(r'role=["\'][^"\']*["\']', '', content_html)
    content_html = re.sub(r'aria-[a-z]+=["\'][^"\']*["\']', '', content_html)
    
    clean_html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
img{{max-width:100%;height:auto;display:block;margin:10px 0}}
p{{margin:8px 0;line-height:1.6}}
body{{font-family:-apple-system,BlinkMacSystemFont,sans-serif;padding:16px}}
strong{{font-weight:bold}}
</style></head>
<body><div id="js_content">{content_html}</div></body></html>"""
    
    upload_html_path = article_dir / "article.html"
    upload_html_path.write_text(clean_html, encoding="utf-8")


def create_html_viewer(article_dir: Path, title: str, images: list[str]) -> None:
    """Create HTML viewer with original images displayed first."""
    
    html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background: #f5f5f5; 
        }}
        .container {{ 
            max-width: 800px; 
            margin: 0 auto; 
            background: white; 
            padding: 30px; 
            border-radius: 8px; 
            box-shadow: 0 2px 8px rgba(0,0,0,0.1); 
        }}
        h1 {{ 
            color: #333; 
            border-bottom: 2px solid #e0e0e0; 
            padding-bottom: 15px; 
            font-size: 24px;
        }}
        .meta {{ 
            color: #666; 
            font-size: 14px; 
            margin-bottom: 20px; 
        }}
        .original-image {{ 
            width: 100%; 
            display: block; 
            margin: 10px 0; 
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .footer {{ 
            text-align: center; 
            padding: 30px; 
            color: #999; 
            font-size: 12px; 
            margin-top: 30px;
            border-top: 1px solid #e0e0e0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <div class="meta">提取自微信公众号</div>
        
        <div class="image-gallery">
'''
    
    # Add all images
    for img in images:
        html_content += f'            <img src="images/{img}" class="original-image" alt="{img}">\n'
    
    html_content += '''
        </div>
        
        <div class="footer">
            <p>数据来源：微信公众号</p>
            <p>原文链接：见 metadata.json</p>
        </div>
    </div>
</body>
</html>
'''
    
    html_path = article_dir / "article_viewer.html"
    html_path.write_text(html_content, encoding="utf-8")


def create_metadata_json(
    article_dir: Path, 
    url: str, 
    meta: ArticleMetadata, 
    images: list[str],
    article_id: str = "",
) -> None:
    """Create metadata.json with structured information."""
    
    metadata = {
        "url": url,
        "title": meta.title or "",
        "author": meta.author or "",
        "published_at": meta.publish_time or "",
        "source": meta.source_url or url,
        "article_id": article_id,
        "extraction_method": "wechat-article-for-ai-pro",
        "extraction_time": datetime.now().isoformat(),
        "image_count": len(images),
        "images": [f"images/{img}" for img in images]
    }
    
    metadata_path = article_dir / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def rename_md_to_standard(article_dir: Path, original_md_name: str) -> None:
    """Rename original markdown file to article.md."""
    original_path = article_dir / original_md_name
    standard_path = article_dir / "article.md"
    
    if original_path.exists() and original_path != standard_path:
        # Read content and fix image paths if needed
        content = original_path.read_text(encoding="utf-8")
        
        # Ensure image paths use local images/ folder
        # Replace any absolute paths or URLs with relative paths
        content = re.sub(
            r'!\[([^\]]*)\]\((?!images/)([^)]+)\)',
            r'![\1](images/\2)',
            content
        )
        
        standard_path.write_text(content, encoding="utf-8")
        original_path.unlink()  # Remove original


def format_standard_output(
    article_dir: Path,
    url: str,
    meta: ArticleMetadata,
    original_md_name: str,
    html_raw: str = "",
) -> str:
    """Format output to standard 7-file structure.
    
    Standard structure:
        article_dir/
        ├── article_original.html  # Raw WeChat HTML (~3-4MB, with base64 images)
        ├── article.html           # Clean upload HTML (~17KB, extracted js_content)
        ├── article_viewer.html    # HTML image viewer (for human viewing)
        ├── article.md             # Markdown with local image paths
        ├── metadata.json          # Structured metadata (with article_id)
        ├── article-ocr.md         # OCR results + QR codes
        ├── images/                # Downloaded images
        └── slices/                # Long image slices (if any)
    
    Returns:
        article_id: The generated 8-character UUID
    """
    # Generate article ID
    article_id = generate_article_id()
    
    # 1. Get list of images
    images_dir = article_dir / "images"
    images = sorted([f.name for f in images_dir.iterdir() if f.name.startswith("img_")]) if images_dir.exists() else []
    
    # 2. Rename markdown to standard name
    rename_md_to_standard(article_dir, original_md_name)
    
    # 3. Save original HTML (if provided)
    if html_raw:
        save_original_html(article_dir, html_raw, meta.title or "Untitled")
        # Also create clean upload HTML from raw
        create_upload_html(article_dir, html_raw, meta.title or "Untitled")
    else:
        # Fallback: create HTML viewer only
        create_html_viewer(article_dir, meta.title or "Untitled", images)
    
    # 4. Create metadata.json with article_id
    create_metadata_json(article_dir, url, meta, images, article_id)
    write_manifest(article_dir, {
        "article_id": article_id,
        "source_url": url,
        "title": meta.title or "",
        "author": meta.author or "",
        "images": [
            {
                "id": Path(img).stem,
                "original_path": f"images/{img}",
                "draft_path": "",
                "action": "extracted",
            }
            for img in images
        ],
        "checks": {
            "image_count": len(images),
            "has_original_html": bool(html_raw),
        },
    })
    
    return article_id
