"""
计算器工具

支持数学表达式计算，包括：
- 基础运算：加减乘除
- 幂运算：2**10 或 2^10
- 数学函数：sqrt, sin, cos, tan, log 等
- 常量：pi, e
"""

import math
from langchain_core.tools import tool


@tool
def calculator(expression: str) -> str:
    """
    计算数学表达式。支持加减乘除、幂运算、开方等。
    
    例如：
    - "2 + 3 * 4" → 14
    - "sqrt(16)" → 4
    - "2^10" 或 "2**10" → 1024
    - "pi * 2" → 6.283...
    
    Args:
        expression: 数学表达式字符串
        
    Returns:
        计算结果字符串
    """
    try:
        # 预处理表达式
        expr = expression.replace("^", "**")
        expr = expr.replace("sqrt", "math.sqrt")
        expr = expr.replace("sin", "math.sin")
        expr = expr.replace("cos", "math.cos")
        expr = expr.replace("tan", "math.tan")
        expr = expr.replace("log", "math.log")
        expr = expr.replace("pi", "math.pi")
        expr = expr.replace("e", "math.e")
        
        # 安全执行
        allowed_names = {"__builtins__": {}, "math": math}
        result = eval(expr, allowed_names)
        
        # 格式化结果
        if isinstance(result, float):
            # 避免浮点数精度问题
            if result == int(result):
                result = int(result)
            else:
                result = round(result, 10)
        
        return f"计算结果: {result}"
    except ZeroDivisionError:
        return "计算错误: 除数不能为零"
    except Exception as e:
        return f"计算错误: {str(e)}"
