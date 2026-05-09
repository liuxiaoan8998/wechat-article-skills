#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate generated article artifacts before upload."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_DIR = SCRIPT_DIR.parents[1] / "_shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

from wechat_pipeline import collect_img_refs, validate_draft_local_images


def find_article_dir(article_id: str, project_root: str | None = None) -> Path:
    root = Path(project_root).expanduser() if project_root else Path.home() / ".hermes" / "output"
    return root / article_id


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_article(article_dir: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []

    metadata_path = article_dir / "metadata.json"
    draft_html_path = article_dir / "draft" / "draft.html"
    draft_json_path = article_dir / "draft" / "draft.json"

    metadata = _load_json(metadata_path)
    draft_meta = _load_json(draft_json_path)

    if not article_dir.exists():
        return False, [f"文章目录不存在: {article_dir}"]
    if not metadata_path.exists():
        errors.append(f"缺少 metadata.json: {metadata_path}")
    if not draft_html_path.exists():
        errors.append(f"缺少 draft/draft.html: {draft_html_path}")
    if not draft_json_path.exists():
        errors.append(f"缺少 draft/draft.json: {draft_json_path}")

    for field in ("article_id", "title", "url"):
        if metadata_path.exists() and not metadata.get(field):
            errors.append(f"metadata.json 缺少字段: {field}")

    for field in ("title", "digest", "author", "content_source_url", "account"):
        if draft_json_path.exists() and not draft_meta.get(field):
            errors.append(f"draft.json 缺少字段: {field}")

    if draft_html_path.exists():
        content = draft_html_path.read_text(encoding="utf-8")
        refs = collect_img_refs(content)
        missing_images = validate_draft_local_images(article_dir, content)
        for ref in missing_images:
            errors.append(f"draft.html 引用了不存在的本地图片: {ref}")
        if refs and not (article_dir / "draft" / "images").exists():
            errors.append("draft.html 含图片引用，但缺少 draft/images 目录")

    return not errors, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验文章处理产物是否可上传")
    parser.add_argument("article_id", help="文章ID")
    parser.add_argument("--project-root", help="文章输出根目录，默认 ~/.hermes/output")
    args = parser.parse_args()

    article_dir = find_article_dir(args.article_id, args.project_root)
    ok, errors = validate_article(article_dir)

    if ok:
        print(f"✅ 文章产物校验通过: {article_dir}")
        return 0

    print(f"❌ 文章产物校验失败: {article_dir}")
    for err in errors:
        print(f"  - {err}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
