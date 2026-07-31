# ADR-009: 密钥信任边界
**状态:** Accepted
**日期:** 2026-07-31

## 背景

在早期版本中，`.dockerignore` **未排除** `.env` 文件，导致 `COPY . .` 将开发环境密钥烘焙进所有 Docker 镜像。任何能访问镜像的人（包括通过镜像仓库拉取）都能提取到 `SECRET_KEY`、数据库密码等敏感信息。

此外，`config.py` 的 `SECRET_KEY` 校验器在环境变量为空或不足 32 字符时，会**回退读取 `.env` 文件**（第 60-68 行）。这意味着即使 Docker Compose 正确传入了密钥，如果环境变量因任何原因丢失，镜像内烘焙的开发密钥可能**静默激活**，造成安全假象。

### 当前状态

- `.dockerignore` 已排除 `.env` 和 `.env.*`（第 11-12 行）
- 所有 Docker Compose 文件使用 `:?` 守卫强制要求密钥：
  - `docker-compose.yml`: `${SECRET_KEY:?SECRET_KEY is required}`
  - `docker-compose.prod.yml`: `${SECRET_KEY:?}`
  - `docker-compose.staging.yml`: `${SECRET_KEY:?}`
- `config.py` 的 `pydantic_settings` 配置仍指定 `env_file = ".env"`（第 94 行），使其在所有环境下默认读取 `.env` 文件

## 选项分析

### 选项 A: 保持现状（.dockerignore 排除 + env_file 回退）
| 维度 | 评估 |
|------|------|
| 复杂度 | Low — 已完成 |
| 安全性 | 中 — `.env` 不进入镜像，但 file fallback 仍存在 |
| 运维风险 | 中 — 生产环境若缺 env var，静默降级到空字符串/随机生成 |

### 选项 B: 生产环境禁用 .env 文件读取
| 维度 | 评估 |
|------|------|
| 复杂度 | Low — 条件判断 env_file |
| 安全性 | 高 — 生产环境完全依赖环境变量 |
| 运维风险 | 低 — `:?` 守卫确保缺失时立即失败 |

### 选项 C: 完全移除 env_file 支持
| 维度 | 评估 |
|------|------|
| 复杂度 | Medium — 影响所有环境 |
| 安全性 | 最高 |
| 开发体验 | 差 — 开发环境也需要手动设置环境变量 |

## 决策

选择**选项 B: 生产环境禁用 `.env` 文件读取**。

### 理由
1. **镜像零密钥**：`.dockerignore` 排除 `.env`，确保镜像不含任何密钥
2. **生产硬失败**：`ENVIRONMENT=production` 时，不读取 `.env` 文件；密钥必须通过 compose 环境变量传入，缺失时 `:?` 守卫立即阻止启动
3. **开发便利**：开发环境 (`ENVIRONMENT=development`) 仍可使用 `.env` 文件
4. **Pydantic Settings 行为**：在 `model_validator` 中根据 `ENVIRONMENT` 值决定是否设置 `env_file`，或使用条件逻辑阻止生产环境读取文件

### 实施要点

```python
# config.py — 生产环境不读取 .env
class Config:
    @staticmethod
    def customise_sources(init_settings, env_settings, file_secret_settings):
        # 生产环境：仅使用环境变量
        # 开发环境：允许 .env 文件
        return (env_settings,)
```

Docker Compose 密钥注入模式：
```yaml
environment:
  - SECRET_KEY=${SECRET_KEY:?SECRET_KEY is required in production}
  - ENVIRONMENT=production
```

## 影响

### 变容易
- 安全审计：明确密钥来源，无隐藏回退
- 生产部署：缺失密钥时立即失败，而非静默降级
- 镜像安全合规：镜像不含任何敏感信息

### 变困难
- 生产环境调试：必须通过环境变量注入所有配置
- CI/CD 流程：需确保所有环境变量在部署前设置

### 需要重新审视
- CI/CD 管道的密钥管理
- 开发环境的 `.env.example` 模板维护
- `config.py` 中 pydantic-settings 的 `env_file` 配置逻辑
