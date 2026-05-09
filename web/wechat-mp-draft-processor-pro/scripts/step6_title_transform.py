#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号草稿处理器 Pro - 步骤6: 标题转换

功能:
  根据文章类型（实习/校招/社招）添加前缀，清理冗余词，生成适合微信公众号发布的标题。

输入:
  article_dir 下的 metadata.json

输出:
  更新 draft/draft.json 中的 title 字段

转换规则:
  1. 前缀映射:
     - "实习"/“实习生" → "实习 | "
     - "暑期实习" → "暑期实习 | "
     - "校招"/“秋招"/“春招"/“校园招聘" → "校招 | "
     - "社招"/“社会招聘"/“全职" → "社招 | "

  2. 冗余词清理:
     - 移除: "热招中!"、"热招中"、"诚聘"、"正式启动"、"启动!"、"启动"、"招聘启动"、"招聘启动!"
     - 移除: 多余的空格和标点

  3. 格式标准化:
     - "|" 统一为 " | "
     - 多余空格去除
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


def detect_job_type(title: str) -> str:
    """检测文章类型，返回前缀"""
    title_lower = title.lower()

    # 优先级: 暑期实习 > 实习 > 校招 > 社招
    if '暑期实习' in title or '暑假实习' in title:
        return '暑期实习'
    if '实习生' in title or '实习' in title:
        return '实习'
    if '校园招聘' in title or '校招' in title or '秋招' in title or '春招' in title:
        return '校招'
    if '社招' in title or '社会招聘' in title or '全职' in title:
        return '社招'

    return ""


def clean_redundant_words(title: str) -> str:
    """清理标题中的冗余词"""
    redundant = [
        r'热招中！',
        r'热招中!',
        r'热招中',
        r'诚聘',
        r'正式启动！',
        r'正式启动!',
        r'正式启动',
        r'启动！',
        r'启动!',
        r'启动',
        r'招聘启动！',
        r'招聘启动!',
        r'招聘启动',
        r'招聘启动！',
        r'招聘启动!',
        r'招聘启动',
    ]

    cleaned = title
    for pattern in redundant:
        cleaned = re.sub(pattern, '', cleaned)

    # 移除多余空格和标点
    cleaned = re.sub(r'[\s｜\uff5c\uff5c]+', ' ', cleaned).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)

    return cleaned


def add_prefix(title: str, job_type: str) -> str:
    """根据类型添加前缀"""
    if not job_type:
        return title

    prefix = f"{job_type} | "

    # 检查是否已经有前缀
    if title.startswith(prefix):
        return title

    # 检查是否已经有其他前缀（如“校园招聘|”）
    if re.match(r'^[一-龥]+｜', title):
        # 已有中文前缀，替换为标准前缀
        title = re.sub(r'^[一-龥]+｜\s*', '', title)

    return prefix + title


def standardize_format(title: str) -> str:
    """标准化标题格式"""
    # 统一分隔符
    title = title.replace('|', ' | ').replace('｜', ' | ')
    # 去除多余空格
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def transform_title(title: str) -> str:
    """
    执行完整标题转换流水线

    1. 检测类型
    2. 清理冗余词
    3. 添加前缀
    4. 标准化格式
    """
    job_type = detect_job_type(title)
    cleaned = clean_redundant_words(title)
    prefixed = add_prefix(cleaned, job_type)
    final = standardize_format(prefixed)
    return final


def update_draft_json(article_dir: str, title: str) -> dict:
    """更新 draft.json 中的 title 字段"""
    draft_dir = Path(article_dir) / "draft"
    json_path = draft_dir / "draft.json"

    draft_data = {}
    if json_path.exists():
        with open(json_path, 'r', encoding='utf-8') as f:
            draft_data = json.load(f)

    draft_data["original_title"] = draft_data.get("title", "")
    draft_data["title"] = title
    draft_data["title_transformed_at"] = datetime.now().isoformat()

    os.makedirs(draft_dir, exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(draft_data, f, ensure_ascii=False, indent=2)

    return draft_data


def title_transform(article_dir: str) -> dict:
    """
    执行标题转换

    Returns:
        dict: 处理结果
    """
    result = {
        "success": False,
        "original_title": "",
        "transformed_title": "",
        "message": "",
    }

    # 1. 加载元数据
    metadata = load_metadata(article_dir)
    original_title = metadata.get('title', '')

    if not original_title:
        result["message"] = "错误：metadata.json 中没有标题"
        return result

    result["original_title"] = original_title

    # 2. 执行转换
    transformed = transform_title(original_title)
    result["transformed_title"] = transformed

    # 3. 更新 draft.json
    draft_data = update_draft_json(article_dir, transformed)

    result["success"] = True
    result["draft_data"] = draft_data
    result["message"] = f"原标题: {original_title} → 转换后: {transformed}"

    return result


def main():
    if len(sys.argv) < 2:
        print("用法: python3 step6_title_transform.py <article_id>")
        print("示例: python3 step6_title_transform.py 4192e361")
        sys.exit(1)

    article_id = sys.argv[1]
    project_root = find_project_root()
    article_dir = os.path.join(project_root, article_id)

    print(f"[步骤6] 标题转换")
    print(f"  文章ID: {article_id}")
    print(f"  文章目录: {article_dir}")
    print()

    result = title_transform(article_dir)

    if result["success"]:
        print(f"  ✓ {result['message']}")
        print()
        print("✅ 步骤6 完成")
    else:
        print(f"  ✗ {result['message']}")
        print()
        print("❌ 步骤6 失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
