#!/usr/bin/env python3
"""
公众号文章搜索工具 - 基于极致了API
功能：搜索 → 保存本地JSON → 同步到飞书Base"""

import requests
import os
import json
import sys
import shutil
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# 自动加载 .env 文件（如果存在）
_env_path = Path(__file__).resolve().parents[3] / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value.strip())

# 自动加载 .env 文件（如果存在）
_env_path = Path(__file__).resolve().parents[3] / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value.strip())

# ============ 配置 ============
API_BASE = "https://www.dajiala.com"
BASE_TOKEN = os.getenv("FEISHU_BASE_TOKEN")
SEARCH_POOL_TABLE_ID = os.getenv("FEISHU_SEARCH_POOL_TABLE_ID")
LARK_CLI = os.getenv("LARK_CLI", shutil.which("lark-cli") or "lark-cli")

# 数据存储目录
DATA_DIR = Path.home() / ".hermes" / "data" / "wechat-search"

def ensure_data_dir():
    """确保数据目录存在"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR

def get_api_key() -> str:
    """获取 API Key"""
    api_key = os.getenv("DAJIALA_API_KEY")
    if not api_key:
        raise ValueError("请设置 DAJIALA_API_KEY 环境变量")
    return api_key

def search_database(
    keyword: str = "",
    any_kw: str = "",
    ex_kw: str = "",
    page: int = 1
) -> List[Dict]:
    """数据库模式搜索公众号文章"""
    url = f"{API_BASE}/fbmain/monitor/v3/kw_search"
    payload = {"key": get_api_key(), "page": page}
    
    if keyword:
        payload["kw"] = keyword
    if any_kw:
        payload["any_kw"] = any_kw
    if ex_kw:
        payload["ex_kw"] = ex_kw
    
    response = requests.post(url, json=payload, timeout=30)
    result = response.json()
    
    if result.get("code") != 0:
        raise Exception(f"搜索失败: {result.get('message', '未知错误')}")
    
    return result.get("data", [])

def search_sousuo(
    keyword: str,
    sort_type: int = 2,
    page: int = 1,
    offset: int = 0,
    cookies_buffer: str = ""
) -> Dict:
    """搜一搜模式搜索公众号文章"""
    url = f"{API_BASE}/fbmain/monitor/v3/web_search"
    payload = {
        "mode": 2,
        "keyword": keyword,
        "BusinessType": 2,
        "Sub_search_type": sort_type,
        "currentPage": page,
        "offset": offset,
        "cookies_buffer": cookies_buffer,
        "key": get_api_key()
    }
    
    response = requests.post(url, json=payload, timeout=30)
    result = response.json()
    
    if result.get("code") != 0:
        raise Exception(f"搜索失败: {result.get('message', '未知错误')}")
    
    # 解析 cookies（可能是JSON字符串）
    cookies = result.get("cookies", {})
    if isinstance(cookies, str):
        try:
            cookies = json.loads(cookies)
        except:
            cookies = {}
    
    return {
        "articles": result.get("data", [{}])[0].get("items", []) if result.get("data") else [],
        "next_offset": result.get("offset"),
        "cookies_buffer": cookies.get("cookies_buffer", "")
    }

def deduplicate_articles(articles: List[Dict], search_mode: str = "database") -> List[Dict]:
    """根据URL去重"""
    seen_urls = set()
    unique_articles = []
    
    # 根据搜索模式选择URL字段
    url_field = "url" if search_mode == "database" else "doc_url"
    
    for article in articles:
        url = article.get(url_field, "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(article)
    
    return unique_articles

def filter_articles(
    articles: List[Dict],
    min_read: Optional[int] = None,
    max_days: Optional[int] = None,
    required_keywords: Optional[List[str]] = None
) -> List[Dict]:
    """筛选文章"""
    filtered = []
    now = datetime.now()
    
    for article in articles:
        # 阅读量筛选
        if min_read:
            read_count = article.get("read", 0) or 0
            if read_count < min_read:
                continue
        
        # 时间筛选
        if max_days:
            pub_time = article.get("publish_time", "")
            if pub_time:
                try:
                    pub_dt = datetime.strptime(pub_time, "%Y-%m-%d %H:%M:%S")
                    if (now - pub_dt).days > max_days:
                        continue
                except:
                    pass
        
        # 关键词筛选
        if required_keywords:
            title = article.get("title", "")
            if not any(kw in title for kw in required_keywords):
                continue
        
        filtered.append(article)
    
    return filtered

def save_to_json(articles: List[Dict], search_params: Dict) -> Path:
    """保存搜索结果到本地JSON文件"""
    ensure_data_dir()
    
    # 生成文件名: search_YYYYMMDD_HHMMSS_keyword.json
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    keyword = search_params.get("keyword", "")[:20]  # 限制长度
    filename = f"search_{timestamp}_{keyword}.json"
    filepath = DATA_DIR / filename
    
    # 构建保存的数据结构
    data = {
        "search_params": search_params,
        "search_time": datetime.now().isoformat(),
        "total_count": len(articles),
        "articles": articles
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filepath

def convert_timestamp_to_date(timestamp) -> int:
    """将时间戳转换为飞书日期格式 (毫秒级时间戳)"""
    if not timestamp:
        return None
    try:
        # 处理秒级时间戳，转换为毫秒
        if isinstance(timestamp, (int, float)):
            return int(timestamp * 1000)
        # 处理字符串时间戳
        elif isinstance(timestamp, str):
            if timestamp.isdigit():
                return int(timestamp) * 1000
            # 已经是日期格式，转换为时间戳
            elif "-" in timestamp:
                dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                return int(dt.timestamp() * 1000)
    except Exception:
        pass
    return None

def clean_html(text: str) -> str:
    """去除HTML标签"""
    import re
    if not text:
        return ""
    # 去除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    # 去除转义字符
    text = text.replace('&quot;', '"').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    return text.strip()

def sync_to_feishu(article: Dict, search_params: Dict, search_mode: str = "database") -> Optional[str]:
    """同步单篇文章到飞书搜索文章池
    
    Args:
        article: 文章数据（数据库模式或搜一搜模式）
        search_params: 搜索参数
        search_mode: 搜索模式 ("database" 或 "sousuo")
    """
    import subprocess
    
    # 根据搜索模式处理不同的字段映射
    if search_mode == "sousuo":
        # 搜一搜模式字段映射
        source = article.get("source", {})
        
        # 处理发布时间
        pub_timestamp = article.get("timestamp") or article.get("date")
        
        # 从 doc_url 中提取 __biz 作为原始ID的替代
        doc_url = article.get("doc_url", "")
        import re
        biz_match = re.search(r'__biz=([^&]+)', doc_url)
        raw_id = biz_match.group(1) if biz_match else ""
        
        record_data = {
            "文章标题": clean_html(article.get("title", "")),
            "公众号名称": source.get("title", "") if isinstance(source, dict) else "",
            "微信号": "",  # 搜一搜模式无此字段
            "原始ID": raw_id,  # 从 doc_url 的 __biz 参数提取
            "文章长链接": doc_url,
            "短链接": "",  # 搜一搜模式无此字段
            "发布时间": convert_timestamp_to_date(pub_timestamp),
            "更新时间": None,  # 搜一搜模式无此字段
            "阅读数": 0,  # 搜一搜模式无此字段
            "点赞数": 0,  # 搜一搜模式无此字段
            "在看数": 0,  # 搜一搜模式无此字段
            "正文内容": clean_html(article.get("desc", ""))[:50000],
            "封面图片": article.get("thumbUrl", ""),
            "搜索关键词": search_params.get("keyword", ""),
            "搜索时间": int(datetime.now().timestamp() * 1000),
            "原始JSON": json.dumps(article, ensure_ascii=False),
            # 搜一搜模式特有字段
            "搜索模式": "搜一搜模式",
            "文章摘要": clean_html(article.get("desc", ""))[:2000],
            "公众号来源": source.get("title", "") if isinstance(source, dict) else "",
            "发布时间文本": source.get("dateTime", "") if isinstance(source, dict) else "",
        }
    else:
        # 数据库模式字段映射
        record_data = {
            "文章标题": article.get("title", ""),
            "公众号名称": article.get("wx_name", ""),
            "微信号": article.get("wx_id", ""),
            "原始ID": article.get("ghid", ""),
            "文章长链接": article.get("url", ""),
            "短链接": article.get("short_link", ""),
            "发布时间": convert_timestamp_to_date(article.get("publish_time")),
            "更新时间": convert_timestamp_to_date(article.get("update_time")),
            "阅读数": article.get("read", 0) or 0,
            "点赞数": article.get("praise", 0) or 0,
            "在看数": article.get("looking", 0) or 0,
            "正文内容": article.get("content", "")[:50000],
            "封面图片": article.get("avatar", ""),
            "搜索关键词": search_params.get("keyword", ""),
            "搜索时间": int(datetime.now().timestamp() * 1000),
            "原始JSON": json.dumps(article, ensure_ascii=False),
            # 搜一搜模式特有字段（数据库模式为空）
            "搜索模式": "数据库模式",
            "文章摘要": article.get("content", "")[:2000],
            "公众号来源": article.get("wx_name", ""),
            "发布时间文本": article.get("publish_time_str", ""),
        }
    
    # 使用 JSON 字符串直接传递（不写入文件）
    json_str = json.dumps(record_data, ensure_ascii=False)
    
    try:
        # 使用 lark-cli 同步 - 直接传递 JSON 字符串
        cmd = [
            LARK_CLI, "base", "+record-upsert",
            "--base-token", BASE_TOKEN,
            "--table-id", SEARCH_POOL_TABLE_ID,
            "--json", json_str,
            "--as", "bot"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            response = json.loads(result.stdout)
            if response.get('ok'):
                record_id = response['data']['record']['record_id_list'][0]
                return record_id
        else:
            # 打印错误信息便于调试
            print(f"\n   同步错误: {result.stderr[:100]}")
        
        return None
    except Exception as e:
        print(f"\n   同步异常: {str(e)[:100]}")
        return None

def print_articles(articles: List[Dict], max_count: int = 10, search_mode: str = "database"):
    """打印文章列表"""
    print(f"\n📊 搜索结果: {len(articles)} 篇文章\n")
    print("=" * 80)
    
    for i, article in enumerate(articles[:max_count], 1):
        if search_mode == "database":
            title = article.get('title', 'N/A')
            wx_name = article.get('wx_name', 'N/A')
            url = article.get('url', 'N/A')
            pub_time = article.get('publish_time', 'N/A')
            read = article.get('read', 'N/A')
            praise = article.get('praise', 'N/A')
        else:
            # 搜一搜模式
            title = clean_html(article.get('title', 'N/A'))
            source = article.get('source', {})
            wx_name = source.get('title', 'N/A') if isinstance(source, dict) else 'N/A'
            url = article.get('doc_url', 'N/A')
            pub_time = article.get('timestamp', 'N/A')
            read = 'N/A'
            praise = 'N/A'
        
        print(f"\n[{i}] 【{wx_name}】{title}")
        print(f"    链接: {url}")
        print(f"    时间: {pub_time} | 阅读: {read} | 点赞: {praise}")
    
    if len(articles) > max_count:
        print(f"\n... 还有 {len(articles) - max_count} 篇文章未显示")
    
    print("\n" + "=" * 80)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="公众号文章搜索工具 - 基于极致了API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 数据库模式搜索并保存到本地
  python search.py --mode database --keyword "实习" --any-kw "互联网,大厂"
  
  # 搜一搜模式获取最新文章并同步到飞书
  python search.py --mode sousuo --keyword "暑期实习" --sort 2 --sync
  
  # 搜索、保存JSON、同步到飞书
  python search.py -k "校招" --output results.json --sync
        """
    )
    
    parser.add_argument("--mode", choices=["database", "sousuo"], default="database",
                       help="搜索模式 (默认: database)")
    parser.add_argument("--keyword", "-k", help="搜索关键词")
    parser.add_argument("--any-kw", help="包含任意关键词（逗号分隔，仅数据库模式）")
    parser.add_argument("--ex-kw", help="排除关键词（逗号分隔，仅数据库模式）")
    parser.add_argument("--sort", type=int, default=2, 
                       help="搜一搜排序: 0不限 2最新 4最热 (默认: 2)")
    parser.add_argument("--output", "-o", help="输出JSON文件路径（默认自动生成）")
    parser.add_argument("--max", type=int, default=10, 
                       help="显示最大文章数 (默认: 10)")
    parser.add_argument("--min-read", type=int, help="最小阅读量筛选")
    parser.add_argument("--max-days", type=int, help="最大发布时间（天）")
    parser.add_argument("--sync", action="store_true",
                       help="同步到飞书Base搜索文章池")
    parser.add_argument("--no-save", action="store_true",
                       help="不保存到本地JSON文件")
    
    args = parser.parse_args()
    
    try:
        # 1. 搜索文章
        print(f"🔍 开始搜索: {args.keyword or '(无关键词)'} (模式: {args.mode})")
        
        search_params = {
            "mode": args.mode,
            "keyword": args.keyword or "",
            "any_kw": args.any_kw or "",
            "ex_kw": args.ex_kw or "",
            "sort": args.sort
        }
        
        if args.mode == "database":
            articles = search_database(
                keyword=args.keyword or "",
                any_kw=args.any_kw or "",
                ex_kw=args.ex_kw or ""
            )
        else:
            result = search_sousuo(
                keyword=args.keyword or "",
                sort_type=args.sort
            )
            articles = result["articles"]
        
        print(f"✅ API返回 {len(articles)} 篇文章")
        
        # 2. 筛选
        if args.min_read or args.max_days:
            articles = filter_articles(
                articles,
                min_read=args.min_read,
                max_days=args.max_days
            )
            print(f"📋 筛选后剩余 {len(articles)} 篇文章")
        
        # 3. 去重
        articles = deduplicate_articles(articles, search_mode=args.mode)
        print(f"📋 去重后剩余 {len(articles)} 篇文章")
        
        # 4. 打印结果
        print_articles(articles, max_count=args.max, search_mode=args.mode)
        
        # 5. 保存到本地JSON
        if not args.no_save:
            if args.output:
                # 使用指定路径
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump({
                        "search_params": search_params,
                        "search_time": datetime.now().isoformat(),
                        "total_count": len(articles),
                        "articles": articles
                    }, f, ensure_ascii=False, indent=2)
                json_path = Path(args.output)
            else:
                # 自动生成路径
                json_path = save_to_json(articles, search_params)
            
            print(f"💾 已保存到本地: {json_path}")
        
        # 6. 同步到飞书
        if args.sync:
            print(f"\n🚀 开始同步到飞书Base...")
            success_count = 0
            failed_count = 0
            
            for i, article in enumerate(articles, 1):
                print(f"  [{i}/{len(articles)}] {article.get('title', 'N/A')[:40]}...", end=" ")
                
                record_id = sync_to_feishu(article, search_params, search_mode=args.mode)
                
                if record_id:
                    print(f"✅ {record_id}")
                    success_count += 1
                else:
                    print("❌ 失败")
                    failed_count += 1
            
            print(f"\n📊 同步完成: 成功 {success_count} 条, 失败 {failed_count} 条")
            print(f"📋 表格链接: https://rqtvt0xmrql.feishu.cn/base/{BASE_TOKEN}?table={SEARCH_POOL_TABLE_ID}")
        
        return 0
        
    except ValueError as e:
        print(f"❌ 配置错误: {e}")
        return 1
    except Exception as e:
        print(f"❌ 搜索失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
