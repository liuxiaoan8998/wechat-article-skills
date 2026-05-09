#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号草稿处理器 Pro - 步骤5: 智能摘要生成

功能:
  基于文章标题和 OCR 内容，提取招聘类文章的核心信息（公司名、岗位类型、届数、地点等），
  生成结构化的智能摘要（120字以内）。

输入:
  article_dir 下的 metadata.json 和 article-ocr.md

输出:
  更新 draft/draft.json 中的 digest 字段
"""

import sys
import os
import re
import json
from pathlib import Path
from datetime import datetime


def find_project_root():
    """检测项目根目录"""
    home = os.path.expanduser("~")
    hermes_output = os.path.join(home, ".hermes", "output")
    if os.path.isdir(hermes_output):
        return hermes_output
    return os.getcwd()


def load_metadata(article_dir: str) -> dict:
    """加载 metadata.json"""
    path = Path(article_dir) / "metadata.json"
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def load_ocr_text(article_dir: str) -> str:
    """加载 article-ocr.md 中的 OCR 识别结果"""
    path = Path(article_dir) / "article-ocr.md"
    if not path.exists():
        return ""

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取 OCR 部分
    # 寻找 "三、图片 OCR 识别内容" 之后的内容
    ocr_match = re.search(
        r'三、图片 OCR 识别内容.*?(?=^## |\Z)',
        content,
        re.DOTALL | re.MULTILINE
    )
    if ocr_match:
        ocr_text = ocr_match.group(0)
        # 移除 markdown 标记，只保留纯文本
        ocr_text = re.sub(r'!\[.*?\]\(.*?\)', '', ocr_text)
        ocr_text = re.sub(r'[#*`\-\|]', ' ', ocr_text)
        ocr_text = re.sub(r'\s+', ' ', ocr_text).strip()
        return ocr_text

    return ""


def extract_company(title: str) -> str:
    """从标题中提取公司名"""
    # 常见公司后缀词
    company_suffixes = [
        '集团', '科技', '互联', '证券', '基金', '银行', '保险',
        '资本', '投行', '研究所', '公司', '企业', '厂', '院',
        'TV', 'BU', 'Lab', 'AI', 'AI研究院'
    ]

    # 模式1: "公司名 | 岗位"
    m = re.match(r'^([^|\uff5c\uff5c\uff5c]+?)[|\uff5c\uff5c\uff5c]', title)
    if m:
        candidate = m.group(1).strip()
        # 确认是否像公司名
        if any(s in candidate for s in company_suffixes) or len(candidate) <= 15:
            return candidate

    # 模式2: "前缀 | 公司名2026年..."
    m = re.search(r'([\u4e00-\u9fa5\w]+(?:集团|科技|证券|基金|银行|保险|公司|研究所|TV|BU))', title)
    if m:
        return m.group(1).strip()

    # 模式3: "节目名实习"
    m = re.search(r'《(.+?)》', title)
    if m and '实习' in title:
        program = m.group(1).strip()
        # 推断公司名
        if '芹果' in title or '芒果' in title:
            return '芒果TV'
        return program

    return ""


def extract_job_type(title: str) -> str:
    """从标题中提取岗位类型"""
    if '暑期实习' in title or '暑假实习' in title:
        return '暑期实习'
    if '实习生' in title or '实习' in title:
        return '实习'
    if '校园招聘' in title or '校招' in title or '秋招' in title or '春招' in title:
        return '校招'
    if '社招' in title or '社会招聘' in title or '全职' in title:
        return '社招'
    return '招聘'


def extract_year(title: str) -> str:
    """从标题中提取届数"""
    m = re.search(r'(20\d{2})届', title)
    if m:
        return m.group(1)
    m = re.search(r'(20\d{2})年', title)
    if m:
        year = int(m.group(1))
        # 如果是春招，届数 = 年份 + 1
        if '春招' in title:
            return str(year + 1)
        return str(year)
    return ""


def extract_position(title: str) -> str:
    """从标题中提取具体岗位"""
    # 模式: "XX实习生"
    m = re.search(r'([\u4e00-\u9fa5\w]+(?:实习生|实习))', title)
    if m:
        pos = m.group(1).strip()
        # 过滤掉已经在 job_type 中的通用词
        if pos not in ['实习生', '实习']:
            return pos

    # 模式: "实习生热招中"
    m = re.search(r'([\u4e00-\u9fa5\w]+?)实习生', title)
    if m:
        return m.group(1).strip() + '实习生'

    return ""


def extract_location(ocr_text: str) -> str:
    """从 OCR 文本中提取工作地点"""
    if not ocr_text:
        return ""

    # 常见城市名
    cities = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '南京',
              '苏州', '西安', '重庆', '天津', '青岛', '深圳', '长沙', '郑州']

    found_cities = []
    for city in cities:
        if city in ocr_text:
            found_cities.append(city)

    # 去重（深圳/深圳 等）
    seen = set()
    unique = []
    for c in found_cities:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    if len(unique) <= 3:
        return ' / '.join(unique)
    return ' / '.join(unique[:3]) + ' 等'


def extract_deadline(ocr_text: str) -> str:
    """从 OCR 文本中提取截止日期"""
    if not ocr_text:
        return ""

    # 日期模式
    patterns = [
        r'截止日期[:：\s]*(\d{4}年\d{1,2}月\d{1,2}日)',
        r'截止[:：\s]*(\d{4}[\-/]\d{1,2}[\-/]\d{1,2})',
        r'截止[:：\s]*(\d{1,2}月\d{1,2}日)',
        r'deadline[:：\s]*(\d{4}[\-/]\d{1,2}[\-/]\d{1,2})',
        r'(招聘时间[:：\s]*至\d{4}年\d{1,2}月\d{1,2}日)',
    ]

    for p in patterns:
        m = re.search(p, ocr_text, re.IGNORECASE)
        if m:
            return m.group(1)

    return ""


def generate_smart_digest(
    title: str,
    ocr_text: str = "",
    max_length: int = 120
) -> str:
    """
    基于标题和 OCR 内容生成智能摘要

    输出格式: 公司名 | 届数 | 岗位类型 | 具体岗位 | 地点 | 截止日期
    """
    company = extract_company(title)
    job_type = extract_job_type(title)
    year = extract_year(title)
    position = extract_position(title)
    location = extract_location(ocr_text)
    deadline = extract_deadline(ocr_text)

    # 构建摘要
    parts = []

    if company:
        parts.append(company)
    if year:
        parts.append(f"{year}届")
    if job_type:
        parts.append(job_type)
    if position and position != job_type:
        parts.append(position)
    if location:
        parts.append(location)
    if deadline:
        parts.append(f"截止{deadline}")

    digest = " | ".join(parts)

    # 如果摘要太短，补充标题关键信息
    if len(digest) < 20 and title:
        # 移除冗余词后作为补充
        clean = re.sub(r'校园招聘|启动|正式启动|热招中|招聘启动|招聘', '', title)
        clean = re.sub(r'[|\uff5c\uff5c\uff5c]', ' ', clean).strip()
        clean = re.sub(r'\s+', ' ', clean)
        if clean and clean != title:
            digest = clean if not digest else f"{digest} | {clean}"

    # 限制长度
    if len(digest) > max_length:
        digest = digest[:max_length - 1] + "…"

    return digest


def update_draft_json(article_dir: str, digest: str) -> dict:
    """更新 draft.json 中的 digest 字段"""
    draft_dir = Path(article_dir) / "draft"
    json_path = draft_dir / "draft.json"

    draft_data = {}
    if json_path.exists():
        with open(json_path, 'r', encoding='utf-8') as f:
            draft_data = json.load(f)

    draft_data["digest"] = digest
    draft_data["digest_generated_at"] = datetime.now().isoformat()
    draft_data["digest_source"] = "smart"

    os.makedirs(draft_dir, exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(draft_data, f, ensure_ascii=False, indent=2)

    return draft_data


def smart_digest(article_dir: str) -> dict:
    """
    执行智能摘要生成

    Returns:
        dict: 处理结果
    """
    result = {
        "success": False,
        "digest": "",
        "message": "",
    }

    # 1. 加载元数据
    metadata = load_metadata(article_dir)
    title = metadata.get('title', '')

    if not title:
        result["message"] = "错误：metadata.json 中没有标题"
        return result

    # 2. 加载 OCR 文本
    ocr_text = load_ocr_text(article_dir)

    # 3. 生成智能摘要
    digest = generate_smart_digest(title, ocr_text)

    # 4. 更新 draft.json
    draft_data = update_draft_json(article_dir, digest)

    result["success"] = True
    result["digest"] = digest
    result["draft_data"] = draft_data
    result["message"] = f"已生成智能摘要: {digest[:50]}..."

    return result


def main():
    if len(sys.argv) < 2:
        print("用法: python3 step5_smart_digest.py <article_id>")
        print("示例: python3 step5_smart_digest.py 4192e361")
        sys.exit(1)

    article_id = sys.argv[1]
    project_root = find_project_root()
    article_dir = os.path.join(project_root, article_id)

    print(f"[步骤5] 智能摘要生成")
    print(f"  文章ID: {article_id}")
    print(f"  文章目录: {article_dir}")
    print()

    result = smart_digest(article_dir)

    if result["success"]:
        print(f"  ✓ {result['message']}")
        print(f"  摘要: {result['digest']}")
        print()
        print("✅ 步骤5 完成")
    else:
        print(f"  ✗ {result['message']}")
        print()
        print("❌ 步骤5 失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
