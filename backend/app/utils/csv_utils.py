def sanitize_csv_cell(value: str) -> str:
    """
    防止 CSV 公式注入
    
    对以 =, +, -, @, \\t, \\r 开头的值加单引号前缀，防止Excel等软件将其解析为公式。
    
    Args:
        value: 需要清洗的单元格值
        
    Returns:
        清洗后的安全值
        
    Examples:
        >>> sanitize_csv_cell("=SUM(A1:A10)")
        "'=SUM(A1:A10)"
        >>> sanitize_csv_cell("normal text")
        'normal text'
    """
    if not isinstance(value, str):
        return value
    if value and value[0] in ("=", "+", "-", "@", "\t", "\r", "\n"):
        return "'" + value
    return value
