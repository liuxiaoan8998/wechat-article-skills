#!/usr/bin/env python3
"""
Regression runner for WeChat draft processing.

Covers extraction + draft generation for a fixed set of article URLs and
validates:
1. Account-specific promotion templates.
2. Long-image draft output does not duplicate overlap regions during stitching.
3. Draft images are generated and referenced as expected.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_CASES = [
    {
        "name": "pure_image_with_qr",
        "url": "https://mp.weixin.qq.com/s/kzLG3UIb_8klfxBJ0EQJgQ?scene=1",
        "expected_mode": "long_image",
    },
    {
        "name": "gif_pure_image_delivery",
        "url": "https://mp.weixin.qq.com/s/PdUJ57klh0DVTLvki-ZVuQ",
        "expected_mode": "long_image",
    },
    {
        "name": "mixed_image_delivery",
        "url": "https://mp.weixin.qq.com/s/t4DWiE89u42t9MXtud56GA",
        "expected_mode": "text",
    },
    {
        "name": "text_delivery_content",
        "url": "https://mp.weixin.qq.com/s/Z4OmhzOI0oIFs2UKdLw0Bg",
        "expected_mode": "text",
    },
]

PROMOTION_MARKERS = {
    "xingyan_shixi": ["行研实习", "订阅费用：19.9元", "关注公众号"],
    "joblinker": ["※尽快投递", "后台回复关键词", "点击名片"],
}
DISALLOWED_MARKERS = {
    "xingyan_shixi": ["※尽快投递"],
    "joblinker": ["行研实习", "订阅费用：19.9元"],
}
TEXT_DELIVERY_KEYWORDS = [
    "投递方式",
    "简历投递",
    "联系方式",
    "申请方式",
    "如何投递",
    "邮箱投递",
    "如何申请",
    "简历发送",
    "联系我们",
]
LONG_IMAGE_OVERLAP = 100


@dataclass
class ScriptContext:
    repo_root: Path
    extract_main: Path
    process_script: Path
    hermes_output: Path
    temp_output: Path


def load_process_module(process_script: Path):
    spec = importlib.util.spec_from_file_location("draft_process_module", process_script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载处理器模块: {process_script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_cmd(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)


def extract_article(ctx: ScriptContext, case_name: str, url: str, force: bool) -> Path:
    case_output = ctx.temp_output / case_name
    if force and case_output.exists():
        shutil.rmtree(case_output)
    case_output.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, str(ctx.extract_main), url, "-o", str(case_output), "-v"]
    if force:
        cmd.append("--force")
    result = run_cmd(cmd, ctx.extract_main.parent)
    if result.returncode != 0:
        raise RuntimeError(
            f"提取失败: {url}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )

    article_dirs = [p for p in case_output.iterdir() if p.is_dir() and p.name != "debug"]
    if not article_dirs:
        raise RuntimeError(f"提取成功但未找到输出目录: {case_output}")

    latest_dir = max(article_dirs, key=lambda p: p.stat().st_mtime)
    metadata_path = latest_dir / "metadata.json"
    if not metadata_path.exists():
        raise RuntimeError(f"缺少 metadata.json: {latest_dir}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    article_id = metadata.get("article_id")
    if not article_id:
        raise RuntimeError(f"metadata.json 缺少 article_id: {metadata_path}")

    hermes_article_dir = ctx.hermes_output / article_id
    if not hermes_article_dir.exists():
        raise RuntimeError(f"提取后未同步到 ~/.hermes/output: {hermes_article_dir}")
    return hermes_article_dir


def summarize_text(text: str, limit: int = 200) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact[:limit]


def check_text_mode_delivery_removed(html: str) -> dict[str, Any]:
    body_text = re.sub(r"<[^>]+>", " ", html)
    body_text = re.sub(r"\s+", " ", body_text)
    remaining = [kw for kw in TEXT_DELIVERY_KEYWORDS if kw in body_text]
    return {
        "delivery_keywords_remaining": remaining,
        "delivery_removed": not remaining,
    }


def check_long_image_overlap(article_dir: Path, report: dict[str, Any]) -> dict[str, Any]:
    ocr_path = article_dir / "article-ocr.md"
    images_dir = article_dir / "images"
    if not ocr_path.exists() or not images_dir.exists():
        return {"checked": False, "reason": "missing_ocr_or_images"}

    ocr_content = ocr_path.read_text(encoding="utf-8")
    blocks = re.split(r"#### 图片:\s*(\S+)", ocr_content)
    overlap_findings: list[dict[str, Any]] = []

    for i in range(1, len(blocks), 2):
        img_name = blocks[i]
        block = blocks[i + 1]
        slice_paths = re.findall(r"`(slices/[^`]+)`", block)
        if len(slice_paths) <= 1:
            continue

        original_path = images_dir / img_name
        generated_path = report["output_dir"] / "images" / img_name
        if not original_path.exists() or not generated_path.exists():
            continue

        from PIL import Image

        original_height = Image.open(original_path).size[1]
        expected_height = original_height - LONG_IMAGE_OVERLAP * (len(slice_paths) - 1)
        actual_height = Image.open(generated_path).size[1]
        overlap_findings.append(
            {
                "image": img_name,
                "slice_count": len(slice_paths),
                "original_height": original_height,
                "actual_height": actual_height,
                "expected_height": expected_height,
                "height_matches_expected": actual_height == expected_height,
            }
        )

    if not overlap_findings:
        return {"checked": False, "reason": "no_multi_slice_images"}

    return {
        "checked": True,
        "images": overlap_findings,
        "all_passed": all(item["height_matches_expected"] for item in overlap_findings),
    }


def run_account_regression(
    process_module,
    article_dir: Path,
    case_name: str,
    account: str,
) -> dict[str, Any]:
    output_dir = article_dir / "regression" / case_name / account
    if output_dir.exists():
        shutil.rmtree(output_dir)

    result = process_module.process_draft(
        article_dir=str(article_dir),
        account=account,
        output_dir=str(output_dir),
    )

    draft_html_path = output_dir / "draft.html"
    draft_json_path = output_dir / "draft.json"
    html = draft_html_path.read_text(encoding="utf-8")
    draft_meta = json.loads(draft_json_path.read_text(encoding="utf-8"))

    img_refs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html)
    local_img_refs = [ref for ref in img_refs if ref.startswith("images/")]

    markers_present = {
        marker: marker in html
        for marker in PROMOTION_MARKERS[account]
    }
    disallowed_present = {
        marker: marker in html
        for marker in DISALLOWED_MARKERS[account]
    }

    report = {
        "account": account,
        "output_dir": output_dir,
        "draft_html_path": draft_html_path,
        "draft_json_path": draft_json_path,
        "mode": draft_meta.get("mode"),
        "title": draft_meta.get("title"),
        "author": draft_meta.get("author"),
        "keyword": draft_meta.get("keyword"),
        "local_image_refs": local_img_refs,
        "local_image_ref_count": len(local_img_refs),
        "markers_present": markers_present,
        "disallowed_present": disallowed_present,
        "all_required_markers_present": all(markers_present.values()),
        "no_disallowed_markers": not any(disallowed_present.values()),
        "html_preview": summarize_text(html),
        "processor_result": result,
    }

    if report["mode"] == "text":
        report.update(check_text_mode_delivery_removed(html))
    else:
        report["delivery_removed"] = None
        report["delivery_keywords_remaining"] = []

    report["long_image_overlap"] = check_long_image_overlap(article_dir, report)
    return report


def run_case(
    ctx: ScriptContext,
    process_module,
    case: dict[str, Any],
    force_extract: bool,
) -> dict[str, Any]:
    article_dir = extract_article(ctx, case["name"], case["url"], force_extract)
    case_report = {
        "name": case["name"],
        "url": case["url"],
        "article_dir": str(article_dir),
        "expected_mode": case["expected_mode"],
        "accounts": {},
    }

    for account in ("xingyan_shixi", "joblinker"):
        account_report = run_account_regression(process_module, article_dir, case["name"], account)
        account_report["mode_matches_expectation"] = (
            account_report["mode"] == case["expected_mode"]
        )
        case_report["accounts"][account] = account_report

    return case_report


def build_summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    for case in cases:
        for account, report in case["accounts"].items():
            checks.append((f"{case['name']}:{account}:mode", report["mode_matches_expectation"]))
            checks.append((f"{case['name']}:{account}:markers", report["all_required_markers_present"]))
            checks.append((f"{case['name']}:{account}:cross_markers", report["no_disallowed_markers"]))
            if report["mode"] == "text":
                checks.append((f"{case['name']}:{account}:delivery_removed", report["delivery_removed"]))
            overlap = report["long_image_overlap"]
            if overlap.get("checked"):
                checks.append((f"{case['name']}:{account}:overlap", overlap.get("all_passed", False)))

    failed = [name for name, ok in checks if not ok]
    return {
        "total_checks": len(checks),
        "failed_checks": failed,
        "passed": not failed,
    }


def make_json_safe(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_json_safe(v) for v in obj]
    return obj


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run draft processor regression tests.")
    parser.add_argument(
        "--output-report",
        type=Path,
        default=Path("/tmp/wechat_draft_regression_report.json"),
        help="Path to save the JSON regression report.",
    )
    parser.add_argument(
        "--force-extract",
        action="store_true",
        help="Re-run extraction even if temp output already exists.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    script_path = Path(__file__).resolve()
    scripts_dir = script_path.parent
    repo_root = scripts_dir.parents[2]
    ctx = ScriptContext(
        repo_root=repo_root,
        extract_main=repo_root / "web" / "wechat-article-for-ai-pro" / "main.py",
        process_script=script_path,
        hermes_output=Path.home() / ".hermes" / "output",
        temp_output=Path("/tmp/wechat-draft-regression"),
    )

    process_module = load_process_module(ctx.process_script)

    case_reports = []
    for case in DEFAULT_CASES:
        print(f"[REGRESSION] Running case: {case['name']}")
        case_reports.append(run_case(ctx, process_module, case, args.force_extract))

    summary = build_summary(case_reports)
    report = {
        "summary": summary,
        "cases": case_reports,
    }
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.write_text(
        json.dumps(make_json_safe(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(make_json_safe(summary), ensure_ascii=False, indent=2))
    print(f"Report saved to: {args.output_report}")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
