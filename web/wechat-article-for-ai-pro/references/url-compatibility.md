# URL兼容性说明

## 支持的URL格式

### 标准短链接（推荐）
```
https://mp.weixin.qq.com/s/xxxxx
https://mp.weixin.qq.com/s?__biz=xxxxx&mid=xxxxx&idx=1&sn=xxxxx
```

### 旧版带参数链接（v2.0.3+支持）
```
https://mp.weixin.qq.com/s?__biz=MzU4MTg1NjA3MQ==&mid=2247483658&idx=1&sn=abc123
```

### 不支持的格式
- 二维码图片（需手动提取链接）
- 复制到浏览器的链接（可能包含跟踪参数）

## 处理方式
- v2.0.3更新了URL正则匹配，支持带参数的URL
- 如果URL被处理成空，会提示"未能提取有效的文章URL"
