#!/usr/bin/env python3
"""
测试自动回复询问流程
"""

import sys
import os

# 添加脚本目录到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from delivery_classifier import classify_delivery
from company_extractor import extract_and_shorten

# 测试数据
test_cases = [
    {
        'title': '腾讯2026校园招聘正式启动',
        'delivery': '发送简历至 campus@tencent.com，邮件主题注明"姓名-岗位-学校"',
    },
    {
        'title': '字节跳动2026届春季校园招聘',
        'delivery': '扫码关注"字节跳动招聘"公众号投递',
    },
    {
        'title': '阿里巴巴实习生招聘',
        'delivery': '添加微信：alibaba-campus2026',
    },
    {
        'title': '美团2026届北斗计划',
        'delivery': 'https://campus.meituan.com',
    },
]

print("="*60)
print("自动回复规则创建测试")
print("="*60)

for case in test_cases:
    title = case['title']
    delivery = case['delivery']
    
    print(f"\n📄 文章：《{title}》")
    print(f"📮 投递方式：{delivery}")
    
    # 分类
    delivery_info = classify_delivery(delivery)
    is_image = delivery_info['type'] == 'image'
    
    # 提取企业简称
    company_short = extract_and_shorten(title)
    
    print(f"\n   分类：{'图片' if is_image else '文字'}投递")
    print(f"   企业简称：{company_short}")
    
    if is_image:
        print(f"   建议关键词：{company_short}（企业简称）")
        print(f"   回复类型：图片")
    else:
        import datetime
        today_keyword = datetime.datetime.now().strftime("%m%d")
        print(f"   建议关键词：{today_keyword}（日期）")
        print(f"   回复内容：")
        print(f"   {company_short}")
        print(f"   投递方式：{delivery}")
    
    print("-"*60)

print("\n✅ 测试完成")
