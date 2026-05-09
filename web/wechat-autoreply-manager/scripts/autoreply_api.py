#!/usr/bin/env python3
"""
简立制作自动回复 API 封装
"""

import os
import json
import requests
from typing import List, Dict, Optional


class WechatAutoreplyAPI:
    """微信公众号自动回复 API 客户端"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('JIANLIZHIZUO_API_KEY')
        self.base_url = 'https://mp.jianlizhizuo.cn/v1'
        
        if not self.api_key:
            raise ValueError('JIANLIZHIZUO_API_KEY not set')
    
    def _headers(self) -> dict:
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def list_accounts(self) -> dict:
        """
        获取所有授权的公众号列表
        
        Returns:
            {
                'code': 0,
                'data': {
                    'list': [
                        {'appid': 'xxx', 'name': '公众号名称', ...},
                        ...
                    ],
                    'total': 3
                }
            }
        """
        url = f'{self.base_url}/accounts'
        response = requests.get(url, headers=self._headers())
        return response.json()
    
    def find_account_by_name(self, name_pattern: str) -> Optional[dict]:
        """
        根据名称查找公众号
        
        Args:
            name_pattern: 名称关键词（不区分大小写）
            
        Returns:
            账号信息 dict 或 None
        """
        result = self.list_accounts()
        
        if result.get('code') != 0:
            return None
        
        accounts = result.get('data', {}).get('list', [])
        
        for account in accounts:
            account_name = account.get('name', '').lower()
            appid = account.get('appid', '').lower()
            if name_pattern.lower() in account_name or name_pattern.lower() in appid:
                return account
        
        return None
    
    def _url(self, appid: str, endpoint: str = '') -> str:
        """构建 API URL"""
        if endpoint:
            return f'{self.base_url}/accounts/{appid}/autoreplies/keywords{endpoint}'
        return f'{self.base_url}/accounts/{appid}/autoreplies/keywords'
    
    def list_rules(self, appid: str, page: int = 1, page_size: int = 20) -> dict:
        """
        获取关键词自动回复规则列表
        
        Args:
            appid: 公众号 AppID
            page: 页码
            page_size: 每页数量
            
        Returns:
            {
                'code': 0,
                'data': {
                    'list': [...],
                    'pagination': {...}
                }
            }
        """
        url = self._url(appid)
        params = {'page': page, 'pageSize': page_size}
        
        response = requests.get(url, params=params, headers=self._headers())
        return response.json()
    
    def get_rule_by_keyword(self, appid: str, keyword: str) -> Optional[dict]:
        """
        根据关键词查找规则
        
        Args:
            appid: 公众号 AppID
            keyword: 关键词
            
        Returns:
            规则 dict 或 None
        """
        result = self.list_rules(appid, page_size=100)
        
        if result.get('code') != 0:
            return None
        
        rules = result.get('data', {}).get('list', [])
        
        for rule in rules:
            if rule.get('keyword') == keyword:
                return rule
        
        return None
    
    def create_text_rule(
        self,
        appid: str,
        keyword: str,
        reply_content: str,
        rule_name: str = None,
        match_mode: str = 'EXACT'
    ) -> dict:
        """
        创建文字回复规则
        
        Args:
            appid: 公众号 AppID
            keyword: 触发关键词
            reply_content: 回复文字内容
            rule_name: 规则名称（默认使用关键词）
            match_mode: EXACT(精确匹配) / FUZZY(模糊匹配)
            
        Returns:
            {'code': 0, 'data': {'ruleId': 'xxx', ...}}
        """
        url = self._url(appid)
        
        payload = {
            'ruleName': rule_name or f'自动回复-{keyword}',
            'keyword': keyword,
            'matchMode': match_mode,
            'replyType': 'TEXT',
            'replyContent': [
                {'type': 'TEXT', 'content': reply_content}
            ],
            'isActive': True
        }
        
        response = requests.post(url, json=payload, headers=self._headers())
        return response.json()
    
    def create_image_rule(
        self,
        appid: str,
        keyword: str,
        media_id: str,
        rule_name: str = None,
        match_mode: str = 'EXACT'
    ) -> dict:
        """
        创建图片回复规则
        
        Args:
            appid: 公众号 AppID
            keyword: 触发关键词
            media_id: 图片素材 MediaID
            rule_name: 规则名称
            match_mode: EXACT(精确匹配) / FUZZY(模糊匹配)
            
        Returns:
            {'code': 0, 'data': {'id': 'xxx', ...}}
        """
        url = self._url(appid)
        
        payload = {
            'ruleName': rule_name or f'自动回复-{keyword}',
            'keyword': keyword,
            'matchMode': match_mode,
            'replyType': 'IMAGE',
            'replyContent': [
                {'type': 'IMAGE', 'mediaId': media_id}  # 注意：使用mediaId字段（不是content）
            ]
        }
        
        response = requests.post(url, json=payload, headers=self._headers())
        return response.json()
    
    def update_text_rule(
        self,
        appid: str,
        rule_id: str,
        new_content: str,
        append: bool = True
    ) -> dict:
        """
        更新文字回复规则（追加或替换）
        
        Args:
            appid: 公众号 AppID
            rule_id: 规则ID
            new_content: 新内容
            append: True=追加, False=替换
            
        Returns:
            {'code': 0, 'data': {...}}
        """
        # 先获取现有规则
        url = f'{self._url(appid)}/{rule_id}'
        
        # 获取现有内容
        list_result = self.list_rules(appid, page_size=100)
        existing_rule = None
        
        if list_result.get('code') == 0:
            for rule in list_result.get('data', {}).get('list', []):
                if rule.get('ruleId') == rule_id:
                    existing_rule = rule
                    break
        
        if not existing_rule:
            return {'code': -1, 'message': '规则不存在'}
        
        # 构建新内容
        if append:
            existing_content = existing_rule.get('replyContent', [])
            if existing_content and len(existing_content) > 0:
                old_text = existing_content[0].get('content', '')
                # 紧凑格式：使用双换行（保留一个空行），去掉分隔线
                combined_content = f"{old_text}\n\n{new_content}"
            else:
                combined_content = new_content
        else:
            combined_content = new_content
        
        payload = {
            'ruleName': existing_rule.get('ruleName'),
            'keyword': existing_rule.get('keyword'),
            'matchMode': existing_rule.get('matchMode'),
            'replyType': 'TEXT',
            'replyContent': [
                {'type': 'TEXT', 'content': combined_content}
            ],
            'isActive': True
        }
        
        response = requests.put(url, json=payload, headers=self._headers())
        return response.json()
    
    def delete_rule(self, appid: str, rule_id: str) -> dict:
        """
        删除规则
        
        Args:
            appid: 公众号 AppID
            rule_id: 规则ID
            
        Returns:
            {'code': 0, 'data': {...}}
        """
        url = f'{self._url(appid)}/{rule_id}'
        # 删除请求不能带 Content-Type: application/json，否则服务端报错
        headers = {'Authorization': f'Bearer {self.api_key}'}
        response = requests.delete(url, headers=headers)
        return response.json()
    
    def upload_image(self, appid: str, image_path: str, name: str = None) -> dict:
        """
        上传图片素材
        
        Args:
            appid: 公众号 AppID
            image_path: 本地图片路径
            name: 素材名称（默认使用文件名）
            
        Returns:
            {
                'code': 0, 
                'data': {
                    'mediaId': 'xxx',  # 注意：返回的是mediaId（驼峰命名）
                    'url': 'xxx',
                    'name': 'xxx',
                    'type': 'IMAGE'
                }
            }
        """
        url = f'{self.base_url}/accounts/{appid}/materials'
        
        with open(image_path, 'rb') as f:
            files = {'media': f}
            data = {
                'type': 'IMAGE', 
                'name': name or os.path.basename(image_path)
            }
            headers = {'Authorization': f'Bearer {self.api_key}'}
            
            response = requests.post(url, files=files, data=data, headers=headers)
        
        return response.json()


if __name__ == '__main__':
    # 测试
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python autoreply_api.py <appid>")
        sys.exit(1)
    
    appid = sys.argv[1]
    api = WechatAutoreplyAPI()
    
    # 测试列出规则
    result = api.list_rules(appid)
    print(f"规则列表: {json.dumps(result, indent=2, ensure_ascii=False)}")
