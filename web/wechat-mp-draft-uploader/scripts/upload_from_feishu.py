#!/usr/bin/env python3
"""
微信公众号草稿上传工具 - 飞书 Base 版本（优化版）
基于简立制作 API 平台

自动根据飞书 Base 文章的"适配账号"查询【账号配置表】获取 AppID

Usage:
    python upload_from_feishu.py --record-id recvhq1MWUhyc5
"""

import argparse
import os
import sys
import json
import re
import requests
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

SHARED_DIR = Path(__file__).resolve().parents[2] / "_shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

from wechat_pipeline import (
    PipelineValidationError,
    collect_img_refs,
    extract_article_content,
    validate_draft_local_images,
)

# API 配置
JIANLIZHIZUO_BASE_URL = "https://mp.jianlizhizuo.cn/v1"

# 默认配置
DEFAULT_BASE_TOKEN = "E9y1bxjHGa9LeGs9q3Tc3J41nmf"
ARTICLE_TABLE_ID = "tblYIqHtHrWUlVnP"      # 文章素材表
ACCOUNT_TABLE_ID = "tblWQzDq4KeYcrsm"      # 账号配置表

# 字段名映射（如果后续字段改名，只需修改这里）
FIELD_STATUS = "文章状态"  # 文章状态字段，可选值：待选题、已选题、已上传草稿、待二创、待排版、待发布、已发布、已取消
FIELD_DRAFT_ID = "草稿ID"  # 草稿ID字段（如有）

# 账号名称映射（飞书 Base 显示名称 -> process.py 账号 key）
ACCOUNT_NAME_MAP = {
    "Joblinker": "joblinker",
    "行研实习": "xingyan_shixi",
    "研究生求职圈": "joblinker",  # 无独立模板，套用 Joblinker
}


class FeishuClient:
    """飞书 Base 客户端"""
    
    def __init__(self, base_token: str = None):
        self.base_token = base_token or DEFAULT_BASE_TOKEN
    
    def _run_lark_cli(self, args: str) -> Dict:
        """执行 lark-cli 命令并返回结果"""
        cmd = f'lark-cli {args} --as bot'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"lark-cli 执行失败: {result.stderr}")
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            raise Exception(f"解析 lark-cli 响应失败: {result.stdout}")
    
    def get_record(self, table_id: str, record_id: str) -> Dict:
        """获取单条记录详情"""
        args = f'base +record-get --base-token {self.base_token} --table-id {table_id} --record-id {record_id}'
        data = self._run_lark_cli(args)
        
        if data.get('ok'):
            return data['data']['record']
        else:
            raise Exception(f"获取记录失败: {data.get('error', '未知错误')}")
    
    def query_records(self, table_id: str, filter_str: str = None, limit: int = 500) -> List[Dict]:
        """查询记录列表"""
        args = f'base +record-list --base-token {self.base_token} --table-id {table_id}'
        
        # lark-cli 不支持 --filter，需要获取所有记录后手动过滤
        if limit:
            args += f' --limit {limit}'
        
        data = self._run_lark_cli(args)
        
        if data.get('ok'):
            # 返回的数据在 data['data'] 中，是二维数组格式
            records_data = data['data'].get('data', [])
            record_ids = data['data'].get('record_id_list', [])
            field_names = data['data'].get('fields', [])  # 这是字段名列表，不是对象列表
            
            # 转换为标准格式
            records = []
            for i, record_values in enumerate(records_data):
                record = {'record_id': record_ids[i] if i < len(record_ids) else ''}
                # 将字段值映射到字段名
                for j, field_name in enumerate(field_names):
                    if j < len(record_values):
                        record[field_name] = record_values[j]
                records.append(record)
            
            return records
        else:
            raise Exception(f"查询记录失败: {data.get('error', '未知错误')}")
    
    def update_record(self, table_id: str, record_id: str, fields: Dict) -> bool:
        """更新记录字段"""
        # 构建 JSON 数据
        json_data = json.dumps(fields, ensure_ascii=False)
        
        # 使用临时文件，放在当前工作目录
        work_dir = Path.cwd()
        json_file = work_dir / f"feishu_update_{record_id}.json"
        
        with open(json_file, 'w', encoding='utf-8') as f:
            f.write(json_data)
        
        try:
            args = f'base +record-upsert --base-token {self.base_token} --table-id {table_id} --record-id {record_id} --json @{json_file.name}'
            data = self._run_lark_cli(args)
            return data.get('ok', False)
        finally:
            if json_file.exists():
                json_file.unlink()
    
    def get_account_config(self, account_name: str) -> Optional[Dict]:
        """
        根据账号名称从【账号配置表】获取配置
        
        Args:
            account_name: 账号名称，如 "Joblinker"
            
        Returns:
            Dict: 包含 appid, app_secret 等配置，未找到返回 None
        """
        # 查询账号配置表所有记录
        items = self.query_records(ACCOUNT_TABLE_ID, limit=100)
        
        # 手动过滤匹配的记录
        for record in items:
            if record.get('账号名称') == account_name:
                return {
                    'record_id': record.get('record_id'),
                    'account_name': record.get('账号名称', ''),
                    'appid': record.get('公众号ID', ''),  # 注意字段名
                    'app_secret': record.get('AppSecret', ''),
                    'author': record.get('作者', ''),  # 新增：默认作者
                    'vertical': record.get('垂直方向', ''),
                    'target_audience': record.get('目标受众', ''),
                    'content_style': record.get('内容风格', ''),
                    'authorization_status': record.get('授权状态', ''),
                    'notes': record.get('备注', '')
                }
        
        return None


class WechatDraftUploader:
    """微信公众号草稿上传器"""
    
    def __init__(self, api_key: str = None, appid: str = None):
        self.api_key = api_key or os.getenv("JIANLIZHIZUO_API_KEY")
        self.appid = appid
        
        if not self.api_key:
            raise ValueError("缺少 API Key，请设置 JIANLIZHIZUO_API_KEY 环境变量")
        if not self.appid:
            raise ValueError("缺少 AppID")
    
    def upload_material(self, file_path: str, name: str = "素材", compress: bool = False) -> Dict:
        """上传永久素材，返回 mediaId 和 url
        
        Args:
            file_path: 图片文件路径
            name: 素材名称
            compress: 是否启用图片压缩（默认False不压缩），
        """
        url = f"{JIANLIZHIZUO_BASE_URL}/accounts/{self.appid}/materials"
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 自动将 .webp 转换为 .jpg（微信 API 不支持 webp）
        if file_path.lower().endswith('.webp'):
            converted_path = self._convert_webp_to_jpg(file_path)
            if converted_path:
                file_path = converted_path
        
        data = {'type': 'IMAGE', 'name': name}
        
        # 检查文件大小，如果超过 1MB 且启用了压缩则压缩
        file_size = os.path.getsize(file_path)
        if compress and file_size > 1024 * 1024:  # 1MB
            print(f"      图片过大 ({file_size / 1024 / 1024:.2f}MB)，正在压缩...")
            compressed_path = self._compress_image(file_path)
            if compressed_path:
                file_path = compressed_path
                print(f"      压缩完成: {os.path.getsize(file_path) / 1024:.2f}KB")
        
        # 根据文件扩展名确定正确的 MIME 类型，同时用文件头兜底校验
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file_path)
        
        # 使用文件头检测实际格式并修正 MIME
        try:
            with open(file_path, 'rb') as fcheck:
                header = fcheck.read(12)
            if header[:6] in (b'GIF89a', b'GIF87a'):
                mime_type = 'image/gif'
            elif header[:8] == b'\x89PNG\r\n\x1a\n':
                mime_type = 'image/png'
            elif header[:2] == b'\xff\xd8':
                mime_type = 'image/jpeg'
            elif header[:4] == b'RIFF' and header[8:12] == b'WEBP':
                mime_type = 'image/webp'
        except Exception:
            pass
        
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        with open(file_path, 'rb') as f:
            files = {'media': (os.path.basename(file_path), f, mime_type)}
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.post(url, data=data, files=files, headers=headers)
        
        result = response.json()
        if result.get('code') == 0:
            return result['data']
        else:
            raise Exception(f"素材上传失败: {result.get('msg', '未知错误')}")
    
    def _convert_webp_to_jpg(self, file_path: str) -> Optional[str]:
        """
        将 .webp 图片转换为 .jpg，返回转换后的路径
        如果转换失败，返回 None
        """
        temp_path = file_path + ".converted.jpg"
        
        try:
            # 尝试使用 sips (macOS)
            cmd = [
                'sips', '-s', 'format', 'jpeg',
                '-s', 'formatOptions', '85',
                file_path, '--out', temp_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(temp_path):
                return temp_path
            
            # sips 失败，尝试 ImageMagick
            cmd = ['convert', file_path, '-quality', '85', temp_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(temp_path):
                return temp_path
            
            # 都失败，清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return None
        
        except Exception as e:
            print(f"      webp 转换出错: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return None
    
    def _compress_image(self, file_path: str, max_size: int = 1024 * 1024) -> str:
        """压缩图片到指定大小以下"""
        import subprocess
        import tempfile
        
        temp_path = file_path + ".compressed.jpg"
        
        try:
            # 使用 macOS sips 命令压缩图片
            # 先尝试转换为 JPEG 并设置质量
            width = 1200  # 初始宽度
            quality = 80
            
            while width > 400:
                cmd = [
                    'sips', '-Z', str(width),
                    '-s', 'format', 'jpeg',
                    '-s', 'formatOptions', str(quality),
                    file_path,
                    '--out', temp_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0 and os.path.exists(temp_path):
                    # 检查文件大小
                    if os.path.getsize(temp_path) <= max_size:
                        return temp_path
                    
                    # 如果还是太大，降低质量或尺寸
                    if quality > 50:
                        quality -= 10
                    else:
                        width = int(width * 0.8)
                        quality = 80
                else:
                    # sips 失败，尝试其他方法
                    break
            
            # 如果 sips 方法失败，尝试 ImageMagick
            width = 1200
            quality = 80
            
            while width > 400:
                cmd = [
                    'convert', file_path,
                    '-resize', f'{width}x{width}>',
                    '-quality', str(quality),
                    temp_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0 and os.path.exists(temp_path):
                    if os.path.getsize(temp_path) <= max_size:
                        return temp_path
                    
                    if quality > 50:
                        quality -= 10
                    else:
                        width = int(width * 0.8)
                        quality = 80
                else:
                    break
            
            # 如果都失败了，返回 None
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return None
        
        except Exception as e:
            print(f"      压缩过程出错: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return None
    
    def create_draft(self, articles: list) -> Dict:
        """创建草稿"""
        url = f"{JIANLIZHIZUO_BASE_URL}/accounts/{self.appid}/drafts"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json={"articles": articles}, headers=headers)
        
        result = response.json()
        if result.get('code') == 0:
            return result['data']
        else:
            error_msg = result.get('msg', '未知错误')
            print(f"API 错误响应: {result}")
            raise Exception(f"创建草稿失败: {error_msg}")


def sanitize_filename(filename: str) -> str:
    """清理文件名，移除非法字符"""
    filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
    filename = filename.strip('. ')
    if len(filename) > 200:
        filename = filename[:200]
    return filename


def find_article_directory(title: str, article_id: str = None) -> Optional[str]:
    """根据标题或article_id查找文章本地目录
    
    Args:
        title: 文章标题（用于模糊匹配）
        article_id: 文章唯一ID（优先使用）
    """
    hermes_output = Path.home() / ".hermes" / "output"
    
    if not hermes_output.exists():
        return None
    
    # 优先通过 article_id 查找（精确匹配）
    if article_id:
        article_dir = hermes_output / article_id
        if article_dir.exists() and article_dir.is_dir():
            # 验证目录有效性（检查是否存在 metadata.json）
            metadata_path = article_dir / "metadata.json"
            if metadata_path.exists():
                return str(article_dir)
    
    # 回退到标题匹配（兼容旧版本）
    for dirname in hermes_output.iterdir():
        if not dirname.is_dir():
            continue
        
        # 检查 metadata.json
        metadata_path = dirname / "metadata.json"
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                local_title = metadata.get('title', '')
                
                # 精确匹配
                if local_title == title:
                    return str(dirname)
                
                # 忽略引号差异的匹配（移除所有类型的引号后比较）
                title_no_quotes = re.sub(r'["""''`]', '', title)
                local_no_quotes = re.sub(r'["""''`]', '', local_title)
                if title_no_quotes == local_no_quotes:
                    return str(dirname)
            except:
                continue
        
        # 目录名匹配（忽略引号）
        dir_name = dirname.name
        title_no_quotes = re.sub(r'["""''`]', '', title)
        dir_no_quotes = re.sub(r'["""''`]', '', dir_name)
        if title_no_quotes == dir_no_quotes:
            return str(dirname)
    
    return None


def parse_image_ocr(article_dir: str) -> Dict[str, Dict]:
    """
    解析 article-ocr.md 文件，获取每张图片的 OCR 信息
    
    Returns:
        Dict: {图片文件名: {ocr_text, dimensions, is_long_image}}
    """
    ocr_path = Path(article_dir) / "article-ocr.md"
    if not ocr_path.exists():
        return {}
    
    try:
        with open(ocr_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return {}
    
    image_info = {}
    
    # 匹配图片块
    pattern = r'#### 图片:\s*(\S+)\s*\n\n\*\*状态\*\*:\s*\[([^\]]+)\]\s*\n\n(.*?)(?=\n--|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)
    
    for img_name, status, ocr_block in matches:
        info = {
            'filename': img_name,
            'ocr_text': '',
            'width': 0,
            'height': 0,
            'is_long_image': '超长图' in status or '切片' in status,
            'is_animated': img_name.lower().endswith('.gif')
        }
        
        # 提取尺寸
        dim_match = re.search(r'(\d+)x(\d+)', status)
        if dim_match:
            info['width'] = int(dim_match.group(1))
            info['height'] = int(dim_match.group(2))
        
        # 提取 OCR 文本
        ocr_lines = []
        for line in ocr_block.split('\n'):
            line = line.strip()
            if line and not line.startswith('**') and not line.startswith('[') and not line.startswith('<!--'):
                ocr_lines.append(line)
        info['ocr_text'] = '\n'.join(ocr_lines)
        
        image_info[img_name] = info
    
    return image_info


def select_best_cover_image(
    images_dir: Path,
    article_title: str,
    article_dir: str
) -> Path:
    """
    智能选择最佳封面图片
    
    策略：
    1. 排除 GIF 动图
    2. 解析 OCR 内容，根据关键词评分
    3. 考虑图片尺寸比例（优先 16:9 或接近微信推荐 900x500）
    4. 排除纯文字图、二维码
    5. 兜底：第一张非动图
    
    Args:
        images_dir: 图片目录
        article_title: 文章标题
        article_dir: 文章目录（用于读取 OCR）
        
    Returns:
        Path: 最佳封面图片路径
    """
    # 获取所有图片（包含 .webp，微信 API 不直接支持 webp，但后面会自动转换）
    all_images = sorted([f for f in images_dir.iterdir() 
                        if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']])
    
    if not all_images:
        raise FileNotFoundError(f"目录中没有图片: {images_dir}")
    
    # 获取 OCR 信息
    ocr_info = parse_image_ocr(article_dir)
    
    # 评分函数
    def score_image(img_path: Path) -> int:
        score = 0
        img_name = img_path.name
        info = ocr_info.get(img_name, {})
        
        # 排除 GIF 动图（大扣分）
        if img_name.lower().endswith('.gif'):
            return -1000
        
        # 排除超长图（通常是详情页长图，不适合做封面）
        if info.get('is_long_image', False):
            score -= 500
        
        ocr_text = info.get('ocr_text', '').lower()
        width = info.get('width', 0)
        height = info.get('height', 0)
        
        # 关键词评分（基于 OCR 内容）
        # 高权重：公司品牌、招聘主题
        if any(kw in ocr_text for kw in ['招聘', '校招', '校园招聘', 'join us', 'career']):
            score += 100
        if any(kw in ocr_text for kw in ['logo', '标志', '公司', '集团', '股份']):
            score += 80
        if any(kw in ocr_text for kw in ['2026', '2027', '春招', '秋招']):
            score += 60
        
        # 标题相关
        title_keywords = set(article_title.lower().split())
        ocr_words = set(ocr_text.split())
        common_words = title_keywords & ocr_words
        score += len(common_words) * 20
        
        # 尺寸评分（微信推荐 900x500，约 1.8:1）
        if width > 0 and height > 0:
            ratio = width / height
            # 接近 1.8:1 的加分
            if 1.5 <= ratio <= 2.2:
                score += 50
            # 太扁或太长的扣分
            if ratio < 1.0 or ratio > 3.0:
                score -= 30
            # 尺寸过小扣分
            if width < 300 or height < 200:
                score -= 40
        
        # 排除纯文字图（OCR 文字过多可能是纯文字海报）
        if len(ocr_text) > 500:
            score -= 50
        
        # 排除二维码（通常有特定文字或尺寸特征）
        if any(kw in ocr_text for kw in ['二维码', '扫码', 'qrcode', '关注公众号']):
            score -= 100
        
        return score
    
    # 对所有图片评分
    scored_images = [(img, score_image(img)) for img in all_images]
    scored_images.sort(key=lambda x: x[1], reverse=True)
    
    # 选择最高分且分数为正的图片
    for img, score in scored_images:
        if score > 0:
            return img
    
    # 兜底：第一张非动图
    for img in all_images:
        if not img.name.lower().endswith('.gif'):
            return img
    
    # 如果全是动图，返回第一张（这种情况很少）
    return all_images[0]


def parse_adapt_accounts(field_value) -> List[str]:
    """
    解析飞书 Base 的【适配账号】字段
    支持多种格式：字符串、数组、对象数组
    """
    if not field_value:
        return []
    
    if isinstance(field_value, str):
        # 逗号分隔的字符串
        return [x.strip() for x in field_value.split(',') if x.strip()]
    
    if isinstance(field_value, list):
        accounts = []
        for item in field_value:
            if isinstance(item, str):
                accounts.append(item)
            elif isinstance(item, dict):
                # 对象数组格式 [{"text": "Joblinker"}]
                text = item.get('text', '')
                if text:
                    accounts.append(text)
        return accounts
    
    return []


def upload_from_feishu(
    record_id: str,
    base_token: str = None,
    cover_image: str = None,
    author: str = None,
    need_open_comment: int = 1,
    compress: bool = False
) -> Dict:
    """
    从飞书 Base 上传文章到微信公众号草稿箱（支持多账号）
    
    自动流程：
    1. 读取飞书 Base 文章记录
    2. 解析【适配账号】字段
    3. 查询【账号配置表】获取所有有效 AppID
    4. 查找本地文章目录
    5. 读取并处理正文内容
    6. 为每个适配账号上传封面和创建草稿
    7. 更新飞书 Base 状态（记录所有草稿ID）
    
    Args:
        record_id: 飞书 Base 文章记录 ID
        base_token: 飞书 Base Token（默认使用配置）
        cover_image: 指定封面图片文件名（可选）
        author: 指定作者（可选，默认从 Base 读取）
        need_open_comment: 是否开启评论（默认1开启）
        compress: 是否启用图片压缩（默认False不压缩）
    
    Returns:
        Dict: 包含 results（每个账号的上传结果列表）
    """
    
    print("=" * 60)
    print("微信公众号草稿上传 - 飞书 Base 自动模式")
    print("=" * 60)
    
    # 1. 初始化飞书客户端
    feishu = FeishuClient(base_token)
    
    # 2. 读取文章记录
    print(f"\n📋 步骤 1: 读取飞书 Base 文章记录")
    print(f"   记录 ID: {record_id}")
    
    article_record = feishu.get_record(ARTICLE_TABLE_ID, record_id)
    # 注意：返回的记录本身就是字段字典，不是嵌套结构
    fields = article_record if isinstance(article_record, dict) else article_record.get('fields', {})
    
    title = fields.get('文章标题', '')
    article_url_raw = fields.get('文章链接', '')
    # 提取纯 URL（如果包含 Markdown 链接格式）
    import re
    url_match = re.search(r'https?://[^\s\[\]()<>"{}|\\^`\[\]]+', article_url_raw)
    article_url = url_match.group(0) if url_match else article_url_raw
    
    digest = fields.get('文章概要', '')
    material_status = fields.get(FIELD_STATUS, '')
    article_id = fields.get('文章ID', '')  # 获取文章ID
    
    # 解析适配账号
    adapt_accounts = parse_adapt_accounts(fields.get('适配账号', []))
    
    print(f"   标题: {title}")
    print(f"   文章ID: {article_id if article_id else '未设置'}")
    print(f"   当前状态: {material_status}")
    print(f"   适配账号: {', '.join(adapt_accounts) if adapt_accounts else '未设置'}")
    
    if not title:
        raise ValueError("飞书记录缺少文章标题")
    
    if not adapt_accounts:
        raise ValueError("飞书记录缺少【适配账号】，无法确定发布到哪个公众号")
    
    # 3. 查询账号配置表获取所有有效配置
    print(f"\n🔍 步骤 2: 查询【账号配置表】获取公众号配置")
    
    account_configs = []
    for account_name in adapt_accounts:
        config = feishu.get_account_config(account_name)
        if config and config.get('appid'):
            account_configs.append(config)
            print(f"   ✓ 找到账号: {account_name}")
            print(f"     AppID: {config['appid']}")
            print(f"     授权状态: {config.get('authorization_status', '未知')}")
    
    if not account_configs:
        raise ValueError(f"未在【账号配置表】中找到有效配置，适配账号: {', '.join(adapt_accounts)}")
    
    # 4. 查找本地文章目录
    print(f"\n📁 步骤 3: 查找本地文章目录")
    article_dir = find_article_directory(title, article_id)  # 优先使用 article_id
    
    if not article_dir:
        raise FileNotFoundError(f"找不到文章目录: {title} (ID: {article_id if article_id else '未设置'})")
    
    print(f"   目录: {article_dir}")
    
    # 如果 Base 中没有文章ID，从目录名获取
    if not article_id:
        article_id = Path(article_dir).name
        print(f"   从目录获取文章ID: {article_id}")
    
    # ===== 自动草稿处理器前置检查 =====
    # 如果 draft/draft.html 不存在，自动调用草稿处理器生成
    draft_html_path = Path(article_dir) / "draft" / "draft.html"
    if not draft_html_path.exists():
        print(f"\n🔄 草稿文件不存在，自动调用草稿处理器...")
        
        # 获取第一个适配账号作为处理目标
        first_account_name = adapt_accounts[0] if adapt_accounts else None
        first_account = ACCOUNT_NAME_MAP.get(first_account_name, first_account_name.lower().replace(' ', '_')) if first_account_name else None
        if first_account:
            process_script = Path.home() / ".hermes/skills/web/wechat-mp-draft-processor-pro/scripts/process.py"
            if process_script.exists():
                cmd = [
                    "python3", str(process_script), article_id,
                    "--account", first_account
                ]
                print(f"   执行: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"   ✓ 草稿处理器执行成功")
                    # 重新检查 draft.html 是否已生成
                    if draft_html_path.exists():
                        print(f"   ✓ draft/draft.html 已生成")
                    else:
                        print(f"   ⚠️ 处理器成功但 draft.html 仍未生成，将使用原始HTML")
                else:
                    print(f"   ⚠️ 草稿处理器执行失败:")
                    print(f"      stderr: {result.stderr[:200]}")
                    print(f"      将继续使用原始HTML上传（可能缺少推广模板）")
            else:
                print(f"   ⚠️ 找不到草稿处理器脚本: {process_script}")
                print(f"      将继续使用原始HTML上传（可能缺少推广模板）")
        else:
            print(f"   ⚠️ 未设置适配账号，无法自动调用草稿处理器")
            print(f"      将继续使用原始HTML上传（可能缺少推广模板）")
    else:
        print(f"   ✓ draft/draft.html 已存在")

    if not draft_html_path.exists():
        raise PipelineValidationError(
            f"草稿处理未生成 draft/draft.html，已阻断上传: {draft_html_path}"
        )
    
    # 5. 读取正文内容（只读一次，所有账号共用）
    print(f"\n📄 步骤 4: 读取文章内容")
    
    using_draft_html = False  # 标记是否使用了 draft.html
    
    # 优先级：draft.html（处理后的草稿）> article_original.html（原始 HTML）> article.html > article.md
    draft_html_path = Path(article_dir) / "draft" / "draft.html"
    original_html_path = Path(article_dir) / "article_original.html"
    html_path = Path(article_dir) / "article.html"
    md_path = Path(article_dir) / "article.md"
    ocr_path = Path(article_dir) / "article-ocr.md"
    
    if draft_html_path.exists():
        # 使用处理后的草稿 HTML - 包含推广模板和隐藏的投递方式
        with open(draft_html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"   使用: draft/draft.html (处理后的草稿，已添加推广模板)")
        using_draft_html = True
        
    elif original_html_path.exists():
        # 使用原始 HTML 文件 - 这是微信原始页面，保留完整结构
        with open(original_html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        content, source_label = extract_article_content(html_content)
        print(f"   使用: article_original.html (提取 {source_label}, {len(content)} 字符)")
        
    elif html_path.exists():
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 提取 body 内容或清理 HTML
        import re
        # 尝试提取 body 内容
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL | re.IGNORECASE)
        if body_match:
            content = body_match.group(1).strip()
        else:
            # 移除 DOCTYPE、html、head 等标签
            content = re.sub(r'<!DOCTYPE[^>]*>', '', html_content, flags=re.IGNORECASE)
            content = re.sub(r'<html[^>]*>|</html>', '', content, flags=re.IGNORECASE)
            content = re.sub(r'<head>.*?</head>', '', content, flags=re.DOTALL | re.IGNORECASE)
            content = content.strip()
        
        # 清理文章结构：移除标题、提取自信息、数据来源等
        # 1. 移除开头的标题 h1 标签
        content = re.sub(r'<h1[^>]*>.*?</h1>', '', content, flags=re.DOTALL | re.IGNORECASE, count=1)
        # 2. 移除 "提取自微信公众号" 的 div
        content = re.sub(r'<div[^>]*class=["\']meta["\'][^>]*>.*?</div>', '', content, flags=re.DOTALL | re.IGNORECASE)
        # 3. 移除 footer 区域（包含数据来源和原文链接）
        content = re.sub(r'<div[^>]*class=["\']footer["\'][^>]*>.*?</div>', '', content, flags=re.DOTALL | re.IGNORECASE)
        # 4. 清理图片间距：移除图片的 margin 样式，保持图片紧密连续
        content = re.sub(r'<img([^>]*?)\s*margin:\s*[^;"]*;?\s*', r'<img\1', content, flags=re.IGNORECASE)
        content = re.sub(r'<img([^>]*?)style=["\']([^"\']*?)\s*margin:\s*[^;"]*;?\s*([^"\']*?)["\']', r'<img\1style="\2\3"', content, flags=re.IGNORECASE)
        content = re.sub(r'<img([^>]*?)style=["\']\s*["\']', r'<img\1', content, flags=re.IGNORECASE)  # 清理空 style
        # 5. 移除所有 class 属性（可能包含冲突样式）
        content = re.sub(r'\s*class=["\'][^"\']*["\']', '', content)
        # 6. 清理空白
        content = re.sub(r'\n\s*\n', '\n', content)
        content = content.strip()
        
        print(f"   使用: article.html (提取正文并清理)")
    elif md_path.exists():
        with open(md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        content = f"<pre>{md_content}</pre>"
        print(f"   使用: article.md (转换为 HTML)")
    elif ocr_path.exists():
        with open(ocr_path, 'r', encoding='utf-8') as f:
            ocr_content = f.read()
        content = f"<pre>{ocr_content}</pre>"
        print(f"   使用: article-ocr.md")
    else:
        raise FileNotFoundError(f"找不到文章内容文件: {article_dir}")
    
    # 5. 如果使用了 draft.html，读取 draft.json 中的处理后元数据
    draft_json_path = Path(article_dir) / "draft" / "draft.json"
    if draft_json_path.exists():
        try:
            with open(draft_json_path, 'r', encoding='utf-8') as f:
                draft_meta = json.load(f)
            
            # 优先使用 draft.json 中的处理后值
            if draft_meta.get('title'):
                old_title = title
                title = draft_meta['title']
                if title != old_title:
                    print(f"   🔄 标题已处理: '{old_title}' -> '{title}'")
            
            if draft_meta.get('digest'):
                old_digest = digest
                digest = draft_meta['digest']
                if digest != old_digest:
                    print(f"   🔄 摘要已生成: {digest[:50]}...")
            
            if draft_meta.get('author'):
                # 如果传入了 author 参数，优先使用传入的值
                if not author:
                    author = draft_meta['author']
                    print(f"   🔄 作者已设置: {author}")
            
            if draft_meta.get('keyword'):
                print(f"   🔄 关键词编号: {draft_meta['keyword']}")
            
            print(f"   使用 draft.json 处理后元数据")
        except Exception as e:
            print(f"   ⚠️ 读取 draft.json 失败: {e}")
    
    # 6. 处理正文中的图片（本地 + 远程CDN），上传到微信素材库
    print(f"\n🖼️  步骤 5: 处理正文图片...")
    
    # 收集所有图片引用（src 和 data-src）
    all_img_refs = set()
    
    # 从 src 属性收集
    src_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
    for match in re.finditer(src_pattern, content):
        all_img_refs.add(match.group(1))
    
    # 从 data-src 属性收集
    data_src_pattern = r'<img[^>]+data-src=["\']([^"\']+)["\'][^>]*>'
    for match in re.finditer(data_src_pattern, content):
        all_img_refs.add(match.group(1))
    
    # 存储图片 URL 映射（所有账号共用）
    image_url_map = {}  # {原始路径/URL: 微信永久URL}
    remote_download_dir = Path(article_dir) / ".temp_remote_images"
    
    if all_img_refs:
        print(f"   发现 {len(all_img_refs)} 个唯一图片引用")
        
        # 使用第一个账号初始化 uploader（用于上传正文图片）
        first_uploader = WechatDraftUploader(appid=account_configs[0]['appid'])
        
        for img_src in all_img_refs:
            if img_src.startswith(('http://', 'https://', '//')):
                # 远程图片：下载后上传（微信草稿API不保留外部域名图片）
                try:
                    remote_download_dir.mkdir(exist_ok=True)
                    
                    parsed_url = img_src.replace('&amp;', '&')
                    url_hash = hashlib.md5(parsed_url.encode()).hexdigest()[:8]
                    
                    # 从 URL 参数 wx_fmt 提取正确扩展名，优于从路径推断
                    ext = Path(parsed_url.split('?')[0]).suffix
                    if not ext:
                        import urllib.parse
                        qs = urllib.parse.parse_qs(urllib.parse.urlparse(parsed_url).query)
                        wx_fmt = qs.get('wx_fmt', [''])[0].lower()
                        if wx_fmt in ['gif', 'png', 'jpg', 'jpeg', 'webp']:
                            ext = f'.{wx_fmt}'
                        else:
                            ext = '.jpg'
                    if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                        ext = '.jpg'
                    
                    temp_filename = f"remote_{url_hash}{ext}"
                    temp_path = remote_download_dir / temp_filename
                    
                    if not temp_path.exists():
                        print(f"   📥 下载远程图片: {img_src[:60]}...")
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                            'Referer': 'https://mp.weixin.qq.com/',
                        }
                        resp = requests.get(parsed_url, headers=headers, timeout=30)
                        resp.raise_for_status()
                        temp_path.write_bytes(resp.content)
                        print(f"      已下载: {temp_path.name} ({len(resp.content)} bytes)")
                    
                    # 检测实际格式，修正扩展名，并将 webp 转换为 png
                    upload_path = str(temp_path)
                    try:
                        from PIL import Image
                        img = Image.open(temp_path)
                        actual_fmt = img.format.upper() if img.format else ''
                        
                        # 如果实际格式与扩展名不匹配，重命名以确保 MIME 正确
                        ext_map = {'JPEG': '.jpg', 'PNG': '.png', 'GIF': '.gif', 'WEBP': '.webp'}
                        correct_ext = ext_map.get(actual_fmt, temp_path.suffix)
                        if correct_ext != temp_path.suffix:
                            new_path = temp_path.with_suffix(correct_ext)
                            temp_path.rename(new_path)
                            temp_path = new_path
                            upload_path = str(temp_path)
                            print(f"      格式修正: {actual_fmt} -> {temp_path.name}")
                        
                        if actual_fmt == 'WEBP':
                            # 转换为 PNG（微信 /materials 接口不支持 webp）
                            png_path = temp_path.with_suffix('.png')
                            if img.mode in ('RGBA', 'LA', 'P'):
                                img = img.convert('RGBA')
                            else:
                                img = img.convert('RGB')
                            img.save(png_path, 'PNG')
                            upload_path = str(png_path)
                            print(f"      WEBP 已转换为 PNG: {png_path.name}")
                    except ImportError:
                        # PIL 未安装，使用文件头兜底检测
                        header = temp_path.read_bytes()[:12]
                        if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
                            print(f"      ⚠️ 检测到 WEBP 但 Pillow 未安装，跳过该图片: {temp_path.name}")
                            raise Exception("Pillow 未安装，无法处理 WEBP 格式")
                    except Exception as e:
                        print(f"      格式转换警告: {e}")
                    
                    img_result = first_uploader.upload_material(upload_path, name=f"{title}_图片", compress=compress)
                    img_url = img_result['url']
                    image_url_map[img_src] = img_url
                    
                    print(f"   ✓ 上传远程图片: {img_src[:40]}... -> {img_url[:50]}...")
                except Exception as e:
                    err_msg = str(e)
                    if "积分不足" in err_msg or "insufficient balance" in err_msg.lower():
                        print(f"   ❌ 远程图片处理失败: {img_src[:60]}... (简立制作平台积分不足，请充值后重试)")
                    elif "unsupported file type" in err_msg.lower():
                        print(f"   ❌ 远程图片处理失败: {img_src[:60]}... (文件格式不支持，请安装 Pillow 库以自动转换 webp 格式)")
                    else:
                        print(f"   ⚠️ 远程图片处理失败: {img_src[:60]}... ({e})")
            else:
                # 本地相对路径
                if using_draft_html:
                    img_path = Path(article_dir) / "draft" / img_src
                else:
                    img_path = Path(article_dir) / img_src
                
                if img_path.exists():
                    try:
                        img_result = first_uploader.upload_material(str(img_path), name=f"{title}_图片", compress=compress)
                        img_url = img_result['url']
                        image_url_map[img_src] = img_url
                        print(f"   ✓ 上传本地图片: {img_src} -> {img_url[:50]}...")
                    except Exception as e:
                        print(f"   ⚠️ 本地图片上传失败: {img_src} ({e})")
                else:
                    print(f"   ⚠️ 本地图片不存在: {img_src}")
        
        # 批量替换 content 中的图片引用（同时替换 src 和 data-src）
        if image_url_map:
            print(f"   正在替换图片 URL（含 src 和 data-src）...")
            for original_src, wx_url in image_url_map.items():
                # 替换 src
                content = re.sub(
                    r'src=["\']' + re.escape(original_src) + r'["\']',
                    f'src="{wx_url}"',
                    content
                )
                # 替换 data-src
                content = re.sub(
                    r'data-src=["\']' + re.escape(original_src) + r'["\']',
                    f'data-src="{wx_url}"',
                    content
                )
            print(f"   ✓ 已替换 {len(image_url_map)} 个图片 URL")
    else:
        print(f"   无图片需要处理")

    if using_draft_html:
        remaining_original_refs = [
            ref for ref in all_img_refs
            if ref not in image_url_map and ref in collect_img_refs(content)
        ]
        if remaining_original_refs:
            raise PipelineValidationError(
                "部分草稿图片未成功上传并替换，已阻断上传: "
                + ", ".join(list(remaining_original_refs)[:10])
            )
        missing_local_images = validate_draft_local_images(Path(article_dir), content)
        if missing_local_images:
            raise PipelineValidationError(
                "草稿 HTML 引用了不存在的本地图片，已阻断上传: "
                + ", ".join(missing_local_images[:10])
            )
        unresolved_refs = [
            ref for ref in collect_img_refs(content)
            if not ref.startswith(("http://", "https://", "//", "data:"))
        ]
        if unresolved_refs:
            raise PipelineValidationError(
                "草稿 HTML 仍包含未上传替换的本地图片，已阻断上传: "
                + ", ".join(unresolved_refs[:10])
            )
    
    # 7. 处理封面图片（所有账号共用同一张封面）
    print(f"\n🖼️  步骤 6: 处理封面图片")
    
    images_dir = Path(article_dir) / "images"
    if not images_dir.exists():
        raise FileNotFoundError(f"找不到图片目录: {images_dir}")
    
    # 确定封面图片
    if cover_image:
        # 用户指定封面
        cover_path = images_dir / cover_image
        print(f"   使用指定封面: {cover_path.name}")
    else:
        # 智能选择封面
        cover_path = select_best_cover_image(images_dir, title, article_dir)
        print(f"   智能选择封面: {cover_path.name}")
    
    if not cover_path.exists():
        raise FileNotFoundError(f"封面图片不存在: {cover_path}")
    
    print(f"   封面: {cover_path.name}")
    
    # 8. 循环上传到所有适配账号
    print(f"\n🚀 步骤 7: 创建微信公众号草稿（共 {len(account_configs)} 个账号）")
    
    upload_results = []
    all_media_ids = []
    all_account_names = []
    
    for idx, account_config in enumerate(account_configs, 1):
        appid = account_config['appid']
        account_name = account_config['account_name']
        account_key = ACCOUNT_NAME_MAP.get(account_name, account_name.lower().replace(' ', '_'))
        
        print(f"\n   [{idx}/{len(account_configs)}] 正在上传到: {account_name}")
        
        # 为后续账号重新生成对应模板的草稿
        if idx > 1:
            print(f"   🔄 正在为 {account_name} 重新生成草稿...")
            
            # 删除旧的 draft 文件，让 process.py 从头重新生成
            if draft_html_path.exists():
                draft_html_path.unlink()
            if draft_json_path.exists():
                draft_json_path.unlink()
            
            # 重新运行 process.py 生成当前账号的 draft
            _process_script = Path.home() / ".hermes/skills/web/wechat-mp-draft-processor-pro/scripts/process.py"
            if _process_script.exists():
                cmd = ["python3", str(_process_script), article_id, "--account", account_key]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if result.returncode == 0:
                    print(f"   \u2713 草稿处理器执行成功")
                else:
                    print(f"   \u26a0\ufe0f 草稿处理器执行失败: {result.stderr[:200]}")
            
            # 重新读取 content
            if draft_html_path.exists():
                with open(draft_html_path, 'r', encoding='utf-8') as f:
                    account_content = f.read()
                
                # 处理新 content 中的图片（补充上传新图片）
                new_img_refs = set()
                for match in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', account_content):
                    new_img_refs.add(match.group(1))
                for match in re.finditer(r'<img[^>]+data-src=["\']([^"\']+)["\'][^>]*>', account_content):
                    new_img_refs.add(match.group(1))
                
                if new_img_refs:
                    print(f"   \u53d1现 {len(new_img_refs)} 个图片引用，补充处理...")
                    uploader = WechatDraftUploader(appid=appid)
                    for img_src in new_img_refs:
                        if img_src not in image_url_map:
                            try:
                                if img_src.startswith(('http://', 'https://', '//')):
                                    # 远程图片
                                    remote_download_dir.mkdir(exist_ok=True)
                                    parsed_url = img_src.replace('&amp;', '&')
                                    url_hash = hashlib.md5(parsed_url.encode()).hexdigest()[:8]
                                    ext = Path(parsed_url.split('?')[0]).suffix
                                    if not ext:
                                        import urllib.parse
                                        qs = urllib.parse.parse_qs(urllib.parse.urlparse(parsed_url).query)
                                        wx_fmt = qs.get('wx_fmt', [''])[0].lower()
                                        if wx_fmt in ['gif', 'png', 'jpg', 'jpeg', 'webp']:
                                            ext = f'.{wx_fmt}'
                                        else:
                                            ext = '.jpg'
                                    if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                                        ext = '.jpg'
                                    temp_filename = f"remote_{url_hash}{ext}"
                                    temp_path = remote_download_dir / temp_filename
                                    if not temp_path.exists():
                                        print(f"      \ud83d\udce5 下载远程图片: {img_src[:60]}...")
                                        headers = {
                                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                            'Referer': 'https://mp.weixin.qq.com/',
                                        }
                                        resp = requests.get(parsed_url, headers=headers, timeout=30)
                                        resp.raise_for_status()
                                        temp_path.write_bytes(resp.content)
                                        print(f"         \u5df2下载: {temp_path.name} ({len(resp.content)} bytes)")
                                    # 格式处理
                                    upload_path = str(temp_path)
                                    try:
                                        from PIL import Image
                                        img = Image.open(temp_path)
                                        actual_fmt = img.format.upper() if img.format else ''
                                        ext_map = {'JPEG': '.jpg', 'PNG': '.png', 'GIF': '.gif', 'WEBP': '.webp'}
                                        correct_ext = ext_map.get(actual_fmt, temp_path.suffix)
                                        if correct_ext != temp_path.suffix:
                                            new_path = temp_path.with_suffix(correct_ext)
                                            temp_path.rename(new_path)
                                            temp_path = new_path
                                            upload_path = str(temp_path)
                                        if actual_fmt == 'WEBP':
                                            png_path = temp_path.with_suffix('.png')
                                            if img.mode in ('RGBA', 'LA', 'P'):
                                                img = img.convert('RGBA')
                                            else:
                                                img = img.convert('RGB')
                                            img.save(png_path, 'PNG')
                                            upload_path = str(png_path)
                                    except ImportError:
                                        pass
                                    except Exception as e:
                                        print(f"         \u683c式转换警告: {e}")
                                    img_result = uploader.upload_material(upload_path, name=f"{title}_图片", compress=compress)
                                    image_url_map[img_src] = img_result['url']
                                    print(f"      \u2713 上传远程图片: {img_src[:40]}...")
                                else:
                                    # 本地图片
                                    img_path = Path(article_dir) / "draft" / img_src
                                    if img_path.exists():
                                        img_result = uploader.upload_material(str(img_path), name=f"{title}_图片", compress=compress)
                                        image_url_map[img_src] = img_result['url']
                                        print(f"      \u2713 上传本地图片: {img_src}")
                                    else:
                                        print(f"      \u26a0\ufe0f 本地图片不存在: {img_src}")
                            except Exception as e:
                                print(f"      \u26a0\ufe0f 图片处理失败: {img_src} ({e})")
                
                # 替换新 content 中的图片 URL
                for original_src, wx_url in image_url_map.items():
                    account_content = re.sub(
                        r'src=["\']' + re.escape(original_src) + r'["\']',
                        f'src="{wx_url}"',
                        account_content
                    )
                    account_content = re.sub(
                        r'data-src=["\']' + re.escape(original_src) + r'["\']',
                        f'data-src="{wx_url}"',
                        account_content
                    )
            else:
                print(f"   \u26a0\ufe0f draft.html 重新生成失败，使用原始 content")
                account_content = content
        else:
            account_content = content
        
        try:
            # 上传封面到该账号的微信素材库
            uploader = WechatDraftUploader(appid=appid)
            cover_result = uploader.upload_material(str(cover_path), name=f"{title}_封面", compress=compress)
            thumb_media_id = cover_result['mediaId']
            print(f"      \u2713 thumbMediaId: {thumb_media_id[:30]}...")
            
            # 组装文章数据
            # 优先使用传入的 author，其次使用账号配置中的作者，最后使用账号名称
            final_author = author or account_config.get('author', '') or account_name
            if len(final_author) > 16:
                final_author = final_author[:16]
            
            final_digest = digest or ""
            if len(final_digest) > 120:
                final_digest = final_digest[:120]
            
            final_title = title[:64] if len(title) > 64 else title
            
            article = {
                "title": final_title,
                "content": account_content,
                "thumbMediaId": thumb_media_id,
                "articleType": "news",
                "author": final_author,
                "digest": final_digest,
                "needOpenComment": need_open_comment
            }
            
            # 创建草稿
            result = uploader.create_draft([article])
            
            print(f"      \u2705 草稿创建成功!")
            print(f"         MediaID: {result['mediaId'][:30]}...")
            
            upload_results.append({
                "account_name": account_name,
                "appid": appid,
                "mediaId": result['mediaId'],
                "title": result['title'],
                "success": True
            })
            all_media_ids.append(result['mediaId'])
            all_account_names.append(account_name)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"      ❌ 上传到 {account_name} 失败: {e}")
            upload_results.append({
                "account_name": account_name,
                "appid": appid,
                "success": False,
                "error": str(e)
            })
    
    # 9. 更新飞书 Base 状态
    print(f"\n🔄 步骤 8: 更新飞书 Base 状态")
    
    # 统计成功/失败
    success_count = sum(1 for r in upload_results if r['success'])
    failed_count = len(upload_results) - success_count
    
    update_fields = {
        FIELD_STATUS: "已上传草稿"
    }
    
    # 回写文章ID（如果从目录中获取到了）
    if article_id:
        update_fields["文章ID"] = article_id
    
    # 如果有草稿ID字段，记录所有草稿ID
    if all_media_ids:
        # 格式: "账号1: mediaId1; 账号2: mediaId2"
        draft_id_value = "; ".join([f"{name}: {mid[:20]}..." for name, mid in zip(all_account_names, all_media_ids)])
        try:
            if FIELD_DRAFT_ID in fields or '草稿ID' in fields:
                update_fields[FIELD_DRAFT_ID] = draft_id_value
        except:
            pass
    
    if feishu.update_record(ARTICLE_TABLE_ID, record_id, update_fields):
        print(f"   ✓ {FIELD_STATUS} 已更新为: 已上传草稿")
        print(f"   ✓ 发布账号: {', '.join(all_account_names)}")
        if failed_count > 0:
            print(f"   ⚠️ 其中 {failed_count} 个账号上传失败")
    else:
        print(f"   ⚠️ 状态更新失败，请手动更新")
    
    # 10. 自动回复规则创建询问（如果上传成功）
    if success_count > 0:
        print(f"\n💬 步骤 9: 自动回复规则创建")
        
        # 先调用 preview 获取计划内容
        preview_cmd = [
            sys.executable,
            os.path.expanduser('~/.hermes/skills/web/wechat-autoreply-manager/scripts/create_autoreply.py'),
            article_id,
            '--preview'
        ]
        try:
            preview_result = subprocess.run(preview_cmd, capture_output=True, text=True, timeout=30)
            preview_output = preview_result.stdout
        except Exception as e:
            preview_output = f"预览获取失败: {e}"
        
        print(f"\n{'='*60}")
        print("🤖 询问: 是否创建自动回复规则？")
        print(f"{'='*60}")
        print(f"\n文章: {title}")
        print(f"适配账号: {', '.join(all_account_names)}")
        print(f"\n--- 预览内容 ---")
        # 打印 preview 输出（去掉顶部的分隔线，保留关键信息）
        for line in preview_output.split('\n'):
            # 过滤掉部分无关行
            if line.strip() and not line.startswith('='*40) and '步骤' not in line and '自动回复规则:' not in line:
                print(line)
        print("---")
        print(f"\n回复 '是' 自动创建，回复 '否' 跳过")
        print(f"\n[HERMES_AUTOREPLY_ASK]")
        print(f"article_id: {article_id}")
        print(f"record_id: {record_id}")
        print(f"[END_HERMES_AUTOREPLY_ASK]")
    
    return {
        "results": upload_results,
        "success_count": success_count,
        "failed_count": failed_count,
        "total_count": len(account_configs)
    }


def find_record_by_no(no: str, base_token: str = None) -> str:
    """
    根据编号（如 NO.008）查找飞书 Base 记录 ID
    
    Args:
        no: 文章编号，如 "NO.008" 或 "008"
        base_token: 飞书 Base Token
        
    Returns:
        str: 记录 ID
        
    Raises:
        ValueError: 未找到或找到多个匹配记录
    """
    # 标准化编号格式
    if not no.upper().startswith('NO.'):
        no = f"NO.{no}"
    no = no.upper()
    
    feishu = FeishuClient(base_token)
    items = feishu.query_records(ARTICLE_TABLE_ID, limit=500)
    
    matches = []
    for item in items:
        item_no = item.get('ID', '')
        if item_no and item_no.upper() == no:
            matches.append({
                'record_id': item.get('record_id'),
                'title': item.get('文章标题', ''),
                'status': item.get('文章状态', ''),
                'no': item_no
            })
    
    if not matches:
        raise ValueError(f"未找到编号为 {no} 的文章")
    
    if len(matches) > 1:
        raise ValueError(f"找到多个编号为 {no} 的文章，请使用 record_id 直接指定")
    
    match = matches[0]
    print(f"✓ 找到文章: {match['no']} | {match['title'][:40]}... | 状态: {match['status']}")
    
    return match['record_id']


def find_record_by_article_id(article_id: str, base_token: str = None) -> str:
    """
    根据文章ID（如 7907d7cb）查找飞书 Base 记录 ID
    
    Args:
        article_id: 文章ID，如 "7907d7cb"
        base_token: 飞书 Base Token
        
    Returns:
        str: 记录 ID
        
    Raises:
        ValueError: 未找到或找到多个匹配记录
    """
    # 清理 article_id（移除可能的空格）
    article_id = article_id.strip().lower()
    
    feishu = FeishuClient(base_token)
    items = feishu.query_records(ARTICLE_TABLE_ID, limit=500)
    
    matches = []
    for item in items:
        item_article_id = item.get('文章ID', '')
        if item_article_id and item_article_id.strip().lower() == article_id:
            matches.append({
                'record_id': item.get('record_id'),
                'title': item.get('文章标题', ''),
                'status': item.get('文章状态', ''),
                'article_id': item_article_id
            })
    
    if not matches:
        raise ValueError(f"未找到文章ID为 {article_id} 的文章")
    
    if len(matches) > 1:
        raise ValueError(f"找到多个文章ID为 {article_id} 的文章，请使用 record_id 直接指定")
    
    match = matches[0]
    print(f"✓ 找到文章: ID={match['article_id']} | {match['title'][:40]}... | 状态: {match['status']}")
    
    return match['record_id']


def find_latest_article_in_context(base_token: str = None) -> str:
    """
    智能上下文检测：查找最近同步到飞书 Base 的文章
    
    策略：
    1. 查询最近同步的文章（按采集时间倒序）
    2. 检查本地目录是否存在
    3. 返回第一个有效的记录
    
    Args:
        base_token: 飞书 Base Token
        
    Returns:
        str: 记录 ID
        
    Raises:
        ValueError: 未找到有效文章
    """
    feishu = FeishuClient(base_token)
    items = feishu.query_records(ARTICLE_TABLE_ID, limit=50)
    
    # 按采集时间倒序（最新的在前）
    sorted_items = sorted(
        items, 
        key=lambda x: x.get('采集时间', 0) or 0, 
        reverse=True
    )
    
    for item in sorted_items:
        record_id = item.get('record_id')
        title = item.get('文章标题', '')
        article_id = item.get('文章ID', '')
        status = item.get('文章状态', '')
        
        # 检查本地目录是否存在
        article_dir = find_article_directory(title, article_id)
        if article_dir:
            print(f"✓ 自动检测到上下文文章: ID={article_id} | {title[:40]}... | 状态: {status}")
            return record_id
    
    raise ValueError("未在上下文中找到有效的文章（请确保文章已同步到飞书 Base 且本地目录存在）")


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description='从飞书 Base 上传文章到微信公众号草稿箱（自动获取 AppID）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 方式1: 使用文章编号（推荐）
    python upload_from_feishu.py --no NO.008
    python upload_from_feishu.py -n 008
    
    # 方式2: 使用记录 ID
    python upload_from_feishu.py --record-id recvhq1MWUhyc5
    
    # 方式3: 使用文章ID（如 7907d7cb）⭐ 新增
    python upload_from_feishu.py --article-id 7907d7cb
    python upload_from_feishu.py -aid 7907d7cb
    
    # 方式4: 自动检测上下文（最近同步的文章）⭐ 新增
    python upload_from_feishu.py --context
    python upload_from_feishu.py -ctx
    
    # 指定封面图片
    python upload_from_feishu.py -n 008 --cover img_001.jpg
    
    # 覆盖作者
    python upload_from_feishu.py -n 008 --author "Joblinker官方"
    
    # 启用图片压缩
    python upload_from_feishu.py -n 008 --compress
        """
    )
    
    # 创建互斥组：--record-id、--no、--article-id、--context 四选一
    id_group = parser.add_mutually_exclusive_group(required=True)
    id_group.add_argument('--record-id', '-r', 
                       help='飞书 Base 文章记录 ID')
    id_group.add_argument('--no', '-n', dest='article_no',
                       help='文章编号，如 NO.008 或 008')
    id_group.add_argument('--article-id', '-aid', dest='article_id',
                       help='文章ID，如 7907d7cb（从提取工具生成）')
    id_group.add_argument('--context', '-ctx', dest='use_context', action='store_true',
                       help='自动检测上下文（使用最近同步的文章）')
    
    parser.add_argument('--base-token', '-b', 
                       help='飞书 Base Token（默认使用配置）')
    parser.add_argument('--cover', '-c', 
                       help='指定封面图片文件名（默认使用第一张）')
    parser.add_argument('--author', '-a', 
                       help='指定作者名称（覆盖账号配置）')
    parser.add_argument('--no-comment', action='store_true', 
                       help='关闭评论（默认开启）')
    parser.add_argument('--compress', '-z', action='store_true',
                       help='启用图片压缩（默认不压缩）')
    
    args = parser.parse_args()
    
    try:
        # 根据参数查找 record_id
        if args.article_no:
            record_id = find_record_by_no(args.article_no, args.base_token)
        elif args.article_id:
            record_id = find_record_by_article_id(args.article_id, args.base_token)
        elif args.use_context:
            record_id = find_latest_article_in_context(args.base_token)
        else:
            record_id = args.record_id
        
        result = upload_from_feishu(
            record_id=record_id,
            base_token=args.base_token,
            cover_image=args.cover,
            author=args.author,
            need_open_comment=0 if args.no_comment else 1,
            compress=args.compress
        )
        
        print(f"\n" + "=" * 60)
        print(f"✅ 上传完成!")
        print(f"=" * 60)
        print(f"成功: {result['success_count']}/{result['total_count']} 个账号")
        for r in result['results']:
            status = "✅" if r['success'] else "❌"
            print(f"{status} {r['account_name']}: {r.get('mediaId', r.get('error', '未知'))[:40]}...")
        print(f"=" * 60)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
