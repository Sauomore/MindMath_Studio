
# -*- coding: utf-8 -*-
"""
公共工具与常量
包含版本号、数学表达式转换函数、预设方程库等
"""

import re

VERSION = "哈基米牌建模器 v1.4"


def to_latex_display(eq_str):
    """将方程转换为书面数学表达式显示"""
    display = eq_str
    display = re.sub(r'\*\*2', '²', display)
    display = re.sub(r'\*\*3', '³', display)
    display = re.sub(r'\*\*(\d+)', r'^\1', display)
    display = display.replace('*', '·')
    display = display.replace('/', '÷')
    display = display.replace('exp(', 'e^(')
    display = display.replace('sqrt(', '√(')
    # 希腊字母
    greek = {'alpha': 'α', 'beta': 'β', 'gamma': 'γ', 'delta': 'δ', 'sigma': 'σ',
             'mu': 'μ', 'omega': 'ω', 'zeta': 'ζ', 'phi': 'φ', 'pi': 'π'}
    for eng, gr in greek.items():
        display = display.replace(eng, gr)
    # 导数符号
    display = display.replace('dy/dt', 'dy/dt')
    display = display.replace('d2y/dt2', 'd²y/dt²')
    display = display.replace('du/dt', '∂u/∂t')
    display = display.replace('du/dx', '∂u/∂x')
    display = display.replace('d2u/dx2', '∂²u/∂x²')
    display = display.replace('d2u/dt2', '∂²u/∂t²')
    return display


def python_to_math_expr(expr):
    """将常用数学表达式转换为Python表达式"""
    result = expr
    result = result.replace('^', '**')
    result = result.replace('²', '**2')
    result = result.replace('³', '**3')
    result = result.replace('·', '*')
    result = result.replace('×', '*')
    result = result.replace('÷', '/')
    result = re.sub(r'e\^\(([^)]+)\)', r'exp(\1)', result)
    result = result.replace('√(', 'sqrt(')
    greek = {'α': 'alpha', 'β': 'beta', 'γ': 'gamma', 'δ': 'delta', 'σ': 'sigma',
             'μ': 'mu', 'ω': 'omega', 'ζ': 'zeta', 'φ': 'phi', 'π': 'pi'}
    for gr, eng in greek.items():
        result = result.replace(gr, eng)
    # 二阶导数符号转换
    result = result.replace("y''", "d2y/dt2")
    result = result.replace("u''", "d2u/dt2")
    return result


# ==================== 扩充预设方程库 ====================
PRESET_EQUATIONS = {
    # ---------- 基础代数方程 ----------
    "线性回归": {
        "equation": "y = a * x + b",
        "display": "y = a·x + b",
        "params": ["a", "b"],
        "description": "一元线性回归方程"
    },
    "二次函数": {
        "equation": "y = a * x**2 + b * x + c",
        "display": "y = a·x² + b·x + c",
        "params": ["a", "b", "c"],
        "description": "二次多项式"
    },
    "三次函数": {
        "equation": "y = a * x**3 + b * x**2 + c * x + d",
        "display": "y = a·x³ + b·x² + c·x + d",
        "params": ["a", "b", "c", "d"],
        "description": "三次多项式"
    },
    "反比例函数": {
        "equation": "y = k / x",
        "display": "y = k ÷ x",
        "params": ["k"],
        "description": "反比例函数"
    },
    "幂函数": {
        "equation": "y = a * x**b",
        "display": "y = a·x^b",
        "params": ["a", "b"],
        "description": "幂函数"
    },
    "指数增长": {
        "equation": "y = a * exp(b * x)",
        "display": "y = a·e^(b·x)",
        "params": ["a", "b"],
        "description": "指数增长"
    },
    "指数衰减": {
        "equation": "y = a * exp(-b * x)",
        "display": "y = a·e^(-b·x)",
        "params": ["a", "b"],
        "description": "指数衰减"
    },
    "对数函数": {
        "equation": "y = a * log(x) + b",
        "display": "y = a·ln(x) + b",
        "params": ["a", "b"],
        "description": "自然对数"
    },
    "常用对数": {
        "equation": "y = a * log10(x) + b",
        "display": "y = a·log₁₀(x) + b",
        "params": ["a", "b"],
        "description": "常用对数"
    },
    # ---------- S型与周期函数 ----------
    "逻辑斯蒂": {
        "equation": "y = L / (1 + exp(-k * (x - x0)))",
        "display": "y = L ÷ (1 + e^(-k·(x-x₀)))",
        "params": ["L", "k", "x0"],
        "description": "逻辑斯蒂增长"
    },
    "双曲正切": {
        "equation": "y = a * tanh(b * x) + c",
        "display": "y = a·tanh(b·x) + c",
        "params": ["a", "b", "c"],
        "description": "双曲正切"
    },
    "正弦函数": {
        "equation": "y = A * sin(omega * x + phi) + C",
        "display": "y = A·sin(ω·x + φ) + C",
        "params": ["A", "omega", "phi", "C"],
        "description": "正弦波"
    },
    "余弦函数": {
        "equation": "y = A * cos(omega * x + phi) + C",
        "display": "y = A·cos(ω·x + φ) + C",
        "params": ["A", "omega", "phi", "C"],
        "description": "余弦波"
    },
    "阻尼振动": {
        "equation": "y = A * exp(-b * x) * sin(omega * x + phi)",
        "display": "y = A·e^(-b·x)·sin(ω·x + φ)",
        "params": ["A", "b", "omega", "phi"],
        "description": "阻尼振动"
    },
    "高斯分布": {
        "equation": "y = A * exp(-(x - mu)**2 / (2 * sigma**2))",
        "display": "y = A·e^(-(x-μ)²/(2σ²))",
        "params": ["A", "mu", "sigma"],
        "description": "高斯分布"
    },
    "瑞利分布": {
        "equation": "y = (x / sigma**2) * exp(-x**2 / (2 * sigma**2))",
        "display": "y = (x÷σ²)·e^(-x²/(2σ²))",
        "params": ["sigma"],
        "description": "瑞利分布"
    },
    # ---------- 常微分方程 ----------
    "一阶ODE-衰减": {
        "equation": "dy/dt = -k * y",
        "display": "dy/dt = -k·y",
        "params": ["k"],
        "description": "指数衰减ODE"
    },
    "一阶ODE-增长": {
        "equation": "dy/dt = k * y",
        "display": "dy/dt = k·y",
        "params": ["k"],
        "description": "指数增长ODE"
    },
    "逻辑斯蒂ODE": {
        "equation": "dy/dt = r * y * (1 - y / K)",
        "display": "dy/dt = r·y·(1 - y/K)",
        "params": ["r", "K"],
        "description": "逻辑斯蒂ODE"
    },
    "二阶ODE-阻尼": {
        "equation": "d2y/dt2 + 2*zeta*omega*dy/dt + omega**2*y = 0",
        "display": "d²y/dt² + 2ζω·dy/dt + ω²·y = 0",
        "params": ["zeta", "omega"],
        "description": "阻尼振动ODE"
    },
    "简谐振动": {
        "equation": "d2y/dt2 + omega**2 * y = 0",
        "display": "d²y/dt² + ω²·y = 0",
        "params": ["omega"],
        "description": "简谐振动"
    },
    # ---------- 偏微分方程 ----------
    "热传导方程": {
        "equation": "du/dt = alpha * d2u/dx2",
        "display": "∂u/∂t = α·∂²u/∂x²",
        "params": ["alpha"],
        "description": "一维热传导"
    },
    "波动方程": {
        "equation": "d2u/dt2 = c**2 * d2u/dx2",
        "display": "∂²u/∂t² = c²·∂²u/∂x²",
        "params": ["c"],
        "description": "一维波动"
    },
    "反应扩散": {
        "equation": "du/dt = D * d2u/dx2 + r * u * (1 - u/K)",
        "display": "∂u/∂t = D·∂²u/∂x² + r·u·(1-u/K)",
        "params": ["D", "r", "K"],
        "description": "Fisher-KPP"
    },
    "对流扩散": {
        "equation": "du/dt = D * d2u/dx2 - v * du/dx",
        "display": "∂u/∂t = D·∂²u/∂x² - v·∂u/∂x",
        "params": ["D", "v"],
        "description": "对流扩散"
    },
    # ---------- 新增方程（物理/化学/生物/金融）----------
    "朗缪尔吸附": {
        "equation": "y = a * x / (1 + b * x)",
        "display": "y = a·x ÷ (1 + b·x)",
        "params": ["a", "b"],
        "description": "朗缪尔吸附等温式"
    },
    "米氏方程": {
        "equation": "v = Vmax * S / (Km + S)",
        "display": "v = Vmax·S ÷ (Km + S)",
        "params": ["Vmax", "Km", "S"],
        "description": "酶动力学（S为底物浓度）"
    },
    "希尔方程": {
        "equation": "y = ymax * x**n / (Kd + x**n)",
        "display": "y = ymax·xⁿ ÷ (Kd + xⁿ)",
        "params": ["ymax", "Kd", "n"],
        "description": "协同结合"
    },
    "阿伦尼乌斯": {
        "equation": "k = A * exp(-Ea / (R * T))",
        "display": "k = A·e^(-Ea/(R·T))",
        "params": ["A", "Ea", "R"],
        "description": "阿伦尼乌斯方程"
    },
    "布莱克-舒尔斯": {
        "equation": "C = S * N(d1) - K * exp(-r * T) * N(d2)",
        "display": "C = S·N(d₁) - K·e^(-rT)·N(d₂)",
        "params": ["S", "K", "r", "T", "sigma"],
        "description": "欧式看涨期权定价（需输入波动率 sigma）"
    },
    "洛伦兹系统": {
        "equation": "dx/dt = sigma * (y - x); dy/dt = x * (rho - z) - y; dz/dt = x * y - beta * z",
        "display": "dx/dt = σ(y-x); dy/dt = x(ρ-z)-y; dz/dt = xy-βz",
        "params": ["sigma", "rho", "beta"],
        "description": "洛伦兹方程"
    },
}