# 微信公众号草稿上传 - 问题与解决方案

## 已解决问题汇总

### 1. 图片压缩参数化（v1.7）

**问题**：图片超过 1MB 自动压缩，但有时不需要压缩

**解决**：添加 `--compress` / `-z` 参数，默认不压缩

```bash
# 默认不压缩
python upload_from_feishu.py -n 008

# 启用压缩
python upload_from_feishu.py -n 008 -z
```

**Git**: `ac7f5a9`

---

### 2. 智能编号查询（v1.8）

**问题**：用户需要查找复杂的 record_id，难以记忆

**解决**：支持 `--no` / `-n` 参数，自动根据 `ID` 字段查询

```bash
# 自动查询 NO.008 对应的 record_id
python upload_from_feishu.py -n 008
python upload_from_feishu.py -n NO.008
```

**实现**：
- 使用 `lark-cli` 查询【文章素材表】
- 匹配 `ID` 字段（支持简写和完整格式）
- 返回对应的 `record_id`

**Git**: `02520c0`

---

### 3. 摘要长度限制修正（v1.10）

**问题**：文档写 128 字符，实际 API 限制 120 字符，导致上传失败

**错误信息**：`description size out of limit`

**解决**：修正截断长度为 120 字符

```python
# 修正前
article["digest"] = digest[:128] if digest else ""

# 修正后
article["digest"] = digest[:120] if digest else ""
```

**Git**: `071b354`

---

### 4. 智能封面选择（v1.9）

**问题**：默认取第一张图片，可能是 GIF 动图或不合适的图片（如二维码、纯文字图）

**解决**：基于 OCR 内容智能评分选择最佳封面

**评分规则**：
| 条件 | 加分 | 说明 |
|------|------|------|
| 包含公司/品牌名称 | +5 | 如 "COSL"、"腾讯" |
| 包含"招聘"/"校招"/"实习" | +3 | 与主题相关 |
| 包含"Logo"/"标志" | +2 | 品牌标识 |
| 包含"二维码"/"关注"/"扫码" | -5 | 不适合做封面 |
| 纯文字图（无图片特征） | -3 | 视觉效果差 |
| 尺寸比例 16:9 | +2 | 微信推荐比例 |
| GIF 动图 | -100 | 直接排除 |

**兜底**：第一张非动图图片

```bash
# 自动选择最佳封面
python upload_from_feishu.py -n 008

# 手动指定封面
python upload_from_feishu.py -n 008 --cover img_002.png
```

**Git**: `3a6e305`

---

### 5. 环境配置优化

**问题**：API Key 未持久化，新会话丢失

**解决**：
1. 添加到 `~/.hermes/.env`
2. 创建 `check_env.sh` 检查脚本

```bash
# 检查环境
source ~/.hermes/skills/web/wechat-mp-draft-uploader/scripts/check_env.sh
```

**Git**: `5e81cb3`

---

## API 限制汇总

| 限制项 | 数值 | 说明 |
|--------|------|------|
| 文件大小 | 10MB | 图片素材上传限制 |
| 摘要长度 | 120字符 | 微信 API 实际限制 |
| 标题长度 | 64字符 | 微信官方限制 |
| 作者长度 | 16字符 | 微信官方限制 |
| 图文数量 | 8篇 | 多图文上限 |

---

## 使用示例

```bash
# 基础用法
python upload_from_feishu.py -n 008

# 完整参数
python upload_from_feishu.py \
    -n 008 \
    -z \
    --cover img_002.png \
    --author "Joblinker官方" \
    --no-comment
```

---

## 简立制作 API 连接超时（SSL Handshake Timeout）

### 现象
- 上传时所有图片素材均失败，提示 `素材上传失败: 未知错误`
- 日志中出现大量 `⚠️ 远程图片处理失败` 和 `⚠️ 本地图片上传失败`
- 最终草稿创建也失败
- 封面和正文图片一张都没有上传成功

### 根因
简立制作平台 API 服务端出现**网络连接超时**，具体表现为 SSL/TLS 握手阶段超时（`TimeoutError: The handshake operation timed out`）。这不是 API 返回的业务错误（如积分不足、格式不支持），而是底层网络连接问题。

### 诊断
```python
import requests

url = "https://api.jianlizhizuo.com/v1/accounts/{appid}/materials"
headers = {"Authorization": f"Bearer {API_KEY}"}

with open("test.png", "rb") as f:
    files = {"media": ("test.png", f, "image/png")}
    resp = requests.post(url, data={"type": "IMAGE", "name": "test"}, files=files, headers=headers, timeout=30)

# 实际抛出：
# requests.exceptions.ReadTimeout: HTTPSConnectionPool(host='api.jianlizhizuo.com', port=443): Read timed out.
```

### 解决
1. **等待 5-10 分钟后重试** — 服务端通常为临时故障
2. **检查网络连接** — 确认本机网络正常
3. **检查平台状态** — 访问简立制作平台确认是否可用

### 与积分不足的区别
| 特征 | API 超时 | 积分不足 |
|------|----------|----------|
| 错误信息 | `素材上传失败: 未知错误` | `积分不足，需要 1 积分，当前余额 0` |
| 底层异常 | `ReadTimeout` / `TimeoutError` | API 正常返回 `code != 0` |
| 第一张图 | 失败 | 可能成功（积分在首张图后耗尽） |
| 解决方式 | 等待重试 | 充值积分 |

---

## 只上传到部分适配账号（无 `--target-account` 参数）

### 现象
- 文章在飞书 Base 中配置了多个【适配账号】（如 `Joblinker` + `行研实习`）
- 用户只想上传到其中一个账号（如仅 `行研实习`）
- 脚本没有 `--target-account` 参数，无法指定单一账号

### 根因
上传脚本的目标账号**严格由飞书 Base【适配账号】字段决定**，脚本不支持命令行参数覆盖。

### 临时 workaround
**通过临时修改 Feishu Base 实现单账号上传**（上传后务必恢复）：

```python
import sys
sys.path.insert(0, '~/.hermes/skills/web/wechat-mp-draft-uploader/scripts')
from upload_from_feishu import FeishuClient, ARTICLE_TABLE_ID

client = FeishuClient()
record_id = 'recviTSxj8a64l'  # 替换为实际 record_id

# 1. 保存原始适配账号
original_accounts = ['Joblinker', '行研实习']

# 2. 临时修改为仅目标账号
client.update_record(ARTICLE_TABLE_ID, record_id, {'适配账号': ['行研实习']})

# 3. 执行上传
# python upload_from_feishu.py --article-id <article_id>

# 4. 恢复原始适配账号（重要！）
client.update_record(ARTICLE_TABLE_ID, record_id, {'适配账号': original_accounts})
```

### 风险
- **忘记恢复**：若上传成功后忘记恢复原始适配账号，后续查看 Base 会误以为该文章只属于一个账号
- **并发冲突**：若同时有其他操作修改同一条记录，可能导致数据不一致

### 长期修复建议
为上传脚本添加 `--target-account` / `-t` CLI 参数：
```bash
# 只上传到指定账号（覆盖 Base 配置）
python upload_from_feishu.py --article-id 0d674f8c --target-account 行研实习
```

---

*最后更新: 2026-05-09*

---

## `ModuleNotFoundError: wechat_pipeline`（共享模块缺失）

### 现象
- 运行 `upload_from_feishu.py` 时报错：`ModuleNotFoundError: No module named 'wechat_pipeline'`
- traceback 指向 `from wechat_pipeline import PipelineValidationError, collect_img_refs, ...`
- 脚本完全无法执行

### 根因
`upload_from_feishu.py` 依赖一个共享模块 `wechat_pipeline`，其位于 `~/.hermes/skills/web/_shared/wechat_pipeline.py`。该模块提供：
- `PipelineValidationError` — 流水线验证异常基类
- `extract_article_content(html)` — 从微信原始 HTML 提取正文
- `collect_img_refs(content)` — 收集 HTML 中所有图片引用
- `validate_draft_local_images(article_dir, content)` — 验证草稿引用的本地图片是否存在

如果该文件被删除、移动或从未创建，上传脚本将直接崩溃。

### 解决
创建缺失的共享模块文件：

```python
# ~/.hermes/skills/web/_shared/wechat_pipeline.py
import re
import json
from pathlib import Path
from typing import Tuple, List

class PipelineValidationError(Exception):
    pass

def extract_article_content(html_content: str) -> Tuple[str, str]:
    match = re.search(r'id="js_content"[^>]*>(.*?)</div>', html_content, re.DOTALL)
    if match:
        return match.group(1).strip(), "js_content"
    match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip(), "body"
    content = re.sub(r'<!DOCTYPE[^>]*>', '', html_content, flags=re.IGNORECASE)
    content = re.sub(r'<html[^>]*>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'</html>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'<head>.*?</head>', '', content, flags=re.IGNORECASE | re.DOTALL)
    return content.strip(), "raw"

def collect_img_refs(content: str) -> List[str]:
    """收集HTML中的图片引用，过滤掉 data: URI 内联图片"""
    refs = set()
    for match in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE):
        ref = match.group(1)
        if not ref.startswith("data:"):
            refs.add(ref)
    for match in re.finditer(r'<img[^>]+data-src=["\']([^"\']+)["\']', content, re.IGNORECASE):
        ref = match.group(1)
        if not ref.startswith("data:"):
            refs.add(ref)
    return sorted(list(refs))

def validate_draft_local_images(article_dir: Path, content: str) -> List[str]:
    refs = collect_img_refs(content)
    missing = []
    draft_images_dir = article_dir / "draft" / "images"
    original_images_dir = article_dir / "images"
    for ref in refs:
        if ref.startswith(("http://", "https://", "//", "data:")):
            continue
        ref_path = ref.lstrip("/")
        found = False
        if draft_images_dir.exists() and (draft_images_dir / ref_path).exists():
            found = True
        if original_images_dir.exists() and (original_images_dir / ref_path).exists():
            found = True
        if not found:
            missing.append(ref)
    return missing

def write_manifest(article_dir: Path, data: dict) -> None:
    manifest_path = article_dir / "manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def validate_required_fields(fields: dict, required: list) -> None:
    missing = [f for f in required if not fields.get(f)]
    if missing:
        raise PipelineValidationError(f"缺少字段: {', '.join(missing)}")
```

**注意**：`collect_img_refs` 必须过滤 `data:` URI，否则内联 SVG 会被误认为缺失的本地图片导致阻断上传。

### 预防
- 将该模块纳入 Skill Git 版本控制，确保新环境部署时自动创建
- 上传脚本启动时做依赖预检：`Path("~/.hermes/skills/web/_shared/wechat_pipeline.py").exists()`

---

## data: URI 内联图片导致"部分草稿图片未成功上传并替换"阻断

### 现象
- 使用 `draft/draft.html` 上传时，步骤5报阻断错误：
  `PipelineValidationError: 部分草稿图片未成功上传并替换，已阻断上传: data:image/svg+xml,%3C%3Fxml version=...`
- 或：`草稿 HTML 引用了不存在的本地图片，已阻断上传: data:image/svg+xml,...`

### 根因
草稿 HTML 中可能包含 `data:image/svg+xml` 形式的**内联图片**（base64 编码的 SVG）。`collect_img_refs` 原实现未过滤 `data:` URI，将其当作需要上传的本地图片引用。验证阶段发现这些 "图片" 既不在远程也不存在于本地目录，于是触发阻断。

### 解决
在 `collect_img_refs` 中增加 `data:` 前缀过滤：

```python
def collect_img_refs(content: str) -> List[str]:
    refs = set()
    for match in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE):
        ref = match.group(1)
        if not ref.startswith("data:"):  # 过滤内联图片
            refs.add(ref)
    # data-src 同理
    return sorted(list(refs))
```

### 预防
- `wechat_pipeline.py` 的 `collect_img_refs` 必须始终过滤 `data:` URI
- 若未来支持 base64 内联图片上传，应单独处理而非混入本地/远程图片逻辑

---

## 飞书 Base 中同一 article_id 存在多条记录

### 现象
- 使用 `--article-id` 上传时报错：`找到多个文章ID为 xxx 的文章，请使用 record_id 直接指定`
- 同一篇原始微信文章包含多个招聘岗位，在 Base 中被拆分为多条记录
- 脚本拒绝执行，无法自动选择

### 根因
【文章ID】字段对应原始微信文章的 URL hash，多条记录（不同岗位）可能共享同一个 `article_id`。脚本通过 `article_id` 查询 Base 时发现多条匹配记录，为避免误操作而主动阻断。

### 解决
改用 `--record-id` 精确指定单条记录：

```bash
# 1. 查询该 article_id 对应的所有记录，获取目标 record_id
lark-cli api GET "/open-apis/bitable/v1/apps/{base_token}/tables/{table_id}/records" \
  --params '{"page_size":500}' \
  --as bot 2>&1 | python3 -c "
import json, sys
data = json.load(sys.stdin)
for item in data.get('data', {}).get('items', []):
    if item.get('fields', {}).get('文章ID') == '4ef45e86':
        print(f\"record_id: {item.get('record_id')}, 适配账号: {item.get('fields', {}).get('适配账号')}, 状态: {item.get('fields', {}).get('文章状态')}\")
"

# 2. 使用 record_id 上传
python upload_from_feishu.py --record-id recvj6UdXBFNTH
```

### 预防
- 一篇文章含多个岗位时，**优先使用 `--record-id`** 而非 `--article-id`
- 在飞书 Base 中通过【文章标题】区分不同岗位记录
- 上传脚本可考虑增加 `--target-account` 参数，在重复记录中按适配账号自动选择

---

## 新账号无独立推广模板的处理（Template Fallback）

### 现象
- 新增公众号账号（如 `研究生求职圈`）需要上传文章
- `process.py` 的 `templates/` 目录下没有对应的推广模板文件（如 `yanjiusheng_qiuzhi.html`）
- 上传时报错：`FileNotFoundError: 推广模板不存在: templates/yanjiusheng_qiuzhi.html`

### 根因
`wechat-mp-draft-processor-pro` 的 `step3_append_promotion.py` 按 `--account {key}` 加载 `templates/{key}.html`。如果该账号没有独立设计推广模板，脚本会直接失败。

### 解决（模板套用）
在 `upload_from_feishu.py` 的 `ACCOUNT_NAME_MAP` 中，将该账号映射到已有模板的账号 key：

```python
# upload_from_feishu.py
ACCOUNT_NAME_MAP = {
    "Joblinker": "joblinker",
    "行研实习": "xingyan_shixi",
    "研究生求职圈": "joblinker",  # 无独立模板，套用 Joblinker
}
```

这样上传时：
1. 飞书 Base 中的【适配账号】显示为 `研究生求职圈`
2. `upload_from_feishu.py` 查询【账号配置表】获取该账号的 AppID
3. 生成草稿时，`ACCOUNT_NAME_MAP` 将其映射为 `joblinker` 传给 `process.py`
4. `process.py` 加载 `templates/joblinker.html`，成功套用已有模板

### 长期建议
- 如果新账号后续有了独立模板，只需在 `templates/` 目录创建对应文件，并修改 `ACCOUNT_NAME_MAP` 映射
- 不同账号的 AppID 是独立的，即使共用同一份模板，最终草稿也是上传到各自独立的公众号

---

## 远程图片格式不匹配导致上传失败

### 现象
- 草稿箱文章内容缺少图片（特别是 GIF 动图）
- 图片在本地 `images/` 目录存在，但上传后草稿箱不显示
- 同篇文章部分图片能显示，部分不能

### 根因
微信 CDN 远程图片 URL 格式与**实际返回的文件格式不一致**：

| 远程 URL 路径标记 | 实际返回格式 | 问题 |
|---|---|---|
| `mmbiz_gif` | GIF / WEBP | 保存为 `.jpg`，MIME 为 `image/jpeg` |
| `mmbiz_png` | PNG / WEBP | 保存为 `.jpg`，MIME 为 `image/jpeg` |
| `mmbiz_jpg` | JPEG / WEBP | 保存为 `.jpg`，MIME 正确但可能被覆盖 |

脚本原逻辑：
1. `Path(url.split('?')[0]).suffix` 从 URL 路径提取扩展名 → 微信 CDN URL **无路径扩展名**
2. 默认回退 `.jpg` → **所有远程图片都保存为 `.jpg`**
3. `mimetypes.guess_type('.jpg')` → 推断为 `image/jpeg`
4. 但实际文件是 GIF/PNG/WEBP → **MIME 类型与文件内容不匹配**
5. 微信 `/materials` API 拒绝上传或上传后无法渲染

### 诊断
```python
from pathlib import Path
import hashlib

temp_dir = Path.home() / ".hermes/output/ARTICLE_ID/.temp_remote_images"
for f in sorted(temp_dir.glob("remote_*")):
    header = f.read_bytes()[:12]
    if header[:6] in (b'GIF89a', b'GIF87a'):
        actual = 'GIF'
    elif header[:8] == b'\x89PNG\r\n\x1a\n':
        actual = 'PNG'
    elif header[:2] == b'\xff\xd8':
        actual = 'JPEG'
    elif header[:4] == b'RIFF' and header[8:12] == b'WEBP':
        actual = 'WEBP'
    else:
        actual = 'UNKNOWN'
    match = "✅" if f.suffix.upper() in ('.JPG', '.JPEG') and actual == 'JPEG' or f.suffix.upper() == f".{actual}" else "❌ 不匹配!"
    print(f"{f.name}: 声明={f.suffix} 实际={actual} {match}")
```

### 修复（v1.11）
1. **URL 参数提取扩展名**：优先从 `wx_fmt=gif|png|jpg|jpeg|webp` URL 参数提取
2. **Pillow 实际格式检测**：下载后用 Pillow `Image.open().format` 检测，不匹配则自动重命名
3. **WEBP 自动转换**：微信 API 不支持 WEBP，自动转换为 PNG
4. **文件头 MIME 兜底**：`upload_material` 中用文件头签名覆盖 `mimetypes.guess_type()` 结果

**Git**: `2026-05-07`

---

## 长图模式文章内容缺失问题

### 现象
- 上传草稿后只有几张图片，没有任何文字说明
- 草稿几乎为空（正文仅 131 字符）
- 文章目录下存在 `article-ocr.md`（含完整文字），但草稿未使用

### 根因
部分公众号文章采用**长图模式**（纯图片发布，无 HTML 文字正文）。上传脚本优先读取 `article_original.html` 提取 `js_content`，但长图模式下：
1. **文章本身无文字**：`js_content` 内纯文本长度为 0，仅含 `<img>` 和 `<section>` 标签
2. **scraper 失败 fallback**：某些链接的 `article_original.html` 仅 418 bytes，是提取工具生成的错误提示页面（非微信原始 HTML）
3. **OCR 内容未被利用**：`article-ocr.md` 包含完整的图片 OCR 文字，但上传脚本未读取

### 诊断脚本
```bash
python3 << 'PYEOF'
import re
from pathlib import Path

for aid in ['cccd65c8', 'e132ab11']:
    f = Path.home() / f".hermes/output/{aid}/article_original.html"
    if f.exists():
        html = f.read_text()
        size = len(html)
        is_stub = 'article-ocr.md' in html and size < 1000
        text_len = len(re.sub(r'<[^>]+>', '', html))
        print(f"{aid}: {size} bytes, is_stub={is_stub}, raw_text={text_len}")
    else:
        print(f"{aid}: file not found")
PYEOF
```

### 解决方案

**短期**：手动基于 OCR 重建 HTML
```python
from pathlib import Path
import re

def build_html_from_ocr(article_dir: str) -> str:
    ocr_path = Path(article_dir) / "article-ocr.md"
    if not ocr_path.exists():
        return None
    md = ocr_path.read_text()
    lines = []
    for line in md.split('\n'):
        if line.strip().startswith('![') or line.strip().startswith('---'):
            continue
        lines.append(line)
    text = '\n'.join(lines)
    html = f"<p>{text.replace(chr(10)*2, '</p><p>').replace(chr(10), '<br/>')}</p>"
    html = re.sub(r'#{1,6}\s+(.+)', r'<h3>\1</h3>', html)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    return html
```

**长期**：上传脚本增加长图模式检测
- 检测 `js_content` 纯文本长度为 0 时，自动回退到 `article-ocr.md`
- 检测 `article_original.html` < 1KB 且含 "article-ocr.md" 字样时，自动使用 OCR

### 预防
- 上传前运行诊断脚本，确认 `article_original.html` 不是提示页面
- 若 `article-ocr.md` 存在且 `article_original.html` < 1KB，直接基于 OCR 构建 HTML
- 公众号后台草稿预览确认内容完整性后再发布

---

## 无图片文章封面处理失败

### 现象
- 上传时报错：`FileNotFoundError: 找不到图片目录`或`目录中没有图片`
- 文章本身为纯文字/文本格式，提取时下载了 0 张图片
- `images/` 目录不存在或为空

### 根因
部分公众号文章采用纯文字发布，没有任何图片素材。上传脚本在步骤6处理封面图片时，会检查 `article_dir/images/` 目录，如果目录不存在或为空就抛出异常。

### 临时解决方案
手动放置一张默认封面图到 `images/` 目录：
```bash
mkdir -p ~/.hermes/output/ARTICLE_ID/images
cp ~/.hermes/skills/web/wechat-mp-draft-uploader/assets/default_cover.png \
   ~/.hermes/output/ARTICLE_ID/images/img_001.png
```

### 长期修复建议
上传脚本在处理封面时增加空目录兼容：
- 检查 `images/` 是否存在且非空
- 若为空，生成一张简单的默认封面图（如纯色背景+文章标题）或允许不传封面
- 或者从正文内容中提取第一张图片作为封面

### 预防
- 提取文章后检查 `images/` 目录，若为空提前准备默认封面图
- 在底层处理中追加空目录兼容

---

## 批量文章提取注意事项

### 现象
- 同时运行多个 `main.py` 提取任务时报错：`ModuleNotFoundError` 或 `ImportError`
- 并行提取失败

### 根因
`wechat-article-for-ai-pro/main.py` 使用全局 Python 环境和共享模块导入，并行运行时可能冲突。

### 解决
**必须串行提取**：一次只运行一篇文章的提取，完成后再提取下一篇。

```bash
# ❌ 错误：并行提取
for url in $urls; do
  python3 main.py "$url" &  # 会冲突
done

# ✅ 正确：串行提取
for url in $urls; do
  python3 main.py "$url"    # 等待完成后再下一个
done
```

---

## Surrogate Pair Emoji 导致 `UnicodeEncodeError`

### 现象
- 多账号上传时，第二个及以后账号上传失败
- 报错：`UnicodeEncodeError: 'utf-8' codec can't encode characters in position 3-4: surrogates not allowed`
- traceback 指向 `upload_from_feishu.py` 中的 `print(f"   🔄 正在为 {account_name} 重新生成草稿...")`

### 根因
在 v1.22 修复多账号模板错乱问题时，添加了包含 emoji `🔄` 的日志输出。但由于 patch 工具或文件编码原因，emoji 被保存为 **UTF-16 surrogate pair**（`\ud83d\udd04`），而非正确的 UTF-8 字节序列（`f0 9f 94 84`）。

Python 的 `print()` 尝试将 surrogate pair 编码为 UTF-8 输出到终端时失败，因为 UTF-8 不支持孤立的 surrogate code units。

### 诊断
```bash
# 检查文件中的 emoji 编码
sed -n '1070p' upload_from_feishu.py | xxd | head -3

# 错误（surrogate pair）
# 00000010: 7428 6622 2020 205c 7564 3833 645c 7564  t(f"   \ud83d\ud
# 00000020: 6430 3420 e6ad a3e5 9ca8 e4b8 ba20 7b61  d04 ......... {a

# 正确（UTF-8）
# 00000010: 7428 6622 2020 20f0 9f94 8420 e6ad a3e5  t(f"   .... ....
# 00000020: 9ca8 e4b8 ba20 7b61 6363 6f75 6e74 5f6e  ..... {account_n
```

### 修复
将 surrogate pair 替换为实际 UTF-8 emoji：
```python
# 错误（surrogate pair，不可见或报错）
print(f"   \ud83d\udd04 正在为 {account_name} 重新生成草稿...")

# 正确（UTF-8 编码的 emoji）
print(f"   🔄 正在为 {account_name} 重新生成草稿...")
```

### 预防
- **在 Python 源码中直接输入 emoji**（复制粘贴或输入法输入），不要依赖转义序列
- 使用 patch 工具修改含 emoji 的代码时，修改后运行脚本验证 emoji 显示正常
- 在 CI/自动化流程中加入编码检查：
  ```bash
  python3 -c "open('upload_from_feishu.py').read().encode('utf-8')" || echo "编码错误"
  ```
- 若看到 `\ud83d\udd04` 或 `\uXXXX` 形式的转义出现在 `.py` 文件字面量中，立即替换为实际字符

---

## 重新运行 `process_draft.py` 但投递方式裁剪结果不变

### 现象
- 用户更新了 `image-processor` 代码（扩展 OCR 关键词），或手动修改了相关逻辑
- 删除旧 `draft/` 目录后重新运行 `process_draft.py`
- 结果与上次**完全一样**：本应被裁剪的图片仍未裁剪，或本不该被裁剪的仍被裁剪
- 例：路易威登文章 `img_004.png` 含"即刻扫码申请"和二维码，但处理后仍直接复制，未裁剪投递方式

### 根因（双重因素）

#### 因素 1：`article-ocr.md` 数据陈旧
`process_draft.py` **读取的是已有的 `article-ocr.md` 和切片目录**，而非实时运行 OCR。如果：
- 之前 `image-processor` 扫描失败，切片 OCR 文本为 `[待识别]`
- 之后即使 `image-processor` 代码更新了，**已有的 `article-ocr.md` 不会自动刷新**

重新运行 `process_draft.py` 只会基于旧 OCR 数据做判断，结果自然不变。

#### 因素 2：普通尺寸图片的检测盲区
`process_draft.py` 的投递方式检测逻辑：
1. 仅扫描有 `slices/` 子目录的**超长图**
2. 对每个切片的 OCR 文本匹配关键词
3. **普通尺寸图片（无切片）直接复制到 draft，不做任何 OCR 检测**

这意味着：即使 `img_004.png` 含二维码和"即刻扫码申请"，只要它不是超长图（无 `slices/`），就会被直接复制，不做裁剪。

### 诊断
```bash
# 1. 检查 article-ocr.md 是否陈旧
grep -c "\u5f85\u8bc6\u522b" ~/.hermes/output/{article_id}/article-ocr.md

# 2. 检查哪些图片有切片（超长图）
ls ~/.hermes/output/{article_id}/images/slices/ 2>/dev/null || echo "无切片"

# 3. 重新运行 image-processor 生成新的 article-ocr.md
cd ~/.hermes/skills/web/image-processor
python3 scripts/image_processor.py --article-dir ~/.hermes/output/{article_id}

# 4. 确认 OCR 已更新后，再重新运行 process_draft.py
cd ~/.hermes/skills/web/wechat-mp-draft-processor
python3 scripts/process_draft.py --article-dir ~/.hermes/output/{article_id} --account joblinker
```

### 解决
| 场景 | 操作 |
|------|------|
| article-ocr.md 含 `[待识别]` | **先重新运行 `image-processor`** 扫描生成新的 OCR 数据，再运行 `process_draft.py` |
| 普通图片含投递方式但未被检测 | 当前流程不支持。需手动裁剪后替换到 `draft/images/`，或在 `image-processor` 阶段对普通图片也执行 OCR |

### 与预期不符的对比
| 用户假设 | 实际行为 |
|----------|----------|
| 更新 image-processor 代码后，重新运行 process_draft.py 即可生效 | ❌ 必须先重新运行 image-processor 更新 article-ocr.md |
| 所有图片都会扫描是否含投递方式 | ❌ 仅扫描超长图的切片，普通图片直接复制 |

---

## 简立制作 API 服务端返回 500 错误（非网络超时）

### 现象
- 上传时**所有图片**均失败：`⚠️ 本地图片上传失败: 素材上传失败: 未知错误`
- 远程图片同样失败：`⚠️ 远程图片处理失败: 素材上传失败: 未知错误`
- 最终阻断：`PipelineValidationError: 部分草稿图片未成功上传并替换`
- 与 SSL 超时不同：**没有 `ReadTimeout` 或 `TimeoutError`，API 正常响应但返回错误**

### 根因
简立制作平台 API **服务端内部故障**，返回 HTTP 500。这不是网络连接问题，也不是 API Key 无效或积分不足。

### 诊断（区分不同故障类型）
```bash
# 1. 测试素材上传端点（最直接）
curl -s -w "\nHTTP_CODE:%{http_code}\n" \
  -X POST -H "Authorization: Bearer $JIANLIZHIZUO_API_KEY" \
  -F "type=IMAGE" -F "name=test" \
  -F "media=@/path/to/test.png" \
  "https://mp.jianlizhizuo.cn/v1/accounts/{appid}/materials"

# 服务端 500 故障的典型返回：
# {"code":50000,"message":"上传素材失败","data":null}
# HTTP_CODE:500

# 2. 测试草稿列表端点（确认服务范围）
curl -s -H "Authorization: Bearer $JIANLIZHIZUO_API_KEY" \
  "https://mp.jianlizhizuo.cn/v1/accounts/{appid}/drafts"

# 同样返回：{"code":50000,"message":"获取草稿列表失败"}
```

### 三种上传失败类型的对比

| 特征 | 服务端 500 故障 | SSL/连接超时 | 积分不足 |
|------|----------------|--------------|----------|
| HTTP 状态码 | 500 | 无响应/超时 | 200 |
| API code | `50000` | 无（抛异常） | 非 0（如 `40003`） |
| 错误信息 | `"上传素材失败"` / `"获取草稿列表失败"` | `ReadTimeout` | `"积分不足"` |
| 第一张图 | 失败 | 失败 | 可能成功 |
| 所有端点 | 均 500 | 网络层问题 | 其他端点正常 |
| 解决方式 | **等待平台修复**（通常 10-30 分钟） | 检查网络后重试 | 充值积分 |

### 解决
1. **不要反复重试** — 服务端 500 是平台内部故障，短时间内重试不会成功
2. **等待 10-30 分钟后再次测试** — 用上述 curl 命令确认平台恢复
3. **联系平台方** — 若持续超过 1 小时，联系简立制作确认服务状态
4. **平台恢复后** — 重新执行上传脚本即可

### 预防
- 上传前先用 curl 快速测试平台健康状态，避免在平台故障时浪费处理时间
- 服务端 500 与 SSL 超时、积分不足有明确区分，按上表对症下药

---

*最后更新: 2026-05-10*