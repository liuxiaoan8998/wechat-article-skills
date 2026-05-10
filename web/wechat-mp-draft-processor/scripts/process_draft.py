#!/usr/bin/env python3
"""
微信公众号草稿处理脚本 - 行研实习账号

核心功能：
1. 读取原始提取的文章
2. 识别文章模式（文字 vs 长图）
3. 隐藏投递方式（文本删除 / 图片裁剪）
4. 标题转换
5. 摘要生成
6. 追加固定推广模板
7. 输出 draft.html + draft.json

Usage:
    python process_draft.py --article-dir ~/.hermes/output/85c8245b/ --account xingyan_shixi
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# 添加 skill 目录到路径
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
WEB_DIR = SKILL_DIR.parent
sys.path.insert(0, str(SKILL_DIR))
sys.path.insert(0, str(WEB_DIR / "_shared"))

from wechat_pipeline import ensure_img_srcs, extract_article_content


# ============ 配置 ============

class XingyanShixiConfig:
    """行研实习账号配置"""

    # 标题前缀规则
    TITLE_PREFIX_RULES = [
        (r"量化", "量化实习 | "),
        (r"金融工程", "实习｜"),
        (r"金融", "实习｜"),
        (r"行研", "行研实习 | "),
        (r"投行", "投行实习 | "),
        (r"基金", "基金实习 | "),
        (r"证券", "证券实习 | "),
    ]
    DEFAULT_PREFIX = "实习｜"

    # 标题中移除的内容
    TITLE_REMOVE_PATTERNS = [
        r"20\d{2}",  # 年份
        r"\d{4}校园招聘",  # 年份+校园招聘
        r"\d{4}校招",  # 年份+校招
        r"[\uff5c|]\s*[一-龥]+\u56e2\u961f\s*$",  # |后面的团队修饰语（如"开源金工魏建榕团队"）
    ]

    # 文字模式：投递方式删除关键词
    DELIVERY_KEYWORDS = [
        "简历投递", "投递方式", "联系方式", "申请方式",
        "如何投递", "邮箱投递", "如何申请", "简历发送",
        "联系我们",
    ]

    # 长图模式：OCR 定位关键词
    OCR_DELIVERY_KEYWORDS = [
        "投递方式", "简历投递", "联系方式", "申请方式",
        "如何申请", "简历发送", "联系我们", "招聘流程",
        "扫码申请", "即刻扫码", "二维码", "网申链接",
        "校园招聘官网", "招聘官网", "投递邮箱", "邮箱投递",
        "网申", "邮件投递", "发送简历", "报名链接",
    ]

    # 固定模板（HTML 格式）
    # 格式参考：https://mp.weixin.qq.com/s/mtiMSmROGUTtEbjb4ASrhw
    # 图片素材永久链接来自 promotion_media_ids.json
    # 优先从外部文件加载，文件不存在时回退到内置模板
    _PROMOTION_TEMPLATE_FALLBACK = """<p style="text-align: center;"><span style="background-color: rgb(217, 33, 66); color: rgb(255, 255, 255); font-weight: bold;">** 简历投递 **</span></p>
<p style="text-align: center;"><strong>点击名片，回复关键词：</strong><strong><span style="color: rgb(6, 28, 99); font-weight: bold;">{keyword}</span></strong></p>
<p style="text-align: center;"><span style="font-size: 14px;">获取简历投递方式</span></p>
<p style="text-align: center;"><img src="http://mmbiz.qpic.cn/mmbiz_gif/l7s0zoz5zgolwlXbicJyeibMUXGUuZVTqsCluSq7tMyibPUtCD1RcAoiaDRsuMZBUKVGAiaOnHd7BOoulJVcx2rskOIysQeaoxNwja7vdF3A2ibq4/0?wx_fmt=gif" style="width: 28px; display: block; margin: 0 auto;"/></p>
<p style="text-align: center;"><strong>转给身边需要的人！不要错过报名时间！</strong></p>
<p><br/></p>
<p>很多家长和同学只知道“金九银十”，以为校园招聘会在9、10月进行，但是近40%的企业会在4月-7月就发布暑期实习和校招/秋招提前批了，并且笔试、面试流程也比较简单，部分岗位有直接转正机会。不要白白浪费上岸机会哦~</p>
<p><br/></p>
<p>值得注意的是，暑期实习和校招/秋招提前批不会影响正式批次的投递和录用，正式批次仍然可以继续投递。相当于提前批给大家多留了一次机会。</p>
<p><br/></p>
<p>如果你不知道都有哪些企业开放暑期实习/校招/秋招，如果你没时间去网上找信息，如果你想把更多的时间精力留给笔试面试，省时省力网申，小编强烈推荐你领取：</p>
<p><br/></p>
<p style="text-align: center;"><span style="color: rgb(6, 28, 99); font-weight: bold;">↓【2026年实习/校招/秋招信息pro汇总表】↓</span></p>
<p style="text-align: center;"><span style="font-size: 14px;">可根据行业、岗位方向、专业要求、地点...进行筛选</span></p>
<p><br/></p>
<p><img src="http://mmbiz.qpic.cn/mmbiz_png/l7s0zoz5zgpzvqUOaE08RmQj9qcmiaflF37BtykGPyp0ibhxFBF6QF7TN7DwROS7iaMxlmmqbWResmMz0kUkCqHSvOqpeIvKOqAN2adX3ibjG50/0?wx_fmt=png" style="width:100%;max-width:100%;display:block;margin:0;"/></p>
<p><br/></p>
<p style="text-align: center;"><strong>（腾讯文档 实时更新 以上仅部分展示）</strong></p>
<p style="text-align: center;"><strong>每天更新！更新至2026年12月31日！</strong></p>
<p style="text-align: center;"><strong>包括国央企、上市公司、事业单位、私企、外企、合资企业，全行业类型！</strong></p>
<p style="text-align: center;"><strong>涵盖互联网/金融/科技/制造业/咨询/快消/医药/地产/教育/文娱等行业</strong></p>
<p style="text-align: center;"><strong>建议同学们提前做好准备，以免错失良机。</strong></p>
<p><br/></p>
<p style="text-align: center;"><strong>订阅费用：19.9元</strong></p>
<p><br/></p>
<p style="text-align: center; background-image: linear-gradient(90deg, rgb(156, 157, 232) 0%, rgb(246, 219, 238) 100%); padding: 8px 0; color: rgb(255, 255, 255); font-weight: bold; letter-spacing: 2px;">如何领取</p>
<p style="text-align: center;"><strong>关注公众号</strong></p>
<p style="text-align: center;">关注"行研实习"，后台回复：订阅</p>
<p style="text-align: center;"><span style="color: rgb(123, 12, 0); font-weight: bold;">一杯奶茶钱，助力你求职快人一步！</span></p>"""

    @classmethod
    def get_promotion_template(cls) -> str:
        """从外部文件加载推广模板，不存在则使用内置模板"""
        template_file = SKILL_DIR / "templates" / "xingyan_shixi.html"
        if template_file.exists():
            with open(template_file, 'r', encoding='utf-8') as f:
                return f.read()
        return cls._PROMOTION_TEMPLATE_FALLBACK

    # 类加载时从文件初始化模板，保持与之前代码兼容
    PROMOTION_TEMPLATE = _PROMOTION_TEMPLATE_FALLBACK

    AUTHOR="行研实习"


IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
LONG_IMAGE_SLICE_OVERLAP = 100
SUPPORTED_ACCOUNTS = {"xingyan_shixi", "joblinker"}


# 加载外部模板文件（如果存在）
_template_file = SKILL_DIR / "templates" / "xingyan_shixi.html"
if _template_file.exists():
    try:
        with open(_template_file, 'r', encoding='utf-8') as f:
            XingyanShixiConfig.PROMOTION_TEMPLATE = f.read()
    except Exception:
        pass


# ============ 工具函数 ============

def load_metadata(article_dir: str) -> Dict:
    """加载 metadata.json"""
    path = Path(article_dir) / "metadata.json"
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def detect_article_mode(article_dir: str) -> str:
    """
检测文章模式：text 或 long_image

    - 如果 article.md 有较多文字内容（>500字符），且图片数量少，认为是文字模式
    - 如果 article.md 文字很少（<300字符），且有超长图，认为是长图模式
    """
    md_path = Path(article_dir) / "article.md"
    ocr_path = Path(article_dir) / "article-ocr.md"

    # 检查 OCR 文件中是否有超长图
    has_long_image = False
    if ocr_path.exists():
        with open(ocr_path, 'r', encoding='utf-8') as f:
            ocr_content = f.read()
        if "超长图" in ocr_content or "已切片" in ocr_content:
            has_long_image = True

    # 检查 article.md 文字量
    md_text_length = 0
    if md_path.exists():
        with open(md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        # 去除 markdown 标记后的纯文字长度
        text = re.sub(r'[#*|\-\[\]!()>`]', '', md_content)
        md_text_length = len(text.strip())

    # 判断逻辑
    if has_long_image and md_text_length < 500:
        return "long_image"
    else:
        return "text"


def transform_title(original_title: str) -> str:
    """
    标题转换：添加前缀、精简
    """
    config = XingyanShixiConfig()

    # 0. 预处理：统一竖线、移除多余空格
    clean_title = original_title.strip()
    clean_title = re.sub(r'\s+', ' ', clean_title)

    # 1. 先精简标题（移除年份、团队后缀等）
    for pattern in config.TITLE_REMOVE_PATTERNS:
        clean_title = re.sub(pattern, "", clean_title)
    clean_title = re.sub(r'\s+', ' ', clean_title).strip()
    # 移除末尾残留的竖线和空格
    clean_title = re.sub(r'[\uff5c|]\s*$', '', clean_title).strip()

    # 2. 确定前缀：检查精简后的标题是否已经以某个前缀开头
    prefix = config.DEFAULT_PREFIX
    for pattern, p in config.TITLE_PREFIX_RULES:
        # 前缀如 "量化实习 | "，核心词是 "量化实习"
        core = p.replace(' | ', '').replace('｜', '').strip()
        # 如果标题已经以该核心词开头，跳过此前缀
        if clean_title.startswith(core):
            prefix = ""
            break
        if re.search(pattern, clean_title):
            prefix = p
            break

    # 3. 组合
    new_title = (prefix + clean_title) if prefix else clean_title

    # 4. 截断到 64 字符
    if len(new_title) > 64:
        new_title = new_title[:63] + "…"

    return new_title


def normalize_account(account: str) -> str:
    """Normalize uploader account keys to processor-supported values."""
    account = (account or "xingyan_shixi").strip()
    aliases = {
        "xingyan_shixi": "xingyan_shixi",
        "joblinker": "joblinker",
        "研究生求职圈": "joblinker",
    }
    return aliases.get(account, account)


def get_account_author(account: str) -> str:
    """Resolve the author shown in draft metadata for each account."""
    account = normalize_account(account)
    authors = {
        "xingyan_shixi": "行研实习",
        "joblinker": "Joblinker",
    }
    return authors.get(account, account)


def load_promotion_template(account: str) -> str:
    """Load the account-specific promotion template with legacy fallback."""
    account = normalize_account(account)
    candidate_paths = [
        SKILL_DIR / "templates" / f"{account}.html",
        WEB_DIR / "wechat-mp-draft-processor-pro" / "templates" / f"{account}.html",
    ]
    for template_path in candidate_paths:
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
    raise FileNotFoundError(
        f"找不到账号 {account} 的推广模板，已检查: "
        + ", ".join(str(path) for path in candidate_paths)
    )


def extract_plain_text(html_or_md: str) -> str:
    """从 HTML 或 Markdown 中提取纯文本"""
    # 先尝试移除 HTML 标签
    text = re.sub(r'<[^>]+>', ' ', html_or_md)
    # 移除 Markdown 标记
    text = re.sub(r'[#*|\-\[\]!()>`]', '', text)
    # 移除多余空格
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def generate_digest(content: str, max_length: int = 120) -> str:
    """
    从正文中自动生成摘要
    """
    text = extract_plain_text(content)

    if len(text) <= max_length:
        return text

    # 在 max_length 附近找句子结束位置
    cutoff = max_length
    # 尝试在截断点附近找句子结束符号
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


def generate_keyword() -> str:
    """生成关键词编号（格式：MMdd）"""
    now = datetime.now()
    return now.strftime("%m%d")


def has_promotion_content(content: str) -> bool:
    """
    检测正文中是否已经包含推广模板内容

    通过检测以下关键特征来判断：
    1. "回复关键词" + "获取简历投递方式"
    2. "订阅费用" 或 "19.9元"
    3. "信息汇总表" / "汇总表" + "筛选"
    4. "一杯奶茶钱"

    返回 True 表示原文已含推广内容，不应再追加模板
    """
    text = extract_plain_text(content)

    indicators = [
        ("回复关键词" in text and "获取简历投递方式" in text),
        ("订阅费用" in text or "19.9元" in text),
        ("汇总表" in text and "筛选" in text),
        ("一杯奶茶钱" in text),
        ("关注" in text and "后台回复" in text and "订阅" in text),
    ]

    # 命中 2 个及以上指标，认为已有推广内容
    hit_count = sum(indicators)
    return hit_count >= 2


# ============ 文字模式处理 ============

def remove_delivery_sections_text(content: str) -> str:
    """
    文字模式：删除投递方式相关段落

    策略：
    1. 使用 BeautifulSoup 解析 HTML
    2. 只遍历"叶级"块级元素（没有子块级元素的），避免父元素被误删
    3. 删除以投递关键词开始的元素及其后续兄弟
    4. 删除包含邮箱地址、联系电话等敏感信息的元素
    """
    from bs4 import BeautifulSoup

    config = XingyanShixiConfig()
    soup = BeautifulSoup(content, 'html.parser')

    # 定义块级标签
    block_tags = ['section', 'p', 'div']

    # 找到所有块级元素
    all_blocks = soup.find_all(block_tags)

    # 辅助函数：检查一个元素是否是另一个元素的祖先
    def is_ancestor_of(ancestor, descendant):
        parent = descendant.parent
        while parent:
            if parent is ancestor:
                return True
            parent = parent.parent
        return False

    # 辅助函数：获取最深层匹配的元素列表
    def get_deepest_matches(matched_list):
        result = []
        for elem in matched_list:
            # 如果这个元素是其他匹配元素的祖先，跳过
            if any(is_ancestor_of(elem, other) for other in matched_list if other is not elem):
                continue
            result.append(elem)
        return result

    # ========== 第一步：找到所有以投递关键词开始的元素 ==========
    keyword_matched = []
    for elem in all_blocks:
        text = elem.get_text(strip=True)
        if not text:
            continue
        for keyword in config.DELIVERY_KEYWORDS:
            pattern = rf'^{re.escape(keyword)}[：:\s]*'
            if re.search(pattern, text, re.IGNORECASE):
                keyword_matched.append(elem)
                break

    # 只保留最深层匹配
    deepest_keyword = get_deepest_matches(keyword_matched)

    # ========== 第二步：找到所有包含邮箱的元素 ==========
    email_matched = []
    for elem in all_blocks:
        text = elem.get_text(strip=True)
        if re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text):
            email_matched.append(elem)

    # 只保留最深层匹配
    deepest_email = get_deepest_matches(email_matched)

    # ========== 第三步：找到所有包含手机号的元素 ==========
    phone_matched = []
    for elem in all_blocks:
        text = elem.get_text(strip=True)
        if re.search(r'1[3-9]\d{9}', text):
            phone_matched.append(elem)

    # 只保留最深层匹配
    deepest_phone = get_deepest_matches(phone_matched)

    # ========== 第四步：收集需要删除的元素 ==========
    elements_to_remove = set()

    # 处理关键词匹配：删除该元素及其后续兄弟
    for elem in deepest_keyword:
        current = elem
        while current and current.name in block_tags:
            elements_to_remove.add(id(current))
            current = current.find_next_sibling()
            if not current:
                break
            # 如果下一个兄弟是标题级元素，停止
            if current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                break
            # 如果下一个兄弟是标题级的块级元素，也停止
            if current.name in block_tags:
                child_text = current.get_text(strip=True)
                # 停止条件：短文本（<15字符）且包含章节标题关键词
                # 注意：不含"投递"、"联系"、"招聘"、"实习"等投递信息中常见词
                if child_text and len(child_text) < 15 and any(
                    kw in child_text for kw in ['岗位', '要求', '流程', '介绍', '关键词', 'end', '团队', '关于', '公司']
                ):
                    break

    # 处理邮箱匹配：只删除该元素本身（不删除后续兄弟）
    for elem in deepest_email:
        elements_to_remove.add(id(elem))

    # 处理手机号匹配：只删除该元素本身
    for elem in deepest_phone:
        elements_to_remove.add(id(elem))

    # 执行删除
    for elem in all_blocks:
        if id(elem) in elements_to_remove:
            elem.decompose()

    # 清理空的块级元素（不含图片的）
    for empty in soup.find_all(block_tags):
        if not empty.get_text(strip=True) and not empty.find('img'):
            empty.decompose()

    return str(soup)


# ============ 长图模式处理 ============

def parse_ocr_slices(article_dir: str) -> List[Dict]:
    """
    解析 article-ocr.md 中的切片信息

    返回：
    [
        {
            "filename": "img_001.jpg",
            "is_long_image": True,
            "slices": [
                {"slice_file": "slices/img_001_slice_01.jpg", "ocr_text": "..."},
                ...
            ]
        }
    ]
    """
    ocr_path = Path(article_dir) / "article-ocr.md"
    if not ocr_path.exists():
        return []

    with open(ocr_path, 'r', encoding='utf-8') as f:
        content = f.read()

    images = []

    # 匹配图片块
    # 格式：#### 图片: img_001.jpg
    img_blocks = re.split(r'#### 图片:\s*(\S+)', content)

    for i in range(1, len(img_blocks), 2):
        img_name = img_blocks[i]
        block = img_blocks[i + 1]

        info = {
            "filename": img_name,
            "is_long_image": "超长图" in block or "已切片" in block,
            "ocr_text": "",
            "slices": []
        }

        # 提取整体 OCR 文本
        ocr_lines = []
        for line in block.split('\n'):
            line = line.strip()
            if line and not line.startswith('**') and not line.startswith('[') and not line.startswith('<!--') and not line.startswith('切片'):
                ocr_lines.append(line)
        info["ocr_text"] = '\n'.join(ocr_lines)

        # 提取切片信息
        slice_pattern = r'`(slices/[^`]+)`'
        slice_files = re.findall(slice_pattern, block)

        # 如果有段标记 [段1] [段2] 等
        segment_pattern = r'\[段(\d+)\](.*?)(?=\[段|\Z)'
        segments = re.findall(segment_pattern, block, re.DOTALL)

        for seg_num, seg_text in segments:
            slice_idx = int(seg_num) - 1
            slice_file = slice_files[slice_idx] if slice_idx < len(slice_files) else None
            if slice_file:
                info["slices"].append({
                    "slice_file": slice_file,
                    "ocr_text": seg_text.strip(),
                    "segment_num": int(seg_num)
                })

        images.append(info)

    return images


def find_delivery_slices(slices_info: List[Dict]) -> List[Tuple[str, str]]:
    """
    找到包含投递方式的切片

    返回：[(图片文件名, 切片文件名), ...]
    """
    config = XingyanShixiConfig()
    delivery_slices = []

    for img_info in slices_info:
        for slice_info in img_info.get("slices", []):
            ocr_text = slice_info.get("ocr_text", "")
            for keyword in config.OCR_DELIVERY_KEYWORDS:
                if keyword in ocr_text:
                    delivery_slices.append((img_info["filename"], slice_info["slice_file"]))
                    break

    return delivery_slices


def crop_slice_remove_delivery(article_dir: str, slice_file: str, output_file: str) -> bool:
    """
    裁剪切片：去除投递方式区域

    策略：
    1. 尝试使用 pytesseract 定位关键词的位置
    2. 如果不可用，使用启发式规则（假设投递方式在切片下半部分，裁剪掉底部 40%）

    返回是否成功
    """
    from PIL import Image

    input_path = Path(article_dir) / slice_file
    output_path = Path(article_dir) / output_file

    if not input_path.exists():
        print(f"    ⚠️ 切片不存在: {input_path}")
        return False

    try:
        img = Image.open(input_path)
        width, height = img.size

        # 尝试使用 pytesseract 定位
        try:
            import pytesseract
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, lang='chi_sim')

            # 查找关键词位置
            config = XingyanShixiConfig()
            min_y = height  # 关键词最早出现的 Y 坐标

            for i, text in enumerate(data['text']):
                for keyword in config.OCR_DELIVERY_KEYWORDS:
                    if keyword in text:
                        y = data['top'][i]
                        if y < min_y:
                            min_y = y

            if min_y < height:
                # 在关键词之上留一些缓冲（比如 20px），然后裁剪
                crop_y = max(0, min_y - 20)
                cropped = img.crop((0, 0, width, crop_y))
                cropped.save(output_path, quality=95)
                print(f"    ✅ 已裁剪投递区域（OCR 定位）: {slice_file} -> {output_file}")
                return True

        except ImportError:
            pass
        except Exception as e:
            print(f"    ⚠️ OCR 定位失败: {e}")

        # 启发式规则：裁剪掉底部 45%
        # 因为投递方式通常在长图下半部分
        crop_y = int(height * 0.55)
        cropped = img.crop((0, 0, width, crop_y))
        cropped.save(output_path, quality=95)
        print(f"    ✂️ 已裁剪投递区域（启发式: 保留55%）: {slice_file} -> {output_file}")
        return True

    except Exception as e:
        print(f"    ❌ 裁剪失败: {e}")
        return False


def crop_image_bottom(
    input_path: Path,
    output_path: Path,
    keep_ratio: float = 0.55
) -> bool:
    """
    对普通图片做底部裁剪，去除投递方式区域

    策略：保留图片顶部 keep_ratio 比例的内容，丢弃底部
    """
    from PIL import Image
    try:
        img = Image.open(input_path)
        width, height = img.size
        crop_y = int(height * keep_ratio)
        cropped = img.crop((0, 0, width, crop_y))
        cropped.save(output_path, quality=95)
        print(f"    ✂️ 已裁剪底部 {(1 - keep_ratio) * 100:.0f}%: {input_path.name}")
        return True
    except Exception as e:
        print(f"    ❌ 普通图片裁剪失败: {e}")
        return False


def process_long_images(article_dir: str, output_dir: str) -> List[str]:
    """
    长图模式：处理图片

    1. 解析 OCR 切片
    2. 找到包含投递方式的切片
    3. 裁剪这些切片
    4. 重新拼接为新长图
    5. 返回处理后的图片路径列表

    返回: [图片文件路径, ...]
    """
    from PIL import Image

    print("  🖼️ 长图模式：处理图片...")

    config = XingyanShixiConfig()

    # 1. 解析 OCR 切片
    slices_info = parse_ocr_slices(article_dir)
    if not slices_info:
        print("  ⚠️ 未找到 OCR 切片信息，使用原图")
        # 复制所有图片到输出目录
        images_dir = Path(article_dir) / "images"
        output_images_dir = Path(output_dir) / "images"
        output_images_dir.mkdir(parents=True, exist_ok=True)

        processed_images = []
        for img_file in sorted(images_dir.iterdir()):
            if img_file.suffix.lower() in IMAGE_EXTENSIONS:
                out_file = output_images_dir / img_file.name
                import shutil
                shutil.copy2(img_file, out_file)
                processed_images.append(str(out_file))

        return processed_images

    # 2. 找到包含投递方式的切片
    delivery_slices = find_delivery_slices(slices_info)
    print(f"  🔍 找到 {len(delivery_slices)} 个含投递方式的切片")

    # 3. 确定需要处理的图片
    images_dir = Path(article_dir) / "images"
    output_images_dir = Path(output_dir) / "images"
    output_images_dir.mkdir(parents=True, exist_ok=True)

    processed_images = []

    for img_info in slices_info:
        img_name = img_info["filename"]
        img_path = images_dir / img_name

        if not img_path.exists():
            continue

        # 检查该图片是否有切片需要裁剪
        slices_to_crop = [(s, f) for s, f in delivery_slices if s == img_name]
        ocr_text = img_info.get("ocr_text", "")
        has_delivery_in_ocr = any(kw in ocr_text for kw in config.OCR_DELIVERY_KEYWORDS)

        # ========== 普通图片检测与裁剪 ==========
        if not img_info.get("is_long_image"):
            if has_delivery_in_ocr or slices_to_crop:
                ocr_text_lower = ocr_text.lower()
                # 如果是纯投递方式图（含二维码/扫码+申请等组合），直接丢弃
                is_pure_delivery = (
                    "二维码" in ocr_text and ("扫码" in ocr_text or "即刻" in ocr_text)
                )
                if is_pure_delivery:
                    print(f"  🚮 普通图片为纯投递方式图，已丢弃: {img_name}")
                    continue

                # 否则做底部裁剪
                out_path = output_images_dir / img_name
                if crop_image_bottom(img_path, out_path, keep_ratio=0.55):
                    processed_images.append(str(out_path))
                    print(f"  ✂️ 裁剪普通图片投递区域: {img_name}")
                else:
                    # 裁剪失败，回退到复制
                    import shutil
                    shutil.copy2(img_path, out_path)
                    processed_images.append(str(out_path))
                    print(f"  ⚠️ 裁剪失败，复制图片: {img_name}")
            else:
                # 无需裁剪，直接复制
                out_path = output_images_dir / img_name
                import shutil
                shutil.copy2(img_path, out_path)
                processed_images.append(str(out_path))
                print(f"  ✅ 复制图片: {img_name}")
            continue

        # ========== 长图切片处理 ==========
        if not slices_to_crop:
            # 无需裁剪，直接复制
            out_path = output_images_dir / img_name
            import shutil
            shutil.copy2(img_path, out_path)
            processed_images.append(str(out_path))
            print(f"  ✅ 复制图片: {img_name}")
            continue

        # 需要裁剪并重新拼接
        print(f"  ✂️ 处理长图: {img_name}")

        # 获取该图片的所有切片
        all_slices = img_info.get("slices", [])

        if not all_slices:
            # 没有切片信息，直接复制
            out_path = output_images_dir / img_name
            import shutil
            shutil.copy2(img_path, out_path)
            processed_images.append(str(out_path))
            print(f"  ⚠️ 无切片信息，直接复制: {img_name}")
            continue

        # 确定含投递关键词的切片索引
        delivery_indices = set()
        for idx, slice_info in enumerate(all_slices):
            slice_file = slice_info["slice_file"]
            if any(f == slice_file for _, f in delivery_slices):
                delivery_indices.add(idx)

        # 尾部切片丢弃策略：
        # 如果含关键词的切片在最后 2 个位置，直接丢弃从它开始的所有尾部切片
        # 这样更彻底地去除底部投递区域
        max_delivery_idx = max(delivery_indices) if delivery_indices else -1
        tail_drop_threshold = len(all_slices) - 2  # 倒数2个切片开始

        if max_delivery_idx >= tail_drop_threshold:
            # 丢弃从第一个含投递关键词的切片开始的所有尾部切片
            first_delivery_idx = min(delivery_indices)
            kept_slices = all_slices[:first_delivery_idx]
            print(f"    📝 尾部切片含投递信息，丢弃切片 {first_delivery_idx + 1}~{len(all_slices)}")
        else:
            # 含关键词切片不在尾部，对每个含关键词切片单独裁剪
            kept_slices = all_slices

        # 处理保留的切片
        processed_slice_files = []
        for idx, slice_info in enumerate(kept_slices):
            slice_file = slice_info["slice_file"]
            is_delivery = idx in delivery_indices

            if is_delivery:
                # 裁剪该切片（含关键词但不在尾部的情况）
                processed_name = f"processed_{Path(slice_file).name}"
                crop_slice_remove_delivery(article_dir, slice_file, processed_name)
                processed_slice_path = Path(article_dir) / processed_name
                if processed_slice_path.exists():
                    processed_slice_files.append(processed_slice_path)
            else:
                # 保留原切片
                original_slice_path = Path(article_dir) / slice_file
                if original_slice_path.exists():
                    processed_slice_files.append(original_slice_path)

        # 重新拼接切片
        if processed_slice_files:
            try:
                # 读取所有切片并拼接。OCR 提取阶段会为长图切片保留 overlap，
                # 重拼时需要去掉后续切片顶部的重叠区，否则会出现内容重复和错位。
                prepared_slices = []
                for idx, slice_path in enumerate(processed_slice_files):
                    slice_img = Image.open(slice_path)
                    if slice_img.mode in ('RGBA', 'P'):
                        slice_img = slice_img.convert('RGB')

                    if idx > 0 and slice_img.size[1] > LONG_IMAGE_SLICE_OVERLAP:
                        slice_img = slice_img.crop(
                            (0, LONG_IMAGE_SLICE_OVERLAP, slice_img.size[0], slice_img.size[1])
                        )
                    prepared_slices.append(slice_img)

                # 计算总高度
                total_height = sum(img.size[1] for img in prepared_slices)
                max_width = max(img.size[0] for img in prepared_slices)

                # 创建新图
                new_img = Image.new('RGB', (max_width, total_height), (255, 255, 255))

                y_offset = 0
                for img in prepared_slices:
                    new_img.paste(img, (0, y_offset))
                    y_offset += img.size[1]

                # 保存
                out_path = output_images_dir / img_name
                new_img.save(out_path, 'JPEG', quality=95)
                processed_images.append(str(out_path))
                print(f"  ✅ 已重新拼接: {img_name} ({max_width}x{total_height})")

                # 清理临时文件
                for f in processed_slice_files:
                    if "processed_" in f.name:
                        f.unlink(missing_ok=True)

            except Exception as e:
                print(f"  ❌ 拼接失败: {e}")
                # 回退：使用原图
                out_path = output_images_dir / img_name
                import shutil
                shutil.copy2(img_path, out_path)
                processed_images.append(str(out_path))

    return processed_images


# ============ 主处理流程 ============

def process_draft(
    article_dir: str,
    account: str = "xingyan_shixi",
    keyword: str = None,
    digest: str = None,
    output_dir: str = None
) -> Dict:
    """
    处理草稿

    Args:
        article_dir: 原始文章目录
        account: 账号配置名称
        keyword: 关键词编号（可选，默认自动生成）
        digest: 摘要（可选，默认自动生成）
        output_dir: 输出目录（可选，默认在原目录下创建 draft/）

    Returns:
        Dict: 处理结果信息
    """
    article_dir = Path(article_dir).resolve()
    account = normalize_account(account)

    if not article_dir.exists():
        raise FileNotFoundError(f"文章目录不存在: {article_dir}")
    if account not in SUPPORTED_ACCOUNTS:
        raise ValueError(f"不支持的账号: {account}，支持: {', '.join(sorted(SUPPORTED_ACCOUNTS))}")

    # 确定输出目录
    if output_dir is None:
        output_dir = article_dir / "draft"
    else:
        output_dir = Path(output_dir).resolve()

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"📝 微信公众号草稿处理 - {get_account_author(account)}")
    print("=" * 60)
    print(f"📁 原始目录: {article_dir}")
    print(f"📁 输出目录: {output_dir}")

    # 1. 加载元数据
    print(f"\n📋 步骤 1: 加载元数据")
    metadata = load_metadata(article_dir)
    original_title = metadata.get('title', '')
    original_url = metadata.get('url', '')
    print(f"   原始标题: {original_title}")
    print(f"   原始链接: {original_url}")

    # 2. 检测文章模式
    print(f"\n🔍 步骤 2: 检测文章模式")
    mode = detect_article_mode(article_dir)
    print(f"   模式: {'长图模式' if mode == 'long_image' else '文字模式'}")

    # 3. 标题转换
    print(f"\n✏️ 步骤 3: 标题转换")
    new_title = transform_title(original_title)
    print(f"   处理后: {new_title}")

    # 4. 生成关键词
    if keyword is None:
        keyword = generate_keyword()
    print(f"\n🔑 步骤 4: 关键词编号")
    print(f"   关键词: {keyword}")

    # 5. 处理正文内容
    print(f"\n📝 步骤 5: 处理正文内容")

    if mode == "text":
        # 文字模式：读取原始 HTML 或 Markdown，删除投递方式
        html_path = article_dir / "article_original.html"
        if not html_path.exists():
            html_path = article_dir / "article.html"

        if html_path.exists():
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()

            body_content, _source_label = extract_article_content(content)
            body_content = ensure_img_srcs(body_content)

            # 移除头部标题
            body_content = re.sub(r'<h1[^>]*>.*?</h1>', '', body_content, flags=re.DOTALL | re.IGNORECASE, count=1)

            # 移除投递方式
            body_content = remove_delivery_sections_text(body_content)
            body_content = ensure_img_srcs(body_content)

        else:
            # 使用 Markdown
            md_path = article_dir / "article.md"
            with open(md_path, 'r', encoding='utf-8') as f:
                md_content = f.read()

            # 简单转换为 HTML
            body_content = f"<pre>{md_content}</pre>"

        # 处理图片：复制到输出目录
        images_dir = article_dir / "images"
        output_images_dir = output_dir / "images"
        if images_dir.exists():
            output_images_dir.mkdir(parents=True, exist_ok=True)
            import shutil
            for img_file in images_dir.iterdir():
                if img_file.suffix.lower() in IMAGE_EXTENSIONS:
                    shutil.copy2(img_file, output_images_dir / img_file.name)

    else:
        # 长图模式：处理图片
        processed_images = process_long_images(str(article_dir), str(output_dir))

        # 构建 HTML：使用处理后的图片
        body_content = ""
        for img_path in processed_images:
            img_name = Path(img_path).name
            body_content += f'<p><img src="images/{img_name}" style="width:100%;max-width:100%;display:block;margin:0;"/></p>\n'

    # 6. 生成摘要（在追加推广模板之前，确保摘要来自正文）
    if digest is None:
        digest = generate_digest(body_content)
    print(f"\n📝 步骤 6: 生成摘要")
    print(f"   摘要: {digest[:60]}...")

    # 7. 追加推广模板（检测原文是否已有推广内容）
    print(f"\n📰 步骤 7: 追加推广模板")
    config = XingyanShixiConfig()

    if has_promotion_content(body_content):
        print("   ⚠️ 检测到原文已含推广内容，跳过追加")
        promotion = ""
    else:
        promotion = load_promotion_template(account).format(keyword=keyword)
        print(f"   ✅ 已追加推广模板（关键词: {keyword}）")

    # 8. 组装最终 HTML
    print(f"\n🔧 步骤 8: 组装 HTML")
    if promotion:
        full_html = f"""<div class="draft-content">
{body_content}
<p><br/></p>
<p><br/></p>
{promotion}
</div>"""
    else:
        full_html = f"""<div class="draft-content">
{body_content}
</div>"""
    full_html = ensure_img_srcs(full_html)

    # 9. 保存文件
    print(f"\n💾 步骤 9: 保存文件")

    # draft.html
    draft_html_path = output_dir / "draft.html"
    with open(draft_html_path, 'w', encoding='utf-8') as f:
        f.write(full_html)
    print(f"   ✅ draft.html: {draft_html_path}")

    # draft.json
    draft_json = {
        "title": new_title,
        "digest": digest,
        "keyword": keyword,
        "author": get_account_author(account),
        "content_source_url": original_url,
        "mode": mode,
        "original_title": original_title,
        "processed_at": datetime.now().isoformat(),
        "account": account,
    }

    draft_json_path = output_dir / "draft.json"
    with open(draft_json_path, 'w', encoding='utf-8') as f:
        json.dump(draft_json, f, ensure_ascii=False, indent=2)
    print(f"   ✅ draft.json: {draft_json_path}")

    print(f"\n" + "=" * 60)
    print(f"✅ 处理完成！")
    print(f"=" * 60)
    print(f"标题: {new_title}")
    print(f"关键词: {keyword}")
    print(f"摘要: {digest[:50]}...")
    print(f"模式: {mode}")
    print(f"输出: {output_dir}")

    return draft_json


def main():
    parser = argparse.ArgumentParser(
        description='微信公众号草稿处理脚本 - 行研实习账号',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 基本用法
    python process_draft.py --article-dir ~/.hermes/output/85c8245b/

    # 指定关键词
    python process_draft.py --article-dir ~/.hermes/output/85c8245b/ --keyword 0427

    # 指定摘要
    python process_draft.py --article-dir ~/.hermes/output/85c8245b/ --digest "这是一个摘要..."

    # 指定输出目录
    python process_draft.py --article-dir ~/.hermes/output/85c8245b/ --output-dir /tmp/draft_output/
        """
    )

    parser.add_argument('--article-dir', '-d', required=True,
                       help='原始文章目录路径')
    parser.add_argument('--account', '-a', default='xingyan_shixi',
                       help='账号配置名称（默认: xingyan_shixi）')
    parser.add_argument('--keyword', '-k',
                       help='关键词编号（默认自动生成 MMdd 格式）')
    parser.add_argument('--digest',
                       help='文章摘要（默认自动提取）')
    parser.add_argument('--output-dir', '-o',
                       help='输出目录（默认在原目录下创建 draft/）')

    args = parser.parse_args()

    try:
        result = process_draft(
            article_dir=args.article_dir,
            account=args.account,
            keyword=args.keyword,
            digest=args.digest,
            output_dir=args.output_dir
        )

        # 输出结果供上传脚本使用
        print(f"\n[DRAFT_RESULT]")
        print(json.dumps(result, ensure_ascii=False))
        print(f"[END_DRAFT_RESULT]")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
