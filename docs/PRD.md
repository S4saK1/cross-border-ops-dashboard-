# 跨境产品资料中英对照系统 — 产品需求文档 (PRD)

> **版本**: v1.0.0-MVP
> **日期**: 2025-07-20
> **状态**: Draft
> **产品定位**: 不是翻译工具，是跨境卖家的产品资料一致性管理系统

---

## 目录

1. [产品概述](#1-产品概述)
2. [功能需求（MVP）](#2-功能需求mvp)
3. [数据模型设计](#3-数据模型设计)
4. [API 端点设计](#4-api-端点设计)
5. [前端页面结构](#5-前端页面结构)
6. [CSV 导出规格](#6-csv-导出规格)
7. [一致性检测规格](#7-一致性检测规格)
8. [安全设计](#8-安全设计)
9. [非功能需求](#9-非功能需求)
10. [迭代路线图](#10-迭代路线图)

---

## 1. 产品概述

### 1.1 产品定位

**一句话**: 跨境卖家的产品资料一致性管理系统。

跨境卖家在 Amazon、阿里国际站等平台运营时，面临一个核心痛点：**同一个产品在不同平台上使用的中英文术语不一致**。比如"颜色"在 Amazon Listing 写成 "Colour"，在阿里国际站写成 "Color"；"面料"有时写 "Material"，有时写 "Fabric"，有时写 "Textile"。这种不一致会导致：

- 平台审核不通过或被降权
- 搜索关键词匹配率低，流量损失
- 品牌专业度受损，买家信任度下降
- 多平台运营时反复人工核对，效率极低

**本系统不是翻译工具**——我们不帮用户从中文翻译成英文。我们的核心价值是：

> **让用户已有的中英文产品资料保持术语一致、格式规范、一键导出到多平台。**

### 1.2 目标用户

| 用户画像 | 特征 | 核心需求 | 付费意愿 |
|----------|------|----------|----------|
| **新手卖家** | SKU < 50，刚起步做跨境 | 快速上架，不出错 | 月付 30-50 元 |
| **成长期卖家** | SKU 50-500，多平台运营 | 批量管理，效率优先 | 月付 100-300 元 |

### 1.3 核心价值

1. **术语一致性保障** — 内置 242 条跨品类术语词典 + 175 组同义词映射，自动检测并纠正不一致
2. **多平台一键导出** — 一次维护产品资料，导出 Amazon (37字段) 和阿里国际站 (29字段) 标准 CSV
3. **批量操作** — Excel/CSV 批量导入产品参数，告别逐条录入
4. **安全合规** — JWT 认证 + RBAC 四角色 + 审计日志，满足团队协作安全需求

### 1.4 竞品分析简述

| 竞品类型 | 代表产品 | 优势 | 劣势 | 我们的差异 |
|----------|----------|------|------|-----------|
| **通用翻译工具** | DeepL、Google Translate | 翻译质量高 | 不理解产品术语体系，无法保证一致性 | 我们不做翻译，做一致性管理 |
| **ERP 系统** | 通途、芒果店长 | 功能全面 | 价格高，学习成本高，术语管理弱 | 我们轻量聚焦，即开即用 |
| **表格管理** | Excel/Google Sheets | 零成本 | 无术语校验，人工维护易出错 | 我们提供结构化管理 + 自动检测 |
| **Listing 优化工具** | Helium 10、Jungle Scout | 数据驱动选品 | 面向英语市场，无中文对照能力 | 我们面向中文卖家，中英双语原生 |

**我们的独特定位**: 填补"通用翻译工具"和"重型 ERP"之间的空白——轻量、专注、开箱即用的跨境术语一致性管理。

---

## 2. 功能需求（MVP）

### 2.1 产品参数库 CRUD

**功能描述**: 用户可以创建、查看、编辑、删除产品信息。每条产品记录包含中英文一一对应的参数字段。系统提供结构化的产品参数管理界面。

**用户故事**:
- 作为新手卖家，我希望能快速录入一个产品的中英文参数（名称、颜色、材质、尺寸等），以便后续一键导出到 Amazon 和阿里国际站。
- 作为成长期卖家，我希望能批量编辑多个产品的同一参数字段，以便高效维护大量 SKU。

**验收标准**:
- [ ] 支持创建产品，必填字段：产品名称（中/英）、SKU、品类
- [ ] 中英文字段一一对应展示，左侧中文、右侧英文
- [ ] 支持编辑单个产品的任意字段
- [ ] 支持删除产品（软删除，30天可恢复）
- [ ] 支持列表分页展示，默认每页 20 条，支持搜索和品类筛选
- [ ] 创建/编辑时自动触发术语一致性检测（见 2.4）
- [ ] 操作记录写入审计日志

**优先级**: **P0**

---

### 2.2 术语词典管理

**功能描述**: 系统内置 242 条术语词典（覆盖 11 个品类），用户可在内置词典基础上添加自定义术语。词典记录中英文标准译法、平台特定译法、同义词和使用备注。

**用户故事**:
- 作为卖家，我希望在录入产品参数时，系统能自动提示标准术语，避免我用错词。
- 作为管理员，我希望能添加公司内部的专用术语到词典中。

**验收标准**:
- [ ] 内置词典不可删除，但可查看完整词条（中/英/品类/备注/平台译法）
- [ ] 支持按品类、关键词筛选词典
- [ ] 支持用户自定义添加新术语（仅 admin/editor 角色）
- [ ] 自定义术语与内置词典统一管理，标记 `is_builtin` 字段
- [ ] 词典变更记录写入审计日志
- [ ] 词典数据初始化时从 `data/dictionary.json` (242 条) 和 `data/synonyms.json` (175 组) 导入

**优先级**: **P0**

---

### 2.3 CSV 导出

**功能描述**: 用户选择产品和目标平台，系统自动将产品参数映射到对应平台的 CSV 模板并生成可下载文件。支持 Amazon（37 字段）和阿里国际站（29 字段）两个模板。

**用户故事**:
- 作为卖家，我希望选中几个产品后，一键导出 Amazon 标准格式的 CSV，直接上传到 Seller Central。
- 作为卖家，我希望能同时导出阿里国际站的 CSV，避免为两个平台分别整理数据。

**验收标准**:
- [ ] 支持单产品和批量导出（勾选多个产品）
- [ ] 导出前自动运行一致性检测，ERROR 级别问题阻断导出并提示
- [ ] CSV 字段映射严格遵循 `data/templates/amazon.json` 和 `data/templates/alibaba.json` 定义
- [ ] 所有文本值通过 CSV 注入防护处理（`sanitize_csv_cell`）
- [ ] 支持选择导出编码（UTF-8 with BOM 推荐，兼容 Excel 打开）
- [ ] 导出文件名格式：`{平台}_{品类}_{日期}.csv`
- [ ] 导出操作写入审计日志

**优先级**: **P0**

---

### 2.4 术语一致性检测

**功能描述**: 系统自动检测产品参数中的术语使用是否一致，分三个级别报告问题。用户可一键采纳建议修正。

**用户故事**:
- 作为卖家，我在录入产品参数后，希望系统能自动告诉我哪些术语用得不标准，方便我一次性修正。
- 作为团队管理员，我希望系统能在导出前拦截明显的术语错误，防止错误资料流出。

**验收标准**:
- [ ] **L1 精确匹配** (ERROR): 同一中文术语在不同产品中使用了不同的英文翻译 → 必须修正才能导出
  - 例: 产品 A 的"颜色"写 "Colour"，产品 B 的"颜色"写 "Color" → 报 ERROR
- [ ] **L2 同义词检测** (WARNING): 检测到非标准化的变体写法 → 建议修正但不阻断导出
  - 例: 使用 "Type-C" 而非标准的 "USB-C" → 报 WARNING
- [ ] **L3 拼写检测** (INFO): 检测到美式/英式拼写差异 → 建议统一
  - 例: 使用 "Colour" 而非 "Color" → 报 INFO
- [ ] 支持一键采纳修正建议（逐条或批量）
- [ ] 检测规则可扩展，基于 `data/consistency-rules.json` 配置
- [ ] 检测结果面板实时展示，包含：问题描述、严重级别、建议修正值、涉及的产品列表

**优先级**: **P0**

---

### 2.5 批量导入

**功能描述**: 用户可以上传 Excel (.xlsx) 或 CSV 文件，系统解析后批量创建或更新产品参数库。

**用户故事**:
- 作为成长期卖家，我已有 200+ 产品的 Excel 表格，我希望能直接导入系统，而不是逐条录入。

**验收标准**:
- [ ] 支持 .xlsx 和 .csv 两种格式上传
- [ ] 上传后进入预览模式：展示解析结果、匹配的字段、未识别的列
- [ ] 支持字段映射：用户将上传文件的列名映射到系统字段
- [ ] 支持两种导入模式：「新建」和「更新（按 SKU 匹配）」
- [ ] 导入前自动运行一致性检测，问题行高亮提示
- [ ] 导入结果汇总：成功 N 条、跳过 N 条、失败 N 条（含失败原因）
- [ ] 单次导入上限 1000 条产品记录
- [ ] 导入操作写入审计日志

**优先级**: **P1**

---

### 2.6 认证授权（JWT + RBAC）

**功能描述**: 系统提供基于 JWT 的认证和基于角色的权限控制（RBAC），支持四种角色。

**用户故事**:
- 作为管理员，我希望能控制团队成员的权限，比如只给运营人员编辑权限，不给删除权限。

**验收标准**:
- [ ] 支持注册/登录，密码 bcrypt 加密存储
- [ ] JWT Token 有效期 24 小时，Refresh Token 有效期 7 天
- [ ] 四种角色权限见下表
- [ ] 未登录用户只能访问登录/注册页面
- [ ] 越权操作返回 403，不泄露资源信息

**优先级**: **P0**（安全基线）

**RBAC 权限矩阵**:

| 资源/操作 | admin | editor | reviewer | viewer |
|-----------|-------|--------|----------|--------|
| 产品参数库 CRUD | ✅ | ✅ 创建/编辑 | 👁 只读 | 👁 只读 |
| 术语词典（内置） | 👁 只读 | 👁 只读 | 👁 只读 | 👁 只读 |
| 术语词典（自定义） | ✅ | ✅ | ❌ | ❌ |
| CSV 导出 | ✅ | ✅ | ✅ | ❌ |
| 批量导入 | ✅ | ✅ | ❌ | ❌ |
| 用户管理 | ✅ | ❌ | ❌ | ❌ |
| 审计日志 | ✅ | ❌ | 👁 自己的 | ❌ |
| 系统设置 | ✅ | ❌ | ❌ | ❌ |

---

### 2.7 审计日志

**功能描述**: 所有关键操作记录到结构化审计日志中，支持查询和追溯。

**用户故事**:
- 作为管理员，当团队成员修改了产品资料并导出后，我希望能追溯是谁在什么时间做了什么修改。

**验收标准**:
- [ ] 记录的操作类型：登录/登出、产品增删改、词典变更、批量导入、CSV 导出、用户管理
- [ ] 日志格式：结构化 JSON，包含 `timestamp`, `user_id`, `action`, `resource_type`, `resource_id`, `details`, `ip_address`
- [ ] 支持按时间范围、操作类型、用户筛选查询
- [ ] 日志保留 180 天，到期自动清理
- [ ] 日志不可删除、不可修改（仅 admin 可查看全部，reviewer 只看自己的）
- [ ] 写入性能：异步写入，不阻塞主业务流程

**优先级**: **P0**（安全基线）

---

## 3. 数据模型设计

### 3.1 实体概览

系统包含 4 个核心实体和 2 个关联表：

```
Product (产品参数库)
  ├── 1:N → ProductField (动态字段)
TermDictionary (术语词典)
UserProfile (用户)
AuditLog (审计日志)
ProductField (产品字段值)  ← 关联表
CustomTerm (自定义术语)     ← 关联表
```

### 3.2 Product（产品）

存储产品核心信息。字段采用固定核心字段 + JSON 动态扩展的设计。

| 字段 | 类型 | 约束 | 默认值 | 说明 |
|------|------|------|--------|------|
| `id` | UUID | PK | auto | 主键 |
| `sku` | VARCHAR(64) | UNIQUE, NOT NULL | — | 唯一商品编号 |
| `product_name_zh` | VARCHAR(200) | NOT NULL | — | 中文产品名称 |
| `product_name_en` | VARCHAR(200) | NOT NULL | — | 英文产品名称 |
| `category` | VARCHAR(50) | NOT NULL | — | 品类，枚举值见词典 categories |
| `brand` | VARCHAR(50) | NULLABLE | NULL | 品牌 |
| `description_zh` | TEXT | NULLABLE | NULL | 中文描述 |
| `description_en` | TEXT | NULLABLE | NULL | 英文描述 |
| `price` | DECIMAL(12,2) | NULLABLE | NULL | 单价 |
| `currency` | VARCHAR(3) | NOT NULL | 'USD' | 货币代码 |
| `stock` | INTEGER | NULLABLE | NULL | 库存数量 |
| `color_zh` | VARCHAR(100) | NULLABLE | NULL | 中文颜色 |
| `color_en` | VARCHAR(100) | NULLABLE | NULL | 英文颜色 |
| `material_zh` | VARCHAR(100) | NULLABLE | NULL | 中文材质 |
| `material_en` | VARCHAR(100) | NULLABLE | NULL | 英文材质 |
| `size` | VARCHAR(100) | NULLABLE | NULL | 尺寸 |
| `weight` | DECIMAL(10,2) | NULLABLE | NULL | 重量 |
| `weight_unit` | VARCHAR(10) | NULLABLE | 'kg' | 重量单位 |
| `length` | DECIMAL(10,2) | NULLABLE | NULL | 长 |
| `width` | DECIMAL(10,2) | NULLABLE | NULL | 宽 |
| `height` | DECIMAL(10,2) | NULLABLE | NULL | 高 |
| `dimension_unit` | VARCHAR(10) | NULLABLE | 'cm' | 尺寸单位 |
| `origin` | VARCHAR(50) | NULLABLE | 'China' | 产地 |
| `model_number` | VARCHAR(64) | NULLABLE | NULL | 型号 |
| `extra_fields` | JSON | NULLABLE | `{}` | 扩展字段（品类特定参数） |
| `consistency_status` | VARCHAR(20) | NOT NULL | 'unchecked' | 一致性状态：unchecked/passed/warning/error |
| `consistency_issues` | JSON | NULLABLE | `[]` | 最近一次检测的问题列表 |
| `is_deleted` | BOOLEAN | NOT NULL | false | 软删除标记 |
| `deleted_at` | TIMESTAMP | NULLABLE | NULL | 删除时间 |
| `created_by` | UUID | FK → UserProfile | — | 创建者 |
| `created_at` | TIMESTAMP | NOT NULL | NOW() | 创建时间 |
| `updated_at` | TIMESTAMP | NOT NULL | NOW() | 更新时间 |

**索引**:
- `idx_product_sku` (UNIQUE) — SKU 查询
- `idx_product_category` — 品类筛选
- `idx_product_name` — 名称搜索（覆盖中英文）
- `idx_product_created_by` — 按创建者查询
- `idx_product_is_deleted` — 软删除过滤

### 3.3 TermDictionary（术语词典）

| 字段 | 类型 | 约束 | 默认值 | 说明 |
|------|------|------|--------|------|
| `id` | UUID | PK | auto | 主键 |
| `zh` | VARCHAR(100) | NOT NULL | — | 中文术语 |
| `en` | VARCHAR(100) | NOT NULL | — | 标准英文术语 |
| `category` | VARCHAR(50) | NOT NULL | — | 品类 |
| `note` | TEXT | NULLABLE | NULL | 使用备注 |
| `synonyms` | JSON | NOT NULL | `[]` | 同义词/变体列表 |
| `platform_amazon` | VARCHAR(100) | NULLABLE | NULL | Amazon 平台专用术语 |
| `platform_alibaba` | VARCHAR(100) | NULLABLE | NULL | 阿里国际站专用术语 |
| `is_builtin` | BOOLEAN | NOT NULL | true | 是否内置词典 |
| `created_by` | UUID | FK → UserProfile | NULL | 创建者（内置为 NULL） |
| `created_at` | TIMESTAMP | NOT NULL | NOW() | 创建时间 |
| `updated_at` | TIMESTAMP | NOT NULL | NOW() | 更新时间 |

**索引**:
- `idx_term_zh_en` (UNIQUE) — 中英文组合唯一
- `idx_term_category` — 品类筛选
- `idx_term_is_builtin` — 内置/自定义区分

### 3.4 UserProfile（用户）

| 字段 | 类型 | 约束 | 默认值 | 说明 |
|------|------|------|--------|------|
| `id` | UUID | PK | auto | 主键 |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | — | 登录邮箱 |
| `password_hash` | VARCHAR(255) | NOT NULL | — | bcrypt 密码哈希 |
| `display_name` | VARCHAR(100) | NOT NULL | — | 显示名称 |
| `role` | VARCHAR(20) | NOT NULL | 'viewer' | 角色：admin/editor/reviewer/viewer |
| `is_active` | BOOLEAN | NOT NULL | true | 账户是否激活 |
| `last_login_at` | TIMESTAMP | NULLABLE | NULL | 最后登录时间 |
| `created_at` | TIMESTAMP | NOT NULL | NOW() | 创建时间 |
| `updated_at` | TIMESTAMP | NOT NULL | NOW() | 更新时间 |

**索引**:
- `idx_user_email` (UNIQUE) — 登录查询
- `idx_user_role` — 按角色查询

### 3.5 AuditLog（审计日志）

| 字段 | 类型 | 约束 | 默认值 | 说明 |
|------|------|------|--------|------|
| `id` | UUID | PK | auto | 主键 |
| `user_id` | UUID | FK → UserProfile | — | 操作用户 |
| `action` | VARCHAR(50) | NOT NULL | — | 操作类型（见枚举） |
| `resource_type` | VARCHAR(50) | NOT NULL | — | 资源类型（product/term/user/import/export） |
| `resource_id` | VARCHAR(64) | NULLABLE | NULL | 资源 ID |
| `details` | JSON | NULLABLE | `{}` | 操作详情 |
| `ip_address` | VARCHAR(45) | NULLABLE | NULL | 客户端 IP（支持 IPv6） |
| `created_at` | TIMESTAMP | NOT NULL | NOW() | 操作时间 |

**枚举值 — action**:
`login`, `logout`, `create`, `update`, `delete`, `restore`, `import`, `export`, `consistency_check`, `user_create`, `user_update`, `user_delete`

**索引**:
- `idx_audit_user_id` — 按用户查询
- `idx_audit_created_at` — 按时间范围查询
- `idx_audit_action` — 按操作类型查询
- `idx_audit_resource` — 资源类型 + ID 组合查询

### 3.6 实体关系图（文字描述）

```
UserProfile (1) ──── (N) Product          [created_by]
UserProfile (1) ──── (N) AuditLog         [user_id]
UserProfile (1) ──── (N) TermDictionary   [created_by, 自定义词典]

Product: extra_fields (JSON) 承载品类特定的动态参数
TermDictionary: synonyms (JSON) 承载同义词变体列表
TermDictionary: platform_* 承载平台特定译法
```

**设计决策**:
- Product 使用**固定核心字段 + JSON 扩展**的混合模型，而非全动态字段。理由：核心字段（SKU、名称、颜色、材质等）占 80% 使用场景，固定字段保证查询效率和数据完整性；JSON 扩展字段处理 20% 的品类特定参数（如 3C 的 RAM、服装的洗涤说明）。
- 所有实体使用 UUID 主键，避免自增 ID 暴露数据规模。

---

## 4. API 端点设计

### 4.1 认证相关

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| `POST` | `/api/v1/auth/register` | 用户注册 | 公开 |
| `POST` | `/api/v1/auth/login` | 登录，返回 JWT | 公开 |
| `POST` | `/api/v1/auth/refresh` | 刷新 Token | 需认证 |
| `GET` | `/api/v1/auth/me` | 获取当前用户信息 | 需认证 |

**POST `/api/v1/auth/login`**

请求 Body:
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

响应:
```json
{
  "access_token": "<access_token>",
  "refresh_token": "<refresh_token>",
  "token_type": "Bearer",
  "expires_in": 86400,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "display_name": "张三",
    "role": "editor"
  }
}
```

### 4.2 产品管理

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| `GET` | `/api/v1/products` | 产品列表（分页、搜索、筛选） | viewer+ |
| `POST` | `/api/v1/products` | 创建产品 | editor+ |
| `GET` | `/api/v1/products/:id` | 产品详情 | viewer+ |
| `PUT` | `/api/v1/products/:id` | 更新产品 | editor+ |
| `DELETE` | `/api/v1/products/:id` | 删除产品（软删除） | admin |
| `POST` | `/api/v1/products/:id/restore` | 恢复已删除产品 | admin |
| `POST` | `/api/v1/products/batch-delete` | 批量删除 | admin |
| `POST` | `/api/v1/products/check-consistency` | 运行一致性检测 | viewer+ |
| `GET` | `/api/v1/products/stats` | 产品统计（总数、品类分布等） | viewer+ |

**GET `/api/v1/products`**

查询参数:
- `page` (int, default 1)
- `page_size` (int, default 20, max 100)
- `search` (string) — 搜索产品名称（中英文）
- `category` (string) — 按品类筛选
- `consistency_status` (string) — 按一致性状态筛选
- `sort_by` (string, default `updated_at`) — 排序字段
- `sort_order` (string, default `desc`) — asc/desc

响应:
```json
{
  "items": [
    {
      "id": "...",
      "sku": "SKU-001",
      "product_name_zh": "男士纯棉T恤",
      "product_name_en": "Men's Cotton T-Shirt",
      "category": "服装鞋帽",
      "brand": "MyBrand",
      "consistency_status": "passed",
      "created_at": "2025-07-20T10:00:00Z",
      "updated_at": "2025-07-20T10:00:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

**POST `/api/v1/products`**

请求 Body:
```json
{
  "sku": "SKU-001",
  "product_name_zh": "男士纯棉T恤",
  "product_name_en": "Men's Cotton T-Shirt",
  "category": "服装鞋帽",
  "brand": "MyBrand",
  "color_zh": "白色",
  "color_en": "White",
  "material_zh": "纯棉",
  "material_en": "100% Cotton",
  "size": "S/M/L/XL",
  "weight": 0.2,
  "weight_unit": "kg",
  "price": 15.99,
  "currency": "USD",
  "extra_fields": {
    "fabric": "100% Cotton",
    "fit_type": "Regular Fit",
    "care_instructions": "Machine wash cold"
  }
}
```

### 4.3 术语词典

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| `GET` | `/api/v1/terms` | 词典列表（分页、搜索） | viewer+ |
| `GET` | `/api/v1/terms/:id` | 词典条目详情 | viewer+ |
| `POST` | `/api/v1/terms` | 添加自定义术语 | editor+ |
| `PUT` | `/api/v1/terms/:id` | 更新术语（仅自定义） | editor+ |
| `DELETE` | `/api/v1/terms/:id` | 删除术语（仅自定义） | admin |
| `GET` | `/api/v1/terms/categories` | 获取所有品类列表 | viewer+ |
| `GET` | `/api/v1/terms/suggest` | 术语自动补全 | viewer+ |

**GET `/api/v1/terms`**

查询参数:
- `category` (string) — 品类筛选
- `q` (string) — 搜索关键词（匹配 zh 或 en）
- `is_builtin` (boolean) — 筛选内置/自定义
- `page`, `page_size` — 分页

**GET `/api/v1/terms/suggest`**

查询参数:
- `q` (string, required) — 用户输入的关键词前缀
- `category` (string) — 限定品类

响应:
```json
{
  "suggestions": [
    { "zh": "颜色", "en": "Color", "category": "通用属性" },
    { "zh": "色号", "en": "Shade", "category": "美妆个护" }
  ]
}
```

### 4.4 CSV 导出

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| `POST` | `/api/v1/export/preview` | 导出预览（含一致性检测结果） | reviewer+ |
| `POST` | `/api/v1/export/csv` | 执行 CSV 导出 | reviewer+ |

**POST `/api/v1/export/csv`**

请求 Body:
```json
{
  "platform": "amazon",
  "product_ids": ["uuid1", "uuid2"],
  "encoding": "utf-8-sig",
  "skip_on_error": false
}
```

响应: CSV 文件流（`Content-Type: text/csv; charset=utf-8`）

错误响应 (400):
```json
{
  "error": "consistency_error",
  "message": "导出被阻断：发现 3 个 ERROR 级别的一致性问题",
  "issues": [
    {
      "severity": "ERROR",
      "field": "color_en",
      "zh_term": "颜色",
      "found_values": ["Color", "Colour"],
      "suggestion": "Color",
      "affected_products": ["SKU-001", "SKU-015"]
    }
  ]
}
```

### 4.5 批量导入

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| `POST` | `/api/v1/import/upload` | 上传导入文件 | editor+ |
| `POST` | `/api/v1/import/preview` | 解析预览 + 字段映射 | editor+ |
| `POST` | `/api/v1/import/execute` | 执行导入 | editor+ |

**POST `/api/v1/import/upload`**

请求: `multipart/form-data`

响应:
```json
{
  "file_id": "import-file-uuid",
  "filename": "products_2025.xlsx",
  "row_count": 200,
  "detected_columns": ["产品名称", "颜色", "材质", "SKU"],
  "preview_rows": [
    { "产品名称": "纯棉T恤", "颜色": "白色", "材质": "100%棉", "SKU": "T-001" }
  ]
}
```

### 4.6 审计日志

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| `GET` | `/api/v1/audit-logs` | 查询审计日志 | admin（全部）/ reviewer（仅自己） |
| `GET` | `/api/v1/audit-logs/:id` | 日志详情 | admin |

### 4.7 用户管理

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| `GET` | `/api/v1/users` | 用户列表 | admin |
| `POST` | `/api/v1/users` | 创建用户 | admin |
| `PUT` | `/api/v1/users/:id` | 更新用户信息/角色 | admin |
| `DELETE` | `/api/v1/users/:id` | 禁用用户（软删除） | admin |

---

## 5. 前端页面结构

### 5.1 路由表

| 路由 | 页面 | 说明 | 权限 |
|------|------|------|------|
| `/login` | 登录页 | 登录/注册 | 公开 |
| `/` | 仪表盘 | 数据概览 | viewer+ |
| `/products` | 产品列表 | 产品管理主页 | viewer+ |
| `/products/new` | 创建产品 | 新建产品表单 | editor+ |
| `/products/:id` | 产品详情 | 查看/编辑产品参数 | viewer+ |
| `/products/import` | 批量导入 | Excel/CSV 导入 | editor+ |
| `/terms` | 术语词典 | 词典管理 | viewer+ |
| `/terms/new` | 添加术语 | 自定义术语表单 | editor+ |
| `/export` | CSV 导出 | 选择产品导出 | reviewer+ |
| `/audit` | 审计日志 | 操作日志查询 | admin |
| `/settings/users` | 用户管理 | 团队成员管理 | admin |

### 5.2 核心页面设计

#### 5.2.1 仪表盘 (`/`)

核心组件:
- **数据卡片行**: 产品总数、术语词典条数、本月导出次数、一致性问题数
- **品类分布图**: 饼图/柱状图展示各品类产品占比
- **最近更新**: 最近 10 条产品更新记录
- **一致性状态概览**: 通过/警告/错误的产品占比

#### 5.2.2 产品列表 (`/products`)

核心组件:
- **搜索栏**: 关键词搜索（产品名称、SKU）+ 品类下拉筛选 + 一致性状态筛选
- **批量操作栏**: 勾选后显示批量删除、批量导出按钮
- **数据表格**:
  | 列 | 说明 |
  |----|------|
  | 勾选框 | 批量操作 |
  | SKU | 产品编号 |
  | 中文名称 | 产品中文名 |
  | 英文名称 | 产品英文名 |
  | 品类 | 所属品类 |
  | 一致性状态 | 🟢通过 / 🟡警告 / 🔴错误 / ⚪未检测 |
  | 更新时间 | 最后更新 |
  | 操作 | 查看/编辑/删除 |

- **分页器**: 底部分页 + 每页条数切换

#### 5.2.3 产品详情/编辑 (`/products/:id`)

核心组件:
- **双栏对照编辑**:
  - 左栏: 中文参数（灰色背景标识语言）
  - 右栏: 英文参数（白色背景标识语言）
  - 中间: 术语提示图标（点击显示标准术语建议）
- **核心参数区**: SKU、名称、品牌、品类、描述
- **物理参数区**: 颜色、材质、尺寸、重量
- **价格参数区**: 价格、货币、库存
- **扩展字段区**: 品类特定参数（根据品类动态展示）
- **一致性检测面板**: 右侧悬浮面板，实时展示检测结果
- **操作栏**: 保存、导出、删除

#### 5.2.4 术语词典 (`/terms`)

核心组件:
- **品类标签栏**: 横向标签切换品类，支持"全部"
- **搜索框**: 中英文关键词搜索
- **词典表格**:
  | 列 | 说明 |
  |----|------|
  | 中文 | 标准中文术语 |
  | 英文 | 标准英文术语 |
  | 品类 | 所属品类 |
  | 同义词 | 变体列表 |
  | Amazon | 平台专用译法 |
  | 阿里 | 平台专用译法 |
  | 来源 | 内置/自定义 |
  | 操作 | 查看/编辑/删除（仅自定义） |

- **新增术语按钮**: 弹窗表单

#### 5.2.5 CSV 导出 (`/export`)

核心组件:
- **平台选择**: Amazon / 阿里国际站 卡片式选择
- **产品选择**: 从产品列表中搜索勾选，支持全选当前页
- **导出预览**: 展示字段映射关系 + 一致性检测结果
  - ✅ 已映射字段数
  - ⚠️ WARNING 问题数（允许导出）
  - ❌ ERROR 问题数（阻断导出）
- **导出按钮**: 有 ERROR 时置灰并显示原因，无 ERROR 时可点击
- **编码选择**: UTF-8 / UTF-8 with BOM（默认 BOM）

#### 5.2.6 批量导入 (`/products/import`)

核心组件:
- **上传区域**: 拖拽上传区 + 文件类型提示（.xlsx / .csv）
- **字段映射**: 左列上传文件列名，右列系统字段下拉选择
- **预览表格**: 展示前 10 行解析结果，问题行红色高亮
- **导入模式**: 新建 / 按 SKU 更新（单选）
- **导入结果**: 成功/跳过/失败计数 + 失败详情下载

### 5.3 用户交互流程

#### 主流程: 从录入到导出

```
用户登录
  ↓
仪表盘 → 查看产品概览
  ↓
产品列表 → 新建产品 / 批量导入
  ↓
产品详情 → 中英双栏编辑
  ↓ （自动触发一致性检测）
一致性面板 → 查看问题 → 一键修正
  ↓
导出页面 → 选择平台 → 预览映射
  ↓ （自动运行最终检测）
下载 CSV → 上传到 Amazon / 阿里国际站
```

---

## 6. CSV 导出规格

### 6.1 Amazon 模板 (37 字段)

数据来源: `data/templates/amazon.json`

| 平台字段 | 系统字段 | 必填 | 类型 | 说明 |
|----------|----------|------|------|------|
| `item_type` | product_type | ✅ | enum | 产品类型 |
| `item_name` | product_name_en | ✅ | string(200) | 产品标题 |
| `external_product_id` | sku | ✅ | string | UPC/EAN/ASIN |
| `external_product_id_type` | id_type | ✅ | enum | ID 类型 |
| `brand_name` | brand | ✅ | string(50) | 品牌名 |
| `manufacturer` | manufacturer | — | string(50) | 制造商 |
| `standard_price` | price | ✅ | decimal | 售价 |
| `currency` | currency | ✅ | enum | 货币代码 |
| `quantity` | stock | ✅ | integer | 库存数量 |
| `main_image_url` | main_image_url | ✅ | url | 主图 URL |
| `other_image_url1` | image_url_1 | — | url | 附图 1 |
| `other_image_url2` | image_url_2 | — | url | 附图 2 |
| `description` | description_en | ✅ | html(2000) | 产品描述(HTML) |
| `bullet_point1` | bullet_1 | ✅ | string(500) | 卖点 1 |
| `bullet_point2` | bullet_2 | — | string(500) | 卖点 2 |
| `bullet_point3` | bullet_3 | — | string(500) | 卖点 3 |
| `bullet_point4` | bullet_4 | — | string(500) | 卖点 4 |
| `bullet_point5` | bullet_5 | — | string(500) | 卖点 5 |
| `generic_keywords` | keywords | — | string(250) | 搜索关键词 |
| `item_weight` | weight | ✅ | decimal | 产品重量 |
| `item_weight_unit_of_measure` | weight_unit | ✅ | enum | 重量单位 |
| `item_length` | length | — | decimal | 长 |
| `item_width` | width | — | decimal | 宽 |
| `item_height` | height | — | decimal | 高 |
| `item_dimensions_unit_of_measure` | dimension_unit | — | enum | 尺寸单位 |
| `color_name` | color_en | ✅ | string | 颜色 |
| `size_name` | size | — | string | 尺寸 |
| `material_type` | material_en | — | string | 材质 |
| `country_of_origin` | origin | ✅ | string | 产地 |
| `condition_type` | condition | ✅ | enum | 商品状态 |
| `list_price` | msrp | — | decimal | 建议零售价 |
| `category` | category | ✅ | string | Amazon 品类 |
| `parent_sku` | parent_sku | — | string | 父 SKU |
| `variation_theme` | variation_theme | — | enum | 变体主题 |
| `gift_wrap` | gift_wrap | — | boolean | 是否支持礼品包装 |
| `shipping_weight` | shipping_weight | — | decimal | 物流重量 |

**枚举值**:
- `condition_type`: New, Refurbished, Used - Like New, Used - Good, Used - Acceptable
- `currency`: USD, EUR, GBP, JPY, CAD, AUD, INR
- `weight_unit`: oz, lb, g, kg
- `dimension_unit`: inches, centimeters
- `external_product_id_type`: UPC, EAN, JAN, ISBN, GCID, ASIN
- `variation_theme`: Size/Color, Color/Size, Size, Color

### 6.2 阿里国际站模板 (29 字段)

数据来源: `data/templates/alibaba.json`

| 平台字段 | 系统字段 | 必填 | 类型 | 说明 |
|----------|----------|------|------|------|
| `Subject` | product_name_en | ✅ | string(128) | 产品标题 |
| `Brand Name` | brand | — | string(50) | 品牌名 |
| `Model Number` | model_number | ✅ | string | 型号 |
| `Product Description` | description_en | ✅ | html(10000) | 产品描述 |
| `Price` | price | ✅ | decimal | 单价(USD) |
| `MOQ` | moq | ✅ | integer | 最小起订量 |
| `Unit` | unit | ✅ | enum | 计价单位 |
| `Supply Ability` | supply_ability | — | string | 月供应能力 |
| `Payment Terms` | payment_terms | ✅ | enum | 付款方式 |
| `Delivery Time` | delivery_time | ✅ | string | 交货天数 |
| `Port` | port | — | string | 发货港口 |
| `Color` | color_en | ✅ | string | 颜色 |
| `Material` | material_en | ✅ | string | 材质 |
| `Size` | size | ✅ | string | 尺寸 |
| `Weight` | weight | — | decimal | 重量 |
| `Weight Unit` | weight_unit | — | enum | 重量单位 |
| `Certification` | certification | — | string | 认证 |
| `Usage` | usage | — | string | 用途 |
| `Place of Origin` | origin | ✅ | string | 产地 |
| `Image 1` | main_image_url | ✅ | url | 主图 URL |
| `Image 2` | image_url_1 | — | url | 附图 1 |
| `Image 3` | image_url_2 | — | url | 附图 2 |
| `Category` | category | ✅ | string | 阿里品类 |
| `Feature` | features | — | string(1000) | 产品特性 |
| `Style Number` | style_number | — | string | 款号 |
| `Size Range` | size_range | — | string | 尺码范围 |
| `Logo` | logo | — | string | Logo 定制 |
| `After-sales Service` | warranty | — | string | 售后服务 |
| `Sample` | sample_info | — | string | 样品信息 |

**枚举值**:
- `Unit`: Piece/Pieces, Set, Meter, Kilogram, Ton, Square Meter, Liter, Pair, Box, Carton
- `Payment Terms`: T/T, PayPal, L/C, D/A, D/P, Western Union, MoneyGram, Credit Card, Alipay, WeChat Pay
- `Weight Unit`: g, kg, oz, lb

**注意事项**:
- 阿里字段名**区分大小写**（如 `Subject` 不是 `subject`）
- Price 应使用 USD
- MOQ 对 B2B 买家至关重要——买家会按 MOQ 筛选

### 6.3 导出流程

```
用户选择平台 + 产品
        ↓
系统运行一致性检测
        ↓
  ┌─── ERROR 存在? ───┐
  │ YES               │ NO
  ↓                   ↓
返回错误列表      生成 CSV
(阻断导出)          ↓
            所有文本值通过 sanitize_csv_cell
                  ↓
            字段映射（系统字段 → 平台字段）
                  ↓
            填充枚举值校验
                  ↓
            生成文件流（UTF-8 BOM）
                  ↓
            触发浏览器下载
                  ↓
            写入审计日志
```

### 6.4 CSV 注入防护

所有文本字段在写入 CSV 前必须经过 `sanitize_csv_cell()` 处理：

```python
def sanitize_csv_cell(value: str) -> str:
    """防止 CSV 公式注入攻击"""
    if not isinstance(value, str):
        return value
    # 危险前缀字符
    dangerous_prefixes = ('=', '+', '-', '@', '\t', '\r', '\n')
    if value.startswith(dangerous_prefixes):
        return "'" + value  # 前缀单引号转义
    return value
```

### 6.5 错误处理

| 错误场景 | HTTP 状态码 | 响应格式 |
|----------|-------------|----------|
| 一致性 ERROR 阻断 | 400 | JSON + issues 列表 |
| 产品不存在 | 404 | JSON error |
| 字段映射失败 | 422 | JSON + missing_fields |
| 无导出权限 | 403 | JSON error |
| 文件生成异常 | 500 | JSON error + 告警 |

---

## 7. 一致性检测规格

### 7.1 检测引擎逻辑

检测引擎采用**三层管道**架构，依次执行：

```
输入：产品参数集合
        ↓
  ┌── L1 精确匹配 ──┐
  │  (ERROR)         │
  ↓                  │
  ┌── L2 同义词检测 ──┘
  │  (WARNING)
  ↓
  ┌── L3 拼写检测 ──┐
  │  (INFO)         │
  ↓                  │
输出：分级问题列表 ──┘
```

### 7.2 规则定义

#### L1 精确匹配 (ERROR)

**逻辑**: 对于同一中文术语，在所有产品中检索其英文翻译的使用情况。如果发现同一中文术语对应了 2 种以上不同的英文写法，报 ERROR。

**数据源**: `TermDictionary` 表中 `zh` 字段相同的记录

**示例**:
```
产品 A: 颜色 → Color
产品 B: 颜色 → Colour
→ L1 ERROR: "颜色" 有 2 种英文译法: ["Color", "Colour"]
```

**处理方式**: ERROR 级别问题必须全部解决后才能导出 CSV。用户可点击"一键采纳标准值"批量修正。

#### L2 同义词检测 (WARNING)

**逻辑**: 检测产品参数中是否使用了非标准化的同义词变体。参考 `data/synonyms.json` 和 `TermDictionary.synonyms`。

**数据源**: `synonyms.json` 中 `synonym_groups` 的 `variants` 列表

**示例**:
```
产品参数: Charging Port = "Type-C"
→ L2 WARNING: "Type-C" 是 "USB-C" 的变体，建议使用标准写法
→ 修正建议: "USB-C"
```

**处理方式**: WARNING 级别不阻断导出，但会在导出预览中高亮提示。用户可选择批量采纳或忽略。

#### L3 拼写检测 (INFO)

**逻辑**: 检测美式/英式拼写差异。参考 `data/consistency-rules.json` 中的 `standardization` 和 `auto_fix_rules`。

**数据源**: `consistency-rules.json` 中 `auto_fix_rules` 的 pattern/replacement 映射

**示例**:
```
产品参数: Color = "Colour"
→ L3 INFO: 建议统一为美式拼写 "Color"（Amazon 平台要求）
```

**处理方式**: INFO 级别仅建议，不影响导出。用户可在设置中选择自动应用 INFO 修正。

### 7.3 检测触发时机

| 触发点 | 触发方式 | 说明 |
|--------|----------|------|
| 产品保存时 | 自动 | 单产品创建/编辑保存后自动运行 |
| 产品详情页 | 实时 | 编辑时防抖触发（500ms 延迟） |
| 批量导入后 | 自动 | 导入完成后对所有新增/更新的产品运行 |
| 导出预览时 | 手动 | 用户点击"导出预览"时运行 |
| 全局扫描 | 手动 | 管理员可触发全库扫描 |

### 7.4 规则配置 (`data/consistency-rules.json`)

```json
{
  "rules": {
    "exact_match": {
      "enabled": true,
      "severity": "ERROR",
      "description": "同一中文术语的英文翻译必须完全一致"
    },
    "synonym_check": {
      "enabled": true,
      "severity": "WARNING",
      "description": "检测同义词变体，建议使用标准化用词"
    },
    "spelling_check": {
      "enabled": true,
      "severity": "INFO",
      "description": "检测美式/英式拼写差异，建议统一"
    }
  },
  "severity_definitions": {
    "ERROR": "明显错误或不一致，必须修正后才能导出",
    "WARNING": "不一致但不一定是错误，建议确认",
    "INFO": "建议优化，不影响导出"
  }
}
```

### 7.5 自动修正规则

系统内置以下自动修正规则（来自 `consistency-rules.json`）：

| 原始值 | 修正为 | 原因 | 严重级别 |
|--------|--------|------|----------|
| Colour | Color | Amazon 平台统一美式拼写 | INFO |
| Fibre | Fiber | 统一美式拼写 | INFO |
| Honour | Honor | 统一美式拼写 | INFO |
| Type-C | USB-C | 推荐标准写法 | WARNING |

### 7.6 结果展示

检测结果面板包含以下信息：

```
┌─────────────────────────────────────────┐
│  一致性检测结果                           │
├─────────────────────────────────────────┤
│  🔴 ERROR: 2 项  🟡 WARNING: 5 项  🔵 INFO: 3 项  │
├─────────────────────────────────────────┤
│  ❌ ERROR: "颜色" 术语不一致              │
│     找到: Color (3个产品), Colour (1个产品)    │
│     建议: 统一为 "Color"                   │
│     [一键修正] [查看详情]                    │
├─────────────────────────────────────────┤
│  ⚠️ WARNING: "充电接口" 使用非标准写法     │
│     找到: Type-C → 建议: USB-C             │
│     [一键修正] [忽略]                       │
└─────────────────────────────────────────┘
```

---

## 8. 安全设计

### 8.1 认证流程

```
用户提交邮箱+密码
        ↓
后端验证密码 (bcrypt)
        ↓
  ┌── 验证通过 ──┐
  │              │ NO → 返回 401
  ↓              
签发 JWT Token (access + refresh)
  ↓
写入审计日志 (action: login)
  ↓
返回 Token 给客户端
  ↓
客户端存储 Token (httpOnly cookie 或内存)
  ↓
后续请求携带 Authorization: Bearer <token>
  ↓
中间件验证 Token → 注入 user_id 到请求上下文
```

**Token 规格**:
- Access Token: 24 小时有效，载荷包含 `user_id`, `role`, `exp`
- Refresh Token: 7 天有效，用于无感续期
- 签名算法: HS256
- Token 存储: 建议 httpOnly secure cookie，避免 localStorage XSS

### 8.2 RBAC 权限矩阵

完整的资源-操作权限矩阵（详见 2.6 节）：

| 角色 | 说明 | 产品 | 词典(内置) | 词典(自定义) | 导出 | 导入 | 用户 | 日志 | 设置 |
|------|------|------|-----------|-------------|------|------|------|------|------|
| **admin** | 管理员 | CRUD | 读 | CRUD | ✅ | ✅ | CRUD | 全部 | ✅ |
| **editor** | 编辑 | 创建/编辑 | 读 | 创建/编辑 | ✅ | ✅ | ❌ | 自己 | ❌ |
| **reviewer** | 审核 | 只读 | 读 | ❌ | ✅ | ❌ | ❌ | 自己 | ❌ |
| **viewer** | 查看 | 只读 | 读 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

**权限检查机制**:
- FastAPI 依赖注入 (`Depends(get_current_user)` + `Depends(require_role([...]))`)
- 每个 API 端点声明所需最低角色
- 403 响应不泄露资源信息（不告诉用户"资源存在但无权限"）

### 8.3 审计日志规格

**记录格式** (结构化 JSON):
```json
{
  "id": "audit-uuid",
  "user_id": "user-uuid",
  "action": "update",
  "resource_type": "product",
  "resource_id": "product-uuid",
  "details": {
    "fields_changed": ["color_en", "material_en"],
    "old_values": { "color_en": "Colour" },
    "new_values": { "color_en": "Color" }
  },
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "created_at": "2025-07-20T10:30:00Z"
}
```

**安全要求**:
- 日志写入采用**追加模式**，无 UPDATE/DELETE 操作
- 应用层和数据库层均禁止删除/修改审计日志
- 日志表无 `DELETE` 权限（数据库用户层面）
- 过期日志通过定时任务归档到冷存储，而非直接删除

### 8.4 数据分类

| 分类 | 说明 | 示例 | 访问控制 |
|------|------|------|----------|
| **Public** | 对外公开 | 平台模板定义 | 无需认证 |
| **Internal** | 系统内部 | 术语词典(内置) | 需认证 |
| **Confidential** | 业务数据 | 产品参数、导出CSV | 按角色控制 |
| **Restricted** | 敏感数据 | 密码哈希、成本价、审计日志 | 仅 admin |

### 8.5 安全 Headers

所有 HTTP 响应必须包含以下安全 Headers:

```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
```

### 8.6 SQL 注入防护

- **ORM 层面**: 全部使用 SQLAlchemy ORM 参数化查询，禁止原始 SQL 字符串拼接
- **输入验证**: Pydantic 模型严格类型校验
- **搜索接口**: 使用 ORM 的 `ilike` / `contains` 方法，不拼接 LIKE 模式

### 8.7 CSV 公式注入防护

详见 6.4 节 `sanitize_csv_cell()` 函数。所有导出的文本值均需经过处理。

---

## 9. 非功能需求

### 9.1 性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| API 响应时间 (P95) | < 200ms | 不含 CSV 导出和批量导入 |
| 产品列表查询 (P95) | < 100ms | 含分页，1万条产品以内 |
| 一致性检测 (50 SKU) | < 2s | 单品类 50 个产品全量检测 |
| CSV 导出 (100 SKU) | < 5s | 100 个产品生成 CSV |
| 批量导入 (500 条) | < 10s | 500 条产品解析 + 写入 |
| 并发用户数 | 50+ | SQLite WAL 模式下 |
| 首屏加载 | < 3s | Next.js SSR + 静态资源 CDN |

### 9.2 数据备份

| 策略 | 频率 | 保留期 | 说明 |
|------|------|--------|------|
| SQLite 文件备份 | 每日 02:00 UTC | 30 天 | `sqlite3 .backup` 命令 |
| 审计日志归档 | 每月 1 日 | 180 天 | 超期压缩到冷存储 |
| 用户上传文件 | 每日增量 | 90 天 | 导入的 Excel/CSV 原始文件 |

### 9.3 部署方案

**MVP 阶段**: 单机部署

```
┌──────────────────────────────────────┐
│           单台服务器 (2C4G+)          │
│                                      │
│  ┌──────────┐    ┌──────────────┐   │
│  │ Nginx    │───→│ Next.js SSR  │   │
│  │ (反代+SSL)│    │ (前端 3000)  │   │
│  └──────────┘    └──────────────┘   │
│                      │               │
│                      ↓               │
│  ┌──────────────────────────────┐   │
│  │ FastAPI (后端 8000)           │   │
│  │ ├── /api/v1/* → 路由         │   │
│  │ ├── SQLAlchemy ORM           │   │
│  │ └── JWT 中间件               │   │
│  └──────────────────────────────┘   │
│                      │               │
│                      ↓               │
│  ┌──────────────────────────────┐   │
│  │ SQLite (WAL 模式)            │   │
│  │ bilingual_cms.db             │   │
│  │ + *.db-journal               │   │
│  └──────────────────────────────┘   │
└──────────────────────────────────────┘
```

**技术选型理由**:
- **SQLite**: MVP 阶段足够，免运维，WAL 模式支持并发读写。预计 5000 SKU + 词典数据 < 10MB
- **单机部署**: MVP 阶段用户量小，降低运维复杂度
- **Nginx 反代**: 统一入口，SSL 终止，静态资源缓存

**扩展阶段** (V2+):
- 数据库迁移到 PostgreSQL
- 容器化部署 (Docker Compose → Kubernetes)
- 多实例 + 负载均衡

---

## 10. 迭代路线图

### Phase 1: MVP (12 周)

| 周次 | 里程碑 | 交付内容 | 优先级 |
|------|--------|----------|--------|
| **W1-2** | 项目搭建 | 项目脚手架、CI/CD、数据库初始化、认证系统 | P0 |
| **W3-4** | 核心数据 | 产品 CRUD API + 前端页面、术语词典加载 | P0 |
| **W5-6** | 一致性引擎 | L1/L2/L3 三层检测引擎、结果面板、一键修正 | P0 |
| **W7-8** | CSV 导出 | Amazon + 阿里国际站模板、字段映射、CSV 注入防护 | P0 |
| **W9-10** | 批量操作 | Excel/CSV 批量导入、字段映射界面、导入结果 | P1 |
| **W11** | 安全加固 | 审计日志、安全 Headers、RBAC 权限测试、SQL 注入测试 | P0 |
| **W12** | 测试上线 | E2E 测试、性能测试、Bug 修复、文档、部署 | P0 |

**MVP 完成标志**:
- [ ] 用户可注册登录，四角色权限生效
- [ ] 可创建/编辑产品，中英对照展示
- [ ] 可查看术语词典，含内置 242 条
- [ ] 一致性检测三级报告正常运行
- [ ] 可导出 Amazon + 阿里国际站标准 CSV
- [ ] 可批量导入 Excel/CSV
- [ ] 审计日志完整记录关键操作
- [ ] 50 SKU 并发操作无明显卡顿

### Phase 2: V2 功能 (8 周)

| 功能 | 说明 | 优先级 |
|------|------|--------|
| **三审三校流程** | 草稿 → 校对 → 定稿，引入审批工作流 | P1 |
| **多平台模板扩展** | Shopee/Lazada/TikTok Shop/Temu CSV 模板 | P1 |
| **图片/富媒体关联** | 产品关联图片管理、多图排序 | P2 |
| **多 SKU/变体管理** | Color/Size 变体组，父 SKU 管理 | P1 |
| **团队协作** | 产品评论、修改建议、@提及通知 | P2 |
| **数据导出增强** | 批量导出历史记录、模板自定义 | P2 |

### Phase 3: V3 愿景

| 方向 | 说明 |
|------|------|
| **AI 辅助翻译** | 接入 LLM，基于术语词典提供上下文翻译建议（而非通用翻译） |
| **平台直连 API** | 通过 Amazon SP-API / 阿里巴巴 Open API 直接同步产品 |
| **多租户** | SaaS 化，支持团队独立空间、数据隔离 |
| **品类智能扩展** | 基于用户数据自动发现新术语、推荐品类词典 |
| **版本控制** | 产品参数变更历史、对比、回滚 |
| **国际化** | 系统本身支持日/韩/西班牙语界面 |

---

## 附录 A: 技术栈确认

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | React / Next.js | SSR + SPA 混合，Tailwind CSS |
| 后端 | Python (FastAPI) | 异步框架，Pydantic 校验 |
| ORM | SQLAlchemy | 全 ORM 操作，禁止原始 SQL |
| 数据库 | SQLite (WAL) | MVP 阶段，可平滑迁移到 PostgreSQL |
| 认证 | JWT + bcrypt | Access/Refresh Token 双 Token |
| 测试 | pytest + httpx + Playwright | 单元测试 + API 测试 + E2E 测试 |

## 附录 B: 术语词典数据概览

- **总条目数**: 242 条
- **同义词组数**: 175 组
- **覆盖品类**: 11 个（通用属性、服装鞋帽、3C电子、家居家具、美妆个护、户外运动、母婴用品、汽车配件、珠宝饰品、办公文具、宠物用品）
- **数据文件**: `data/dictionary.json`, `data/synonyms.json`
- **一致性规则**: `data/consistency-rules.json`

## 附录 C: 平台模板字段对比

| 维度 | Amazon | 阿里国际站 |
|------|--------|-----------|
| 总字段数 | 37 | 29 |
| 必填字段数 | 18 | 12 |
| 特有字段 | item_type, bullet_points, condition_type, gift_wrap | MOQ, Payment Terms, Delivery Time, Port, Sample |
| 描述长度限制 | 2,000 字符 | 10,000 字符 |
| 图片数量 | 1 主图 + 2 附图 | 1 主图 + 2 附图 |

## 附录 D: 术语一致性检测示例

| 场景 | 检测级别 | 问题描述 | 修正建议 |
|------|----------|----------|----------|
| 产品 A 用 "Color"，产品 B 用 "Colour" | L1 ERROR | 同一中文术语"颜色"的英文翻译不一致 | 统一为 "Color" |
| 使用 "Type-C" 而非 "USB-C" | L2 WARNING | "Type-C" 是非标准变体 | 使用 "USB-C" |
| 使用 "Colour" 而非 "Color" | L3 INFO | 英式拼写，建议统一美式 | 使用 "Color" |
| 使用 "Material" 描述面料 | L2 WARNING | "Material" 偏通用，面料场景建议用 "Fabric" | 使用 "Fabric" |

---

> **文档维护**: 本文档随产品迭代持续更新。重大变更需经产品负责人审批。
>
> **下一步**: 进入技术设计阶段，输出 API 接口详细设计文档 (API Spec) 和数据库迁移脚本。
