#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML 修复工具

用途：修复 step1 字符串截断可能导致的 broken HTML。

主要问题：
  1. 截断点可能落在 HTML 开始标签内部，导致属性不完整（如 <div class="foo»）
  2. 截断点可能落在属性值内部，导致引号不匹配
  3. 最后一个元素可能只有开始标签没有结束标签

修复策略：
  - 从截断点向前扫描，检查是否有未闭合的 `<`
  - 检查未闭合的标签引号和属性引号
  - 移除不完整的最后一个标签，确保 HTML 结构完整
"""

import re


def repair_truncated_html(html: str) -> str:
    """
    修复被截断后可能损坏的 HTML。

    主要处理：
    1. 如果截断点落在标签内部（有 `<` 但没有后续的 `>` 闭合），移除该不完整标签。
    2. 如果存在未闭合的属性引号，移除到最近的 `<` 之前。
    3. 如果最后一个开始标签没有对应的结束标签，尝试补上。

    Args:
        html: 可能被截断的 HTML 字符串

    Returns:
        修复后的 HTML 字符串
    """
    # 策略：从尾部向前扫描，找到最后一个完整的文本/标签位置
    # 如果最后一个 `<` 没有被 `>` 闭合，说明截断点在标签内部

    html = html.rstrip()

    # 1. 检查末尾是否有未闭合的标签
    last_lt = html.rfind("<")
    last_gt = html.rfind(">")

    if last_lt > last_gt:
        # 有未闭合的 `<`，截断点在标签内部
        # 检查这个未闭合的 `<` 是否是注释开始 `<!--`
        if html[last_lt:last_lt+4] == "<!--":
            # 注释未闭合，移除整个注释
            html = html[:last_lt]
        else:
            # 普通标签未闭合，移除到 `<` 之前
            html = html[:last_lt]

    # 2. 检查未闭合的属性引号
    # 检查双引号是否平衡
    double_quotes = html.count('"')
    if double_quotes % 2 != 0:
        # 双引号不平衡，可能有属性被截断
        # 找到最近一个单独的左双引号，移除从那里到末尾
        pos = html.rfind('"')
        # 向前找 `<`
        lt_before_quote = html.rfind("<", 0, pos)
        if lt_before_quote != -1:
            html = html[:lt_before_quote]

    single_quotes = html.count("'")
    if single_quotes % 2 != 0:
        # 单引号不平衡
        pos = html.rfind("'")
        lt_before_quote = html.rfind("<", 0, pos)
        if lt_before_quote != -1:
            html = html[:lt_before_quote]

    # 3. 再次检查未闭合标签（引号修复后可能还有残留）
    last_lt = html.rfind("<")
    last_gt = html.rfind(">")
    if last_lt > last_gt:
        html = html[:last_lt]

    html = html.rstrip()

    # 4. 确保最后一个完整的内容节点被正确关闭
    # 检查是否有未闭合的标签
    open_tags = re.findall(r'<([a-zA-Z][a-zA-Z0-9]*)[^>]*?[^/]>', html)
    close_tags = re.findall(r'</([a-zA-Z][a-zA-Z0-9]*)>', html)

    # 简单的标签平衡检查（只处理常见容器标签）
    self_closing = {"br", "hr", "img", "input", "meta", "link", "area", "base",
                    "col", "embed", "param", "source", "track", "wbr"}
    stack = []
    for tag in re.finditer(r'<(/?)([a-zA-Z][a-zA-Z0-9]*)[^>]*?>', html):
        is_close = tag.group(1) == "/"
        tag_name = tag.group(2).lower()
        if tag_name in self_closing:
            continue
        if is_close:
            if stack and stack[-1] == tag_name:
                stack.pop()
        else:
            stack.append(tag_name)

    # 补上未闭合的标签
    for tag_name in reversed(stack):
        html += f"</{tag_name}>"

    # 5. 确保有 body 和 html 结束标签
    if "</html>" not in html:
        if "</body>" not in html:
            html += "\n</body>\n</html>"
        else:
            html += "\n</html>"

    return html


def repair_broken_html(html: str) -> str:
    """
    入口函数，与 repair_truncated_html 相同。
    """
    return repair_truncated_html(html)


def main():
    """测试用例"""
    test_cases = [
        # 正常情况
        ('<div class="foo">正文</div></body></html>', '<div class="foo">正文</div></body></html>'),
        # 未闭合标签
        ('<div class="foo">正文</div><span class="bar">未完', '<div class="foo">正文</div>'),
        # 属性引号未闭合
        ('<div class="foo">正文</div><img src="pic.jpg', '<div class="foo">正文</div>'),
        # 标签未平衡
        ('<div><p>正文</p>', '<div><p>正文</p></div></body></html>'),
    ]

    print("🔧 HTML 修复工具测试")
    print("=" * 60)

    all_passed = True
    for i, (input_html, expected) in enumerate(test_cases, 1):
        result = repair_truncated_html(input_html)
        passed = result == expected
        status = "✅ 通过" if passed else "❌ 失败"
        if not passed:
            all_passed = False
        print(f"\n测试 {i}: {status}")
        print(f"  输入:    {input_html[:50]}...")
        print(f"  预期:    {expected[:50]}...")
        print(f"  实际:    {result[:50]}...")

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 部分测试失败，请检查实现。")


if __name__ == "__main__":
    main()
