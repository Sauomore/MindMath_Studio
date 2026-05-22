# -*- coding: utf-8 -*-
import os
import json
import pandas as pd
import numpy as np
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from scipy.stats import norm
from scipy.integrate import odeint
from scipy.sparse import diags
from scipy.sparse.linalg import spsolve
from sklearn.linear_model import LinearRegression
from utils import PRESET_EQUATIONS, to_latex_display, python_to_math_expr

app = Flask(__name__)
CORS(app)

current_dataframe = None
user_equations = {}

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
    global current_dataframe
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

if __name__ == '__main__':
    import webbrowser
    from threading import Timer
    import os
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        Timer(1, lambda: webbrowser.open('http://127.0.0.1:5000')).start()
    app.run(debug=True, host='0.0.0.0', port=5000)