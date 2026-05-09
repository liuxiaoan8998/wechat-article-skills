#!/usr/bin/env python3
"""
微信公众号文章提取 - 同步执行模式 v3.0
单次对话内完成：工具提取 → AI总结 → Base同步
"""

import subprocess
import json
import os
import sys

# 自动加载 .env 文件（如果存在）
_env_path = Path(__file__).resolve().parents[3] / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value.strip())
import re
from datetime import datetime
from pathlib import Path

SHARED_DIR = Path(__file__).resolve().parents[2] / "_shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

from wechat_pipeline import PipelineValidationError, validate_required_fields

# 配置
BASE_TOKEN = os.getenv("FEISHU_BASE_TOKEN")
TABLE_ID = os.getenv("FEISHU_ARTICLE_TABLE_ID")
OUTPUT_BASE = os.getenv("WECHAT_EXTRACT_OUTPUT_BASE", "/tmp/test_output")
TOOL_PATH = os.getenv("WECHAT_ARTICLE_TOOL_PATH", "/tmp/wechat-article-for-ai-pro")


def run_tool_extraction(url: str) -> dict:
    """
    阶段1: 工具提取
    """
    print(f"\n📦 阶段1: 工具提取")
    print("-" * 40)
    
    # 设置 PYTHONPATH
    env = os.environ.copy()
    env['PYTHONPATH'] = TOOL_PATH
    
    code = """
import sys
from wechat_to_md.cli import main

# 自动加载 .env 文件（如果存在）
_env_path = Path(__file__).resolve().parents[3] / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value.strip())
sys.argv = ['wechat_to_md', sys.argv[1], '-o', sys.argv[2]]
main()
"""
    cmd = ["/usr/bin/python3", "-c", code, url, OUTPUT_BASE]

    result = subprocess.run(
        cmd,
        cwd=TOOL_PATH,
        capture_output=True,
        text=True,
        timeout=180,
        env=env,
    )
    
    if result.returncode != 0:
        print(f"❌ 工具提取失败: {result.stderr[:500]}")
        return {"success": False, "error": result.stderr[:500]}
    
    print(f"✅ 工具提取完成")
    
    # 查找最新生成的目录
    if os.path.exists(OUTPUT_BASE):
        dirs = [d for d in os.listdir(OUTPUT_BASE) if os.path.isdir(os.path.join(OUTPUT_BASE, d))]
        if dirs:
            latest_dir = max(dirs, key=lambda x: os.path.getctime(os.path.join(OUTPUT_BASE, x)))
            article_dir = os.path.join(OUTPUT_BASE, latest_dir)
            
            # 读取 metadata
            metadata_path = os.path.join(article_dir, 'metadata.json')
            metadata = {}
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            # 读取 OCR 内容
            ocr_path = os.path.join(article_dir, 'article-ocr.md')
            ocr_content = ""
            if os.path.exists(ocr_path):
                with open(ocr_path, 'r', encoding='utf-8') as f:
                    ocr_content = f.read()
            
            return {
                "success": True,
                "output_dir": article_dir,
                "metadata": metadata,
                "ocr_content": ocr_content
            }
    
    return {"success": False, "error": "无法找到输出目录"}


def analyze_industry(ocr_content: str) -> str:
    """分析行业"""
    # 这里应该由 AI 分析，简化版本
    if "酒店" in ocr_content or "洲际" in ocr_content:
        return "消费品"
    elif "索尼" in ocr_content or "科技" in ocr_content:
        return "消费品"
    return "其他"


def analyze_field(ocr_content: str) -> str:
    """分析领域"""
    if "酒店" in ocr_content:
        return "消费品"
    elif "索尼" in ocr_content:
        return "消费品"
    return "其他"


def analyze_job_types(ocr_content: str) -> list:
    """分析岗位类型"""
    types = []
    if "实习" in ocr_content or "校园大使" in ocr_content:
        types.append("实习")
    if "校招" in ocr_content or "校园招聘" in ocr_content:
        types.append("校招")
    if "社招" in ocr_content or "热招" in ocr_content or "总经理" in ocr_content:
        types.append("社招")
    if not types:
        types.append("实习")  # 默认
    return types[:2]  # 最多2个


def analyze_location(ocr_content: str) -> str:
    """分析工作地点"""
    cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "西安", "南京", "长沙"]
    found = []
    for city in cities:
        if city in ocr_content:
            found.append(city)
    
    if len(found) >= 3:
        return "多城市"
    elif found:
        return found[0]
    return "多城市"


def analyze_education(ocr_content: str) -> str:
    """分析学历要求"""
    if "本科及以上" in ocr_content or "本科" in ocr_content:
        return "本科"
    elif "硕士" in ocr_content:
        return "硕士"
    elif "博士" in ocr_content:
        return "博士"
    return "/"


def analyze_deadline(ocr_content: str) -> str:
    """分析截止日期"""
    # 查找日期格式
    patterns = [
        r'(\d{4})年(\d{1,2})月(\d{1,2})日',
        r'(\d{4})-(\d{2})-(\d{2})',
        r'(\d{1,2})月(\d{1,2})日'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, ocr_content)
        if match:
            return match.group(0)
    
    return "/"


def analyze_apply_method(ocr_content: str) -> str:
    """分析投递方式"""
    if "二维码" in ocr_content or "扫描" in ocr_content:
        return "扫描二维码投递"
    elif "点击" in ocr_content and "投递" in ocr_content:
        return "点击链接投递"
    elif "邮箱" in ocr_content:
        return "邮箱投递"
    return "/"


def analyze_highlights(ocr_content: str) -> str:
    """分析原文亮点"""
    highlights = []
    
    # P0 福利
    if "包食宿" in ocr_content or "提供住宿" in ocr_content:
        highlights.append("包食宿")
    if "六险二金" in ocr_content:
        highlights.append("六险二金")
    
    # P1 发展
    if "转正" in ocr_content or "留用" in ocr_content:
        highlights.append("可转正")
    if "Offer" in ocr_content or "offer" in ocr_content:
        highlights.append("提前锁定Offer")
    
    # P2 背书
    if "500强" in ocr_content or "世界500强" in ocr_content:
        highlights.append("世界500强")
    if "大厂" in ocr_content or "知名" in ocr_content:
        highlights.append("大厂")
    
    # P3 流程
    if "免笔试" in ocr_content:
        highlights.append("免笔试")
    
    if highlights:
        return ";".join(highlights[:5])  # 最多5个
    return "/"


def generate_summary(ocr_content: str, metadata: dict) -> str:
    """生成文章概要"""
    title = metadata.get('title', '')
    author = metadata.get('author', '')
    
    # 提取关键信息生成摘要
    summary = f"{author}发布{title}"
    
    # 限制长度
    if len(summary) > 500:
        summary = summary[:497] + "..."
    
    return summary


def determine_topic(ocr_content: str, industry: str, job_types: list) -> str:
    """确定选题方向"""
    job_type_str = "/".join(job_types)
    return f"{industry}行业{job_type_str}机会"


def match_accounts(job_types: list, ocr_content: str) -> list:
    """匹配适配账号"""
    accounts = []
    
    if "实习" in job_types:
        accounts.append("Joblinker")
    
    if "校招" in job_types:
        if "Joblinker" not in accounts:
            accounts.append("研究生求职圈")
        else:
            accounts.append("研究生求职圈")
    
    if "金融" in ocr_content or "投资" in ocr_content or "行研" in ocr_content:
        if "行研实习" not in accounts:
            accounts.append("行研实习")
    
    return accounts if accounts else ["Joblinker"]


def analyze_tags(ocr_content: str) -> list:
    """分析标签"""
    tags = []
    
    if "500强" in ocr_content or "大厂" in ocr_content:
        tags.append("大厂")
    if "国企" in ocr_content or "央企" in ocr_content:
        tags.append("国企")
    if "外企" in ocr_content or "外资" in ocr_content:
        tags.append("外企")
    if "急招" in ocr_content or "热招" in ocr_content:
        tags.append("急招")
    if "可内推" in ocr_content:
        tags.append("可内推")
    
    return tags[:3]  # 最多3个


def ai_analysis(ocr_content: str, metadata: dict) -> dict:
    """
    阶段2: AI分析
    """
    print(f"\n🤖 阶段2: AI分析")
    print("-" * 40)
    
    analysis = {
        "行业": analyze_industry(ocr_content),
        "领域": analyze_field(ocr_content),
        "岗位类型": analyze_job_types(ocr_content),
        "工作地点": analyze_location(ocr_content),
        "学历要求": analyze_education(ocr_content),
        "截止日期": analyze_deadline(ocr_content),
        "投递方式": analyze_apply_method(ocr_content),
        "原文亮点": analyze_highlights(ocr_content),
        "文章概要": generate_summary(ocr_content, metadata),
        "选题方向": determine_topic(ocr_content, analyze_industry(ocr_content), analyze_job_types(ocr_content)),
        "适配账号": match_accounts(analyze_job_types(ocr_content), ocr_content),
        "优先级": "中",
        "标签": analyze_tags(ocr_content)
    }
    
    print(f"✅ AI分析完成")
    return analysis


def sync_to_feishu(metadata: dict, ai_analysis: dict) -> dict:
    """
    阶段3: 飞书Base同步
    """
    print(f"\n📤 阶段3: 飞书Base同步")
    print("-" * 40)
    
    # 构建记录数据
    record_data = {
        # 基础字段
        "文章标题": metadata.get('title', ''),
        "公众号": metadata.get('author', ''),
        "发布时间": metadata.get('published_at', '')[:10] if metadata.get('published_at') else '/',
        "文章链接": metadata.get('url', ''),
        "文章ID": metadata.get('article_id', ''),  # 新增：文章唯一ID
        "文章状态": "待选题",
        "文章来源": "链接",
        "采集时间": int(datetime.now().timestamp() * 1000),
        
        # AI分析字段
        **ai_analysis
    }
    
    # 字段完整性校验
    required_fields = [
        '文章标题', '公众号', '发布时间', '文章链接', '文章ID',
        '行业', '领域', '岗位类型', '工作地点', 
        '学历要求', '截止日期', '投递方式',
        '原文亮点', '文章概要', '选题方向',
        '文章状态', '文章来源', '适配账号',
        '优先级', '标签', '采集时间'
    ]
    
    missing = validate_required_fields(record_data, required_fields)
    filled_count = len(required_fields) - len(missing)
    
    print(f"📊 字段填充: {filled_count}/{len(required_fields)}")
    if missing:
        raise PipelineValidationError(f"飞书 Base 必填字段缺失，已阻断写入: {', '.join(missing)}")
    
    # 写入临时文件
    with open('sync_data.json', 'w', encoding='utf-8') as f:
        json.dump(record_data, f, ensure_ascii=False)
    
    # 执行同步
    cmd = [
        "lark-cli", "base", "+record-upsert",
        "--base-token", BASE_TOKEN,
        "--table-id", TABLE_ID,
        "--json", "@sync_data.json",
        "--as", "bot",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # 清理
    if os.path.exists('sync_data.json'):
        os.remove('sync_data.json')
    
    if result.returncode == 0:
        response = json.loads(result.stdout)
        if response.get('ok'):
            record_id = response['data']['record']['record_id_list'][0]
            print(f"✅ 同步成功！记录ID: {record_id}")
            return {
                "success": True,
                "record_id": record_id,
                "fields_filled": filled_count,
                "total_fields": len(required_fields)
            }
        else:
            print(f"❌ 同步失败: {response.get('error')}")
            return {"success": False, "error": response.get('error')}
    else:
        print(f"❌ 命令失败: {result.stderr[:300]}")
        return {"success": False, "error": result.stderr[:300]}


def process_article(url: str, title: str = "") -> dict:
    """
    处理单篇文章（完整流程）
    """
    print(f"\n{'='*80}")
    print(f"处理文章: {title or url}")
    print(f"{'='*80}")
    
    # 阶段1: 工具提取
    stage1 = run_tool_extraction(url)
    if not stage1['success']:
        return {"success": False, "stage": 1, "error": stage1['error']}
    
    # 阶段2: AI分析
    stage2 = ai_analysis(stage1['ocr_content'], stage1['metadata'])
    
    # 阶段3: Base同步
    stage3 = sync_to_feishu(stage1['metadata'], stage2)
    if not stage3['success']:
        return {"success": False, "stage": 3, "error": stage3['error']}
    
    return {
        "success": True,
        "title": stage1['metadata'].get('title', ''),
        "record_id": stage3['record_id'],
        "fields_filled": stage3['fields_filled'],
        "total_fields": stage3['total_fields'],
        "output_dir": stage1['output_dir']
    }


def main():
    """
    主函数 - 处理命令行参数或交互式输入
    """
    if len(sys.argv) > 1:
        # 命令行模式
        url = sys.argv[1]
        title = sys.argv[2] if len(sys.argv) > 2 else ""
        result = process_article(url, title)
        
        if result['success']:
            print(f"\n✅ 完成: {result['title']}")
            print(f"   记录ID: {result['record_id']}")
            print(f"   字段填充: {result['fields_filled']}/{result['total_fields']}")
        else:
            print(f"\n❌ 失败: {result.get('error', '未知错误')}")
            sys.exit(1)
    else:
        # 交互式模式
        print("微信公众号文章提取 - 同步执行模式 v3.0")
        print("=" * 80)
        
        url = input("请输入文章URL: ").strip()
        if not url:
            print("❌ URL不能为空")
            sys.exit(1)
        
        result = process_article(url)
        
        if result['success']:
            print(f"\n{'='*80}")
            print("✅ 任务完成")
            print(f"{'='*80}")
            print(f"标题: {result['title']}")
            print(f"记录ID: {result['record_id']}")
            print(f"字段填充: {result['fields_filled']}/{result['total_fields']}")
            print(f"输出目录: {result['output_dir']}")
        else:
            print(f"\n❌ 任务失败: {result.get('error', '未知错误')}")


if __name__ == "__main__":
    main()
