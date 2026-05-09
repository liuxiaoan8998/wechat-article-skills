# 原始HTML过大问题与解决方案

## 问题描述
- `article_original.html` 含有所有图片的base64编码，大小达3.7MB
- 上传到公众号草稿箱时因文件过大而失败

## 解决方案（v2.0实现）
从原始HTML中提取 `js_content` 部分生成精简HTML：
- 大小从 3.7MB 降至 ~17KB
- 保留完整文章格式和图片链接
- 去除不必要的外联资源和脚本

## 文件用途
| 文件 | 用途 |
|------|------|
| article_original.html | 保留完整原始数据，用于添加自定义头部或模板 |
| article.html | 上传草稿箱使用（精简版） |
| article_viewer.html | 本地查看（仅标题+图片） |
