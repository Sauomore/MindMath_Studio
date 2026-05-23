# -*- coding: utf-8 -*-
"""
SPDX-License-Identifier: MIT
Copyright (c) 2026, Sauomore
"""
"""
方程求解核心逻辑
包含：求解调度器、代数方程求解、常微分方程求解、偏微分方程求解
"""

import numpy as np
from scipy.integrate import odeint
from scipy.sparse import diags
from scipy.sparse.linalg import spsolve
from scipy.stats import norm


class StopRequestedException(Exception):
    """用户主动中断异常"""
    pass


def solve_equation(equation_data, param_values, x_values, t_values,
                   x_column, y_column, dataframe, stop_check=None):
    """根据方程类型分发求解

    Args:
        equation_data: 方程字典，包含 equation, display, params 等
        param_values: 参数值字典
        x_values: 自变量数组
        t_values: 时间数组
        x_column: 数据中的 x 列名（可能为 None）
        y_column: 数据中的 y 列名（可能为 None）
        dataframe: 原始数据 DataFrame
        stop_check: 可调用对象，返回 True 表示请求中断

    Returns:
        结果字典
    """
    eq_str = equation_data["equation"]
    display_eq = equation_data.get("display", eq_str)

    if "d2u" in eq_str or "du/d" in eq_str:
        return solve_pde(eq_str, display_eq, param_values, x_values, t_values, stop_check)
    elif "dy/d" in eq_str or "y'" in eq_str or "d2y" in eq_str:
        return solve_ode(eq_str, display_eq, param_values, t_values,
                         equation_data.get("name", ""), stop_check)
    else:
        return solve_algebraic(eq_str, display_eq, param_values, x_values, t_values,
                               x_column, y_column, dataframe, stop_check)


def solve_algebraic(eq_str, display_eq, param_values, x_values, t_values,
                    x_column, y_column, dataframe, stop_check=None):
    """求解代数方程（显式 y = f(x, ...)）"""
    if stop_check and stop_check():
        raise StopRequestedException()

    if "=" in eq_str:
        _, right = eq_str.split("=", 1)
    else:
        right = eq_str

    x_values = np.array(x_values, dtype=float)
    t_values = np.array(t_values, dtype=float)

    # 安全计算环境
    safe_dict = {
        'x': x_values,
        't': t_values,
        'np': np,
        'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
        'exp': np.exp, 'log': np.log, 'log10': np.log10,
        'ln': np.log, 'sqrt': np.sqrt, 'abs': np.abs,
        'tanh': np.tanh,
        'pi': np.pi, 'e': np.e,
        'N': norm.cdf,
    }

    # 添加用户映射参数
    for param, value in param_values.items():
        if value is not None:
            safe_dict[param] = value
        else:
            safe_dict[param] = 0.0

    # 自动补全常用变量
    if 'T' not in safe_dict and 'T' in right:
        safe_dict['T'] = t_values
    if 'S' not in safe_dict and 'S' in right:
        safe_dict['S'] = x_values
    if 'I' not in safe_dict and 'I' in right:
        safe_dict['I'] = x_values
    if 'C' not in safe_dict and 'C' in right:
        safe_dict['C'] = x_values

    # 布莱克-舒尔斯向量化处理
    if 'N(d1)' in right or 'N(d2)' in right:
        S = safe_dict.get('S', 100.0)
        K = safe_dict.get('K', 100.0)
        r = safe_dict.get('r', 0.05)
        T = safe_dict.get('T', 1.0)
        sigma = safe_dict.get('sigma', 0.2)

        # 确保是数组并长度一致
        if isinstance(S, np.ndarray) and S.shape == (1,):
            S = np.full_like(x_values, S[0])
        if isinstance(K, np.ndarray) and K.shape == (1,):
            K = np.full_like(x_values, K[0])
        if isinstance(r, np.ndarray) and r.shape == (1,):
            r = np.full_like(x_values, r[0])
        if isinstance(T, np.ndarray) and T.shape == (1,):
            T = np.full_like(x_values, T[0])
        if isinstance(sigma, np.ndarray) and sigma.shape == (1,):
            sigma = np.full_like(x_values, sigma[0])

        T_safe = np.where(T <= 0, 1e-6, T)
        denominator = sigma * np.sqrt(T_safe)
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T_safe) / denominator
        d2 = d1 - sigma * np.sqrt(T_safe)
        safe_dict['d1'] = d1
        safe_dict['d2'] = d2

    expr_str = right.strip().replace('^', '**')
    y_values = eval(expr_str, {"__builtins__": {}}, safe_dict)
    y_values = np.array(y_values, dtype=float)

    # 形状处理
    if y_values.shape == ():
        y_values = np.full_like(x_values, y_values)
    elif y_values.shape == (1,):
        y_values = np.full_like(x_values, y_values[0])
    elif y_values.shape != x_values.shape:
        if y_values.size == 1:
            y_values = np.full_like(x_values, y_values.flatten()[0])
        else:
            raise ValueError(f"形状不匹配: x.shape={x_values.shape}, y.shape={y_values.shape}")

    result = {
        'type': 'algebraic',
        'x': x_values,
        'y': y_values,
        'equation': eq_str,
        'display_eq': display_eq,
        'x_column': x_column,
        'y_column': y_column
    }
    if y_column and dataframe is not None and y_column in dataframe.columns:
        result['y_obs'] = dataframe[y_column].values
    return result


def get_param_value(param_values, param_name, default):
    """安全地从参数字典中获取标量值"""
    value = param_values.get(param_name, default)
    if isinstance(value, np.ndarray):
        return float(value[0]) if len(value) > 0 else default
    return float(value) if value is not None else default


def solve_ode(eq_str, display_eq, param_values, t_values, eq_name="", stop_check=None):
    """求解常微分方程"""
    if stop_check and stop_check():
        raise StopRequestedException()

    t = np.array(t_values, dtype=float)

    # 提取常用参数
    k = get_param_value(param_values, 'k', 0.1)
    zeta = get_param_value(param_values, 'zeta', 0.5)
    omega = get_param_value(param_values, 'omega', 1.0)
    r = get_param_value(param_values, 'r', 1.0)
    K = get_param_value(param_values, 'K', 10.0)

    # 判断是否为逻辑斯蒂ODE
    is_logistic = ("逻辑斯蒂ODE" in eq_name) or ("r * y * (1" in eq_str and "K" in eq_str)

    if "d2y" in eq_str or "y''" in eq_str:
        def damped_vibration(y, t, zeta, omega):
            x, v = y
            dxdt = v
            dvdt = -2 * zeta * omega * v - omega ** 2 * x
            return [dxdt, dvdt]

        y0 = [1.0, 0.0]
        solution = odeint(damped_vibration, y0, t, args=(zeta, omega))
        y_values = solution[:, 0]
    elif is_logistic:
        def logistic(y, t, r, K):
            return r * y * (1 - y / K)

        y0 = 0.1
        y_values = odeint(logistic, y0, t, args=(r, K)).flatten()
    else:
        def decay(y, t, k):
            return -k * y

        y0 = 1.0
        y_values = odeint(decay, y0, t, args=(k,)).flatten()

    return {'type': 'ode', 't': t, 'y': y_values, 'equation': eq_str, 'display_eq': display_eq}


def solve_pde(eq_str, display_eq, param_values, x_values, t_values, stop_check=None):
    """求解偏微分方程（有限差分）"""
    if stop_check and stop_check():
        raise StopRequestedException()

    alpha = get_param_value(param_values, 'alpha', 0.1)
    c = get_param_value(param_values, 'c', 1.0)
    D = get_param_value(param_values, 'D', 0.1)
    r = get_param_value(param_values, 'r', 1.0)
    K = get_param_value(param_values, 'K', 10.0)
    v = get_param_value(param_values, 'v', 0.5)

    x = np.array(x_values, dtype=float) if len(x_values) > 1 else np.linspace(0, 10, 100)
    t = np.array(t_values, dtype=float)
    dx = x[1] - x[0] if len(x) > 1 else 1.0
    dt = t[1] - t[0] if len(t) > 1 else 0.1
    N = len(x)
    u = np.zeros((len(t), N))
    # 初始高斯分布
    u[0, :] = np.exp(-(x - np.mean(x)) ** 2 / 2)

    # 确定方程类型
    if "热传导" in eq_str or "alpha" in eq_str.lower():
        r_cn = alpha * dt / (2 * dx ** 2)
        main_A = (1 + 2 * r_cn) * np.ones(N - 2)
        off_A = -r_cn * np.ones(N - 3)
        A = diags([off_A, main_A, off_A], [-1, 0, 1], format='csr')
        main_B = (1 - 2 * r_cn) * np.ones(N - 2)
        off_B = r_cn * np.ones(N - 3)
        B = diags([off_B, main_B, off_B], [-1, 0, 1], format='csr')
        for n in range(len(t) - 1):
            if stop_check and stop_check():
                raise StopRequestedException()
            rhs = B.dot(u[n, 1:-1])
            rhs[0] += r_cn * u[n, 0]
            rhs[-1] += r_cn * u[n, -1]
            u[n + 1, 1:-1] = spsolve(A, rhs)
            u[n + 1, 0] = u[n + 1, 1]
            u[n + 1, -1] = u[n + 1, -2]
    elif "波动" in eq_str or "c**2" in eq_str:
        u[1, :] = u[0, :]
        r_wave = c * dt / dx
        for n in range(1, len(t) - 1):
            if stop_check and stop_check():
                raise StopRequestedException()
            for i in range(1, N - 1):
                u[n + 1, i] = 2 * u[n, i] - u[n - 1, i] + r_wave ** 2 * (
                            u[n, i + 1] - 2 * u[n, i] + u[n, i - 1])
            u[n + 1, 0] = u[n + 1, 1]
            u[n + 1, -1] = u[n + 1, -2]
    else:  # 反应扩散
        r_diff = D * dt / dx ** 2
        main_A = (1 + 2 * r_diff) * np.ones(N - 2)
        off_A = -r_diff * np.ones(N - 3)
        A = diags([off_A, main_A, off_A], [-1, 0, 1], format='csr')
        for n in range(len(t) - 1):
            if stop_check and stop_check():
                raise StopRequestedException()
            reaction = r * u[n, 1:-1] * (1 - u[n, 1:-1] / K) * dt
            rhs = u[n, 1:-1] + r_diff * (u[n, 2:] - 2 * u[n, 1:-1] + u[n, :-2]) + reaction
            u[n + 1, 1:-1] = spsolve(A, rhs)
            u[n + 1, 0] = u[n + 1, 1]
            u[n + 1, -1] = u[n + 1, -2]

    # 处理可能的数值问题
    if np.isnan(u).any() or np.isinf(u).any():
        u = np.nan_to_num(u, nan=0.0, posinf=1.0, neginf=0.0)

    return {'type': 'pde', 'x': x, 't': t, 'u': u, 'equation': eq_str, 'display_eq': display_eq}