# 跨境产品资料中英对照系统 - 代码审查报告

## 概要
本报告对"跨境产品资料中英对照系统"进行了全面代码审查，覆盖安全、性能、正确性和可维护性四个维度。审查发现了一些严重和高危的安全问题，需要立即修复。

## 严重问题 (🔴 Critical / 🔴 High)

### 1. JWT密钥硬编码在.env文件中
- **文件**: `./backend/app/config.py`
- **行号**: 8
- **问题**: `SECRET_KEY: str = secrets.token_urlsafe(32)` 被 `.env` 文件中的 `SECRET_KEY=dev-secret-key-do-not-use-in-production` 覆盖，使用了弱密钥
- **严重度**: 🔴 Critical
- **修复建议**: 
  1. 从生产环境移除硬编码密钥
  2. 使用环境变量或密钥管理服务（如AWS Secrets Manager）
  3. 在生产环境中生成强随机密钥

### 2. 用户注册缺少角色验证
- **文件**: `./backend/app/api/auth.py`
- **行号**: 21-35
- **问题**: 注册端点允许任何用户指定任意角色（包括admin），没有权限控制
- **严重度**: 🔴 High
- **修复建议**:
  1. 限制注册时只能选择"viewer"角色
  2. 或要求管理员授权才能创建高权限账户
  3. 添加输入验证：`if data.role not in ["viewer"]: raise HTTPException(...)`

### 3. 密码策略缺失
- **文件**: `./backend/app/schemas/auth.py`
- **行号**: 6-7
- **问题**: 密码字段没有最小长度、复杂度要求，允许空密码或弱密码
- **严重度**: 🔴 High
- **修复建议**:
  ```python
  from pydantic import field_validator
  
  class UserCreate(BaseModel):
      password: str
      
      @field_validator('password')
      @classmethod
      def validate_password(cls, v):
          if len(v) < 8:
              raise ValueError('密码长度至少8位')
          if not any(c.isupper() for c in v):
              raise ValueError('密码需包含大写字母')
          if not any(c.isdigit() for c in v):
              raise ValueError('密码需包含数字')
          return v
  ```

### 4. 文件上传路径遍历风险
- **文件**: `./backend/app/api/import_.py`
- **行号**: 92-99
- **问题**: 文件名直接用于构建临时文件路径，可能导致路径遍历攻击
- **严重度**: 🔴 High
- **修复建议**:
  1. 清洗文件名：`import re; safe_filename = re.sub(r'[^\w\-.]', '_', file.filename)`
  2. 使用UUID重命名：`file_path = os.path.join(temp_dir, f"import_{file_id}{ext}")`
  3. 验证文件扩展名白名单

## 高危问题 (🟠 High)

### 5. 内存缓存无过期机制
- **文件**: `./backend/app/api/import_.py`
- **行号**: 20, 123-130
- **问题**: `_upload_cache` 字典无限增长，没有过期清理机制，可能导致内存泄漏
- **严重度**: 🟠 High
- **修复建议**:
  1. 使用 `TTLCache` 或类似带过期的缓存
  2. 添加定期清理任务
  3. 限制缓存大小

### 6. 数据库查询缺少索引
- **文件**: `./backend/app/models/product.py`
- **问题**: 缺少常用查询字段的索引，影响性能
- **严重度**: 🟠 High
- **修复建议**:
  ```python
  class Product(Base):
      __tablename__ = "products"
      # 现有字段...
      
      __table_args__ = (
          Index('idx_product_sku', 'sku'),
          Index('idx_product_category', 'category'),
          Index('idx_product_consistency_status', 'consistency_status'),
          Index('idx_product_is_deleted', 'is_deleted'),
      )
  ```

### 7. CSV导出缺少UTF-8 BOM
- **文件**: `./backend/app/api/export.py`
- **行号**: 39
- **问题**: 导出的CSV文件可能在Excel中显示乱码，因为缺少UTF-8 BOM
- **严重度**: 🟠 High
- **修复建议**:
  ```python
  # 在输出开头添加BOM
  output.write('\ufeff')  # UTF-8 BOM
  ```

### 8. 错误信息泄露敏感信息
- **文件**: `./backend/app/api/import_.py`
- **行号**: 108
- **问题**: `str(e)` 可能泄露内部错误信息，如文件路径、数据库错误等
- **严重度**: 🟠 High
- **修复建议**:
  ```python
  except Exception as e:
      # 记录详细错误到日志
      logger.error(f"文件解析失败: {e}", exc_info=True)
      # 返回通用错误信息
      raise HTTPException(status_code=400, detail="文件解析失败，请检查文件格式")
  ```

## 中等问题 (🟡 Medium)

### 9. 缺少CSRF保护
- **文件**: `./backend/app/main.py`
- **行号**: 16-22
- **问题**: CORS配置允许所有方法（`allow_methods=["*"]`），但缺少CSRF令牌验证
- **严重度**: 🟡 Medium
- **修复建议**:
  1. 限制CORS方法：`allow_methods=["GET", "POST", "PUT", "DELETE"]`
  2. 对状态变更操作添加CSRF令牌验证

### 10. 前端Token存储不安全
- **文件**: `./frontend/src/lib/api.ts`
- **行号**: 8-9
- **问题**: JWT存储在localStorage中，容易受到XSS攻击
- **严重度**: 🟡 Medium
- **修复建议**:
  1. 考虑使用HttpOnly Cookie存储token
  2. 或添加XSS防护措施

### 11. 数据模型缺少验证
- **文件**: `./backend/app/models/product.py`
- **问题**: 缺少字段长度限制和格式验证
- **严重度**: 🟡 Medium
- **修复建议**:
  ```python
  sku = Column(String(64), unique=True, nullable=False)
  product_name_zh = Column(String(200), nullable=False)
  price = Column(Float, nullable=True)
  ```

### 12. 测试覆盖率不足
- **文件**: `./backend/tests/`
- **问题**: 缺少边界条件、错误处理、并发场景的测试
- **严重度**: 🟡 Medium
- **修复建议**:
  1. 添加边界条件测试（空输入、最大长度、特殊字符）
  2. 添加并发测试
  3. 添加安全测试（SQL注入、XSS）

## 低级问题 (🟢 Low)

### 13. 代码重复
- **文件**: `./backend/app/api/products.py`, `./backend/app/api/terms.py`
- **问题**: 分页逻辑重复，可以提取为通用工具函数
- **严重度**: 🟢 Low
- **修复建议**:
  ```python
  def paginate(query, page, page_size):
      total = query.count()
      items = query.offset((page - 1) * page_size).limit(page_size).all()
      return items, total, math.ceil(total / page_size) if total > 0 else 0
  ```

### 14. 缺少日志记录
- **文件**: 多个API端点
- **问题**: 关键操作（登录、注册、数据修改）没有日志记录
- **严重度**: 🟢 Low
- **修复建议**: 添加结构化日志记录

### 15. 文档不完整
- **文件**: 多个模块
- **问题**: 缺少API文档、部署文档、架构文档
- **严重度**: 🟢 Low
- **修复建议**: 补充完整文档

## 做得好的地方
1. **代码结构清晰**: 使用了合理的模块划分（api、models、core、utils）
2. **认证授权实现**: JWT + RBAC实现了基本的访问控制
3. **一致性检测引擎**: 三层检测逻辑设计合理，扩展性好
4. **CSV工具函数**: `sanitize_csv_cell`有效防止了公式注入
5. **测试框架**: 使用了pytest和httpx，有基本的测试结构

## 总体评估
系统基本功能完整，但存在多个严重安全漏洞需要立即修复。建议优先处理：
1. 密钥管理和认证安全问题
2. 文件上传安全
3. 数据验证和错误处理

## 建议的修复优先级
1. **立即修复**: 问题1-4（严重安全问题）
2. **本周修复**: 问题5-8（高危问题）
3. **下个迭代**: 问题9-12（中等问题）
4. **持续改进**: 问题13-15（低级问题）

---
**审查人**: 科迪（Cody） · 代码审查师  
**审查日期**: 2025年7月23日  
**审查版本**: 1.0