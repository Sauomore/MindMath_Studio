# -*- coding: utf-8 -*-
"""
SPDX-License-Identifier: MIT
Copyright (c) 2026, Sauomore
"""

import os
import json
import uuid
import pandas as pd
import numpy as np
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from scipy.stats import norm
from scipy.integrate import odeint
from scipy.sparse import diags
from scipy.sparse.linalg import spsolve
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.svm import SVC, SVR
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.cluster import KMeans
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report, r2_score, mean_squared_error, silhouette_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from utils import PRESET_EQUATIONS, to_latex_display, python_to_math_expr

app = Flask(__name__)
CORS(app)

current_dataframe = None
user_equations = {}
current_equation = None
param_mapping = {}
ml_models = {}  # 存储训练好的模型 {model_id: {'model': model, 'type': ...}}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/user_equations', methods=['GET', 'POST'])
def manage_user_equations():
    global user_equations
    if request.method == 'GET':
        return jsonify(user_equations)
    else:
        data = request.json
        name = data.get('name')
        eq_data = data.get('equation_data')
        if not name or not eq_data:
            return jsonify({'error': '无效数据'}), 400
        user_equations[name] = eq_data
        return jsonify({'success': True})

@app.route('/api/delete_user_equation', methods=['POST'])
def delete_user_equation():
    global user_equations
    name = request.json.get('name')
    if name in user_equations:
        del user_equations[name]
        return jsonify({'success': True})
    return jsonify({'error': '方程不存在'}), 404

@app.route('/api/upload', methods=['POST'])
def upload_csv():
    global current_dataframe
    if 'file' not in request.files:
        return jsonify({'error': '未选择文件'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '空文件名'}), 400
    try:
        sep = '\t' if file.filename.endswith(('.tsv', '.txt')) else ','
        df = pd.read_csv(file, sep=sep)
        current_dataframe = df
        preview = df.head(100).replace({np.nan: None}).to_dict(orient='records')
        return jsonify({
            'success': True,
            'columns': df.columns.tolist(),
            'data': preview,
            'rows': len(df)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/current_data', methods=['GET'])
def get_current_data():
    if current_dataframe is None:
        return jsonify({'columns': [], 'data': [], 'rows': 0})
    preview = current_dataframe.head(500).replace({np.nan: None}).to_dict(orient='records')
    return jsonify({
        'columns': current_dataframe.columns.tolist(),
        'data': preview,
        'rows': len(current_dataframe)
    })

@app.route('/api/export', methods=['POST'])
def export_data():
    global current_dataframe
    if current_dataframe is None:
        return jsonify({'error': '无数据'}), 400
    file_format = request.json.get('format', 'csv')
    if file_format == 'csv':
        csv_str = current_dataframe.to_csv(index=False, encoding='utf-8-sig')
        return jsonify({'success': True, 'data': csv_str, 'type': 'csv'})
    elif file_format == 'tsv':
        tsv_str = current_dataframe.to_csv(index=False, sep='\t', encoding='utf-8-sig')
        return jsonify({'success': True, 'data': tsv_str, 'type': 'tsv'})
    else:
        return jsonify({'error': '不支持的格式'}), 400

@app.route('/api/add_row', methods=['POST'])
def add_row():
    global current_dataframe
    if current_dataframe is None:
        current_dataframe = pd.DataFrame(columns=['新列'])
    new_row = {col: '' for col in current_dataframe.columns}
    current_dataframe = pd.concat([current_dataframe, pd.DataFrame([new_row])], ignore_index=True)
    return jsonify({'success': True, 'rows': len(current_dataframe)})

@app.route('/api/add_column', methods=['POST'])
def add_column():
    global current_dataframe
    data = request.json
    col_name = data.get('col_name', '').strip()
    if not col_name:
        return jsonify({'error': '列名不能为空'}), 400
    if current_dataframe is None:
        current_dataframe = pd.DataFrame(columns=[col_name])
    else:
        if col_name in current_dataframe.columns:
            return jsonify({'error': f'列 "{col_name}" 已存在'}), 400
        current_dataframe[col_name] = ''
    return jsonify({'success': True, 'columns': current_dataframe.columns.tolist()})

@app.route('/api/update_cell', methods=['POST'])
def update_cell():
    global current_dataframe
    data = request.json
    row = data.get('row')
    col = data.get('col')
    value = data.get('value')
    if current_dataframe is None or row is None or col is None:
        return jsonify({'error': '无效请求'}), 400
    if col not in current_dataframe.columns:
        return jsonify({'error': '列不存在'}), 400
    if row >= len(current_dataframe):
        return jsonify({'error': '行索引超出范围'}), 400
    if value == '':
        value = None
    else:
        try:
            value = float(value)
        except ValueError:
            pass
    current_dataframe.at[row, col] = value
    return jsonify({'success': True})

@app.route('/api/delete_rows', methods=['POST'])
def delete_rows():
    global current_dataframe
    data = request.json
    indices = data.get('indices', [])
    if current_dataframe is None or not indices:
        return jsonify({'error': '无效索引'}), 400
    current_dataframe = current_dataframe.drop(indices).reset_index(drop=True)
    return jsonify({'success': True, 'rows': len(current_dataframe)})

@app.route('/api/delete_column', methods=['POST'])
def delete_column():
    global current_dataframe
    data = request.json
    col_name = data.get('col_name')
    if current_dataframe is None or col_name not in current_dataframe.columns:
        return jsonify({'error': '列不存在'}), 400
    current_dataframe = current_dataframe.drop(columns=[col_name])
    return jsonify({'success': True, 'columns': current_dataframe.columns.tolist()})

@app.route('/api/fill_missing', methods=['POST'])
def fill_missing():
    global current_dataframe
    data = request.json
    method = data.get('method', 'mean')
    constant = data.get('constant', 0)
    if current_dataframe is None:
        return jsonify({'error': '无数据'}), 400
    df = current_dataframe.copy()
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if method == 'mean':
        df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
    elif method == 'median':
        df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())
    elif method == 'mode':
        mode_vals = df[numeric_cols].mode().iloc[0] if not df[numeric_cols].mode().empty else 0
        df[numeric_cols] = df[numeric_cols].fillna(mode_vals)
    elif method == 'constant':
        df = df.fillna(constant)
    elif method == 'ffill':
        df = df.fillna(method='ffill')
    elif method == 'bfill':
        df = df.fillna(method='bfill')
    elif method == 'interpolate':
        df = df.interpolate()
    else:
        return jsonify({'error': '不支持的方法'}), 400
    current_dataframe = df
    return jsonify({'success': True})

@app.route('/api/detect_missing', methods=['GET'])
def detect_missing():
    if current_dataframe is None:
        return jsonify({'missing_count': 0, 'details': {}})
    missing = current_dataframe.isnull().sum()
    total = missing.sum()
    details = {col: int(missing[col]) for col in missing.index if missing[col] > 0}
    return jsonify({'missing_count': int(total), 'details': details})

@app.route('/api/detect_outliers', methods=['POST'])
def detect_outliers():
    if current_dataframe is None:
        return jsonify({'outliers': []})
    method = request.json.get('method', 'iqr')
    outliers = []
    for col in current_dataframe.select_dtypes(include=[np.number]).columns:
        data = current_dataframe[col].dropna()
        if len(data) < 4:
            continue
        if method == 'iqr':
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            mask = (current_dataframe[col] < lower) | (current_dataframe[col] > upper)
        else:
            mean = data.mean()
            std = data.std()
            mask = np.abs((current_dataframe[col] - mean) / std) > 3
        for idx in current_dataframe.index[mask]:
            outliers.append({
                'row': int(idx),
                'col': col,
                'value': float(current_dataframe.loc[idx, col]) if pd.notna(current_dataframe.loc[idx, col]) else None
            })
    return jsonify({'outliers': outliers})

@app.route('/api/clear_outliers', methods=['POST'])
def clear_outliers():
    global current_dataframe
    data = request.json
    outliers = data.get('outliers', [])
    if current_dataframe is None:
        return jsonify({'error': '无数据'}), 400
    for o in outliers:
        row = o['row']
        col = o['col']
        if col in current_dataframe.columns and row < len(current_dataframe):
            current_dataframe.loc[row, col] = np.nan
    return jsonify({'success': True})

@app.route('/api/equations', methods=['GET'])
def get_equations():
    all_eq = {**PRESET_EQUATIONS, **user_equations}
    return jsonify(all_eq)

@app.route('/api/preview', methods=['POST'])
def preview_curve():
    data = request.json
    eq_expr = data.get('equation')
    params = data.get('params', {})
    x_min = data.get('x_min', -5)
    x_max = data.get('x_max', 5)
    steps = data.get('steps', 200)

    if '=' in eq_expr:
        _, right = eq_expr.split('=', 1)
    else:
        right = eq_expr
    right = right.replace('^', '**')

    x_vals = np.linspace(x_min, x_max, steps).tolist()
    y_vals = []
    safe_dict = {
        'x': 0, 'np': np, 'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
        'exp': np.exp, 'log': np.log, 'log10': np.log10, 'sqrt': np.sqrt,
        'abs': np.abs, 'tanh': np.tanh, 'pi': np.pi, 'e': np.e
    }
    safe_dict.update(params)
    for x in x_vals:
        safe_dict['x'] = x
        try:
            y = eval(right, {"__builtins__": {}}, safe_dict)
            y_vals.append(float(y))
        except:
            y_vals.append(np.nan)
    return jsonify({'x': x_vals, 'y': y_vals})

@app.route('/api/solve', methods=['POST'])
def solve():
    global current_dataframe, current_equation, param_mapping
    req = request.json
    equation_data = req.get('equation_data')
    param_mapping = req.get('param_mapping', {})
    x_range = req.get('x_range', [-10, 10])
    t_range = req.get('t_range', [0, 10])
    x_column = req.get('x_column')
    y_column = req.get('y_column')
    selected_rows = req.get('selected_rows', [])

    if not equation_data:
        return jsonify({'error': '方程数据为空'}), 400

    current_equation = equation_data

    if current_dataframe is not None and len(selected_rows) > 0:
        df = current_dataframe.iloc[selected_rows].reset_index(drop=True)
    else:
        df = current_dataframe

    if x_column and df is not None and x_column in df.columns:
        x_values = df[x_column].values
    else:
        x_values = np.linspace(x_range[0], x_range[1], 200)
    t_values = np.linspace(t_range[0], t_range[1], 100)

    final_params = {}
    for param, mapping in param_mapping.items():
        typ = mapping.get('type')
        val = mapping.get('value')
        if typ == 'column' and df is not None and val in df.columns:
            final_params[param] = df[val].values
        elif typ == 'constant':
            try:
                final_params[param] = float(val) if val is not None else 1.0
            except:
                final_params[param] = 1.0
        elif typ == 'x':
            final_params[param] = x_values
        elif typ == 't':
            final_params[param] = t_values
        else:
            final_params[param] = 1.0

    try:
        result = unified_solver(equation_data, final_params, x_values, t_values, x_column, y_column, df)
        serializable = serialize_result(result)
        return jsonify({'success': True, 'result': serializable})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

def unified_solver(eq_data, params, x, t, x_col, y_col, df):
    eq_str = eq_data['equation']
    display_eq = eq_data.get('display', eq_str)
    if 'd2u' in eq_str or 'du/d' in eq_str or '∂u/∂t' in eq_str:
        return solve_pde(eq_str, display_eq, params, x, t)
    elif 'dy/d' in eq_str or "y'" in eq_str or 'd2y' in eq_str:
        return solve_ode(eq_str, display_eq, params, t, eq_data.get('name', ''))
    else:
        return solve_algebraic(eq_str, display_eq, params, x, t, x_col, y_col, df)

def solve_algebraic(eq_str, display_eq, params, x, t, x_col, y_col, df):
    if '=' in eq_str:
        _, right = eq_str.split('=', 1)
    else:
        right = eq_str
    right = right.replace('^', '**')
    safe_dict = {
        'x': x, 't': t, 'np': np,
        'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
        'exp': np.exp, 'log': np.log, 'log10': np.log10,
        'sqrt': np.sqrt, 'abs': np.abs, 'tanh': np.tanh,
        'pi': np.pi, 'e': np.e, 'N': norm.cdf
    }
    safe_dict.update(params)
    if 'N(d1)' in right or 'N(d2)' in right:
        S = safe_dict.get('S', 100.0)
        K = safe_dict.get('K', 100.0)
        r = safe_dict.get('r', 0.05)
        T = safe_dict.get('T', 1.0)
        sigma = safe_dict.get('sigma', 0.2)
        T_safe = np.where(T <= 0, 1e-6, T)
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T_safe) / (sigma * np.sqrt(T_safe))
        d2 = d1 - sigma * np.sqrt(T_safe)
        safe_dict['d1'] = d1
        safe_dict['d2'] = d2
    y = eval(right, {"__builtins__": {}}, safe_dict)
    y = np.array(y, dtype=float)
    if y.shape != x.shape:
        if y.size == 1:
            y = np.full_like(x, y.flatten()[0])
        else:
            y = np.broadcast_to(y, x.shape)
    result = {'type': 'algebraic', 'x': x, 'y': y, 'equation': eq_str, 'display_eq': display_eq}
    if y_col and df is not None and y_col in df.columns:
        result['y_obs'] = df[y_col].values
    return result

def solve_ode(eq_str, display_eq, params, t, eq_name):
    k = params.get('k', 0.1) if not isinstance(params.get('k'), np.ndarray) else params['k'][0]
    zeta = params.get('zeta', 0.5) if not isinstance(params.get('zeta'), np.ndarray) else params['zeta'][0]
    omega = params.get('omega', 1.0) if not isinstance(params.get('omega'), np.ndarray) else params['omega'][0]
    r = params.get('r', 1.0) if not isinstance(params.get('r'), np.ndarray) else params['r'][0]
    K = params.get('K', 10.0) if not isinstance(params.get('K'), np.ndarray) else params['K'][0]

    is_logistic = ("逻辑斯蒂" in eq_name) or ("r * y * (1" in eq_str and "K" in eq_str)
    if "d2y" in eq_str or "y''" in eq_str:
        def damped(y, t, z, om):
            return [y[1], -2*z*om*y[1] - om**2*y[0]]
        y0 = [1.0, 0.0]
        sol = odeint(damped, y0, t, args=(zeta, omega))
        y = sol[:, 0]
    elif is_logistic:
        def logistic(y, t, rr, kk):
            return rr * y * (1 - y/kk)
        y0 = 0.1
        y = odeint(logistic, y0, t, args=(r, K)).flatten()
    else:
        def decay(y, t, kk):
            return -kk * y
        y0 = 1.0
        y = odeint(decay, y0, t, args=(k,)).flatten()
    return {'type': 'ode', 't': t, 'y': y, 'equation': eq_str, 'display_eq': display_eq}

def solve_pde(eq_str, display_eq, params, x, t):
    alpha = params.get('alpha', 0.1) if not isinstance(params.get('alpha'), np.ndarray) else params['alpha'][0]
    c = params.get('c', 1.0) if not isinstance(params.get('c'), np.ndarray) else params['c'][0]
    D = params.get('D', 0.1) if not isinstance(params.get('D'), np.ndarray) else params['D'][0]
    r = params.get('r', 1.0) if not isinstance(params.get('r'), np.ndarray) else params['r'][0]
    K = params.get('K', 10.0) if not isinstance(params.get('K'), np.ndarray) else params['K'][0]

    x_vals = x if len(x) > 1 else np.linspace(0, 10, 100)
    t_vals = t
    dx = x_vals[1] - x_vals[0] if len(x_vals) > 1 else 1.0
    dt = t_vals[1] - t_vals[0] if len(t_vals) > 1 else 0.1
    N = len(x_vals)
    u = np.zeros((len(t_vals), N))
    u[0, :] = np.exp(-(x_vals - np.mean(x_vals)) ** 2 / 2)

    if "热传导" in eq_str or "alpha" in eq_str.lower():
        r_cn = alpha * dt / (2 * dx ** 2)
        main_A = (1 + 2 * r_cn) * np.ones(N - 2)
        off_A = -r_cn * np.ones(N - 3)
        A = diags([off_A, main_A, off_A], [-1, 0, 1], format='csr')
        main_B = (1 - 2 * r_cn) * np.ones(N - 2)
        off_B = r_cn * np.ones(N - 3)
        B = diags([off_B, main_B, off_B], [-1, 0, 1], format='csr')
        for n in range(len(t_vals) - 1):
            rhs = B.dot(u[n, 1:-1])
            rhs[0] += r_cn * u[n, 0]
            rhs[-1] += r_cn * u[n, -1]
            u[n + 1, 1:-1] = spsolve(A, rhs)
            u[n + 1, 0] = u[n + 1, 1]
            u[n + 1, -1] = u[n + 1, -2]
    elif "波动" in eq_str or "c**2" in eq_str:
        u[1, :] = u[0, :]
        r_wave = c * dt / dx
        for n in range(1, len(t_vals) - 1):
            for i in range(1, N - 1):
                u[n + 1, i] = 2 * u[n, i] - u[n - 1, i] + r_wave ** 2 * (u[n, i + 1] - 2 * u[n, i] + u[n, i - 1])
            u[n + 1, 0] = u[n + 1, 1]
            u[n + 1, -1] = u[n + 1, -2]
    else:
        r_diff = D * dt / dx ** 2
        main_A = (1 + 2 * r_diff) * np.ones(N - 2)
        off_A = -r_diff * np.ones(N - 3)
        A = diags([off_A, main_A, off_A], [-1, 0, 1], format='csr')
        for n in range(len(t_vals) - 1):
            reaction = r * u[n, 1:-1] * (1 - u[n, 1:-1] / K) * dt
            rhs = u[n, 1:-1] + r_diff * (u[n, 2:] - 2 * u[n, 1:-1] + u[n, :-2]) + reaction
            u[n + 1, 1:-1] = spsolve(A, rhs)
            u[n + 1, 0] = u[n + 1, 1]
            u[n + 1, -1] = u[n + 1, -2]
    u = np.nan_to_num(u, nan=0.0, posinf=1.0, neginf=0.0)
    return {'type': 'pde', 'x': x_vals, 't': t_vals, 'u': u, 'equation': eq_str, 'display_eq': display_eq}

def serialize_result(result):
    out = {'type': result['type'], 'equation': result.get('equation'), 'display_eq': result.get('display_eq')}
    if result['type'] == 'algebraic':
        out['x'] = result['x'].tolist()
        out['y'] = result['y'].tolist()
        if 'y_obs' in result:
            out['y_obs'] = result['y_obs'].tolist()
    elif result['type'] == 'ode':
        out['t'] = result['t'].tolist()
        out['y'] = result['y'].tolist()
    elif result['type'] == 'pde':
        out['x'] = result['x'].tolist()
        out['t'] = result['t'].tolist()
        out['u'] = result['u'].tolist()
    return out

@app.route('/api/linear_regression', methods=['POST'])
def linear_regression_api():
    global current_dataframe
    try:
        data = request.json
        mode = data.get('mode', 'column')
        selected_rows = data.get('selected_rows', [])
        selected_columns = data.get('selected_columns', [])

        if current_dataframe is None:
            return jsonify({'error': '无数据，请先导入CSV或添加列'}), 400

        if mode == 'column':
            x_col = data.get('x_col')
            y_col = data.get('y_col')
            if not x_col or not y_col:
                return jsonify({'error': '请选择 X 列和 Y 列'}), 400
            if x_col not in current_dataframe.columns or y_col not in current_dataframe.columns:
                return jsonify({'error': '所选列不存在'}), 400
            if selected_rows:
                df = current_dataframe.iloc[selected_rows].copy()
            else:
                df = current_dataframe.copy()
            df = df.dropna(subset=[x_col, y_col])
            if len(df) < 2:
                return jsonify({'error': '有效数据点不足（少于2个）'}), 400
            X = df[x_col].values.reshape(-1, 1)
            y = df[y_col].values
            x_label = x_col
            y_label = y_col

        elif mode == 'single_column':
            y_col = data.get('y_col')
            if not y_col:
                return jsonify({'error': '请选择要回归的列'}), 400
            if y_col not in current_dataframe.columns:
                return jsonify({'error': '所选列不存在'}), 400
            if selected_rows:
                df = current_dataframe.iloc[selected_rows].copy()
            else:
                df = current_dataframe.copy()
            df = df.dropna(subset=[y_col])
            if len(df) < 2:
                return jsonify({'error': '有效数据点不足（少于2个）'}), 400
            X = np.arange(len(df)).reshape(-1, 1)
            y = df[y_col].values
            x_label = '行序号'
            y_label = y_col

        else:  # row mode
            row_index = data.get('row_index')
            if row_index is None:
                return jsonify({'error': '请选择行索引'}), 400
            if row_index >= len(current_dataframe):
                return jsonify({'error': '行索引超出范围'}), 400
            row_data = current_dataframe.iloc[row_index]
            if selected_columns:
                cols = [c for c in selected_columns if c in current_dataframe.columns]
            else:
                cols = current_dataframe.select_dtypes(include=[np.number]).columns.tolist()
                if not cols:
                    return jsonify({'error': '没有数值列可用于行模式'}), 400
            numeric_vals = []
            for col in cols:
                val = row_data[col]
                if pd.notna(val) and isinstance(val, (int, float)):
                    numeric_vals.append(float(val))
            if len(numeric_vals) < 2:
                return jsonify({'error': f'有效数值点不足（仅有 {len(numeric_vals)} 个数值）'}), 400
            X = np.arange(len(numeric_vals)).reshape(-1, 1)
            y = np.array(numeric_vals)
            x_label = '列序号'
            y_label = f'行 {row_index} 的数值'

        model = LinearRegression()
        model.fit(X, y)
        y_pred = model.predict(X)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot != 0 else 0
        rmse = np.sqrt(ss_res / len(y))
        n = len(y)
        p = 2
        if ss_res > 0:
            aic = n * np.log(ss_res / n) + 2 * p
            bic = n * np.log(ss_res / n) + p * np.log(n)
        else:
            aic = bic = -np.inf
        x_line = np.linspace(X.min(), X.max(), 100)
        y_line = model.predict(x_line.reshape(-1, 1))

        return jsonify({
            'success': True,
            'mode': mode,
            'slope': float(model.coef_[0]),
            'intercept': float(model.intercept_),
            'r2': r2,
            'rmse': rmse,
            'aic': aic,
            'bic': bic,
            'x_original': X.flatten().tolist(),
            'y_original': y.tolist(),
            'x_line': x_line.tolist(),
            'y_line': y_line.tolist(),
            'x_label': x_label,
            'y_label': y_label
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500


# ==================== 新增功能：数据筛选、描述性统计、非线性拟合、项目保存/加载 ====================

@app.route('/api/filter_data', methods=['POST'])
def filter_data():
    global current_dataframe
    data = request.json
    column = data.get('column')
    operator = data.get('operator')
    value = data.get('value')
    if current_dataframe is None or column not in current_dataframe.columns:
        return jsonify({'error': '无效请求'}), 400
    df = current_dataframe.copy()
    try:
        if operator == '>':
            df = df[df[column] > float(value)]
        elif operator == '>=':
            df = df[df[column] >= float(value)]
        elif operator == '<':
            df = df[df[column] < float(value)]
        elif operator == '<=':
            df = df[df[column] <= float(value)]
        elif operator == '==':
            df = df[df[column] == value]
        elif operator == 'contains' and isinstance(value, str):
            df = df[df[column].astype(str).str.contains(value, na=False)]
        else:
            return jsonify({'error': '不支持的运算符'}), 400
        current_dataframe = df.reset_index(drop=True)
        preview = current_dataframe.head(100).replace({np.nan: None}).to_dict(orient='records')
        return jsonify({
            'success': True,
            'columns': current_dataframe.columns.tolist(),
            'data': preview,
            'rows': len(current_dataframe)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/describe', methods=['GET'])
def describe_data():
    if current_dataframe is None:
        return jsonify({'error': '无数据'}), 400
    numeric_cols = current_dataframe.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) == 0:
        return jsonify({'message': '没有数值列', 'stats': {}})
    desc = current_dataframe[numeric_cols].describe().to_dict()
    skewness = current_dataframe[numeric_cols].skew().to_dict()
    kurtosis = current_dataframe[numeric_cols].kurtosis().to_dict()
    return jsonify({
        'stats': desc,
        'skewness': skewness,
        'kurtosis': kurtosis,
        'columns': numeric_cols.tolist()
    })


@app.route('/api/curve_fit', methods=['POST'])
def curve_fit():
    global current_dataframe
    data = request.json
    x_col = data.get('x_col')
    y_col = data.get('y_col')
    equation = data.get('equation')
    selected_rows = data.get('selected_rows', [])

    if current_dataframe is None or x_col not in current_dataframe.columns or y_col not in current_dataframe.columns:
        return jsonify({'error': '列不存在'}), 400

    if selected_rows:
        df = current_dataframe.iloc[selected_rows].copy()
    else:
        df = current_dataframe.copy()
    df = df.dropna(subset=[x_col, y_col])
    if len(df) < 3:
        return jsonify({'error': '有效数据点不足（至少需要3个点）'}), 400

    x_data = df[x_col].values
    y_data = df[y_col].values

    import re
    param_names = sorted(set(re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', equation)) - {'x', 'exp', 'sin', 'cos', 'tan', 'log', 'sqrt', 'log10', 'abs', 'tanh'})
    if not param_names:
        return jsonify({'error': '方程中未检测到参数（如 a,b,c）'}), 400

    def func(x, *params):
        local_dict = {'x': x, 'np': np}
        for name, val in zip(param_names, params):
            local_dict[name] = val
        try:
            return eval(equation, {"__builtins__": {}}, local_dict)
        except Exception:
            return np.full_like(x, np.nan)

    from scipy.optimize import curve_fit
    try:
        p0 = [1.0] * len(param_names)
        popt, pcov = curve_fit(func, x_data, y_data, p0=p0, maxfev=5000)
        perr = np.sqrt(np.diag(pcov)) if pcov is not None else [np.nan] * len(param_names)
        y_pred = func(x_data, *popt)
        ss_res = np.sum((y_data - y_pred) ** 2)
        ss_tot = np.sum((y_data - np.mean(y_data)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot != 0 else 0
        rmse = np.sqrt(ss_res / len(y_data))
        n = len(y_data)
        p = len(param_names)
        aic = n * np.log(ss_res / n) + 2 * p if ss_res > 0 else -np.inf
        bic = n * np.log(ss_res / n) + p * np.log(n) if ss_res > 0 else -np.inf
        x_line = np.linspace(x_data.min(), x_data.max(), 200)
        y_line = func(x_line, *popt)
        return jsonify({
            'success': True,
            'params': {name: float(popt[i]) for i, name in enumerate(param_names)},
            'errors': {name: float(perr[i]) for i, name in enumerate(param_names)},
            'r2': r2,
            'rmse': rmse,
            'aic': aic,
            'bic': bic,
            'x_original': x_data.tolist(),
            'y_original': y_data.tolist(),
            'x_line': x_line.tolist(),
            'y_line': y_line.tolist(),
            'equation': equation,
            'x_label': x_col,
            'y_label': y_col
        })
    except Exception as e:
        return jsonify({'error': f'拟合失败: {str(e)}'}), 500


@app.route('/api/save_project', methods=['POST'])
def save_project():
    """保存项目（数据 + 当前方程 + 参数映射）返回 JSON 供前端下载，处理 NaN 序列化问题"""
    global current_dataframe, current_equation, param_mapping

    def convert(obj):
        """递归转换 numpy/pandas 类型为 Python 原生类型，NaN 转为 None"""
        if isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [convert(i) for i in obj]
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj) if not np.isnan(obj) else None
        elif isinstance(obj, np.ndarray):
            return convert(obj.tolist())
        elif isinstance(obj, pd.Series):
            return convert(obj.tolist())
        elif isinstance(obj, pd.DataFrame):
            df_clean = obj.replace([np.inf, -np.inf], None).where(pd.notnull(obj), None)
            return convert(df_clean.to_dict(orient='records'))
        else:
            return obj

    try:
        if current_dataframe is None:
            return jsonify({'error': '无数据可保存'}), 400

        df_serializable = convert(current_dataframe)
        eq_serializable = convert(current_equation)
        mapping_serializable = convert(param_mapping)

        project = {
            'dataframe': df_serializable,
            'columns': convert(current_dataframe.columns.tolist()),
            'equation': eq_serializable,
            'param_mapping': mapping_serializable
        }

        # 验证序列化可行性
        json.dumps(project)
        return jsonify({'success': True, 'project': project})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'服务器内部错误: {str(e)}'}), 500


@app.route('/api/load_project', methods=['POST'])
def load_project():
    global current_dataframe, current_equation, param_mapping
    data = request.json
    project = data.get('project')
    if not project:
        return jsonify({'error': '无效项目文件'}), 400
    df_records = project.get('dataframe')
    if df_records:
        df = pd.DataFrame(df_records)
        current_dataframe = df
    else:
        current_dataframe = None
    current_equation = project.get('equation')
    param_mapping = project.get('param_mapping', {})
    return jsonify({'success': True})


# ==================== 机器学习模型接口 ====================

@app.route('/api/ml/train', methods=['POST'])
def ml_train():
    """训练机器学习模型（分类、回归、聚类）"""
    global current_dataframe, ml_models
    data = request.json
    model_type = data.get('model_type')      # 'classification', 'regression', 'clustering'
    algorithm = data.get('algorithm')        # e.g. 'logistic', 'random_forest', 'kmeans'
    target_col = data.get('target_col')      # 目标列（分类/回归必须）
    feature_cols = data.get('feature_cols', [])  # 特征列列表（聚类时可选）
    selected_rows = data.get('selected_rows', [])
    test_size = data.get('test_size', 0.2)
    params = data.get('params', {})          # 算法参数，如 {'n_estimators': 100, 'random_state': 42}

    if current_dataframe is None:
        return jsonify({'error': '无数据'}), 400

    if selected_rows:
        df = current_dataframe.iloc[selected_rows].copy()
    else:
        df = current_dataframe.copy()
    # 删除目标列缺失值
    if model_type != 'clustering' and target_col:
        df = df.dropna(subset=[target_col])
    # 特征列缺失值简单删除（或者可填充，此处简化）
    if feature_cols:
        df = df.dropna(subset=feature_cols)
    if len(df) < 2:
        return jsonify({'error': '有效样本不足'}), 400

    if model_type in ['classification', 'regression']:
        if target_col not in df.columns:
            return jsonify({'error': f'目标列 {target_col} 不存在'}), 400
        if not feature_cols:
            # 默认所有数值列（除目标列外）
            feature_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c != target_col]
        if len(feature_cols) == 0:
            return jsonify({'error': '没有可用的特征列'}), 400
        X = df[feature_cols].values
        y = df[target_col].values

        # 处理目标列编码（如果是分类且为字符串）
        label_encoder = None
        if model_type == 'classification' and y.dtype == 'object':
            label_encoder = LabelEncoder()
            y = label_encoder.fit_transform(y)
            class_names = label_encoder.classes_.tolist()
        else:
            class_names = None

        # 划分训练/测试集
        stratify = y if model_type == 'classification' else None
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=params.get('random_state', 42), stratify=stratify)

        # 标准化（部分算法需要）
        scaler = None
        if algorithm in ['svm', 'svr', 'knn', 'kneighbors']:
            scaler = StandardScaler()
            X_train = scaler.fit_transform(X_train)
            X_test = scaler.transform(X_test)

        # 选择模型
        if model_type == 'classification':
            if algorithm == 'logistic':
                model = LogisticRegression(max_iter=1000, random_state=params.get('random_state', 42))
            elif algorithm == 'decision_tree':
                model = DecisionTreeClassifier(random_state=params.get('random_state', 42))
            elif algorithm == 'random_forest':
                model = RandomForestClassifier(random_state=params.get('random_state', 42))
            elif algorithm == 'svm':
                model = SVC(probability=True, random_state=params.get('random_state', 42))
            elif algorithm == 'knn':
                model = KNeighborsClassifier()
            else:
                return jsonify({'error': f'不支持的分类算法: {algorithm}'}), 400
        else:  # regression
            if algorithm == 'linear':
                model = LinearRegression()
            elif algorithm == 'ridge':
                model = Ridge(random_state=params.get('random_state', 42))
            elif algorithm == 'lasso':
                model = Lasso(random_state=params.get('random_state', 42))
            elif algorithm == 'decision_tree':
                model = DecisionTreeRegressor(random_state=params.get('random_state', 42))
            elif algorithm == 'random_forest':
                model = RandomForestRegressor(random_state=params.get('random_state', 42))
            elif algorithm == 'svm':
                model = SVR()
            elif algorithm == 'knn':
                model = KNeighborsRegressor()
            else:
                return jsonify({'error': f'不支持的回归算法: {algorithm}'}), 400

        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        model_id = str(uuid.uuid4())
        ml_models[model_id] = {
            'model': model,
            'type': model_type,
            'algorithm': algorithm,
            'feature_cols': feature_cols,
            'target_col': target_col,
            'params': params,
            'scaler': scaler,
            'label_encoder': label_encoder,
            'class_names': class_names
        }

        # 评估指标
        if model_type == 'classification':
            acc = accuracy_score(y_test, y_pred)
            cm = confusion_matrix(y_test, y_pred).tolist()
            report = classification_report(y_test, y_pred, output_dict=True)
            metrics = {'accuracy': acc, 'confusion_matrix': cm, 'classification_report': report}
        else:
            r2 = r2_score(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            metrics = {'r2': r2, 'rmse': rmse}

        return jsonify({
            'success': True,
            'model_id': model_id,
            'algorithm': algorithm,
            'model_type': model_type,
            'feature_cols': feature_cols,
            'target_col': target_col,
            'metrics': metrics
        })

    elif model_type == 'clustering':
        if not feature_cols:
            feature_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(feature_cols) == 0:
            return jsonify({'error': '没有数值特征列用于聚类'}), 400
        X = df[feature_cols].values
        n_clusters = params.get('n_clusters', 3)
        model = KMeans(n_clusters=n_clusters, random_state=params.get('random_state', 42), n_init=10)
        labels = model.fit_predict(X)
        model_id = str(uuid.uuid4())
        ml_models[model_id] = {
            'model': model,
            'type': 'clustering',
            'algorithm': 'kmeans',
            'feature_cols': feature_cols,
            'params': params
        }
        silhouette = silhouette_score(X, labels) if len(set(labels)) > 1 else None
        return jsonify({
            'success': True,
            'model_id': model_id,
            'algorithm': 'kmeans',
            'model_type': 'clustering',
            'feature_cols': feature_cols,
            'n_clusters': n_clusters,
            'silhouette_score': silhouette,
            'cluster_labels': labels.tolist()
        })

    else:
        return jsonify({'error': 'model_type 必须是 classification, regression 或 clustering'}), 400


@app.route('/api/ml/predict', methods=['POST'])
def ml_predict():
    """使用已训练的模型对新数据进行预测"""
    global current_dataframe, ml_models
    data = request.json
    model_id = data.get('model_id')
    new_data_rows = data.get('new_data')  # 可选，如果为空则使用当前数据中的特征列
    if model_id not in ml_models:
        return jsonify({'error': '模型不存在'}), 404
    model_info = ml_models[model_id]
    model = model_info['model']
    feature_cols = model_info['feature_cols']
    model_type = model_info['type']
    scaler = model_info.get('scaler')
    label_encoder = model_info.get('label_encoder')

    if new_data_rows is not None:
        df_new = pd.DataFrame(new_data_rows)
        # 检查特征列是否存在
        missing = [c for c in feature_cols if c not in df_new.columns]
        if missing:
            return jsonify({'error': f'新数据缺少特征列: {missing}'}), 400
        X = df_new[feature_cols].values
    else:
        if current_dataframe is None:
            return jsonify({'error': '无当前数据，请提供 new_data 参数'}), 400
        df = current_dataframe.dropna()
        missing = [c for c in feature_cols if c not in df.columns]
        if missing:
            return jsonify({'error': f'当前数据缺少特征列: {missing}'}), 400
        X = df[feature_cols].values

    if scaler is not None:
        X = scaler.transform(X)

    if model_type == 'clustering':
        predictions = model.predict(X).tolist()
    else:
        predictions = model.predict(X).tolist()
        if label_encoder is not None:
            # 将数值标签还原为原始类别名称
            predictions = label_encoder.inverse_transform(predictions).tolist()

    return jsonify({
        'success': True,
        'model_id': model_id,
        'predictions': predictions,
        'num_samples': len(predictions)
    })


@app.route('/api/ml/models', methods=['GET'])
def ml_list_models():
    """列出所有已保存的模型"""
    models_info = []
    for mid, info in ml_models.items():
        models_info.append({
            'model_id': mid,
            'type': info['type'],
            'algorithm': info['algorithm'],
            'feature_cols': info['feature_cols'],
            'target_col': info.get('target_col'),
            'params': info.get('params', {})
        })
    return jsonify({'models': models_info})


@app.route('/api/ml/models/<model_id>', methods=['DELETE'])
def ml_delete_model(model_id):
    """删除指定模型"""
    global ml_models
    if model_id in ml_models:
        del ml_models[model_id]
        return jsonify({'success': True})
    else:
        return jsonify({'error': '模型不存在'}), 404


if __name__ == '__main__':
    import webbrowser
    from threading import Timer
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        Timer(1, lambda: webbrowser.open('http://127.0.0.1:5000')).start()
    app.run(debug=True, host='0.0.0.0', port=5000)