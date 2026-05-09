#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""微信公众号草稿处理器 Pro - 统一入口

功能：
  对指定文章ID的 article_original.html 执行完整清洗流水线，
  输出到 draft/draft.html，供uploader优先读取。

流水线步骤：
  步骤1: 删除尾部噪音（"预览时标签不可点"之后的所有内容）
  步骤2: 删除头部噪音（activity-name、meta_content、js_novel_card）
  步骤2.5: 图片智能处理（识别并移除/裁剪投递方式图片，重写HTML图片引用为本地路径）
  步骤3: 追加账号推广模板（根据 --account 参数）
  步骤5: 智能摘要生成（基于标题和OCR提取招聘类信息的结构化摘要）
  步骤6: 标题转换（根据文章类型添加前缀、清理冗余词）

用法：
  python3 process.py <article_id> [steps] [--account xingyan_shixi|joblinker]

示例：
  # 执行所有步骤（默认，账号 xingyan_shixi）
  python3 process.py e3e9eabf

  # 只执行步骤1
  python3 process.py e3e9eabf --step 1

  # 执行步骤1+2
  python3 process.py e3e9eabf --steps 1,2

  # 指定账号（行研实习）
  python3 process.py e3e9eabf --account xingyan_shixi

  # 指定账号（Joblinker）
  python3 process.py e3e9eabf --account joblinker

  # 指定关键词
  python3 process.py e3e9eabf --account joblinker --keyword 0430
"""

import sys
import os
import argparse

from pathlib import Path

SHARED_DIR = Path(__file__).resolve().parents[2] / "_shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

from wechat_pipeline import extract_article_content, write_manifest


def find_project_root():
    """检测项目根目录，优先使用 ~/.hermes/output"""
    home = os.path.expanduser("~")
    hermes_output = os.path.join(home, ".hermes", "output")
    if os.path.isdir(hermes_output):
        return hermes_output
    return os.getcwd()


# 导入步骤模块
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

try:
    from step1_clean_noise import clean_tail_noise
    from step2_clean_header_noise import clean_header_noise
    from step2_5_process_images import process_article_images
    from step3_append_promotion import append_promotion
    from step5_smart_digest import smart_digest
    from step6_title_transform import title_transform
except ImportError as e:
    print(f"错误：无法导入步骤模块: {e}")
    sys.exit(1)


def process_article(article_id: str, steps: list = None, account: str = "xingyan_shixi", keyword: str = None) -> dict:
    """
    执行完整清洗流水线

    Args:
        article_id: 文章ID
        steps: 要执行的步骤列表，默认所有
        account: 账号配置名称
        keyword: 关键词编号（可选）

    Returns:
        dict: 每个步骤的执行结果
    """
    project_root = find_project_root()
    article_dir = os.path.join(project_root, article_id)
    original_path = os.path.join(article_dir, "article_original.html")

    if not os.path.isfile(original_path):
        print(f"❌ 错误：找不到文章原始文件: {original_path}")
        sys.exit(1)

    results = {
        "article_id": article_id,
        "article_dir": article_dir,
        "account": account,
        "steps": {}
    }

    all_steps = [1, 2, 3, 5, 6]
    if steps is None:
        steps = all_steps

    print("🚀 微信公众号草稿处理器 Pro")
    print(f"   文章ID: {article_id}")
    print(f"   执行步骤: {', '.join(map(str, steps))}")
    print(f"   账号: {account}")
    if keyword:
        print(f"   关键词: {keyword}")
    print(f"   输出目标: {article_dir}/draft/draft.html")
    print("=" * 60)

    # 预清洗：从 article_original.html 提取正文内容
    # 这是所有后续步骤的输入基础
    print("\n📋 步骤0: 基础提取（从原始HTML提取正文）")
    with open(original_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    content, source_label = extract_article_content(html_content)
    print(f"   ✅ 从 {source_label} 提取正文 ({len(content)} 字符)")

    # 确保 draft 目录存在
    draft_dir = os.path.join(article_dir, "draft")
    os.makedirs(draft_dir, exist_ok=True)

    # 写入初始 draft.html
    draft_path = os.path.join(draft_dir, "draft.html")
    with open(draft_path, 'w', encoding='utf-8') as f:
        f.write(content)

    write_manifest(Path(article_dir), {
        "article_id": article_id,
        "article_dir": article_dir,
        "account": account,
        "content_source": source_label,
        "checks": {
            "initial_draft_size": len(content),
            "original_html_size": len(html_content),
        },
    })

    print(f"   初始草稿: {len(content)} 字符")
    print(f"   原始HTML: {len(html_content)} 字符")
    print(f"   减小比例: {(1 - len(content)/len(html_content))*100:.1f}%")

    # 步骤1: 尾部噪音清理
    if 1 in steps:
        print("\n📋 步骤1: 尾部噪音清理")
        r1 = clean_tail_noise(article_dir)
        results["steps"][1] = r1
        if r1["success"]:
            print(f"   ✅ 成功 | 删除 {r1['removed_size']} 字符 | 输出: {r1['output_path']}")
        else:
            print(f"   ⚠️ 失败 | {r1['message']}")

    # 步骤2: 头部噪音清理
    if 2 in steps:
        print("\n📋 步骤2: 头部噪音清理")
        r2 = clean_header_noise(article_dir)
        results["steps"][2] = r2
        if r2["success"]:
            print(f"   ✅ 成功 | 删除 {len(r2['elements_removed'])} 个元素 | 输出: {r2['output_path']}")
        else:
            print(f"   ⚠️ 失败 | {r2['message']}")

    # 步骤3: 追加推广模板
    if 3 in steps:
        # 先执行图片智能处理（在追加推广模板之前，确保正文图片已处理完毕）
        print("\n📰 步骤2.5: 图片智能处理")
        r25 = process_article_images(article_id)
        results["steps"][2.5] = r25
        if r25["success"]:
            print(f"   ✅ 成功 | {r25.get('message', '')}")
            stats = r25.get('stats', {})
            if stats:
                print(f"      图片统计: 总计{stats.get('total_images', 0)} 张, 移除{stats.get('removed', 0)} 张, 重写{stats.get('rewritten', 0)} 张")
        else:
            print(f"   ⚠️ 失败 | {r25.get('message', '')}")

        print("\n📋 步骤3: 追加推广模板")
        r3 = append_promotion(article_dir, account=account, keyword=keyword)
        results["steps"][3] = r3
        if r3["success"]:
            status = "已含推广，跳过" if r3["already_has_promotion"] else f"已追加（关键词: {r3.get('keyword', '')}）"
            print(f"   ✅ 成功 | {status} | 输出: {r3['output_path']}")
        else:
            print(f"   ⚠️ 失败 | {r3['message']}")

    # 步骤5: 智能摘要生成
    if 5 in steps:
        print("\n📋 步骤5: 智能摘要生成")
        r5 = smart_digest(article_dir)
        results["steps"][5] = r5
        if r5["success"]:
            print(f"   ✅ 成功 | {r5['message']}")
        else:
            print(f"   ⚠️ 失败 | {r5['message']}")

    # 步骤6: 标题转换
    if 6 in steps:
        print("\n📋 步骤6: 标题转换")
        r6 = title_transform(article_dir)
        results["steps"][6] = r6
        if r6["success"]:
            print(f"   ✅ 成功 | {r6['message']}")
        else:
            print(f"   ⚠️ 失败 | {r6['message']}")

    # 总结
    print("\n" + "=" * 60)
    print("📈 清洗完成总结")
    draft_path = os.path.join(article_dir, "draft", "draft.html")
    if os.path.exists(draft_path):
        draft_size = os.path.getsize(draft_path)
        original_size = os.path.getsize(original_path)
        print(f"   原始大小: {original_size:,} 字节")
        print(f"   草稿大小: {draft_size:,} 字节")
        print(f"   减小比例: {(1 - draft_size/original_size)*100:.1f}%")
    print(f"   草稿路径: {draft_path}")

    # 显示 draft.json 摘要
    json_path = os.path.join(article_dir, "draft", "draft.json")
    if os.path.exists(json_path):
        import json
        with open(json_path, 'r', encoding='utf-8') as f:
            draft_data = json.load(f)
        print(f"\n   元数据摘要:")
        print(f"     标题: {draft_data.get('title', 'N/A')[:50]}...")
        print(f"     原标题: {draft_data.get('original_title', 'N/A')[:50]}...")
        print(f"     关键词: {draft_data.get('keyword', 'N/A')}")
        print(f"     作者: {draft_data.get('author', 'N/A')}")
        print(f"     摘要: {draft_data.get('digest', 'N/A')[:60]}...")
    print("=" * 60)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="微信公众号草稿处理器 Pro - 统一入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 process.py e3e9eabf
  python3 process.py 4192e361 --steps 1,2
  python3 process.py f9d1d82e --account xingyan_shixi
  python3 process.py f9d1d82e --account xingyan_shixi --keyword 0429
  python3 process.py ce52a022 --account joblinker --keyword 0430
        """
    )
    parser.add_argument("article_id", help="文章ID（如 e3e9eabf）")
    parser.add_argument("--steps", "-s", default="1,2,3,5,6",
                       help="要执行的步骤，默认 1,2,3,5,6，用逗号分隔（步骤4为去水印，尚未实现）")
    parser.add_argument("--step", type=int,
                       help="只执行单个步骤（1,2,3,5,6）")
    parser.add_argument("--account", "-a", default="xingyan_shixi",
                       help="账号配置名称（默认: xingyan_shixi）")
    parser.add_argument("--keyword", "-k",
                       help="关键词编号（默认自动生成 MMdd）")

    args = parser.parse_args()

    if args.step:
        steps = [args.step]
    else:
        steps = [int(x.strip()) for x in args.steps.split(",") if x.strip()]

    process_article(args.article_id, steps, account=args.account, keyword=args.keyword)


if __name__ == "__main__":
    main()
