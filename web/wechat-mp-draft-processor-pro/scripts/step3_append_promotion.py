#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号草稿处理器 Pro - 步骤3: 追加推广模板

功能:
  根据账号配置，在 draft.html 正文区域（js_content）尾部追加推广模板。
  同时生成 draft.json 元数据文件。

输入:
  draft/draft.html（步骤1+2 的输出）

输出:
  draft/draft.html（追加模板后）
  draft/draft.json（元数据）

用法:
  python3 step3_append_promotion.py <article_id> --account xingyan_shixi
  python3 step3_append_promotion.py <article_id> --account xingyan_shixi --keyword 0429
"""

import sys
import os
import re
import json
from pathlib import Path
from datetime import datetime


def find_project_root():
    """检测项目根目录，优先使用 ~/.hermes/output"""
    home = os.path.expanduser("~")
    hermes_output = os.path.join(home, ".hermes", "output")
    if os.path.isdir(hermes_output):
        return hermes_output
    return os.getcwd()


def resolve_input_path(article_dir: str) -> str:
    """确定输入文件路径: draft/draft.html"""
    draft_path = os.path.join(article_dir, "draft", "draft.html")
    if os.path.isfile(draft_path):
        return draft_path
    # 回退到 article_original.html
    original_path = os.path.join(article_dir, "article_original.html")
    return original_path


def load_promotion_template(account: str) -> str:
    """加载账号对应的推广模板 HTML"""
    script_dir = Path(__file__).resolve().parent
    skill_dir = script_dir.parent
    template_path = skill_dir / "templates" / f"{account}.html"

    if not template_path.exists():
        raise FileNotFoundError(
            f"推广模板不存在: {template_path}\n"
            f"请先在 templates/ 目录下创建 {account}.html"
        )

    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()


def has_promotion_content(html: str) -> bool:
    """检测正文中是否已包含推广模板内容。

    通过检测以下关键特征来判断：
    - 行研实习（xingyan_shixi）：
      1. "回复关键词" + "获取简历投递方式"
      2. "订阅费用" 或 "19.9元"
      3. "汇总表" / "信息汇总表" + "筛选"
      4. "一杯奶茶钱"
    - Joblinker：
      1. "简历投递" + "点击名片"
      2. "后台回复关键词" + "获取简历投递方式"
      3. "※尽快投递"
    """
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text).strip()

    # 行研实习检测指标
    xingyan_indicators = [
        ("回复关键词" in text and "获取简历投递方式" in text),
        ("订阅费用" in text or "19.9元" in text),
        ("汇总表" in text and "筛选" in text),
        ("一杯奶茶钱" in text),
        ("关注" in text and "后台回复" in text and "订阅" in text),
    ]

    # Joblinker 检测指标
    joblinker_indicators = [
        ("简历投递" in text and "点击名片" in text),
        ("后台回复关键词" in text and "获取简历投递方式" in text),
        ("※尽快投递" in text),
    ]

    xingyan_hit = sum(xingyan_indicators)
    joblinker_hit = sum(joblinker_indicators)

    # 任何一个账号检测通过即认为已包含推广
    return xingyan_hit >= 2 or joblinker_hit >= 2


def generate_keyword() -> str:
    """生成关键词编号（格式：MMdd）"""
    now = datetime.now()
    return now.strftime("%m%d")


def extract_digest(html: str, max_length: int = 120) -> str:
    """从正文 HTML 中自动提取摘要"""
    # 先移除 script 和 style 标签
    html = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
    # 移除 HTML 标签
    text = re.sub(r'<[^>]+>', ' ', html)
    # 移除多余空白
    text = re.sub(r'\s+', ' ', text).strip()

    if len(text) <= max_length:
        return text

    # 在 max_length 附近找句子结束位置
    cutoff = max_length
    for i in range(max_length - 1, max_length - 30, -1):
        if i < 0:
            break
        if text[i] in '。！？.!?':
            cutoff = i + 1
            break

    digest = text[:cutoff]
    if cutoff < len(text):
        digest += "…"

    return digest


def load_metadata(article_dir: str) -> dict:
    """加载 metadata.json"""
    path = Path(article_dir) / "metadata.json"
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def get_account_author(account: str) -> str:
    """获取账号对应的作者名称"""
    authors = {
        "xingyan_shixi": "行研实习",
        "joblinker": "Joblinker",
    }
    return authors.get(account, account)


def append_promotion(
    article_dir: str,
    account: str = "xingyan_shixi",
    keyword: str = None,
) -> dict:
    """
    在 draft.html 中追加推广模板，并生成 draft.json

    Args:
        article_dir: 文章目录路径
        account: 账号配置名称
        keyword: 关键词编号（可选，默认自动生成 MMdd）

    Returns:
        dict: 处理结果
    """
    input_path = resolve_input_path(article_dir)
    draft_dir = os.path.join(article_dir, "draft")
    output_path = os.path.join(draft_dir, "draft.html")
    json_path = os.path.join(draft_dir, "draft.json")

    result = {
        "success": False,
        "input_path": input_path,
        "output_path": output_path,
        "json_path": json_path,
        "account": account,
        "keyword": keyword,
        "template_found": False,
        "already_has_promotion": False,
        "promotion_appended": False,
        "message": "",
    }

    if not os.path.isfile(input_path):
        result["message"] = f"错误：输入文件不存在: {input_path}"
        return result

    # 1. 加载推广模板
    try:
        template = load_promotion_template(account)
        result["template_found"] = True
    except FileNotFoundError as e:
        result["message"] = str(e)
        return result

    # 2. 读取 draft.html
    with open(input_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # 3. 检测是否已有推广内容
    if has_promotion_content(html):
        result["already_has_promotion"] = True
        result["message"] = "检测到正文已含推广内容，跳过追加模板。"
        promotion_html = ""
    else:
        # 4. 生成关键词
        if keyword is None:
            keyword = generate_keyword()
        result["keyword"] = keyword

        # 5. 填充占位符
        promotion_html = template.format(keyword=keyword)
        result["promotion_appended"] = True
        result["message"] = f"已追加推广模板（账号: {account}, 关键词: {keyword}）。"

    # 6. 解析 HTML 并追加模板
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        result["message"] = "错误：未安装 BeautifulSoup4，请运行: pip install beautifulsoup4"
        return result

    soup = BeautifulSoup(html, 'html.parser')

    # 找到 js_content
    js_content = soup.find(id='js_content')

    if js_content and promotion_html:
        # 将推广模板解析为片段
        promo_soup = BeautifulSoup(promotion_html, 'html.parser')

        # 先插入分隔空行
        js_content.append(soup.new_tag('p'))
        js_content.append(soup.new_tag('p'))

        # 追加模板内容
        for child in list(promo_soup.children):
            js_content.append(child)

    elif promotion_html:
        # 找不到 js_content，直接在 body 末尾追加
        body = soup.find('body')
        if body:
            promo_soup = BeautifulSoup(promotion_html, 'html.parser')
            body.append(soup.new_tag('p'))
            body.append(soup.new_tag('p'))
            for child in list(promo_soup.children):
                body.append(child)
        else:
            # 最后手段：直接在 HTML 末尾追加
            promo_soup = BeautifulSoup(promotion_html, 'html.parser')
            soup.append(promo_soup)

    # 7. 输出 HTML
    cleaned_html = str(soup)

    os.makedirs(draft_dir, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(cleaned_html)

    # 8. 生成 draft.json
    metadata = load_metadata(article_dir)
    original_title = metadata.get('title', '')
    original_url = metadata.get('url', '')

    # 提取摘要（从当前正文提取，不含推广模板）
    if promotion_html:
        # 提取摘要时去掉推广模板部分
        body_for_digest = re.sub(re.escape(promotion_html), '', html, flags=re.DOTALL)
        digest = extract_digest(body_for_digest)
    else:
        digest = extract_digest(html)

    draft_json = {
        "title": original_title,
        "digest": digest,
        "keyword": keyword or result.get("keyword", ""),
        "author": get_account_author(account),
        "content_source_url": original_url,
        "account": account,
        "processed_at": datetime.now().isoformat(),
    }

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(draft_json, f, ensure_ascii=False, indent=2)

    result["success"] = True
    result["draft_json"] = draft_json
    return result


def main():
    if len(sys.argv) < 2:
        print("用法: python3 step3_append_promotion.py <article_id> [--account xingyan_shixi] [--keyword 0429]")
        print("示例: python3 step3_append_promotion.py f9d1d82e --account xingyan_shixi")
        sys.exit(1)

    article_id = sys.argv[1]

    # 解析参数
    account = "xingyan_shixi"
    keyword = None

    for i, arg in enumerate(sys.argv):
        if arg == "--account" and i + 1 < len(sys.argv):
            account = sys.argv[i + 1]
        if arg == "--keyword" and i + 1 < len(sys.argv):
            keyword = sys.argv[i + 1]

    # 验证账号
    valid_accounts = ["xingyan_shixi", "joblinker"]
    if account not in valid_accounts:
        print(f"错误：不支持的账号 {account}")
        print(f"支持的账号: {', '.join(valid_accounts)}")
        sys.exit(1)

    project_root = find_project_root()
    article_dir = os.path.join(project_root, article_id)

    print(f"[步骤3] 追加推广模板")
    print(f"  文章ID: {article_id}")
    print(f"  账号: {account}")
    if keyword:
        print(f"  关键词: {keyword}")
    print(f"  输入: {resolve_input_path(article_dir)}")
    print(f"  输出: {article_dir}/draft/draft.html")
    print(f"  元数据: {article_dir}/draft/draft.json")
    print()

    result = append_promotion(article_dir, account=account, keyword=keyword)

    print(f"  结果: {result['message']}")
    print(f"  模板加载: {'✅' if result['template_found'] else '❌'}")
    print(f"  已含推广: {'✅' if result['already_has_promotion'] else '❌'}")
    print(f"  追加模板: {'✅' if result['promotion_appended'] else '❌'}")
    if result.get("keyword"):
        print(f"  关键词: {result['keyword']}")
    if result.get("draft_json"):
        print(f"  摘要: {result['draft_json'].get('digest', '')[:50]}...")
    print()

    if result["success"]:
        print("✅ 步骤3 完成")
    else:
        print("❌ 步骤3 失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
