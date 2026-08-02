# Pull Request

> 审查标准见 [`docs/CODE_REVIEW_GUIDE.md`](docs/CODE_REVIEW_GUIDE.md)。提交前请完成下方自检清单。

## 描述

请包含对更改的简要描述以及相关动机。列出此 PR 解决的任何依赖项。

修复 # (issue)

## 更改类型

请删除不相关的选项：

- [ ] Bug 修复（修复了一个问题）
- [ ] 新功能（添加了功能）
- [ ] 破坏性更改（修复或功能会导致现有功能无法按预期工作）
- [ ] 文档更新（仅更新文档）
- [ ] 安全修复（涉及认证/授权/密钥/注入防护）

## 作者自检清单（合并前必须全部勾选）

- [ ] 本地已运行 lint：`flake8 app/`（后端）/ `npm run lint`（前端）
- [ ] 本地已运行类型检查：`npm run typecheck`（前端；后端类型检查见 flake8/bandit 门禁）
- [ ] 本地已运行测试且通过：`pytest`（后端）/ `npm run test`（前端）
- [ ] 已运行密钥扫描（如 `gitleaks detect` 或 `bandit -r app/`），无新增密钥/漏洞
- [ ] 无调试代码（`print` / `pdb` 断点 / 临时日志）遗留
- [ ] 无硬编码凭证 / API Key / SECRET_KEY（一律走环境变量）
- [ ] 涉及数据库结构变更时，已通过 Alembic 迁移（非 `create_all`）
- [ ] 涉及端点增删改时，已同步更新 OpenAPI 与 `docs/api-reference.md`
- [ ] 新增逻辑已补充测试，且未降低整体覆盖率
- [ ] 已更新 CHANGELOG.md（如适用）

## 安全敏感路径确认（如涉及，请勾选）

- [ ] Token 仅经 `httpOnly` + `Secure` + `SameSite` Cookie 传递（非 localStorage）
- [ ] 所有数据库访问使用 ORM / 参数化查询（无字符串拼接 SQL）
- [ ] 导出 CSV 单元格已对 `= + - @` 及换行转义（ADR-004）
- [ ] 关键 CRUD 操作已写入审计日志（ADR-002）
- [ ] 导出前已嵌入一致性检测阻断（ERROR 级阻断，ADR-003）

## 测试

请描述您为验证更改而运行的测试。提供说明以便我们能够复现。

- [ ] 单元测试
- [ ] 集成测试
- [ ] 端到端测试
- [ ] 手动测试

**测试配置**：
* Python 版本：
* Node.js 版本：
* 操作系统：

## Reviewer 检查（由审查者填写）

审查者请按 [`docs/CODE_REVIEW_GUIDE.md` §6 审查清单](docs/CODE_REVIEW_GUIDE.md) 逐条核对，并在评论中给出结论：
`APPROVED` / `APPROVED_WITH_NITS` / `CHANGES_REQUESTED` / `REJECTED`。
安全敏感路径需额外 1 名 Security Reviewer 批准（见 CODEOWNERS）。

## 截图（如果适用）

添加截图以帮助解释您的更改。

## 其他信息

添加任何其他有关 PR 的信息。
