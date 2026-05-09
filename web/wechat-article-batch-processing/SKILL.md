---
name: wechat-article-batch-processing
description: >
  微信公众号文章批量提取与故障排查技能。用于一次性处理多个微信文章链接时的串行批量执行、链接失效检测、debug HTML 诊断等场景。
  不含任何凭证，所有敏感信息均从环境变量或调用方读取。
---

# 微信文章批量处理与故障排查

> **使用场景**：用户一次性发送多个微信文章链接，需要批量提取、分析、同步。
>
> **执行原则**：串行处理（Camoufox 不支持并发），单篇失败不阻断后续文章，失败时自动诊断原因。

---

## 批量处理流程

```
用户发送 N 个微信链接
    ↓
for url in urls:
    ↓
    1. 工具提取（Camoufox + RapidOCR）
    2. 判断是否失败
       ├── 是 → 诊断失败原因（链接失效 / 解析错误 / 其他）
       │         → 记录错误，继续下一篇
       └── 否 → 复制到 ~/.hermes/output/{article_id}/
    3. 读取 metadata.json + article-ocr.md
    4. AI 分析（13个字段）
    5. 构建完整 Base 记录（23字段）
    6. 同步到飞书 Base
    7. 记录结果
    ↓
输出汇总报告
```

### 批量执行脚本框架（无凭证版）

```python
import subprocess
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

def batch_extract_and_sync(
    urls: list[str],
    output_base: str = "/tmp/test_output",
    tool_path: str = "/tmp/wechat-article-for-ai-pro",
    python_bin: str = "/usr/bin/python3",
    hermes_output: str = None  # 默认: ~/.hermes/output
) -> list[dict]:
    """
    批量提取微信文章并同步到飞书Base。
    
    Args:
        urls: 微信文章URL列表
        output_base: 工具临时输出目录
        tool_path: wechat-article-for-ai-pro 项目路径
        python_bin: Python 解释器路径（建议系统Python）
        hermes_output: 永久输出目录
        
    Returns:
        list[dict]: 每篇文章的处理结果
        示例: [{"url": "...", "success": True, "article_id": "...", "record_id": "...", "error": None}, ...]
    """
    if hermes_output is None:
        hermes_output = str(Path.home() / ".hermes" / "output")
    
    results = []
    
    # 清理上次工具输出
    if os.path.exists(output_base):
        for item in os.listdir(output_base):
            item_path = os.path.join(output_base, item)
            if os.path.isdir(item_path) and item != "debug":
                shutil.rmtree(item_path)
    
    for i, url in enumerate(urls):
        print(f"\n[{'='*60}")
        print(f"[{i+1}/{len(urls)}] 处理: {url}")
        print(f"{'='*60}")
        
        result = {
            "url": url,
            "success": False,
            "article_id": None,
            "record_id": None,
            "error": None
        }
        
        try:
            # ========== 阶段 1: 工具提取 ==========
            cmd = f'cd {tool_path} && {python_bin} main.py "{url}" -o {output_base} -v'
            extract_result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=300
            )
            
            if extract_result.returncode != 0:
                # 检查是否为链接失效
                debug_dir = Path(output_base) / "debug"
                if debug_dir.exists():
                    debug_files = sorted(debug_dir.glob("debug_*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
                    if debug_files:
                        debug_content = debug_files[0].read_text(errors="ignore")
                        if "Weixin Official Accounts Platform" in debug_content:
                            result["error"] = "链接已失效（返回空页面），请从微信重新复制分享链接"
                        elif "<title></title>" in debug_content or "<title>\n</title>" in debug_content:
                            result["error"] = "链接需要微信登录态或验证，请检查 URL 是否包含必要的 scene 参数"
                        else:
                            result["error"] = f"提取失败: {extract_result.stderr[:200]}"
                    else:
                        result["error"] = f"提取失败: {extract_result.stderr[:200]}"
                else:
                    result["error"] = f"提取失败: {extract_result.stderr[:200]}"
                results.append(result)
                continue
            
            # ========== 获取文章输出目录 ==========
            tmp_dirs = [d for d in Path(output_base).iterdir() if d.is_dir() and d.name != "debug"]
            
            if not tmp_dirs:
                result["error"] = "未找到工具提取的输出目录"
                results.append(result)
                continue
            
            # 选择最新创建的目录
            article_dir = max(tmp_dirs, key=lambda p: p.stat().st_mtime)
            
            # 读取 metadata.json 获取 article_id
            metadata_path = article_dir / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                article_id = metadata.get("article_id", article_dir.name)
            else:
                article_id = article_dir.name
            
            result["article_id"] = article_id
            
            # 复制到永久目录
            dest_dir = Path(hermes_output) / article_id
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(article_dir, dest_dir)
            print(f"✅ 已复制到: {dest_dir}")
            
            # ========== 阶段 2 & 3: AI分析 + Base同步 ==========
            # 注：此处调用具体的分析和同步逻辑
            # 实际实现时，读取 article-ocr.md 进行AI分析，
            # 构建 record_data，然后调用 lark-cli 同步
            
            # 示例（假设已实现同步函数）:
            # record_data = build_record_from_ocr(dest_dir)
            # sync_result = sync_to_feishu(record_data)
            # result["record_id"] = sync_result.get("record_id")
            
            result["success"] = True
            
        except subprocess.TimeoutExpired:
            result["error"] = "工具提取超时（300秒），可能为网络不稳定"
        except Exception as e:
            result["error"] = str(e)
        
        results.append(result)
    
    return results


def print_batch_report(results: list[dict]):
    """打印批量处理汇总报告"""
    success_count = sum(1 for r in results if r["success"])
    fail_count = len(results) - success_count
    
    print(f"\n{'='*60}")
    print(f"📋 批量处理汇总报告")
    print(f"{'='*60}")
    print(f"总数: {len(results)} 篇 | ✅ 成功: {success_count} | ❌ 失败: {fail_count}")
    print(f"-" * 60)
    
    for i, r in enumerate(results, 1):
        status = "✅" if r["success"] else "❌"
        print(f"{i}. {status} {r['url'][:55]}...")
        if r.get("article_id"):
            print(f"   文章ID: {r['article_id']}")
        if r.get("record_id"):
            print(f"   记录ID: {r['record_id']}")
        if r.get("error"):
            print(f"   错误: {r['error']}")
    
    print(f"{'='*60}")
```

---

## 链接失效检测

### 常见失败模式

| 失败信息 | 根本原因 | 验证方法 | 处理建议 |
|---------|----------|----------|----------|
| `Parse error: Could not extract article title` | 链接已过期/需验证 | 检查 debug HTML 标题 | 从微信重新复制 |
| 标题为 `Weixin Official Accounts Platform` | 空页面（链接已失效） | browser_navigate 二次确认 | 请求新链接 |
| 标题为空 `<title></title>` | 需要登录态/scene参数 | 检查 URL 是否完整 | 补充 scene 参数 |
| Camoufox 启动失败 | 浏览器进程冲突 | 检查进程 `ps aux \| grep camoufox` | kill 进程后重试 |
| 超时（300s） | 网络不稳定/图片过多 | 分批处理或缩短超时 | 重试或检查网络 |

### debug HTML 诊断

```bash
# 查看最新 debug 文件中的标题
ls -lt /tmp/test_output/debug/debug_*.html | head -1

# 提取标题
cat /tmp/test_output/debug/debug_*.html | grep -o '<title>[^<]*</title>' | tail -1

# 判断结果：
# - <title>Weixin Official Accounts Platform</title> → 链接失效
# - <title></title> → 需要登录态
# - <title>文章标题</title> → 正常（解析阶段失败）
```

### browser_navigate 二次验证

当工具提取失败且 debug HTML 显示异常时，使用 Hermes 浏览器工具进行二次验证：

```python
# 步骤1: 访问链接
# browser_navigate(url=url)

# 步骤2: 获取快照
# snapshot = browser_snapshot(full=False)  # compact 模式足够

# 步骤3: 判断
# - 如果快照内容极少/空白 → 链接失效
# - 如果正常显示文章内容 → 工具问题，可尝试重试
```

---

## 关键经验

### 1. 必须使用系统 Python

```bash
# ✓ 正确
/usr/bin/python3 main.py "{url}" -o {output_base} -v

# ✗ 错误（可能缺少依赖）
# venv/bin/python3 main.py ...
```

### 2. 单篇失败不阻断

批量处理时，单篇失败应记录错误并继续处理后续文章，不得中断整个批次。

### 3. 永久目录同步

提取完成后必须复制到 `~/.hermes/output/{article_id}/`，确保上传脚本可以找到。

### 4. 失败分类

| 分类 | 处理 | 是否需要用户干预 |
|------|------|----------------|
| 链接失效 | 记录错误，跳过 | 是（请求新链接） |
| 工具崩溃 | kill 进程后重试 | 否 |
| 网络超时 | 重试 1-2 次 | 否 |
| 解析失败 | 检查 debug HTML，分析原因 | 可能 |

---

## 版本历史

| 版本 | 变更 |
|------|------|
| v1.0 | 初始版本：批量处理流程 + 链接失效检测 + debug HTML 诊断 |