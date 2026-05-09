#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号草稿处理器 Pro - 步骤2.5: 图片智能处理

功能：
  1. 调用 image-processor 识别并处理文章图片（移除/裁剪投递方式图片）
  2. 重写 draft.html 中的图片引用，将微信CDN地址替换为本地处理后的图片路径
  3. 删除被标记为"移除"的图片对应的<img>标签

用法：
  python3 step2_5_process_images.py <article_id>
"""

import sys
import os
import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlparse

SHARED_DIR = Path(__file__).resolve().parents[2] / "_shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

from wechat_pipeline import write_manifest


def find_project_root() -> str:
    """检测项目根目录，优先使用 ~/.hermes/output"""
    home = os.path.expanduser("~")
    hermes_output = os.path.join(home, ".hermes", "output")
    if os.path.isdir(hermes_output):
        return hermes_output
    return os.getcwd()


def run_image_processor(article_id: str) -> bool:
    """
    调用 image-processor 处理文章图片

    Returns:
        bool: 是否成功
    """
    script_path = os.path.expanduser(
        "~/.hermes/skills/web/image-processor/scripts/image_processor.py"
    )

    if not os.path.isfile(script_path):
        print(f"⚠️  image_processor.py 不存在: {script_path}")
        return False

    cmd = [
        sys.executable,
        script_path,
        "process-article-images",
        "--article-id", article_id,
    ]

    print(f"  执行: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"⚠️  image-processor 执行失败: {result.stderr}")
        return False

    print(f"  image-processor 输出:\n{result.stdout}")
    return True


def load_image_map(article_dir: str) -> Dict[str, Dict]:
    """
    读取 image_map.json

    Returns:
        {img_name: {action, draft_path, ...}}
    """
    map_path = os.path.join(article_dir, "draft", "image_map.json")
    if not os.path.isfile(map_path):
        return {}

    with open(map_path, "r", encoding="utf-8") as f:
        return json.load(f)


def rewrite_image_references(html_path: str, image_map: Dict[str, Dict]) -> Tuple[str, Dict]:
    """
    重写 HTML 中的图片引用

    策略：
      - HTML 中 <img> 标签的顺序对应 images/img_001.png, img_002.png, ...
      - 第 N 个 <img>（从1开始）对应 img_{N:03d}.png
      - action=removed: 删除该 <img> 标签
      - action=cropped/kept: 替换 src/data-src 为本地路径 images/img_xxx.png

    Args:
        html_path: draft.html 路径
        image_map: image_map.json 内容

    Returns:
        (new_html, stats)
    """
    from bs4 import BeautifulSoup

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    img_tags = soup.find_all("img")

    stats = {
        "total_images": len(img_tags),
        "removed": 0,
        "rewritten": 0,
        "skipped": 0,
    }

    if not img_tags:
        print("  未在 HTML 中发现 <img> 标签")
        return html, stats

    def _filename_from_ref(ref: str) -> str:
        if not ref:
            return ""
        parsed = urlparse(ref.replace("&amp;", "&"))
        name = Path(parsed.path).name
        return name

    def _info_for_img(tag, fallback_idx: int):
        candidates = []
        for attr in ("src", "data-src"):
            value = tag.get(attr)
            if not value:
                continue
            filename = _filename_from_ref(value)
            if filename:
                candidates.append(filename)
                if "." in filename:
                    candidates.append(f"{Path(filename).stem}.png")
                    candidates.append(f"{Path(filename).stem}.jpg")
        data_index = tag.get("data-index") or tag.get("data-report-img-idx")
        if data_index is not None and str(data_index).isdigit():
            candidates.append(f"img_{int(data_index) + 1:03d}.png")
            candidates.append(f"img_{int(data_index) + 1:03d}.jpg")
        candidates.append(f"img_{fallback_idx:03d}.png")
        candidates.append(f"img_{fallback_idx:03d}.jpg")

        for name in candidates:
            if name in image_map:
                return name, image_map[name]
        return f"img_{fallback_idx:03d}.png", None

    for img_idx, tag in enumerate(img_tags, 1):
        img_name, info = _info_for_img(tag, img_idx)

        if not info:
            # 没有对应的 image_map 记录，保留原样
            print(f"  ⚠️  图片 {img_name} 未在 image_map 中找到，保留原样")
            stats["skipped"] += 1
            continue

        action = info.get("action", "kept")

        if action in ("removed", "removed_whole"):
            # A类：整图移除 —— 从 HTML 中删除该<img>标签
            tag.decompose()
            stats["removed"] += 1
            print(f"  ✗ 移除图片 {img_name} (纯投递图)")

        elif action in ("cropped", "kept"):
            # B类（裁剪）或 C类（保留）：替换为本地路径
            # 本地路径相对于 draft/ 目录
            local_path = info.get("draft_path") or f"draft/images/{img_name}"
            local_path = local_path.removeprefix("draft/")

            tag["src"] = local_path
            if tag.has_attr("data-src"):
                tag["data-src"] = local_path
            for attr in ("data-w", "data-ratio", "data-index", "data-report-img-idx"):
                if tag.has_attr(attr):
                    del tag[attr]
            stats["rewritten"] += 1
            action_label = "裁剪" if action == "cropped" else "保留"
            print(f"  ✓ 重写图片 {img_name} -> {local_path} ({action_label})")

    new_html = str(soup)

    # 清理因删除<img>导致的空<p>或空<section>标签
    new_html = re.sub(r'<p[^>]*>\s*</p>', '', new_html, flags=re.IGNORECASE)
    new_html = re.sub(r'<section[^>]*>\s*</section>', '', new_html, flags=re.IGNORECASE)
    # 清理连续空行
    new_html = re.sub(r'\n{3,}', '\n\n', new_html)

    return new_html, stats


def process_article_images(article_id: str) -> dict:
    """
    主流程：处理文章图片并重写 HTML

    Returns:
        dict: 操作结果
    """
    project_root = find_project_root()
    article_dir = os.path.join(project_root, article_id)
    draft_dir = os.path.join(article_dir, "draft")
    html_path = os.path.join(draft_dir, "draft.html")

    result = {
        "success": False,
        "article_id": article_id,
        "image_processor_ok": False,
        "image_map_loaded": False,
        "html_rewritten": False,
        "stats": {},
        "message": "",
    }

    # 检查前置条件
    if not os.path.isfile(html_path):
        result["message"] = f"错误：draft.html 不存在: {html_path}"
        return result

    images_dir = os.path.join(article_dir, "images")
    if not os.path.isdir(images_dir):
        result["message"] = f"⚠️  图片目录不存在: {images_dir}，跳过图片处理"
        # 没有图片也不报错，视为成功
        result["success"] = True
        return result

    # 1. 调用 image-processor
    print("  [2.5a] 调用 image-processor 分析并处理图片...")
    result["image_processor_ok"] = run_image_processor(article_id)

    if not result["image_processor_ok"]:
        print("⚠️  image-processor 执行失败，跳过图片重写")
        # 不阻塞流程，继续返回成功
        result["success"] = True
        return result

    # 2. 读取 image_map.json
    print("  [2.5b] 读取图片处理结果...")
    image_map = load_image_map(article_dir)
    if not image_map:
        print("⚠️  未找到 image_map.json，跳过图片重写")
        result["success"] = True
        return result

    result["image_map_loaded"] = True
    print(f"  发现 {len(image_map)} 张图片的处理记录")

    # 3. 重写 HTML 图片引用
    print("  [2.5c] 重写 draft.html 中的图片引用...")
    new_html, stats = rewrite_image_references(html_path, image_map)
    result["stats"] = stats

    # 4. 保存
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(new_html)

    write_manifest(Path(article_dir), {
        "article_id": article_id,
        "image_map": image_map,
        "checks": {
            "draft_img_tags": stats["total_images"],
            "removed_images": stats["removed"],
            "rewritten_images": stats["rewritten"],
            "skipped_images": stats["skipped"],
        },
    })

    result["html_rewritten"] = True
    result["success"] = True
    result["message"] = (
        f"图片处理完成。总计 {stats['total_images']} 个<img>标签，"
        f"移除 {stats['removed']} 张，重写 {stats['rewritten']} 张，跳过 {stats['skipped']} 张。"
    )

    return result


def main():
    if len(sys.argv) < 2:
        print("用法: python3 step2_5_process_images.py <article_id>")
        sys.exit(1)

    article_id = sys.argv[1]

    print(f"[步骤2.5] 图片智能处理")
    print(f"  文章ID: {article_id}")
    print()

    result = process_article_images(article_id)

    print(f"\n结果: {result['message']}")
    print(f"  image-processor: {'✅' if result['image_processor_ok'] else '⚠️'}")
    print(f"  image_map 加载: {'✅' if result['image_map_loaded'] else '⚠️'}")
    print(f"  HTML 重写: {'✅' if result['html_rewritten'] else '⚠️'}")

    if result["success"]:
        print("\n✅ 步骤2.5 完成")
    else:
        print(f"\n❌ 步骤2.5 失败: {result['message']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
