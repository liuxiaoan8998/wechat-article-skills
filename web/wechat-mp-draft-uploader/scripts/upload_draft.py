#!/usr/bin/env python3
"""
微信公众号草稿上传工具
基于简立制作 API 平台

Usage:
    python upload_draft.py --article-dir "~/.hermes/output/文章标题/" --cover "cover.jpg"
    python upload_draft.py --title "标题" --content "content.html" --cover "cover.jpg"
"""

import argparse
import os
import sys
import json
import requests
from pathlib import Path
from typing import List, Dict, Optional

# API 配置
BASE_URL = "https://mp.jianlizhizuo.cn/v1"


class WechatDraftUploader:
    """微信公众号草稿上传器"""
    
    def __init__(self, api_key: str = None, appid: str = None):
        """
        初始化上传器
        
        Args:
            api_key: 简立制作平台 API Key，默认从环境变量读取
            appid: 公众号 AppID，默认从环境变量读取
        """
        self.api_key = api_key or os.getenv("JIANLIZHIZUO_API_KEY")
        self.appid = appid or os.getenv("WECHAT_APPID")
        
        if not self.api_key:
            raise ValueError("缺少 API Key，请设置 JIANLIZHIZUO_API_KEY 环境变量")
        if not self.appid:
            raise ValueError("缺少 AppID，请设置 WECHAT_APPID 环境变量")
    
    def _headers(self, content_type: str = "application/json") -> Dict:
        """生成请求头"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if content_type:
            headers["Content-Type"] = content_type
        return headers
    
    def upload_material(self, file_path: str, material_type: str = "IMAGE", name: str = None, description: str = None) -> dict:
        """
        上传永久素材
        
        Args:
            file_path: 文件本地路径
            material_type: 素材类型 IMAGE/VOICE/VIDEO/THUMB
            name: 素材名称
            description: 视频素材简介（VIDEO类型时使用）
            
        Returns:
            dict: 包含 mediaId, url(图片类型), name, type
        """
        url = f"{BASE_URL}/accounts/{self.appid}/materials"
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 准备表单数据
        data = {
            'type': material_type,
            'name': name or os.path.basename(file_path)
        }
        if description and material_type == "VIDEO":
            data['description'] = description
        
        with open(file_path, 'rb') as f:
            files = {'media': (os.path.basename(file_path), f, 'application/octet-stream')}
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.post(url, data=data, files=files, headers=headers)
        
        result = response.json()
        if result.get('code') == 0:
            media_id = result['data']['mediaId']
            material_url = result['data'].get('url', '')
            print(f"✅ 素材上传成功: {media_id}")
            if material_url:
                print(f"   URL: {material_url}")
            return result['data']
        else:
            raise Exception(f"素材上传失败: {result.get('msg', '未知错误')}")
    
    def upload_cover_image(self, image_path: str, name: str = "封面图片") -> str:
        """
        上传封面图片，返回 thumbMediaId
        使用 upload_material API 获取永久素材 mediaId
        
        Args:
            image_path: 封面图片本地路径
            name: 素材名称
            
        Returns:
            str: thumbMediaId (即 mediaId)
        """
        result = self.upload_material(image_path, material_type="IMAGE", name=name)
        return result['mediaId']
    
    def upload_content_image(self, image_path: str, name: str = "正文图片") -> str:
        """
        上传正文图片，返回永久 URL
        使用 upload_material API 获取图片 URL
        
        Args:
            image_path: 图片本地路径
            name: 素材名称
            
        Returns:
            str: 图片永久 URL
        """
        result = self.upload_material(image_path, material_type="IMAGE", name=name)
        return result['url']
    
    def create_draft(self, articles: List[Dict]) -> Dict:
        """
        创建草稿
        
        Args:
            articles: 文章列表，每项包含:
                - title: 标题（必填）
                - content: 正文 HTML（必填）
                - thumbMediaId: 封面素材ID（article_type=news 时必填）
                - articleType: 文章类型，默认 news
                - author: 作者
                - digest: 摘要
                - contentSourceUrl: 原文链接
                - needOpenComment: 是否开启评论，0/1
                
        Returns:
            Dict: 包含 mediaId, title, articleCount
        """
        url = f"{BASE_URL}/accounts/{self.appid}/drafts"
        
        # 验证文章数量
        if len(articles) > 8:
            raise ValueError("多图文最多支持8篇文章")
        
        # 验证必填字段
        for i, article in enumerate(articles):
            if not article.get('title'):
                raise ValueError(f"第{i+1}篇文章缺少标题")
            if not article.get('content'):
                raise ValueError(f"第{i+1}篇文章缺少正文")
            if article.get('articleType', 'news') == 'news' and not article.get('thumbMediaId'):
                raise ValueError(f"第{i+1}篇文章缺少封面 thumbMediaId")
        
        payload = {"articles": articles}
        response = requests.post(url, json=payload, headers=self._headers())
        
        result = response.json()
        if result.get('code') == 0:
            data = result['data']
            print(f"✅ 草稿创建成功!")
            print(f"   MediaID: {data['mediaId']}")
            print(f"   标题: {data['title']}")
            print(f"   文章数: {data['articleCount']}")
            return data
        else:
            raise Exception(f"创建草稿失败: {result.get('msg', '未知错误')}")
    
    def upload_article_from_directory(self, article_dir: str, cover_image: str = None, 
                                      author: str = None, digest: str = None,
                                      content_source_url: str = None) -> Dict:
        """
        从文章目录上传单篇文章到草稿箱
        
        Args:
            article_dir: 文章输出目录路径（如 ~/.hermes/output/文章标题/）
            cover_image: 封面图片文件名（默认使用 images/ 目录下的第一张图片）
            author: 作者名称
            digest: 文章摘要
            content_source_url: 原文链接
            
        Returns:
            Dict: 草稿信息
        """
        article_path = Path(article_dir).expanduser()
        
        if not article_path.exists():
            raise FileNotFoundError(f"文章目录不存在: {article_dir}")
        
        # 读取文章标题
        metadata_path = article_path / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            title = metadata.get('title', '无标题')
        else:
            title = article_path.name
        
        # 读取正文 HTML（优先使用原始微信HTML，若不存在则使用article.html）
        html_path = article_path / "article_original.html"
        if not html_path.exists():
            html_path = article_path / "article.html"
        if html_path.exists():
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            # 尝试从 markdown 转换
            md_path = article_path / "article.md"
            if md_path.exists():
                with open(md_path, 'r', encoding='utf-8') as f:
                    md_content = f.read()
                # 简单转换为 HTML（实际使用时需要更好的转换）
                content = f"<pre>{md_content}</pre>"
            else:
                raise FileNotFoundError(f"找不到文章正文: {article_dir}")
        
        # 处理封面图片
        images_dir = article_path / "images"
        if cover_image:
            cover_path = images_dir / cover_image
        elif images_dir.exists():
            # 使用第一张图片作为封面
            image_files = list(images_dir.glob("img_*"))
            if image_files:
                cover_path = image_files[0]
            else:
                raise FileNotFoundError(f"目录中没有图片: {images_dir}")
        else:
            raise FileNotFoundError(f"图片目录不存在: {images_dir}")
        
        # 上传封面
        thumb_media_id = self.upload_cover_image(str(cover_path))
        
        # 组装文章数据
        article = {
            "title": title[:64],  # 限制64字符
            "content": content,
            "thumbMediaId": thumb_media_id,
            "articleType": "news",
            "author": author or "",
            "digest": digest or "",
            "contentSourceUrl": content_source_url or "",
            "needOpenComment": 1
        }
        
        # 创建草稿
        return self.create_draft([article])


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description='上传文章到微信公众号草稿箱')
    parser.add_argument('--article-dir', '-d', help='文章目录路径')
    parser.add_argument('--title', '-t', help='文章标题')
    parser.add_argument('--content', '-c', help='正文 HTML 文件路径')
    parser.add_argument('--cover', '-i', help='封面图片路径')
    parser.add_argument('--author', '-a', help='作者名称')
    parser.add_argument('--digest', help='文章摘要')
    parser.add_argument('--source-url', '-s', help='原文链接')
    parser.add_argument('--api-key', help='API Key（默认从环境变量读取）')
    parser.add_argument('--appid', help='公众号 AppID（默认从环境变量读取）')
    
    args = parser.parse_args()
    
    try:
        uploader = WechatDraftUploader(api_key=args.api_key, appid=args.appid)
        
        if args.article_dir:
            # 从目录上传
            result = uploader.upload_article_from_directory(
                article_dir=args.article_dir,
                cover_image=args.cover,
                author=args.author,
                digest=args.digest,
                content_source_url=args.source_url
            )
        elif args.title and args.content:
            # 从指定文件上传
            with open(args.content, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not args.cover:
                print("错误: 必须指定封面图片 --cover")
                sys.exit(1)
            
            thumb_media_id = uploader.upload_cover_image(args.cover)
            
            article = {
                "title": args.title,
                "content": content,
                "thumbMediaId": thumb_media_id,
                "author": args.author or "",
                "digest": args.digest or "",
                "contentSourceUrl": args.source_url or "",
                "needOpenComment": 1
            }
            
            result = uploader.create_draft([article])
        else:
            parser.print_help()
            sys.exit(1)
        
        print(f"\n草稿 MediaID: {result['mediaId']}")
        print(f"预览链接: https://mp.weixin.qq.com/s/{result['mediaId']}")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
