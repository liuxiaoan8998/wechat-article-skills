#!/usr/bin/env python3
"""
飞书 Base 文章重复记录清理脚本

场景：同一篇原始微信文章被拆分为多个岗位记录，导致 Base 中多条记录共享同一 article_id。
上传脚本报错："找到多个文章ID为 xxx 的文章"。

功能：
  1. 查询指定 article_id 的所有记录
  2. 保留最新一条（或用户指定 record_id）
  3. 删除其余历史记录
  4. 将保留记录的状态重置为"已选题"
  5. 可选：自动重新生成草稿并上传

用法：
  # 仅清理重复记录（保留最新）
  python3 cleanup_duplicate_records.py --article-id 7c3989b2

  # 保留指定 record_id，删除其他
  python3 cleanup_duplicate_records.py --article-id 7c3989b2 --keep recvjbuwMHZUx7

  # 清理 + 自动重新上传
  python3 cleanup_duplicate_records.py --article-id 7c3989b2 --upload

  # 仅查询（不删除）
  python3 cleanup_duplicate_records.py --article-id 7c3989b2 --dry-run
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

BASE_TOKEN = "E9y1bxjHGa9LeGs9q3Tc3J41nmf"
TABLE_ID = "tblYIqHtHrWUlVnP"
ARTICLE_STATUS_SELECTED = "已选题"


def lark_api(method: str, path: str, data: dict = None) -> dict:
    """调用 lark-cli API，返回 JSON 响应"""
    cmd = ["lark-cli", "api", method, path, "--as", "bot"]
    if data is not None:
        cmd.extend(["--data", json.dumps(data, ensure_ascii=False)])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ lark-cli 错误: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    try:
        resp = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"❌ 无法解析响应: {result.stdout[:500]}", file=sys.stderr)
        sys.exit(1)

    if not resp.get("ok", False):
        code = resp.get("error", {}).get("code", "unknown")
        msg = resp.get("error", {}).get("message", "unknown error")
        print(f"❌ API 错误 [{code}]: {msg}", file=sys.stderr)
        sys.exit(1)

    return resp


def find_records_by_article_id(article_id: str) -> List[dict]:
    """通过 article_id 查询所有记录"""
    filter_json = json.dumps({"文章ID": article_id}, ensure_ascii=False)
    path = (
        f"/open-apis/bitable/v1/apps/{BASE_TOKEN}/tables/{TABLE_ID}/records"
        f"?page_size=500&filter={filter_json}"
    )
    resp = lark_api("GET", path)
    items = resp.get("data", {}).get("items", [])
    return items


def delete_record(record_id: str) -> bool:
    """删除单条记录"""
    path = f"/open-apis/bitable/v1/apps/{BASE_TOKEN}/tables/{TABLE_ID}/records/{record_id}"
    try:
        lark_api("DELETE", path)
        return True
    except SystemExit:
        return False


def update_record_status(record_id: str, status: str = ARTICLE_STATUS_SELECTED) -> bool:
    """更新记录状态"""
    path = f"/open-apis/bitable/v1/apps/{BASE_TOKEN}/tables/{TABLE_ID}/records/{record_id}"
    data = {"文章状态": [status]}
    try:
        lark_api("PUT", path, data)
        return True
    except SystemExit:
        return False


def get_record_created_time(record: dict) -> str:
    """获取记录创建时间（用于排序）"""
    # 尝试多个字段，回退到空字符串
    fields = record.get("fields", {})
    return fields.get("创建时间", "") or fields.get("created_time", "") or ""


def print_records(records: List[dict], highlight_record_id: Optional[str] = None):
    """打印记录列表"""
    print(f"\n查询到 {len(records)} 条记录:")
    print("-" * 80)
    for r in records:
        rid = r.get("record_id", "")
        fields = r.get("fields", {})
        title = fields.get("文章标题", "")
        status = fields.get("文章状态", "")
        created = get_record_created_time(r)
        marker = " ⭐保留" if rid == highlight_record_id else ""
        print(f"  {rid} | {title[:40]:<40} | {status:<10} | {created}{marker}")
    print("-" * 80)


def main():
    parser = argparse.ArgumentParser(description="飞书 Base 文章重复记录清理")
    parser.add_argument("--article-id", "-aid", required=True, help="文章ID（8位UUID）")
    parser.add_argument("--keep", "-k", help="指定保留的 record_id（默认保留最新）")
    parser.add_argument("--upload", "-u", action="store_true", help="清理后自动重新上传")
    parser.add_argument("--dry-run", "-n", action="store_true", help="仅查询，不执行删除")
    parser.add_argument("--account", "-a", default="joblinker", help="重新生成草稿时的账号（默认 joblinker）")
    args = parser.parse_args()

    print(f"🔍 查询 article_id 为 {args.article_id} 的所有记录...")
    records = find_records_by_article_id(args.article_id)

    if not records:
        print(f"⚠️ 未找到 article_id 为 {args.article_id} 的记录")
        sys.exit(0)

    if len(records) == 1:
        print(f"✅ 只有 1 条记录（{records[0].get('record_id')}），无需清理")
        keep_id = records[0].get("record_id")
    else:
        # 确定保留哪条
        if args.keep:
            keep_id = args.keep
            # 验证是否存在
            valid = any(r.get("record_id") == keep_id for r in records)
            if not valid:
                print(f"❌ 指定的 record_id {keep_id} 不在查询结果中")
                print_records(records)
                sys.exit(1)
        else:
            # 按创建时间排序，保留最新
            records_sorted = sorted(records, key=get_record_created_time, reverse=True)
            keep_id = records_sorted[0].get("record_id")

        print_records(records, highlight_record_id=keep_id)

        if args.dry_run:
            print("\n👀 dry-run 模式，不执行任何删除/修改操作")
            sys.exit(0)

        # 删除非保留记录
        to_delete = [r for r in records if r.get("record_id") != keep_id]
        print(f"\n🗑️  即将删除 {len(to_delete)} 条历史记录...")
        for r in to_delete:
            rid = r.get("record_id")
            if delete_record(rid):
                print(f"  ✅ 已删除 {rid}")
            else:
                print(f"  ❌ 删除失败 {rid}")

    # 重置状态
    print(f'\n🔄 重置保留记录 {keep_id} 状态为 "{ARTICLE_STATUS_SELECTED}"...')
    if update_record_status(keep_id):
        print(f"  ✅ 状态已更新")
    else:
        print(f"  ❌ 状态更新失败")

    # 可选：重新生成草稿并上传
    if args.upload:
        print(f"\n📝 重新生成草稿（account={args.account}）...")

        # 删除旧 draft 目录
        draft_dir = Path.home() / ".hermes/output" / args.article_id / "draft"
        if draft_dir.exists():
            import shutil
            shutil.rmtree(draft_dir)
            print(f"  ✅ 已清除旧 draft 目录")

        # 调用 process.py
        processor = (
            Path.home()
            / ".hermes/skills/web/wechat-mp-draft-processor-pro/scripts/process.py"
        )
        result = subprocess.run(
            [sys.executable, str(processor), args.article_id, "--account", args.account],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"  ❌ 草稿生成失败:\n{result.stderr}", file=sys.stderr)
            sys.exit(1)
        print(f"  ✅ 草稿生成成功")

        # 调用上传脚本
        print(f"\n🚀 开始上传到草稿箱...")
        uploader = (
            Path.home()
            / ".hermes/skills/web/wechat-mp-draft-uploader/scripts/upload_from_feishu.py"
        )
        result = subprocess.run(
            [sys.executable, str(uploader), "--record-id", keep_id],
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"  ❌ 上传失败:\n{result.stderr}", file=sys.stderr)
            sys.exit(1)

    print("\n✅ 操作完成")


if __name__ == "__main__":
    main()
