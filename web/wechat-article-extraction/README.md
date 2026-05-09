# Git 版本管理说明

## 项目信息

- **项目路径**: `~/.hermes/skills/web/wechat-article-extraction/`
- **Git 仓库**: 已初始化
- **当前版本**: v2.0
- **提交记录**: 1 条

## 文件结构

```
.
├── .git/           # Git 版本控制
├── SKILL.md        # 快速参考文档
├── STANDARD.md     # 完整标准规范
└── README.md       # 本说明文件
```

## 版本历史

### v2.0 (2026-04-13)
- 初始版本
- 确定 wechat-article-for-ai 为标准工具
- 定义输出格式规范
- 完整工作流程文档

## 后续更新流程

每次修改后执行：

```bash
cd ~/.hermes/skills/web/wechat-article-extraction

# 查看修改状态
git status

# 添加修改的文件
git add SKILL.md STANDARD.md

# 提交并写清楚变更说明
git commit -m "v2.x: 变更说明

- 详细变更点1
- 详细变更点2
- 详细变更点3"
```

## 查看历史

```bash
# 查看提交历史
git log --oneline

# 查看详细差异
git log -p

# 查看文件修改历史
git log --follow -p SKILL.md
```

## 回滚版本

如需回滚到之前版本：

```bash
# 查看历史提交
git log --oneline

# 回滚到指定版本（替换abc123为实际commit hash）
git checkout abc123

# 或创建新分支保留当前
git checkout -b old-version abc123
```

## 注意事项

1. **每次修改后及时提交**，不要累积大量修改
2. **写清晰的提交信息**，说明变更内容
3. **保留历史版本**，便于回溯和对比
4. **重要变更前创建标签**：
   ```bash
   git tag -a v2.1 -m "版本2.1：添加可折叠内容功能"
   ```

---

**最后更新**: 2026-04-13  
**当前提交**: a65f6ed Initial commit: wechat-article-extraction skill v2.0
