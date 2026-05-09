#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号草稿处理器 Pro - 步骤2: 清理头部噪音

功能:
  删除头部噪音元素，包括：
  1. <h1 class="rich_media_title" id="activity-name"> - 标题区（包含文章标题、账号名称）
  2. <div id="meta_content" class="rich_media_meta_list"> - 元信息区（包含发布时间、IP属地等）
  3. <div id="js_novel_card" class="novel-card"> - 小说推荐卡片（通常已隐藏）

输入优先级:
  1. draft/draft.html（步骤1的输出，如果存在）
  2. article_original.html（原始文件）

输出:
  draft/draft.html

用法:
  python3 step2_clean_header_noise.py <article_id>
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


def resolve_input_path(article_dir: str) -> str:
    """
    确定输入文件路径
    优先级: draft/draft.html > article_original.html
    """
    draft_path = os.path.join(article_dir, "draft", "draft.html")
    original_path = os.path.join(article_dir, "article_original.html")

    if os.path.isfile(draft_path):
        return draft_path
    return original_path


def clean_header_noise(article_dir: str) -> dict:
    """
    清理文章头部噪音

    Args:
        article_dir: 文章目录路径

    Returns:
        dict: 操作结果
    """
    input_path = resolve_input_path(article_dir)
    draft_dir = os.path.join(article_dir, "draft")
    output_path = os.path.join(draft_dir, "draft.html")

    result = {
        "success": False,
        "input_path": input_path,
        "output_path": output_path,
        "elements_found": [],
        "elements_removed": [],
        "original_size": 0,
        "cleaned_size": 0,
        "removed_size": 0,
        "message": "",
    }

    if not os.path.isfile(input_path):
        result["message"] = f"错误：输入文件不存在: {input_path}"
        return result

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        result["message"] = "错误：未安装 BeautifulSoup4，请运行: pip install beautifulsoup4"
        return result

    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    result["original_size"] = len(content)

    soup = BeautifulSoup(content, "html.parser")

    # 定义头部噪音元素的选择器
    # 按优先级排序：id > class，确保精确匹配
    noise_selectors = [
        {"id": "activity-name"},
        {"id": "meta_content"},
        {"id": "js_novel_card"},
    ]

    removed = []
    found = []

    # 先找到 img-content 和 js_content，用于判断元素位置
    img_content = soup.find(id="img-content")
    js_content = soup.find(id="js_content")

    for selector in noise_selectors:
        elem = soup.find(**selector)
        if not elem:
            continue

        elem_id = elem.get("id", "")
        elem_class = " ".join(elem.get("class", []))
        tag_info = f"<{elem.name} id='{elem_id}' class='{elem_class}'>"
        found.append(tag_info)

        # 判断该元素是否为头部噪音：
        # 1. 如果在 img-content 内且在 js_content 之前
        # 2. 或者没有 img-content/js_content，直接删除
        is_header = False

        if img_content and js_content:
            # 检查元素是否在 img-content 内
            is_in_img = elem in img_content.descendants or elem.parent == img_content
            if is_in_img:
                # 检查元素在 img_content 的子元素中的位置是否在 js_content 之前
                img_children = [
                    c for c in img_content.children
                    if hasattr(c, "name") and c.name
                ]
                try:
                    elem_idx = img_children.index(elem)
                    js_idx = img_children.index(js_content)
                    is_header = elem_idx < js_idx
                except ValueError:
                    # 如果不在直接子元素中，检查是否在 js_content 之前的位置
                    # 通过 DOM 兄弟节点计算位置
                    def get_element_index_in_parent(el, parent):
                        """获取元素在父元素的直接子节点中的索引"""
                        for idx, child in enumerate(parent.children):
                            if child is el:
                                return idx
                            # 检查是否是子元素
                            if hasattr(child, 'descendants'):
                                if el in child.descendants:
                                    return idx
                        return -1

                    elem_idx = get_element_index_in_parent(elem, img_content)
                    js_idx = get_element_index_in_parent(js_content, img_content)
                    if elem_idx != -1 and js_idx != -1:
                        is_header = elem_idx < js_idx
                    else:
                        # 不能确定位置，假设是头部元素
                        is_header = True
        else:
            # 没有 img-content 或 js_content，直接删除已知的头部元素
            is_header = True

        if is_header:
            elem.decompose()
            removed.append(tag_info)

    result["elements_found"] = found
    result["elements_removed"] = removed

    # 输出标准化的HTML
    cleaned_html = soup.prettify(formatter="minimal")

    result["cleaned_size"] = len(cleaned_html)
    result["removed_size"] = len(content) - len(cleaned_html)

    # 创建 draft 目录并写入
    os.makedirs(draft_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(cleaned_html)

    result["success"] = True
    result["message"] = (
        f"已成功清理头部噪音。"
        f"发现 {len(found)} 个元素，删除 {len(removed)} 个头部噪音元素。"
        f"原始大小: {result['original_size']} → 清洗后: {result['cleaned_size']}"
    )
    return result


def main():
    if len(sys.argv) < 2:
        print("用法: python3 step2_clean_header_noise.py <article_id>")
        print("示例: python3 step2_clean_header_noise.py 4192e361")
        sys.exit(1)

    article_id = sys.argv[1]

    project_root = find_project_root()
    article_dir = os.path.join(project_root, article_id)

    print(f"[步骤2] 清理文章头部噪音")
    print(f"  文章ID: {article_id}")
    print(f"  输入文件: {resolve_input_path(article_dir)}")
    print(f"  输出文件: {article_dir}/draft/draft.html")
    print()

    result = clean_header_noise(article_dir)

    print(f"结果: {result['message']}")
    print(f"  发现元素: {len(result['elements_found'])}")
    if result["elements_found"]:
        print(f"    详细: {', '.join(result['elements_found'])}")
    print(f"  删除元素: {len(result['elements_removed'])}")
    if result["elements_removed"]:
        print(f"    详细: {', '.join(result['elements_removed'])}")
    print(f"  原始大小: {result['original_size']} 字符")
    print(f"  清洗后大小: {result['cleaned_size']} 字符")
    print(f"  删除大小: {result['removed_size']} 字符")
    print(f"  输出文件: {result['output_path']}")
    print()

    if result["success"]:
        print("✅ 步骤2 完成")
    else:
        print("❌ 步骤2 失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
