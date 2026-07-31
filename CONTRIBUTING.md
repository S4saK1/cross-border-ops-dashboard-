# 贡献指南

感谢您对跨境产品资料中英对照系统的关注！我们欢迎任何形式的贡献，包括但不限于代码提交、问题报告、功能建议和文档改进。

## 如何贡献

### 1. 报告问题

如果您发现了bug或有功能建议，请通过以下方式提交：

1. **GitHub Issues**：使用提供的Issue模板
2. **问题描述**：详细描述问题或建议
3. **复现步骤**：提供详细的复现步骤
4. **环境信息**：包括操作系统、浏览器版本等
5. **截图/日志**：如适用，提供相关截图或日志

### 2. 代码贡献

#### 开发环境设置

```bash
# 1. Fork项目仓库
git clone https://github.com/your-username/bilingual-product-cms.git
cd bilingual-product-cms

# 2. 创建开发分支
git checkout -b feature/your-feature-name

# 3. 安装依赖
cd backend
pip install -r requirements.txt
cd ../frontend
npm install

# 4. 启动开发环境
docker compose up -d
```

#### 代码规范

##### Python（后端）
- 遵循 [PEP 8](https://peps.python.org/pep-0008/) 编码规范
- 使用类型注解（Type Hints）
- 编写清晰的文档字符串（Docstrings）
- 保持函数简洁，单一职责原则

##### TypeScript/React（前端）
- 使用TypeScript严格模式
- 遵循React Hooks最佳实践
- 使用Tailwind CSS进行样式管理
- 保持组件可复用性

##### 通用规范
- 编写清晰的提交信息
- 添加必要的测试用例
- 更新相关文档
- 保持代码简洁可读

#### 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/) 规范：

```
<类型>[可选 范围]: <描述>

[可选 正文]

[可选 脚注]
```

**类型说明**：
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式调整（不影响功能）
- `refactor`: 代码重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具相关
- `ci`: CI/CD相关

**示例**：
```
feat(auth): 添加密码强度验证

- 添加密码长度检查（最少8位）
- 添加大小写字母检查
- 添加数字检查
- 添加特殊字符检查

Closes #123
```

#### Pull Request流程

1. **确保代码质量**
   - 运行所有测试：`pytest`（后端）/ `npm test`（前端）
   - 检查代码风格：`flake8`（后端）/ `eslint`（前端）
   - 确保没有安全漏洞

2. **更新文档**
   - 更新相关API文档
   - 更新README.md（如需要）
   - 添加变更日志条目

3. **创建PR**
   - 填写PR模板
   - 关联相关Issue
   - 请求代码审查

4. **代码审查**
   - 审查标准、流程、严重级别与合并准入门槛详见 **[代码审查指南](docs/CODE_REVIEW_GUIDE.md)**
   - 提交前请完成 PR 模板中的**作者自检清单**（lint / type / test / 密钥扫描 / 无硬编码凭证等）
   - 审查者按指南 §6 清单逐条核对，结论为 `APPROVED` / `APPROVED_WITH_NITS` / `CHANGES_REQUESTED` / `REJECTED`
   - 合并前必须满足：CI 全绿、无未解决 🔴 Blocker、覆盖率不下降、至少 1 个 Approval（安全敏感路径需 2 个）
   - 响应审查意见，及时修复问题，修复后 `@reviewer` 重新请求审查，保持 PR 更新

### 3. 文档贡献

#### 文档类型
- **API文档**：FastAPI自动生成的OpenAPI文档
- **用户手册**：面向最终用户的使用指南
- **开发文档**：面向开发者的架构和设计文档
- **部署文档**：部署和运维相关文档

#### 文档规范
- 使用Markdown格式
- 保持结构清晰
- 提供实际示例
- 及时更新过时内容

### 4. 测试贡献

#### 测试类型
- **单元测试**：测试单个函数或模块
- **集成测试**：测试模块间交互
- **端到端测试**：测试完整用户流程

#### 测试规范
- 测试覆盖率目标：80%以上
- 测试命名清晰：`test_<功能>_<场景>`
- 测试独立：每个测试独立运行
- 测试可重复：多次运行结果一致

## 开发流程

### 1. 功能开发

```bash
# 1. 创建功能分支
git checkout -b feature/new-feature

# 2. 开发功能
# ... 编写代码 ...

# 3. 添加测试
# ... 编写测试 ...

# 4. 更新文档
# ... 更新文档 ...

# 5. 提交代码
git add .
git commit -m "feat: 添加新功能"

# 6. 推送分支
git push origin feature/new-feature

# 7. 创建Pull Request
```

### 2. Bug修复

```bash
# 1. 创建修复分支
git checkout -b fix/bug-description

# 2. 修复bug
# ... 修复代码 ...

# 3. 添加测试
# ... 添加回归测试 ...

# 4. 提交代码
git add .
git commit -m "fix: 修复bug描述"

# 5. 推送分支
git push origin fix/bug-description

# 6. 创建Pull Request
```

## 社区准则

### 行为准则
- 尊重所有参与者
- 保持专业和友善
- 接受建设性批评
- 避免人身攻击

### 沟通准则
- 使用清晰的语言
- 提供具体的反馈
- 保持耐心和理解
- 尊重不同观点

## 获得帮助

如果您在贡献过程中遇到问题，可以通过以下方式获得帮助：

1. **GitHub Discussions**：社区讨论区
2. **GitHub Issues**：问题报告和功能建议
3. **邮件联系**：项目维护者邮箱
4. **文档参考**：项目文档和Wiki

## 许可证

通过贡献代码，您同意您的贡献将在 [MIT许可证](LICENSE) 下发布。

## 致谢

感谢所有为项目做出贡献的人！您的贡献使这个项目变得更好。

---

**注意**：本指南可能会更新，请定期查看最新版本。