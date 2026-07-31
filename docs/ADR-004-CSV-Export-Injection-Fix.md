# ADR-004: 修复CSV导出注入防护
**状态:** Proposed
**日期:** 2024-01-15

## 背景
当前CSV导出存在注入风险，`sanitize_csv_cell`函数只检查了部分危险字符。根据技术债评估报告#18，需要补充`\n`字符检查，完善CSV注入防护。

## 选项分析

### 选项A: 现有函数基础上补充\n检查
| 维度 | 评估 |
|------|------|
| 复杂度 | Low |
| 成本 | 低 - 只需修改一个函数 |
| 可扩展性 | 中 - 解决当前问题但可能不完整 |

**优点：**
- 改动最小
- 快速解决问题
- 向后兼容

**缺点：**
- 可能遗漏其他注入向量
- 防护不够全面

### 选项B: 全面重写CSV安全函数
| 维度 | 评估 |
|------|------|
| 复杂度 | Medium |
| 成本 | 中 - 需要重新设计函数 |
| 可扩展性 | 优 - 全面防护 |

**优点：**
- 全面防护各种注入
- 代码更清晰
- 易于维护和扩展

**缺点：**
- 需要更多开发时间
- 可能影响现有功能

### 选项C: 使用成熟的CSV安全库
| 维度 | 评估 |
|------|------|
| 复杂度 | Low |
| 成本 | 低 - 使用现有库 |
| 可扩展性 | 优 - 专业库维护 |

**优点：**
- 经过实战检验
- 持续更新维护
- 功能全面

**缺点：**
- 增加依赖
- 可能需要调整现有代码

## 决策
推荐**选项B: 全面重写CSV安全函数**，理由如下：
1. **安全性优先**：全面防护各种CSV注入攻击
2. **代码质量提升**：函数职责更清晰
3. **维护性好**：易于理解和修改
4. **符合最佳实践**：实现完整的安全防护

## 具体实现方案

### 安全防护策略
1. **危险字符检测**
   - 公式注入字符：`=`, `+`, `-`, `@`, `\t`, `\r`
   - 换行符：`\n`, `\r\n`
   - 引号字符：`"`
   - 分隔符转义

2. **编码处理**
   - UTF-8编码安全
   - 特殊字符转义
   - BOM处理

### 重写后的sanitize_csv_cell函数
```python
def sanitize_csv_cell(value: str) -> str:
    """
    防止 CSV 公式注入和格式攻击
    
    处理策略：
    1. 检测并处理公式注入字符
    2. 转义换行符防止格式破坏
    3. 处理引号字符防止字段逃逸
    4. 确保UTF-8编码安全
    
    Args:
        value: 需要清洗的单元格值
        
    Returns:
        清洗后的安全值
        
    Examples:
        >>> sanitize_csv_cell("=SUM(A1:A10)")
        "'=SUM(A1:A10)"
        >>> sanitize_csv_cell("line1\nline2")
        "'line1\\nline2"
        >>> sanitize_csv_cell('value with "quotes"')
        "'value with \\"quotes\\""
    """
    if not isinstance(value, str):
        return str(value)
    
    # 1. 处理公式注入字符
    if value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
        value = "'" + value
    
    # 2. 处理换行符（防止格式破坏）
    if "\n" in value or "\r" in value:
        # 将换行符转义为文本形式
        value = value.replace("\n", "\\n").replace("\r", "\\r")
        # 添加前缀标记
        if not value.startswith("'"):
            value = "'" + value
    
    # 3. 处理引号字符（防止字段逃逸）
    if '"' in value:
        # 双引号转义
        value = value.replace('"', '\\"')
        # 如果包含引号，确保用引号包围
        if not value.startswith("'"):
            value = "'" + value
    
    return value
```

### 增强的CSV导出函数
```python
def safe_csv_export(data: list, headers: list) -> str:
    """
    安全的CSV导出函数
    
    Args:
        data: 数据列表
        headers: 表头列表
        
    Returns:
        安全的CSV内容
    """
    output = io.StringIO()
    
    # 添加UTF-8 BOM
    output.write('\ufeff')
    
    writer = csv.writer(
        output,
        quoting=csv.QUOTE_ALL,  # 所有字段都用引号包围
        escapechar='\\',  # 转义字符
        lineterminator='\n'  # 统一行终止符
    )
    
    # 写入表头
    writer.writerow([safe_csv_header(h) for h in headers])
    
    # 写入数据
    for row in data:
        safe_row = [sanitize_csv_cell(str(cell)) for cell in row]
        writer.writerow(safe_row)
    
    return output.getvalue()
```

### 安全测试用例
1. **公式注入测试**
   ```python
   def test_formula_injection():
       test_cases = [
           ("=SUM(A1:A10)", "'=SUM(A1:A10)"),
           ("+cmd|' /C calc'!A0", "'+cmd|' /C calc'!A0"),
           ("-2+3", "'-2+3"),
           ("@SUM(A1:A10)", "'@SUM(A1:A10)"),
       ]
       for input_val, expected in test_cases:
           assert sanitize_csv_cell(input_val) == expected
   ```

2. **换行符测试**
   ```python
   def test_newline_injection():
       test_cases = [
           ("line1\nline2", "'line1\\nline2"),
           ("line1\r\nline2", "'line1\\r\\nline2"),
           ("line1\rline2", "'line1\\rline2"),
       ]
       for input_val, expected in test_cases:
           assert sanitize_csv_cell(input_val) == expected
   ```

3. **引号测试**
   ```python
   def test_quote_injection():
       test_cases = [
           ('value with "quotes"', "'value with \\"quotes\\""),
           ('"quoted value"', "'\\"quoted value\\""),
           ("value with 'single quotes'", "value with 'single quotes'"),
       ]
       for input_val, expected in test_cases:
           assert sanitize_csv_cell(input_val) == expected
   ```

## 影响
### 变容易
- CSV导出安全性显著提升
- 防止各种CSV注入攻击
- 符合安全编码规范

### 变困难
- 可能影响现有CSV导出格式
- 需要更新相关测试用例
- 可能影响Excel等软件的解析

### 需要重新审视的部分
- 现有CSV导出功能
- 测试用例
- 用户使用习惯
- 下游系统兼容性

## 兼容性考虑
1. **Excel兼容性**
   - 确保BOM正确添加
   - 测试中文字符显示
   - 验证公式防护效果

2. **下游系统兼容性**
   - 测试现有系统解析
   - 验证数据完整性
   - 确保格式一致性

3. **向后兼容**
   - 保持现有API接口不变
   - 逐步迁移而非强制更新
   - 提供兼容模式选项

## 测试验证方案
1. **安全测试**
   - 各种注入攻击测试
   - 边界值测试
   - 特殊字符测试

2. **功能测试**
   - 正常数据导出测试
   - 大数据量测试
   - 并发导出测试

3. **兼容性测试**
   - Excel导入测试
   - 其他CSV解析器测试
   - 不同操作系统测试

4. **性能测试**
   - 处理时间测试
   - 内存使用测试
   - 文件大小测试