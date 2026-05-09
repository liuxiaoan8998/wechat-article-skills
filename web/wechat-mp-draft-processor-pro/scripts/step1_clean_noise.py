#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号草稿处理器 Pro - 步骤1: 清理尾部噪音

功能：
  根据文章ID，找到对应的 article_original.html，
  删除从“预览时标签不可点”向后到文章结尾的所有内容（噪音），
  然后写入 draft/draft.html。

用法：
  python3 step1_clean_noise.py <article_id>
"""

import sys
import os


def find_project_root():
    """检测项目根目录，优先使用 ~/.hermes/output"""
    home = os.path.expanduser("~")
    hermes_output = os.path.join(home, ".hermes", "output")
    if os.path.isdir(hermes_output):
        return hermes_output
    return os.getcwd()


def clean_tail_noise(article_dir: str, marker: str = "预览时标签不可点") -> dict:
    """
    清理文章尾部噪音

    Args:
        article_dir: 文章目录路径（包含 article_original.html）
        marker: 噪音分界标记文本

    Returns:
        dict: 操作结果
    """
    source_path = os.path.join(article_dir, "draft", "draft.html")
    original_path = os.path.join(article_dir, "article_original.html")
    draft_dir = os.path.join(article_dir, "draft")
    output_path = os.path.join(draft_dir, "draft.html")

    result = {
        "success": False,
        "source_path": source_path,
        "output_path": output_path,
        "marker_found": False,
        "marker_position": -1,
        "original_size": 0,
        "cleaned_size": 0,
        "removed_size": 0,
        "message": "",
    }

    import re
    from html_repair import repair_truncated_html

    # 优先使用 draft/draft.html（前置步骤的输出），回退到 article_original.html
    if os.path.isfile(source_path):
        input_path = source_path
    else:
        input_path = original_path
        source_path = original_path

    if not os.path.isfile(input_path):
        result["message"] = f"错误：输入文件不存在: {input_path}"
        return result

    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    result["original_size"] = len(content)

    # 查找标记
    marker_pos = content.find(marker)
    result["marker_position"] = marker_pos

    if marker_pos == -1:
        result["marker_found"] = False
        result["message"] = f"未找到噪音分界标记“{marker}”，未执行删除操作。"
        result["cleaned_size"] = len(content)
        # 仍然保存（无变化）
        cleaned = content
        result["success"] = True
    else:
        result["marker_found"] = True

        # 删除从标记开始到文件结尾的所有内容
        cleaned = content[:marker_pos]

        # 修复截断可能导致的 broken HTML
        cleaned = repair_truncated_html(cleaned)

        result["cleaned_size"] = len(cleaned)
        result["removed_size"] = len(content) - len(cleaned)
        result["success"] = True
        result["message"] = (
            f"已成功清理尾部噪音。"
            f"在位置 {marker_pos} 处找到标记“{marker}”，"
            f"删除了 {result['removed_size']} 字符。"
            f"原始大小: {result['original_size']} → 清洗后: {result['cleaned_size']}"
        )

    # 创建 draft 目录并写入
    os.makedirs(draft_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(cleaned)

    return result


def main():
    if len(sys.argv) < 2:
        print("用法: python3 step1_clean_noise.py <article_id> [marker_text]")
        print("示例: python3 step1_clean_noise.py e3e9eabf")
        sys.exit(1)

    article_id = sys.argv[1]
    marker = sys.argv[2] if len(sys.argv) > 2 else "预览时标签不可点"

    project_root = find_project_root()
    article_dir = os.path.join(project_root, article_id)

    print(f"[步骤1] 清理文章尾部噪音")
    print(f"  文章ID: {article_id}")
    print(f"  标记文本: {marker}")
    print(f"  源文件: {article_dir}/article_original.html")
    print(f"  输出: {article_dir}/draft/draft.html")
    print()

    result = clean_tail_noise(article_dir, marker)

    print(f"结果: {result['message']}")
    print(f"  标记找到: {result['marker_found']}")
    print(f"  标记位置: {result['marker_position']}")
    print(f"  原始大小: {result['original_size']} 字符")
    print(f"  清洗后大小: {result['cleaned_size']} 字符")
    print(f"  删除大小: {result['removed_size']} 字符")
    print(f"  输出文件: {result['output_path']}")
    print()

    if result["success"]:
        print("✅ 步骤1 完成")
    else:
        print("❌ 步骤1 失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
