---
name: image-processor
description: >
  通用图片处理器。支持截图/裁剪、图片拼接、长图切片与重新拼接、格式转换，
  并支持识别招聘文章图片中的投递二维码/投递邮箱/投递说明块，将原图切成可堆叠显示的正文片段。
  可通过命令行调用，也可通过 Hermes 工具调用。
  通用于微信公众号文章图片处理、模板图片加工等场景。
required_env_vars: []
required_commands:
  - python3
---

# 通用图片处理器

## 功能概述

| 功能 | 描述 |
|------|------|
| **裁剪 (Crop)** | 按坐标、比例、OCR 关键词定位裁剪 |
| **拼接 (Stitch)** | 垂直/水平拼接多张图片，支持对齐和间距 |
| **网格 (Grid)** | 网格式拼接图片 |
| **切片 (Slice)** | 长图按最大高度切片，支持重叠区域 |
| **重拼 (Stitch Slices)** | 将切片重新拼接为长图 |
| **转换 (Convert)** | 格式转换、RGBA→RGB、实际格式检测 |
| **投递块分段 (Process Article Images)** | 识别投递二维码/邮箱/网申说明，输出可堆叠显示的正文片段，而不是强制重拼成长图文件 |

## 当前目标

这个 skill 现在优先解决三类公众号招聘图：

1. **纯二维码投递图**
   例：只有二维码和“即刻扫码申请”之类提示。
   处理：整图移除。

2. **纯投递说明图**
   例：只有“投递简历邮箱”“联系方式”等说明条。
   处理：整图移除。

3. **混合图中的投递块**
   例：长图正文里穿插招聘官网二维码、投递邮箱、咨询方式。
   处理：切掉投递块，保留上半段/下半段多个正文片段。
   输出：多个片段文件，前端显示时直接纵向堆叠，不要求生成一张新的物理长图。

## 实战技巧

### OCR 不可用时的精确裁剪

OCR 依赖 tesseract，安装失败或网络问题导致不可用时，切勿盲目使用 `fallback-ratio` 回退。
经验证明：**招聘海报的"投递方式"通常在图片底部 10%以内，回退比例应用 0.85–0.92，而不是 0.5–0.6。**

**推荐工作流**：
```
1. 用户发送图片
2. 尝试 crop-ocr（若 OCR 可用，精确定位）
3. 若 OCR 失败：
   a. 先运行 info 查看图片尺寸
   b. 使用 vision_analyze 分析图片结构，确定"投递方式"所在大致位置
   c. 根据位置计算合适比例（如在 90%处，ratio 用 0.88）
   d. 执行 crop --ratio x --anchor top
   e. vision_analyze 验证结果
```

**实战案例**（深蓝互动招聘海报，1336×11467）：
```bash
# 第一步：OCR 尝试（失败，未安装 tesseract）
python image_processor.py crop-ocr \
  --input poster.jpg --output tmp.jpg \
  --keywords "投递方式" --direction above --fallback-ratio 0.88

# 第二步：使用 vision 分析确认结构
# vision 分析发现"投递方式"在图片底部约 10%区域

# 第三步：按 0.88 比例裁剪，保留顶部88%
python image_processor.py crop \
  --input poster.jpg --output cropped.jpg \
  --ratio 0.88 --anchor top

# 第四步：vision 验证，确认有用内容完整、投递入口已去除
```

### 招聘海报裁剪参考比例

| 海报类型 | 投递/申请位置 | 建议 ratio | 说明 |
|---------|-------------|------------|------|
| 简约型（信息少） | 中下部 | 0.70-0.80 | 内容较少，投递占比较大 |
| 丰富型（信息多） | 底部 5-10% | 0.88-0.92 | 内容较多，投递只占小部分 |
| 未知型 | 未知 | 先用 vision 估算 | 避免盲目使用 0.5-0.6 |

## 前置条件

```bash
pip install Pillow

# 可选（OCR 裁剪需要，优先 rapidocr，回退 pytesseract）
pip install rapidocr

# 或者（如果使用 pytesseract，需要额外安装 tesseract 二进制）
pip install pytesseract
# macOS: brew install tesseract tesseract-lang
# Ubuntu: sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim
```

## 使用方式

### 方式一：命令行直接调用

```bash
cd ~/.hermes/skills/web/image-processor/scripts

# 1. 裁剪 - 按比例保留上部 60%
python image_processor.py crop \
  --input ~/input.jpg --output ~/output.jpg \
  --ratio 0.6 --anchor top

# 2. 裁剪 - 绝对坐标
python image_processor.py crop \
  --input ~/input.jpg --output ~/output.jpg \
  --left 0 --top 0 --right 800 --bottom 600

# 3. OCR 关键词裁剪（保留"投递方式"上方的内容）
python image_processor.py crop-ocr \
  --input ~/input.jpg --output ~/output.jpg \
  --keywords "投递方式" "简历投递" --direction above \
  --fallback-ratio 0.6

# 4. 垂直拼接多张图片
python image_processor.py stitch \
  --inputs ~/img1.jpg ~/img2.jpg ~/img3.jpg \
  --output ~/result.jpg --direction vertical

# 5. 水平拼接
python image_processor.py stitch \
  --inputs ~/img1.jpg ~/img2.jpg \
  --output ~/result.jpg --direction horizontal --align center

# 6. 网格拼接（2列）
python image_processor.py grid \
  --inputs ~/a.jpg ~/b.jpg ~/c.jpg ~/d.jpg \
  --output ~/grid.jpg --cols 2 --padding 10

# 7. 长图切片（每片最大 2000px）
python image_processor.py slice \
  --input ~/long.jpg --output-dir ~/slices/ \
  --max-height 2000 --overlap 50

# 8. 重新拼接切片
python image_processor.py stitch-slices \
  --input-dir ~/slices/ --output ~/reconstructed.jpg

# 9. 格式转换（自动检测实际格式）
python image_processor.py convert \
  --input ~/img.webp --output ~/img.png

# 10. 查看图片信息
python image_processor.py info --input ~/img.jpg

# 11. 批量处理公众号文章图片（识别并移除投递方式内容）
python image_processor.py process-article-images \
  --article-id 8f16cbbc \
  --keywords "投递方式" "网申通道" "简历投递" "扫码投递" "申请方式" "网申" "二维码" "扫码申请" "投递邮箱" \
  --delivery-ratio 0.7 \
  --buffer 30 \
  --qr-padding 24
```

### 方式二：Hermes 交互式处理

**场景：用户发送图片，返回处理后的图片**

```
用户发送图片
    ↓
Hermes 接收图片，保存到临时路径
    ↓
根据用户指令调用对应功能
    ↓
返回处理后的图片
```

**交互指令示例**：

| 用户指令 | 执行操作 |
|---------|---------|
| "把这张图裁剪上半部分" | `crop --ratio 0.5 --anchor top` |
| "拼接这两张图片" | `stitch --direction vertical` |
| "把这个长图切成3段" | `slice --max-height <h/3>` |
| "转换成 PNG" | `convert --output xxx.png` |
| "保留"投递方式"之上的内容" | `crop-ocr --keywords "投递方式" --direction above` |

### 方式三：Python API 调用

```python
import sys
sys.path.insert(0, "~/.hermes/skills/web/image-processor/scripts")
from image_processor import crop_image, stitch_images, slice_long_image, convert_image

# 裁剪
crop_image("input.jpg", "output.jpg", ratio=0.6, anchor="top")

# 拼接
stitch_images(["img1.jpg", "img2.jpg"], "result.jpg", direction="vertical")

# 切片
slices = slice_long_image("long.jpg", "./slices/", max_height=2000)

# 转换
convert_image("img.webp", "img.png")
```

## 核心功能详解

### 1. 裁剪（Crop）

**按比例裁剪**（最常用）：
```bash
python image_processor.py crop --input img.jpg --output out.jpg --ratio 0.6 --anchor top
```
- `ratio`: 0-1 之间，保留的比例
- `anchor`: `top`(保留上部)/`bottom`(保留底部)/`center`(保留中间)

**按坐标裁剪**：
```bash
python image_processor.py crop --input img.jpg --output out.jpg --left 0 --top 0 --right 800 --bottom 600
```

### 2. OCR 关键词定位裁剪（Crop-OCR）

适用于从图片中精确定位并删除/保留某个区域：

```bash
python image_processor.py crop-ocr \
  --input article_img.jpg --output cropped.jpg \
  --keywords "投递方式" "简历投递" "联系方式" \
  --direction above \
  --buffer 30 \
  --fallback-ratio 0.6
```

| 参数 | 说明 |
|------|------|
| `keywords` | 要查找的关键词列表（多个关键词为"或"关系） |
| `direction` | `above`保留关键词上方，`below`保留关键词下方 |
| `buffer` | 关键词周围缓冲像素（默认20） |
| `fallback-ratio` | OCR 失败时的回退比例 |

**工作原理**：
1. 调用 pytesseract 进行 OCR 识别
2. 查找关键词在图片中的坐标
3. 按方向裁剪（保留关键词上方或下方）
4. 若 OCR 失败，使用 fallback-ratio 回退

### 3. 拼接（Stitch）

**垂直拼接**（默认）：
```bash
python image_processor.py stitch \
  --inputs img1.jpg img2.jpg img3.jpg \
  --output out.jpg
```

**水平拼接**：
```bash
python image_processor.py stitch \
  --inputs left.jpg right.jpg \
  --output out.jpg --direction horizontal --align center
```

**对齐方式**：
- 垂直拼接: `center`/居中、`left`/左对齐、`right`/右对齐
- 水平拼接: `center`/居中、`top`/顶对齐、`bottom`/底对齐

### 4. 长图切片与重拼

**切片**：
```bash
python image_processor.py slice \
  --input long.jpg --output-dir ./slices/ \
  --max-height 2000 --overlap 50
```
- `max-height`: 每片最大高度（像素）
- `overlap`: 相邻切片重叠像素（用于无缝拼接，默认50）

**重新拼接**：
```bash
python image_processor.py stitch-slices \
  --input-dir ./slices/ --output reconstructed.jpg
```

### 5. 格式转换

```bash
# 自动检测实际格式（可靠，不依赖扩展名）
python image_processor.py info --input img.jpg
# 输出: 实际格式: WEBP （即使扩展名是 .jpg）

# 转换
python image_processor.py convert --input img.webp --output img.png
```

**自动处理**：
- RGBA → RGB（自动转换，避免保存失败）
- 实际格式检测（不依赖文件扩展名）

### 6. 批量处理公众号文章图片（process-article-images）

专为公众号运营工作流设计，自动识别文章图片中的投递方式内容并分类处理：

**A类（纯投递图）**: 二维码/投递说明占据图片主体 → 整图移除到 `draft/delivery/`

**B类（混合图）**: 图片中仅部分区域是投递块 → 将原图切成多个正文片段，投递块单独保存到 `draft/delivery/`

**C类（正文图）**: 未检测到关键词 → 原样复制到 `draft/images/`

```bash
python image_processor.py process-article-images \
  --article-id 8f16cbbc \
  --keywords "投递方式" "网申通道" "简历投递" "扫码投递" "申请方式" "网申" "二维码" "扫码申请" "投递邮箱" \
  --delivery-ratio 0.7 \
  --buffer 30 \
  --qr-padding 24 \
  --min-qr-size 120
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--article-id` | 文章ID | 必填 |
| `--keywords` | 检测关键词列表 | 见上方 |
| `--delivery-ratio` | 判定为纯投递图的面积占比阈值 | 0.7 |
| `--buffer` | 文本块上下扩展像素 | 30 |
| `--qr-padding` | 二维码块上下扩展像素 | 24 |
| `--min-qr-size` | 识别为主要二维码块的最小边长 | 120 |
| `--display-gap` | 多片段堆叠时建议间距 | 0 |

**输出结果**：
```
~/.hermes/output/{article_id}/
├── draft/
│   ├── images/              # 处理后的正文图片 / 分段片段
│   │   └── *_part_01.jpg    # 分段后的正文片段
│   ├── delivery/            # 被移除/裁掉的投递区域
│   ├── image_map.json       # 图片处理映射表
│   └── display_manifest.json # 前端如何堆叠显示片段
└── images/                # 原始图片（不变）
```

**前置依赖**：
```bash
# 优先方案（纯 Python，无需外部二进制）
pip install rapidocr

# 回退方案（需要 tesseract 二进制）
pip install pytesseract
# macOS: brew install tesseract tesseract-lang
# Ubuntu: sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim
```

若未安装 OCR 依赖，脚本会自动 fallback，所有图片按 C 类处理（原样保留），并提示安装方法。

## 与微信公众号工作流集成

### 场景 1：长图模式文章处理

```
原始文章图片
    ↓
OCR + 二维码检测，找到投递块
    ↓
若整张都是投递内容 → 整图移除
    ↓
若只有局部是投递块 → 切成多个正文片段
    ↓
上传 / 渲染时直接纵向堆叠这些片段
```

**实际命令**：
```bash
# 直接按文章批量处理
python image_processor.py process-article-images \
  --article-id abc123 \
  --keywords "投递方式" "简历投递" "二维码" "扫码申请" "投递邮箱"
```

### 场景 2：二创文章图片加工

```bash
# 将多张截图拼接成长图
python image_processor.py stitch \
  --inputs ~/screenshot1.jpg ~/screenshot2.jpg ~/screenshot3.jpg \
  --output ~/article_long.jpg --direction vertical

# 网格展示多个活动图片
python image_processor.py grid \
  --inputs ~/event1.jpg ~/event2.jpg ~/event3.jpg ~/event4.jpg \
  --output ~/event_grid.jpg --cols 2
```

### 场景 3：WEBP 格式转换

微信文章中的图片经常是 WEBP 格式（扩展名却是 .png/.jpg）：

```bash
# 检测
python image_processor.py info --input img.png
# 输出: 实际格式: WEBP

# 转换
python image_processor.py convert --input img.png --output img_fixed.jpg
```

## 快速交互模式（用户发图→返回处理图）

当用户直接发送图片并要求处理时，使用以下极简流程：

```
1. 保存用户图片到临时路径
2. 根据用户指令调用对应功能
3. 返回处理后的图片
```

**常见指令映射：**

| 用户说法 | 对应命令 |
|---------|---------|
| "裁掉下半部分" / "只保留上半" | `crop --ratio 0.5 --anchor top` |
| "截取底部" / "只要下半" | `crop --ratio 0.5 --anchor bottom` |
| "把这两张拼成一张" | `stitch --direction vertical` |
| "水平拼接" | `stitch --direction horizontal` |
| "切成3段" | `slice --max-height <h/3>` |
| "转换成PNG" | `convert --output xxx.png` |
| "去掉二维码" | `crop --ratio 0.92 --anchor top` 或 vision 分析后精确裁剪 |
| "保留“XX”以上的内容" | `crop-ocr --keywords "XX" --direction above` |

**关键原则：**
- 先探索、确认用户需求，再执行
- 裁剪前先用 `info` 查看图片尺寸
- 对于未知内容分布的图片，先用 vision 分析再裁剪，避免盲目使用默认比例
- 拼接后检查边缘对齐，确保视觉连贯性

## 常见问题与排错

### rapidocr 首次运行下载模型（正常）

首次使用 rapidocr 时，会自动从 ModelScope 下载约 15MB 的 ONNX 模型文件（检测+分类+识别各一个）。表现为控制台输出大量 `[INFO] download_file` 日志，耗时 10-30 秒。**这是正常现象，下载一次后后续调用秒开。**

```
[INFO] Initiating download: https://www.modelscope.cn/models/RapidAI/RapidOCR/...
[INFO] download size: 4.53MB
...
```

若网络受限导致下载失败，rapidocr 会抛异常，脚本自动回退到 pytesseract 或按 C 类处理。

### macOS urllib3 SSL 警告（可忽略）

macOS 上 rapidocr 可能触发如下警告，**不影响功能**：

```
NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with LibreSSL 2.8.3
```

### 重复图片（webp + jpg）

微信文章提取后，可能出现同一图片的 webp 和 jpg 两个版本（如 `img_001.jpg` 和 `img_001.webp`）。`process-article-images` 会分别处理两者，可能产生重复结果。当前策略是全部处理、由上游流程去重。

### 没有检测到关键词，但图片确实含投递方式

可能原因：
1. **OCR 识别失败**：图片中投递方式是纯图片（无文字），或文字过小/模糊。可尝试降低 `--delivery-ratio` 阈值、增大 `--qr-padding`，或人工 vision 检查。
2. **关键词不匹配**：自定义关键词未覆盖。可扩展 `--keywords` 列表，如添加 `"申请"`、`"报名"`、`"投递"` 等同义词。
3. **只有二维码没有文字**：若环境安装了 `pyzbar` 或 `opencv-python`，脚本会直接按二维码框辅助切分；否则会更依赖 OCR 文本提示。
4. **rapidocr 置信度过滤**：当前实现未按置信度过滤。若遇到漏检，可检查 rapidocr 原始输出确认是否识别到了文字但置信度过低。

### crop-ocr 与 process-article-images 的 OCR 引擎差异

| 命令 | 支持的 OCR 引擎 | 说明 |
|------|---------------|------|
| `crop-ocr` | 仅 pytesseract | 需要 tesseract 二进制 |
| `process-article-images` | rapidocr → pytesseract | 优先纯 Python 方案，无需外部二进制 |

**建议**：批量处理文章图片时优先使用 `process-article-images`；单张精确裁剪且系统已装 tesseract 时可用 `crop-ocr`。

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-04-28 | 初始版本，支持裁剪、拼接、切片、转换、OCR定位裁剪 |
| v1.1 | 2026-04-29 | 添加快速交互模式指南，支持"用户发图→返回处理图"场景 |
| v1.2 | 2026-04-29 | process-article-images 支持双引擎 OCR（优先 rapidocr，回退 pytesseract），无需外部 tesseract 二进制 |
| v1.3 | 2026-05-09 | process-article-images 重构为“投递块分段”模型：支持二维码框辅助识别、纯投递图整图移除、混合图切成可堆叠显示的多个正文片段，并新增 `display_manifest.json` |
