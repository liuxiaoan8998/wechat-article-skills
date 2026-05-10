# 微信公众号文章提取标准方案

## 1. 标准工具

**工具名称**: wechat-article-for-ai  
**GitHub**: https://github.com/bzd6661/wechat-article-for-ai  
**安装路径**: `/tmp/wechat-article-for-ai`

### 1.1 安装

```bash
git clone https://github.com/bzd6661/wechat-article-for-ai.git
cd wechat-article-for-ai
pip install -r requirements.txt
```

### 1.2 基本使用

```bash
# 单篇文章提取
python main.py "https://mp.weixin.qq.com/s/ARTICLE_ID" -o ./output

# 带详细日志
python main.py "https://mp.weixin.qq.com/s/ARTICLE_ID" -o ./output -v

# 强制覆盖已存在输出
python main.py "https://mp.weixin.qq.com/s/ARTICLE_ID" -o ./output --force
```

---

## 2. 输出规范

### 2.1 输出文件结构

工具提取后，必须整理为以下标准结构：

```
~/.hermes/output/{article_title}/
├── article.md              # Markdown格式（含本地图片路径）
├── article.html            # HTML查看器（优先展示原图）
├── metadata.json           # 结构化元数据
└── images/                 # 下载的所有图片
    ├── img_001.jpg
    ├── img_002.png
    └── ...
```

### 2.2 各文件要求

#### article.md（必须）

- 使用工具生成的 Markdown 文件
- 包含 YAML frontmatter（标题、作者、日期、来源）
- 图片引用使用本地路径：`images/img_xxx.jpg`
- 保留原始内容和格式

示例：
```markdown
---
title: "瑞幸咖啡2026春季校园招聘正式启动"
author: "瑞幸咖啡招聘"
date: "2026-04-10 18:08:20"
source: "https://mp.weixin.qq.com/s/..."
---

# 瑞幸咖啡2026春季校园招聘正式启动

![Image](images/img_001.jpg)
![Image](images/img_002.jpg)
...
```

#### article.html（必须）

- **优先展示原图**，保持专业设计效果
- 下方提供结构化文字内容
- 使用本地图片路径
- 响应式设计，适配不同屏幕

模板结构：
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        .container { max-width: 800px; margin: 0 auto; }
        .original-image { width: 100%; display: block; }
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <div class="meta">Author · Date</div>
        
        <!-- Original images -->
        <img src="images/img_001.jpg" class="original-image">
        <img src="images/img_002.jpg" class="original-image">
        ...
        
        <!-- Structured content -->
        <div class="content">
            <h2>Key Information</h2>
            <!-- Extracted text -->
        </div>
    </div>
</body>
</html>
```

#### metadata.json（必须）

结构化元数据，便于程序处理：

```json
{
  "url": "https://mp.weixin.qq.com/s/...",
  "title": "文章标题",
  "author": "公众号名称",
  "published_at": "2026-04-10 18:08:20",
  "source": "https://mp.weixin.qq.com/s/...",
  "extraction_method": "wechat-article-for-ai",
  "extraction_time": "2026-04-13 18:28:00",
  "image_count": 40,
  "images": [
    "images/img_001.jpg",
    "images/img_002.png",
    ...
  ]
}
```

#### images/ 文件夹（必须）

- 包含工具下载的所有图片
- 保持原始文件名（img_001.jpg, img_002.png 等）
- 不得遗漏任何图片
- 图片格式保持原样（jpg, png, gif 等）

---

## 3. 完整工作流程

### 3.1 提取文章

```python
import os
import json
import shutil

# 配置
article_url = "https://mp.weixin.qq.com/s/..."
article_title = "文章标题（从YAML frontmatter获取）"
output_base = f"~/.hermes/output/{article_title}"
tool_output = f"{output_base}/tool_output"

# 步骤1：使用工具提取
terminal(command=f'''
    cd /tmp/wechat-article-for-ai && \
    python main.py "{article_url}" \
        -o {tool_output} \
        --force \
        -v
''')

# 步骤2：获取工具生成的文件夹名
# 工具会创建：tool_output/<文章标题>/
tool_generated_dir = os.path.join(tool_output, article_title)

# 步骤3：复制文件到标准位置
# 创建标准目录结构
os.makedirs(output_base, exist_ok=True)

# 复制 Markdown
shutil.copy(
    os.path.join(tool_generated_dir, f"{article_title}.md"),
    os.path.join(output_base, "article.md")
)

# 复制图片文件夹
shutil.copytree(
    os.path.join(tool_generated_dir, "images"),
    os.path.join(output_base, "images"),
    dirs_exist_ok=True
)

# 步骤4：创建 HTML 查看器
create_html_viewer(output_base, article_title)

# 步骤5：创建 metadata.json
create_metadata(output_base, article_url, article_title)

# 步骤6：清理临时文件
shutil.rmtree(tool_output)

print(f"✅ 提取完成：{output_base}")
```

### 3.2 创建 HTML 查看器

```python
def create_html_viewer(output_dir, title):
    """创建HTML查看器，优先展示原图"""
    
    # 读取Markdown获取元数据
    md_path = os.path.join(output_dir, "article.md")
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()
    
    # 获取图片列表
    images_dir = os.path.join(output_dir, "images")
    images = sorted([f for f in os.listdir(images_dir) if f.startswith("img_")])
    
    # 生成HTML
    html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        .container {{ max-width: 800px; margin: 0 auto; }}
        .original-image {{ width: 100%; display: block; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <div class="meta">提取自微信公众号</div>
        
        <div class="image-gallery">
'''
    
    # 添加所有图片
    for img in images:
        html_content += f'            <img src="images/{img}" class="original-image">\n'
    
    html_content += '''
        </div>
        
        <div style="text-align: center; padding: 30px; color: #666;">
            <p>数据来源：微信公众号</p>
            <p>原文链接：见 metadata.json</p>
        </div>
    </div>
</body>
</html>
'''
    
    # 保存HTML
    html_path = os.path.join(output_dir, "article.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"✓ 创建HTML: {html_path}")
```

### 3.3 创建 Metadata

```python
def create_metadata(output_dir, url, title):
    """创建metadata.json"""
    
    import yaml
    
    # 从Markdown读取YAML frontmatter
    md_path = os.path.join(output_dir, "article.md")
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 解析YAML frontmatter
    if content.startswith('---'):
        _, frontmatter, _ = content.split('---', 2)
        metadata = yaml.safe_load(frontmatter)
    else:
        metadata = {}
    
    # 获取图片列表
    images_dir = os.path.join(output_dir, "images")
    images = sorted([f for f in os.listdir(images_dir) if f.startswith("img_")])
    
    # 构建完整metadata
    full_metadata = {
        "url": url,
        "title": metadata.get("title", title),
        "author": metadata.get("author", ""),
        "published_at": metadata.get("date", ""),
        "source": metadata.get("source", url),
        "extraction_method": "wechat-article-for-ai",
        "extraction_time": datetime.now().isoformat(),
        "image_count": len(images),
        "images": [f"images/{img}" for img in images]
    }
    
    # 保存
    metadata_path = os.path.join(output_dir, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(full_metadata, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 创建Metadata: {metadata_path}")
```

---

## 4. 质量检查清单

提取完成后，必须检查以下项目：

### 4.1 文件完整性

- [ ] `article.md` 存在且不为空
- [ ] `article.html` 存在且可正常打开
- [ ] `metadata.json` 存在且格式正确
- [ ] `images/` 文件夹存在
- [ ] 图片数量 ≥ 10 张（典型值）

### 4.2 内容完整性

- [ ] Markdown 包含 YAML frontmatter
- [ ] 图片引用使用本地路径
- [ ] HTML 能正常显示所有图片
- [ ] 无损坏的图片文件

### 4.3 格式正确性

- [ ] JSON 格式有效
- [ ] HTML 无语法错误
- [ ] Markdown 渲染正常
- [ ] 图片路径正确

---

## 5. 常见问题处理

### 5.1 工具安装问题

**问题**: `pip install` 失败  
**解决**: 
```bash
# 使用Python 3.8+
python3 --version

# 使用虚拟环境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5.2 验证码问题

**问题**: 提取时遇到验证码  
**解决**:
```bash
# 使用 --no-headless 手动解决
python main.py "URL" -o ./output --no-headless
```

### 5.3 图片下载失败

**问题**: 部分图片下载失败  
**解决**:
```bash
# 使用 --force 重新运行
python main.py "URL" -o ./output --force
```

### 5.4 内容为空

**问题**: 提取的内容为空  
**解决**:
- 等待几分钟后重试（微信限流）
- 检查URL是否正确
- 使用 `--no-headless` 查看浏览器状态

---

## 6. 最佳实践

### 6.1 始终使用工具

❌ **不要** 使用 browser_scroll + vision_analyze  
✅ **必须** 使用 wechat-article-for-ai 工具

### 6.2 优先展示原图

❌ **不要** 只用CSS重设计  
✅ **必须** 在HTML中嵌入原图

### 6.3 下载所有图片

❌ **不要** 保留远程URL  
✅ **必须** 下载到本地 images/ 文件夹

### 6.4 提供结构化内容

✅ **必须** 同时提供 Markdown（便于搜索）  
✅ **必须** 提供HTML（便于查看）  
✅ **必须** 提供metadata（便于程序处理）

---

## 7. 更新记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-04-13 | v2.0 | 确定 wechat-article-for-ai 为标准方案 |

---

## 8. 参考资源

- **工具仓库**: https://github.com/bzd6661/wechat-article-for-ai
- **标准文档**: `STANDARD.md`（本文档）
- **快速参考**: `SKILL.md`
- **对比分析**: `~/.hermes/output/方案对比分析报告.md`
- **示例输出**: `~/.hermes/output/{article_id}/` (article_id 为8位UUID)

---

**此文档为微信文章提取的标准操作规范，所有相关任务必须遵循。**
