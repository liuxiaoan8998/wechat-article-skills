# WeChat Article Extraction Pro - 参考文档

## 项目地址
- GitHub: https://github.com/liuxiaoan8998/wechat-article-for-ai-pro
- 本地路径: /tmp/wechat-article-for-ai-pro

## 安装步骤

### 1. 克隆项目（已自动完成）
```bash
cd /tmp && rm -rf wechat-article-for-ai-pro
git clone https://github.com/liuxiaoan8998/wechat-article-for-ai-pro.git
```

### 2. 运行安装脚本
```bash
bash ~/.hermes/skills/web/wechat-article-extraction-pro/scripts/setup.sh
```

### 3. 手动安装（备用）
```bash
cd /tmp/wechat-article-for-ai-pro
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 依赖清单
- playwright (浏览器自动化)
- beautifulsoup4 (HTML解析)
- markdownify (Markdown转换)
- rapidocr-onnxruntime (OCR识别)
- pillow (图片处理)
- requests (HTTP请求)
- opencv-python (二维码识别，v1.7+)

## 二维码识别功能 (v1.7+)

工具现已支持自动识别图片中的二维码内容，包括：
- 招聘/报名链接（自动标记）
- 普通URL链接
- 联系方式（电话、邮箱）
- 纯文本内容

### 技术实现
- **引擎**: OpenCV QRCodeDetector（无需系统依赖）
- **备选**: pyzbar（如系统已安装zbar库）
- **智能分类**: 自动识别招聘相关链接并标记

### 输出示例
```markdown
#### 图片: img_002.png

**状态**: [普通图片 400x400]

[No text detected]

**二维码识别**:
🔗 **链接**: https://rlsbt.zj.gov.cn/...
```

## 使用方式

### 基础用法
```bash
cd /tmp/wechat-article-for-ai-pro
source venv/bin/activate
python main.py "https://mp.weixin.qq.com/s/xxxxx"
```

### 输出文件
- `article.md` - 基础Markdown
- `article.html` - HTML格式
- `article-ocr.md` - OCR结果（需Hermes回填第三部分）
- `metadata.json` - 元数据
- `images/` - 原始图片
- `slices/` - 长图切片

## 故障排除

### 问题1: OCR识别失败
- 检查rapidocr是否安装: `pip show rapidocr-onnxruntime`
- 检查图片格式: 支持PNG/JPG，RGBA格式已自动转换

### 问题2: 浏览器启动失败
- 安装Playwright浏览器: `playwright install chromium`
- 或使用Camoufox（需单独安装）

### 问题3: 目录被误删
- 重新运行setup.sh脚本
- 或从GitHub重新克隆

### 问题4: 二维码识别失败
- 检查opencv是否安装: `pip show opencv-python`
- 二维码识别依赖OpenCV，无需额外系统依赖
- 识别结果会显示在article-ocr.md的"二维码识别"部分

## 版本历史
- v1.0: 基础提取功能
- v1.5: 添加RapidOCR支持
- v1.5.1: 修复RGBA图片处理问题
- v1.7: **新增二维码识别功能** - 自动检测图片中的二维码并提取内容
- v2.0: Hybrid模式（工具+AI协作）
