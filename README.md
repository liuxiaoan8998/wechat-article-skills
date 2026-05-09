# 微信公众号运营自动化 Skill 集

本仓库存放微信公众号运营全流程自动化所需的 Hermes Skill 文件，位于 `web/` 目录下。

## 技能集合（Skill Set）

| Skill | 路径 | 功能说明 |
|-------|--------|---------|
| **文章搜索** | `web/wechat-article-search` | 基于极致了 API 搜索公众号历史文章，并同步至飞书 Base 选题库 |
| **文章提取** | `web/wechat-article-extraction-pro` | 从微信公众号链接抓取原始 HTML，生成 Markdown/HTML/JSON 等多格式输出 |
| **AI内容处理** | `web/wechat-article-for-ai-pro` | 提取文章内容并转化为 AI 友好格式（OCR 增强、图片提取） |
| **草稿处理** | `web/wechat-mp-draft-processor-pro` | 对原始 HTML 进行多步清洗，追加账号推广模板，生成可上传草稿 |
| **草稿上传** | `web/wechat-mp-draft-uploader` | 基于简立制作 API，将处理后的文章自动上传至微信公众号草稿箱 |
| **自动回复** | `web/wechat-autoreply-manager` | 上传完成后，自动分析「投递方式」并创建关键词自动回复规则 |
| **图片处理** | `web/image-processor` | 截图/裁剪、图片拼接、长图切片与格式转换等通用图片操作 |
| **批量处理** | `web/wechat-article-batch-processing` | 批量文章链接的串行执行、失效检测与故障排查 |
| **内容模式识别** | `web/wechat-article-content-patterns` | 识别长图模式 vs 正常 HTML 模式，处理不同发布形式 |
| **飞书网关** | `web/feishu-gateway` | 飞书（Lark）网关配置与故障排查 |

## 数据流转

```
【搜索】极致了 API → 飞书 Base 选题库
              ↓
【提取】微信文章链接 → 原始 HTML / Markdown / 图片
              ↓
【处理】草稿清洗 + 账号推广模板 → draft.html
              ↓
【上传】简立制作 API → 微信公众号草稿箱
              ↓
【回复】分析投递方式 → 创建关键词自动回复
```

## 环境配置说明

本项目运行需要以下密钥，请在本地配置后使用，**勿提交至公开仓库**：

| 配置项 | 占位符 | 说明 |
|--------|--------|------|
| 极致了 API Key | `JZL-YOUR_DAJIALA_API_KEY_HERE` | 公众号文章搜索 |
| 简立制作 API Key | `sk-YOUR_JIANLI_API_KEY_HERE` | 草稿上传 + 自动回复 |
| 飞书 Base Token | `YOUR_FEISHU_BASE_TOKEN_HERE` | 选题库读写 |
| 微信 AppID | `wxYOUR_APPID_HERE` | 公众号身份 |
| 微信 AppSecret | `YOUR_APPSECRET_HERE` | 公众号密钥 |

## 使用方式

本 Skill 集为 [Hermes Agent](https://github.com/hermes) 的扩展技能，需要将目录结构同步至 `~/.hermes/skills/web/` 下使用。

## 版本历史

- `v1.0` (2026-05-09) — 初始化，整合 10+ 个核心 Skill 至 Git 管理，仓库位于 `~/.hermes/skills/`
