# Python 基础知识

## 什么是 Python？

Python 是一种高级、通用的编程语言，由 Guido van Rossum 于 1991 年首次发布。Python 的设计哲学强调代码的可读性和简洁性，使用缩进来定义代码块。

## Python 的特点

1. **简单易学**：Python 语法简洁清晰，非常适合初学者
2. **跨平台**：可在 Windows、Linux、macOS 等系统上运行
3. **丰富的库**：拥有大量第三方库，如 NumPy、Pandas、Django 等
4. **解释型语言**：无需编译，直接运行
5. **动态类型**：变量无需声明类型

## Python 数据类型

### 基本数据类型

- **int（整数）**：如 1, 100, -50
- **float（浮点数）**：如 3.14, -0.5
- **str（字符串）**：如 "hello", 'world'
- **bool（布尔值）**：True 或 False

### 容器类型

- **list（列表）**：有序可变序列，如 [1, 2, 3]
- **tuple（元组）**：有序不可变序列，如 (1, 2, 3)
- **dict（字典）**：键值对集合，如 {"name": "Alice", "age": 25}
- **set（集合）**：无序不重复元素集合，如 {1, 2, 3}

## 常用语法

### 条件语句

```python
if condition:
    # 条件为真时执行
elif another_condition:
    # 另一个条件为真时执行
else:
    # 其他情况
```

### 循环语句

```python
# for 循环
for item in iterable:
    print(item)

# while 循环
while condition:
    # 循环体
```

### 函数定义

```python
def function_name(param1, param2):
    """函数文档字符串"""
    # 函数体
    return result
```

## Python 应用领域

1. **Web 开发**：Django, Flask, FastAPI
2. **数据科学**：Pandas, NumPy, Matplotlib
3. **机器学习**：TensorFlow, PyTorch, Scikit-learn
4. **自动化脚本**：系统管理、任务自动化
5. **人工智能**：LangChain, OpenAI API
