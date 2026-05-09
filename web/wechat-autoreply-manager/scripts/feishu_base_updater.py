#!/usr/bin/env python3
"""
飞书Base更新模块
用于更新文章状态等字段
"""

import os
import json
import subprocess
from typing import Optional

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


class FeishuBaseUpdater:
    """飞书Base更新器"""
    
    def __init__(self, base_token: str = None):
        self.base_token = base_token or os.getenv('FEISHU_BASE_TOKEN')
        self.table_id = os.getenv('FEISHU_ARTICLE_TABLE_ID')  # 文章素材表
    
    def update_record(self, record_id: str, fields: dict) -> dict:
        """
        更新Base记录字段
        
        Args:
            record_id: 飞书记录ID (如 recvhG4ofP69H5)
            fields: 要更新的字段字典，如 {"文章状态": "已配置自动回复"}
            
        Returns:
            {'success': True/False, 'data': {...}, 'error': '...'}
        """
        # 使用 +record-upsert 命令，--json参数
        import json
        json_str = json.dumps(fields, ensure_ascii=False)
        
        cmd = f"lark-cli base +record-upsert --base-token {self.base_token} --table-id {self.table_id} --record-id {record_id} --json '{json_str}' --as bot"
        
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': f'命令执行失败: {result.stderr}'
                }
            
            # 解析输出
            try:
                response = json.loads(result.stdout)
                if response.get('ok'):
                    return {
                        'success': True,
                        'data': response.get('data', {})
                    }
                else:
                    return {
                        'success': False,
                        'error': response.get('error', '未知错误')
                    }
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'error': f'无法解析响应: {result.stdout[:500]}'
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': '命令执行超时'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_article_status(self, record_id: str, status: str) -> dict:
        """
        更新文章状态
        
        Args:
            record_id: 飞书记录ID
            status: 新状态，如 "已配置自动回复"
            
        Returns:
            更新结果
        """
        return self.update_record(record_id, {'文章状态': status})
    
    def query_record(self, record_id: str) -> dict:
        """
        查询记录详情
        
        Args:
            record_id: 飞书记录ID
            
        Returns:
            {'success': True/False, 'data': {...}, 'error': '...'}
        """
        cmd = f'lark-cli base +record-get --base-token {self.base_token} --table-id {self.table_id} --record-id {record_id} --as bot'
        
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': f'命令执行失败: {result.stderr}'
                }
            
            try:
                response = json.loads(result.stdout)
                if response.get('ok'):
                    return {
                        'success': True,
                        'data': response.get('data', {})
                    }
                else:
                    return {
                        'success': False,
                        'error': response.get('error', '未知错误')
                    }
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'error': f'无法解析响应: {result.stdout[:500]}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


if __name__ == '__main__':
    # 测试
    updater = FeishuBaseUpdater()
    
    # 测试查询（需要替换为实际的record_id）
    # result = updater.query_record('recvhG4ofP69H5')
    # print(json.dumps(result, ensure_ascii=False, indent=2))
    
    print("飞书Base更新模块")
    print("用法：")
    print("  from feishu_base_updater import FeishuBaseUpdater")
    print("  updater = FeishuBaseUpdater()")
    print("  updater.update_article_status('record_id', '已配置自动回复')")
