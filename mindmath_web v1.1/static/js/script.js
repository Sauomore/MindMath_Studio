//SPDX-License-Identifier: MIT
//Copyright (c) 2026, Sauomore

// static/js/script.js
// MindMath Studio 主前端脚本

document.addEventListener('DOMContentLoaded', function() {
    // ---------- 全局状态 ----------
    let currentData = { columns: [], rows: [], selectedRows: new Set() };
    let equations = {};
    let currentEquationKey = null;
    let currentEquationData = null;
    let paramMapping = {};
    let previewChart = null;
    let currentOutliers = [];
    let resultChart = null;
    let currentResult = null;
    let sliceChart = null;

    // DOM 元素
    const dataPanel = document.getElementById('dataPanel');
    const equationPanel = document.getElementById('equationPanel');
    const resultPanel = document.getElementById('resultPanel');
    const mlPanel = document.getElementById('mlPanel');
    const btnData = document.getElementById('btnData');
    const btnEquation = document.getElementById('btnEquation');
    const btnResult = document.getElementById('btnResult');
    const btnML = document.getElementById('btnML');

    function showPanel(panel) {
        dataPanel.style.display = 'none';
        equationPanel.style.display = 'none';
        resultPanel.style.display = 'none';
        mlPanel.style.display = 'none';
        if (panel === 'data') dataPanel.style.display = 'block';
        else if (panel === 'equation') equationPanel.style.display = 'block';
        else if (panel === 'result') resultPanel.style.display = 'block';
        else if (panel === 'ml') mlPanel.style.display = 'block';
        [btnData, btnEquation, btnResult, btnML].forEach(btn => btn.classList.remove('active-nav'));
        if (panel === 'data') btnData.classList.add('active-nav');
        else if (panel === 'equation') btnEquation.classList.add('active-nav');
        else if (panel === 'result') btnResult.classList.add('active-nav');
        else if (panel === 'ml') btnML.classList.add('active-nav');
    }
    btnData.onclick = () => showPanel('data');
    btnEquation.onclick = () => { showPanel('equation'); loadEquations(); updateLRMode(); };
    btnResult.onclick = () => showPanel('result');
    btnML.onclick = () => { showPanel('ml'); updateMLColumns(); updateMLModelSelect(); };

    // 模态框
    const introModal = document.getElementById('introModal');
    const aboutModal = document.getElementById('aboutModal');
    const faqModal = document.getElementById('faqModal');
    const describeModal = document.getElementById('describeModal');
    document.getElementById('introBtn').onclick = () => introModal.style.display = 'flex';
    document.getElementById('aboutBtn').onclick = () => aboutModal.style.display = 'flex';
    document.getElementById('faqBtn').onclick = () => faqModal.style.display = 'flex';
    document.getElementById('closeIntroModal').onclick = () => introModal.style.display = 'none';
    document.getElementById('closeAboutModal').onclick = () => aboutModal.style.display = 'none';
    document.getElementById('closeFaqModal').onclick = () => faqModal.style.display = 'none';
    document.getElementById('closeDescribeModal').onclick = () => describeModal.style.display = 'none';
    window.onclick = function(e) {
        if (e.target === introModal) introModal.style.display = 'none';
        if (e.target === aboutModal) aboutModal.style.display = 'none';
        if (e.target === faqModal) faqModal.style.display = 'none';
        if (e.target === describeModal) describeModal.style.display = 'none';
    };

    function escapeHtml(str) { if (!str) return ''; return str.replace(/[&<>]/g, function(m) { return { '&':'&amp;', '<':'&lt;', '>':'&gt;' }[m] || m; }); }

    // 更新筛选列下拉框
    function updateFilterColumns() {
        const filterCol = document.getElementById('filterColumn');
        if (!filterCol) return;
        filterCol.innerHTML = '<option value="">选择列</option>';
        currentData.columns.forEach(col => {
            const opt = document.createElement('option');
            opt.value = col;
            opt.textContent = col;
            filterCol.appendChild(opt);
        });
    }
    function updateFitColumns() {
        const fitX = document.getElementById('fitXCol');
        const fitY = document.getElementById('fitYCol');
        if (!fitX || !fitY) return;
        fitX.innerHTML = ''; fitY.innerHTML = '';
        if (currentData.columns.length === 0) return;
        currentData.columns.forEach(col => {
            fitX.appendChild(new Option(col, col));
            fitY.appendChild(new Option(col, col));
        });
    }

    // 数据表格
    async function loadData() {
        const res = await fetch('/api/current_data');
        const json = await res.json();
        if (json.columns) {
            currentData.columns = json.columns;
            currentData.rows = json.data;
            currentData.selectedRows.clear();
            renderTable();
            updateLinearRegressionColumns();
            updateRowModeSelectors();
            updateLRMode();
            updateFilterColumns();
            updateFitColumns();
            updateMLColumns();
        }
    }

    function renderTable() {
    const thead = document.getElementById('tableHead');
    const tbody = document.getElementById('tableBody');
    thead.innerHTML = '';
    tbody.innerHTML = '';

    // 关键：如果没有列，显示提示并返回
    if (!currentData.columns || currentData.columns.length === 0) {
        thead.innerHTML = '<tr><th>暂无数据，请导入CSV或添加列</th></tr>';
        return;
    }

    // 生成表头：复选框 + 每列名称
    let headerHtml = '<tr><th class="checkbox-col"><input type="checkbox" id="selectAll"></th>';
    currentData.columns.forEach(function(col) {
        headerHtml += '<th>' + escapeHtml(col) + '</th>';
    });
    headerHtml += '</tr>';
    thead.innerHTML = headerHtml;

    // 全选/反选事件绑定
    const selectAll = document.getElementById('selectAll');
    if (selectAll) {
        selectAll.onchange = function(e) {
            document.querySelectorAll('.row-select').forEach(function(chk, idx) {
                chk.checked = e.target.checked;
                updateSelectedRow(parseInt(chk.dataset.idx), chk.checked);
            });
        };
    }

    // 生成数据行
    currentData.rows.forEach(function(row, idx) {
        let tr = '<tr>';
        tr += '<td class="checkbox-col"><input type="checkbox" class="row-select" data-idx="' + idx + '"></td>';
        currentData.columns.forEach(function(col) {
            let val = (row[col] !== undefined && row[col] !== null) ? row[col] : '';
            tr += '<td contenteditable="true" data-row="' + idx + '" data-col="' + escapeHtml(col) + '">' + escapeHtml(String(val)) + '</td>';
        });
        tr += '</tr>';
        tbody.insertAdjacentHTML('beforeend', tr);
    });

    // 绑定可编辑单元格的失焦事件
    document.querySelectorAll('td[contenteditable="true"]').forEach(function(cell) {
        cell.onblur = async function(e) {
            const row = parseInt(cell.dataset.row);
            const col = cell.dataset.col;
            const val = cell.innerText;
            await fetch('/api/update_cell', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ row: row, col: col, value: val })
            });
            loadData();
        };
    });

    // 绑定行选择框事件
    document.querySelectorAll('.row-select').forEach(function(chk) {
        chk.onchange = function(e) {
            let idx = parseInt(e.target.dataset.idx);
            updateSelectedRow(idx, e.target.checked);
        };
    });

    document.getElementById('cleanMsg').innerText = '共 ' + currentData.rows.length + ' 行，已选 ' + currentData.selectedRows.size + ' 行';

    // 更新其他下拉框
    updateLinearRegressionColumns();
    updateRowModeSelectors();
    updateFilterColumns();
    updateFitColumns();
    updateMLColumns();
    applyStickyHeader();
    }

    function updateSelectedRow(idx, checked) {
        if (checked) currentData.selectedRows.add(idx);
        else currentData.selectedRows.delete(idx);
        document.getElementById('cleanMsg').innerText = '共 ' + currentData.rows.length + ' 行，已选 ' + currentData.selectedRows.size + ' 行';
    }

    function updateLinearRegressionColumns() {
        const cols = currentData.columns;
        const xSel = document.getElementById('lrXCol');
        const ySel = document.getElementById('lrYCol');
        const singleSel = document.getElementById('lrSingleYCol');
        if (!xSel || !ySel || !singleSel) return;
        xSel.innerHTML = ''; ySel.innerHTML = ''; singleSel.innerHTML = '';
        if (cols.length === 0) {
            xSel.innerHTML = '<option>无数据</option>'; ySel.innerHTML = '<option>无数据</option>'; singleSel.innerHTML = '<option>无数据</option>';
            return;
        }
        cols.forEach(function(c) {
            xSel.appendChild(new Option(c, c));
            ySel.appendChild(new Option(c, c));
            singleSel.appendChild(new Option(c, c));
        });
    }

    function updateRowModeSelectors() {
        const rowSel = document.getElementById('lrRowIndex');
        const colStart = document.getElementById('lrColStart');
        const colEnd = document.getElementById('lrColEnd');
        if (!rowSel) return;
        rowSel.innerHTML = '';
        if (currentData.rows.length === 0) { rowSel.innerHTML = '<option>无数据</option>'; return; }
        for (let i = 0; i < currentData.rows.length; i++) rowSel.appendChild(new Option('行 ' + i, i));
        if (colStart && colEnd) {
            const cols = currentData.columns;
            colStart.innerHTML = '<option value="">全部</option>';
            colEnd.innerHTML = '<option value="">全部</option>';
            cols.forEach(function(c) { colStart.appendChild(new Option(c, c)); colEnd.appendChild(new Option(c, c)); });
        }
    }

    function updateLRMode() {
        const mode = document.querySelector('input[name="lrMode"]:checked').value;
        document.getElementById('lrColumnMode').style.display = mode === 'column' ? 'flex' : 'none';
        document.getElementById('lrSingleColumnMode').style.display = mode === 'single_column' ? 'block' : 'none';
        document.getElementById('lrRowMode').style.display = mode === 'row' ? 'block' : 'none';
        if (mode === 'row') updateRowModeSelectors();
    }
    document.querySelectorAll('input[name="lrMode"]').forEach(function(r) { r.addEventListener('change', updateLRMode); });

    // 方程库
    async function loadEquations() {
        const res = await fetch('/api/equations');
        equations = await res.json();
        renderEquationList();
    }
    function renderEquationList() {
        const container = document.getElementById('eqList');
        container.innerHTML = '';
        const search = document.getElementById('searchEq').value.toLowerCase();
        for (let [name, data] of Object.entries(equations)) {
            if (search && !name.toLowerCase().includes(search)) continue;
            const div = document.createElement('div');
            div.className = 'eq-item' + (currentEquationKey === name ? ' selected' : '');
            div.innerHTML = '<strong>' + escapeHtml(name) + '</strong><br><small>' + escapeHtml(data.display || data.equation) + '</small>';
            div.onclick = function() { selectEquation(name, data); };
            container.appendChild(div);
        }
    }
    function selectEquation(name, data) {
        currentEquationKey = name;
        currentEquationData = data;
        document.getElementById('eqName').innerText = name;
        document.getElementById('eqFormula').innerText = data.display || data.equation;
        renderParamInputs(data.params || []);
        renderEquationList();
        updatePreview();
    }
    function renderParamInputs(params) {
        const area = document.getElementById('paramArea');
        area.innerHTML = '';
        paramMapping = {};
        if (!params.length) { area.innerHTML = '<div style="color:gray;">无参数</div>'; return; }
        params.forEach(function(p) {
            const div = document.createElement('div');
            div.className = 'param-row';
            div.innerHTML = '<span>' + escapeHtml(p) + '</span><div><select class="param-type" data-param="' + p + '"><option value="constant">常数</option><option value="column">数据列</option><option value="x">变量x</option><option value="t">变量t</option></select><input class="param-value" placeholder="值或列名" style="width:120px;"></div>';
            area.appendChild(div);
            const typeSel = div.querySelector('.param-type');
            const valInp = div.querySelector('.param-value');
            function update() {
                let typ = typeSel.value, val = valInp.value;
                if (typ === 'constant') { if (!val) val = '1'; valInp.placeholder = '数值'; }
                else if (typ === 'column') valInp.placeholder = '列名';
                else { valInp.placeholder = '(自动)'; val = null; }
                paramMapping[p] = { type: typ, value: val };
                updatePreview();
            }
            typeSel.onchange = update;
            valInp.oninput = update;
            typeSel.value = 'constant';
            valInp.value = '1';
            update();
        });
    }
    async function updatePreview() {
        if (!currentEquationData) return;
        const xMin = parseFloat(document.getElementById('xMin').value);
        const xMax = parseFloat(document.getElementById('xMax').value);
        const paramsPreview = {};
        for (let [p, map] of Object.entries(paramMapping)) {
            paramsPreview[p] = map.type === 'constant' ? (parseFloat(map.value) || 1) : 1;
        }
        const res = await fetch('/api/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ equation: currentEquationData.equation, params: paramsPreview, x_min: xMin, x_max: xMax, steps: 200 }) });
        const json = await res.json();
        if (previewChart) previewChart.destroy();
        const ctx = document.getElementById('previewCanvas').getContext('2d');
        previewChart = new Chart(ctx, { type: 'line', data: { labels: json.x.map(function(v) { return v.toFixed(2); }), datasets: [{ label: '预览曲线', data: json.y, borderColor: '#4a90e2', fill: false, pointRadius: 0 }] }, options: { responsive: true } });
    }
    document.getElementById('refreshPreviewBtn').onclick = updatePreview;
    document.getElementById('searchEq').oninput = function() { renderEquationList(); };
    document.getElementById('addCustomEqBtn').onclick = function() {
        const name = prompt('方程名称');
        if (!name) return;
        const eq = prompt('表达式 (y = ...)');
        if (!eq) return;
        const paramsRaw = prompt('参数名 (逗号分隔)');
        const params = paramsRaw ? paramsRaw.split(',').map(function(s) { return s.trim(); }) : [];
        fetch('/api/user_equations', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: name, equation_data: { equation: eq, display: eq, params: params, description: '自定义' } }) }).then(function() { loadEquations(); });
    };
    document.getElementById('delCustomEqBtn').onclick = function() {
        if (!currentEquationKey) { alert('请选中一个自定义方程'); return; }
        fetch('/api/delete_user_equation', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: currentEquationKey }) }).then(function() { loadEquations(); });
    };

    // 线性回归
    document.getElementById('lrRunBtn').onclick = async function() {
        const mode = document.querySelector('input[name="lrMode"]:checked').value;
        let payload = { mode: mode, selected_rows: Array.from(currentData.selectedRows) };
        if (mode === 'column') {
            const x = document.getElementById('lrXCol').value;
            const y = document.getElementById('lrYCol').value;
            if (!x || !y) { alert('请选择X,Y列'); return; }
            payload.x_col = x; payload.y_col = y;
        } else if (mode === 'single_column') {
            const y = document.getElementById('lrSingleYCol').value;
            if (!y) { alert('请选择Y列'); return; }
            payload.y_col = y;
        } else {
            const row = parseInt(document.getElementById('lrRowIndex').value);
            if (isNaN(row)) { alert('请选择行'); return; }
            payload.row_index = row;
            const start = document.getElementById('lrColStart').value;
            const end = document.getElementById('lrColEnd').value;
            if (start && end) {
                const cols = currentData.columns;
                const si = cols.indexOf(start);
                const ei = cols.indexOf(end);
                if (si !== -1 && ei !== -1 && si <= ei) payload.selected_columns = cols.slice(si, ei+1);
            }
        }
        const btn = document.getElementById('lrRunBtn');
        btn.innerHTML = '<i class="fas fa-spinner fa-pulse"></i> 计算中...';
        const res = await fetch('/api/linear_regression', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const json = await res.json();
        btn.innerHTML = '<i class="fas fa-chart-line"></i> 执行线性回归';
        if (json.success) { showPanel('result'); displayLinearRegressionResult(json); }
        else alert('回归失败: ' + json.error);
    };

    function displayLinearRegressionResult(data) {
        document.getElementById('algebraicOdeContainer').style.display = 'grid';
        document.getElementById('pdeContainer').style.display = 'none';
        if (resultChart) resultChart.destroy();
        const canvas = document.getElementById('resultCanvas');
        if (!canvas) return;
        resultChart = new Chart(canvas.getContext('2d'), {
            type: 'scatter',
            data: {
                datasets: [
                    { label: '原始数据 (' + data.x_label + ' vs ' + data.y_label + ')', data: data.x_original.map(function(x,i) { return { x: x, y: data.y_original[i] }; }), backgroundColor: '#4a90e2', pointRadius: 4, type: 'scatter' },
                    { label: '拟合线: y = ' + data.slope.toFixed(4) + ' * x + ' + data.intercept.toFixed(4), data: data.x_line.map(function(x,i) { return { x: x, y: data.y_line[i] }; }), borderColor: '#e67e22', borderWidth: 2, fill: false, type: 'line', pointRadius: 0 }
                ]
            },
            options: { responsive: true, scales: { x: { title: { display: true, text: data.x_label } }, y: { title: { display: true, text: data.y_label } } } }
        });
        document.getElementById('statsPanel').innerHTML = '<strong>线性回归统计量</strong><br>R²: ' + data.r2.toFixed(6) + '<br>RMSE: ' + data.rmse.toFixed(6) + '<br>AIC: ' + data.aic.toFixed(2) + '<br>BIC: ' + data.bic.toFixed(2) + '<br>斜率: ' + data.slope.toFixed(6) + '<br>截距: ' + data.intercept.toFixed(6);
        document.getElementById('infoPanel').innerHTML = '线性回归模型: ' + data.y_label + ' = ' + data.slope.toFixed(4) + ' * ' + data.x_label + ' + ' + data.intercept.toFixed(4);
    }

    // 非线性拟合
    document.getElementById('runFitBtn').onclick = async function() {
        const xCol = document.getElementById('fitXCol').value;
        const yCol = document.getElementById('fitYCol').value;
        const equation = document.getElementById('fitEquation').value;
        if (!xCol || !yCol) { alert('请选择 X 列和 Y 列'); return; }
        if (!equation) { alert('请输入方程表达式'); return; }
        const selectedIndices = Array.from(currentData.selectedRows);
        const btn = document.getElementById('runFitBtn');
        btn.innerHTML = '<i class="fas fa-spinner fa-pulse"></i> 拟合中...';
        const res = await fetch('/api/curve_fit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ x_col: xCol, y_col: yCol, equation: equation, selected_rows: selectedIndices })
        });
        const json = await res.json();
        btn.innerHTML = '开始拟合';
        if (json.success) {
            showPanel('result');
            displayFitResult(json);
        } else alert('拟合失败: ' + json.error);
    };

    function displayFitResult(data) {
        document.getElementById('algebraicOdeContainer').style.display = 'grid';
        document.getElementById('pdeContainer').style.display = 'none';
        if (resultChart) resultChart.destroy();
        const canvas = document.getElementById('resultCanvas');
        if (!canvas) return;
        const scatterData = data.x_original.map((x, i) => ({ x: x, y: data.y_original[i] }));
        const lineData = data.x_line.map((x, i) => ({ x: x, y: data.y_line[i] }));
        resultChart = new Chart(canvas.getContext('2d'), {
            type: 'scatter',
            data: {
                datasets: [
                    { label: `原始数据 (${data.x_label} vs ${data.y_label})`, data: scatterData, backgroundColor: '#4a90e2', pointRadius: 4, type: 'scatter' },
                    { label: `拟合曲线: ${data.equation}`, data: lineData, borderColor: '#e67e22', borderWidth: 2, fill: false, type: 'line', pointRadius: 0 }
                ]
            },
            options: { responsive: true, scales: { x: { title: { display: true, text: data.x_label } }, y: { title: { display: true, text: data.y_label } } } }
        });
        let paramsStr = Object.entries(data.params).map(([k, v]) => `${k}=${v.toFixed(4)}`).join(', ');
        document.getElementById('statsPanel').innerHTML = `
            <strong>非线性拟合结果</strong><br>
            参数: ${paramsStr}<br>
            R²: ${data.r2.toFixed(6)}<br>
            RMSE: ${data.rmse.toFixed(6)}<br>
            AIC: ${data.aic.toFixed(2)}<br>
            BIC: ${data.bic.toFixed(2)}
        `;
        document.getElementById('infoPanel').innerHTML = `方程: ${data.equation}<br>${data.y_label} = f(${data.x_label})`;
    }

    // 数据筛选
    document.getElementById('applyFilterBtn').onclick = async function() {
        const column = document.getElementById('filterColumn').value;
        const operator = document.getElementById('filterOperator').value;
        const value = document.getElementById('filterValue').value;
        if (!column) { alert('请选择列'); return; }
        const res = await fetch('/api/filter_data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ column, operator, value })
        });
        const json = await res.json();
        if (json.success) {
            currentData.columns = json.columns;
            currentData.rows = json.data;
            currentData.selectedRows.clear();
            renderTable();
        } else alert('筛选失败: ' + json.error);
    };
    document.getElementById('resetFilterBtn').onclick = function() { loadData(); };

    // 描述性统计
    document.getElementById('describeBtn').onclick = async function() {
        const res = await fetch('/api/describe');
        const json = await res.json();
        if (json.error) { alert(json.error); return; }
        if (json.columns.length === 0) { alert('没有数值列'); return; }
        let html = '<table border="1" style="border-collapse:collapse;width:100%;"><thead><tr><th>统计量</th>';
        json.columns.forEach(col => html += `<th>${col}</th>`);
        html += '</table></thead><tbody>';
        const statsNames = ['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max'];
        statsNames.forEach(stat => {
            html += '<tr><td><strong>' + stat + '</strong></td>';
            json.columns.forEach(col => {
                let val = (json.stats[col] && json.stats[col][stat] !== undefined) ? json.stats[col][stat] : '-';
                if (typeof val === 'number') val = val.toFixed(4);
                html += `<td>${val}</td>`;
            });
            html += '</tr>';
        });
        html += '<tr><td><strong>偏度</strong></td>';
        json.columns.forEach(col => {
            let val = json.skewness[col] !== undefined ? json.skewness[col].toFixed(4) : '-';
            html += `<td>${val}</td>`;
        });
        html += '</tr>';
        html += '<tr><td><strong>峰度</strong></td>';
        json.columns.forEach(col => {
            let val = json.kurtosis[col] !== undefined ? json.kurtosis[col].toFixed(4) : '-';
            html += `<td>${val}</td>`;
        });
        html += '</tr></tbody></table>';
        document.getElementById('describeContent').innerHTML = html;
        describeModal.style.display = 'flex';
    };

    // 项目保存/加载（确保按钮事件绑定）
    const saveProjectBtn = document.getElementById('saveProjectBtn');
    const loadProjectBtn = document.getElementById('loadProjectBtn');

    if (saveProjectBtn) {
        saveProjectBtn.onclick = async function() {
            try {
                const res = await fetch('/api/save_project', { method: 'POST' });
                const json = await res.json();
                if (json.success) {
                    const blob = new Blob([JSON.stringify(json.project, null, 2)], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'mindmath_project.json';
                    a.click();
                    URL.revokeObjectURL(url);
                    alert('项目已保存');
                } else {
                    alert('保存失败: ' + (json.error || '未知错误'));
                }
            } catch (err) {
                alert('保存失败: ' + err.message);
            }
        };
    } else {
        console.error('未找到保存项目按钮 (id="saveProjectBtn")');
    }

    if (loadProjectBtn) {
        loadProjectBtn.onclick = function() {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'application/json';
            input.onchange = async function(e) {
                const file = e.target.files[0];
                if (!file) return;
                const text = await file.text();
                const project = JSON.parse(text);
                const res = await fetch('/api/load_project', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ project })
                });
                const json = await res.json();
                if (json.success) {
                    alert('项目加载成功，即将刷新页面');
                    location.reload();
                } else {
                    alert('加载失败: ' + json.error);
                }
            };
            input.click();
        };
    } else {
        console.error('未找到加载项目按钮 (id="loadProjectBtn")');
    }

    // 求解
    document.getElementById('solveBtn').onclick = async function() {
        if (!currentEquationData) { alert('请先选择方程'); return; }
        const xRange = [parseFloat(document.getElementById('xMin').value), parseFloat(document.getElementById('xMax').value)];
        const tRange = [parseFloat(document.getElementById('tMin').value), parseFloat(document.getElementById('tMax').value)];
        const payload = { equation_data: currentEquationData, param_mapping: paramMapping, x_range: xRange, t_range: tRange, x_column: null, y_column: null, selected_rows: Array.from(currentData.selectedRows) };
        const btn = document.getElementById('solveBtn');
        btn.innerHTML = '<i class="fas fa-spinner fa-pulse"></i> 求解中...';
        const res = await fetch('/api/solve', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const json = await res.json();
        btn.innerHTML = '<i class="fas fa-play"></i> 开始求解';
        if (json.success) { currentResult = json.result; displayResult(currentResult); }
        else alert('求解失败: ' + json.error);
    };
    document.getElementById('exportResultBtn').onclick = function() { if (currentResult) alert('导出功能已实现，详见控制台'); };
    document.getElementById('clearResultBtn').onclick = function() {
        currentResult = null;
        document.getElementById('algebraicOdeContainer').style.display = 'grid';
        document.getElementById('pdeContainer').style.display = 'none';
        if (resultChart) resultChart.destroy();
        document.getElementById('statsPanel').innerHTML = '<strong>拟合统计量</strong><br>R²: --<br>RMSE: --<br>AIC: --<br>BIC: --';
        document.getElementById('infoPanel').innerHTML = '';
    };
    function displayResult(result) {
        document.getElementById('algebraicOdeContainer').style.display = 'none';
        document.getElementById('pdeContainer').style.display = 'none';
        if (result.type === 'pde') {
            document.getElementById('pdeContainer').style.display = 'block';
            renderPdeResult(result);
        } else {
            document.getElementById('algebraicOdeContainer').style.display = 'grid';
            renderAlgebraicOdeResult(result);
        }
    }
    function renderAlgebraicOdeResult(result) {
        if (resultChart) resultChart.destroy();
        let xData, yData, yObs = null, isOde = (result.type === 'ode');
        if (isOde) { xData = result.t; yData = result.y; }
        else { xData = result.x; yData = result.y; yObs = result.y_obs; }
        const chartType = document.getElementById('chartTypeSelect').value;
        let chartConfig = { type: 'line', data: {}, options: { responsive: true } };
        if (chartType === 'residual' && yObs) {
            const residuals = yObs.map(function(obs,i) { return obs - yData[i]; });
            chartConfig.type = 'scatter';
            chartConfig.data = { datasets: [{ label: '残差', data: xData.map(function(x,i) { return { x: x, y: residuals[i] }; }), backgroundColor: '#e74c3c', pointRadius: 3 }] };
            chartConfig.options.scales = { x: { title: { display: true, text: isOde ? 't' : 'x' } }, y: { title: { display: true, text: '残差' } } };
        } else if (chartType === 'qq' && !isOde) {
            const sorted = [...yData].sort(function(a,b) { return a-b; });
            const n = sorted.length;
            const theoretical = sorted.map(function(_,i) { const p = (i+0.5)/n; return Math.sqrt(2)*Math.erfinv(2*p-1); });
            chartConfig.type = 'scatter';
            chartConfig.data = { datasets: [{ label: 'Q-Q 图', data: theoretical.map(function(t,i) { return { x: t, y: sorted[i] }; }), backgroundColor: '#4a90e2', pointRadius: 3 }] };
            chartConfig.options.scales = { x: { title: { display: true, text: '理论分位数' } }, y: { title: { display: true, text: '样本分位数' } } };
        } else {
            let dataset = { label: '模型结果', data: xData.map(function(x,i) { return { x: x, y: yData[i] }; }), borderColor: '#4a90e2', backgroundColor: '#4a90e2' };
            if (chartType === 'line') { dataset.showLine = true; dataset.pointRadius = 0; }
            else if (chartType === 'scatter') { dataset.showLine = false; dataset.pointRadius = 3; }
            else if (chartType === 'bar') { chartConfig.type = 'bar'; dataset = { label: '模型结果', data: yData, backgroundColor: '#4a90e2' }; xData = xData.map(function(v) { return v.toFixed(2); }); }
            else if (chartType === 'step') { dataset.showLine = true; dataset.stepped = true; dataset.pointRadius = 0; }
            else if (chartType === 'fill') { dataset.fill = true; dataset.backgroundColor = 'rgba(74,144,226,0.2)'; }
            chartConfig.data = { datasets: [dataset] };
            if (chartType !== 'bar') chartConfig.data.labels = xData.map(function(v) { return v.toFixed(2); });
            else chartConfig.data.labels = xData;
            chartConfig.options.scales = { x: { title: { display: true, text: isOde ? 't' : 'x' } }, y: { title: { display: true, text: 'y' } } };
        }
        const canvas = document.getElementById('resultCanvas');
        if (canvas) resultChart = new Chart(canvas.getContext('2d'), chartConfig);
        if (yObs && !isOde) {
            const n = yObs.length;
            const ssRes = yObs.reduce(function(s,obs,i) { return s + (obs - yData[i])**2; }, 0);
            const meanObs = yObs.reduce(function(a,b) { return a+b; }, 0) / n;
            const ssTot = yObs.reduce(function(s,obs) { return s + (obs-meanObs)**2; }, 0);
            const r2 = 1 - ssRes/ssTot;
            const rmse = Math.sqrt(ssRes/n);
            const p = (currentEquationData.params || []).length;
            const aic = n * Math.log(ssRes/n) + 2*p;
            const bic = n * Math.log(ssRes/n) + p * Math.log(n);
            document.getElementById('statsPanel').innerHTML = '<strong>拟合统计量</strong><br>R²: ' + r2.toFixed(6) + '<br>RMSE: ' + rmse.toFixed(6) + '<br>AIC: ' + aic.toFixed(2) + '<br>BIC: ' + bic.toFixed(2);
        } else {
            document.getElementById('statsPanel').innerHTML = '<strong>' + (isOde ? 'ODE 求解' : '代数方程求解') + '</strong><br>数据点数: ' + xData.length;
        }
        document.getElementById('infoPanel').innerHTML = '方程: ' + result.display_eq + '<br>类型: ' + (result.type === 'ode' ? '常微分方程' : '代数方程');
    }
    function renderPdeResult(result) {
        const x = result.x, t = result.t, u = result.u;
        const nx = x.length, nt = t.length;
        const slider = document.getElementById('timeSlider');
        slider.max = nt-1; slider.value = 0;
        document.getElementById('timeValue').innerText = t[0].toFixed(4);
        function drawHeatmap() {
            const canvas = document.getElementById('heatmapCanvas');
            const ctx = canvas.getContext('2d');
            const w = canvas.clientWidth, h = canvas.clientHeight;
            canvas.width = w; canvas.height = h;
            const uMin = Math.min(...u.flat()), uMax = Math.max(...u.flat());
            const colormap = (function(name) {
                const maps = {
                    viridis: function(t) { return [30+150*t, 50+100*t, 70+150*t]; },
                    inferno: function(t) { return [255*t, 50+100*t, 20+50*t]; },
                    plasma: function(t) { return [255*t, 50+100*t, 150+100*t]; },
                    coolwarm: function(t) { var r = 0.5+0.5*Math.sin(t*Math.PI), b = 0.5-0.5*Math.sin(t*Math.PI); return [255*r, 128, 255*b]; }
                };
                return maps[name] || maps.viridis;
            })(document.getElementById('colormapSelect').value);
            const img = ctx.createImageData(w, h);
            for (let i=0; i<w; i++) {
                for (let j=0; j<h; j++) {
                    const xi = Math.floor(i/w * nx);
                    const ti = Math.floor((h-1-j)/h * nt);
                    const val = u[ti][xi];
                    const norm = (val - uMin) / (uMax - uMin + 1e-10);
                    const rgb = colormap(norm);
                    const idx = (j*w + i)*4;
                    img.data[idx] = rgb[0];
                    img.data[idx+1] = rgb[1];
                    img.data[idx+2] = rgb[2];
                    img.data[idx+3] = 255;
                }
            }
            ctx.putImageData(img, 0, 0);
            ctx.font = '12px Inter';
            ctx.fillStyle = '#333';
            ctx.fillText('空间 x →', w-80, h-5);
            ctx.save();
            ctx.translate(15, h/2);
            ctx.rotate(-Math.PI/2);
            ctx.fillText('时间 t ↑', 0, 0);
            ctx.restore();
            const grad = ctx.createLinearGradient(w-40, 10, w-20, h-20);
            grad.addColorStop(0, 'rgb(' + colormap(1).join(',') + ')');
            grad.addColorStop(1, 'rgb(' + colormap(0).join(',') + ')');
            ctx.fillStyle = grad;
            ctx.fillRect(w-35, 10, 15, h-30);
            ctx.fillStyle = '#333';
            ctx.fillText(uMax.toFixed(2), w-45, 15);
            ctx.fillText(uMin.toFixed(2), w-45, h-15);
        }
        function drawSlice(idx) {
            if (sliceChart) sliceChart.destroy();
            const canvas = document.getElementById('sliceCanvas');
            if (!canvas) return;
            sliceChart = new Chart(canvas.getContext('2d'), {
                type: 'line',
                data: { labels: x.map(function(v) { return v.toFixed(2); }), datasets: [{ label: 't = ' + t[idx].toFixed(4), data: u[idx], borderColor: '#e67e22', fill: false, pointRadius: 0 }] },
                options: { responsive: true, scales: { x: { title: { display: true, text: 'x' } }, y: { title: { display: true, text: 'u' } } } }
            });
        }
        drawHeatmap();
        drawSlice(0);
        slider.oninput = function(e) {
            const idx = parseInt(e.target.value);
            document.getElementById('timeValue').innerText = t[idx].toFixed(4);
            drawSlice(idx);
        };
        document.getElementById('colormapSelect').onchange = drawHeatmap;
        document.getElementById('pdeStats').innerHTML = '<strong>PDE 信息</strong><br>方程: ' + result.display_eq + '<br>空间点数: ' + nx + '<br>时间点数: ' + nt + '<br>u 范围: [' + Math.min(...u.flat()).toFixed(4) + ', ' + Math.max(...u.flat()).toFixed(4) + ']';
    }

    // ---------- 机器学习模块 ----------
    function updateMLColumns() {
        const targetSel = document.getElementById('mlTargetCol');
        const featureSel = document.getElementById('mlFeatureCols');
        if (!targetSel || !featureSel) return;
        targetSel.innerHTML = '';
        featureSel.innerHTML = '';
        if (currentData.columns.length === 0) return;
        currentData.columns.forEach(col => {
            targetSel.appendChild(new Option(col, col));
            const opt = new Option(col, col);
            featureSel.appendChild(opt);
        });
    }

    function updateMLModelSelect() {
        const select = document.getElementById('mlPredictModelSelect');
        if (!select) return;
        fetch('/api/ml/models')
            .then(r => r.json())
            .then(data => {
                select.innerHTML = '<option value="">选择模型</option>';
                data.models.forEach(model => {
                    const opt = new Option(`${model.algorithm} (${model.type}) - ID:${model.model_id.slice(0,8)}`, model.model_id);
                    select.appendChild(opt);
                });
            });
    }

    const algMap = {
        classification: ['logistic', 'decision_tree', 'random_forest', 'svm', 'knn'],
        regression: ['linear', 'ridge', 'lasso', 'decision_tree', 'random_forest', 'svm', 'knn'],
        clustering: ['kmeans']
    };
    const algNames = {
        logistic: '逻辑回归', decision_tree: '决策树', random_forest: '随机森林', svm: '支持向量机', knn: 'K近邻',
        linear: '线性回归', ridge: '岭回归', lasso: 'Lasso回归', kmeans: 'K-Means'
    };
    document.getElementById('mlModelTypeSelect').addEventListener('change', function(e) {
        const type = e.target.value;
        const algoSelect = document.getElementById('mlAlgorithmSelect');
        algoSelect.innerHTML = '';
        algMap[type].forEach(algo => {
            const opt = new Option(algNames[algo] || algo, algo);
            algoSelect.appendChild(opt);
        });
        document.getElementById('mlParamsArea').style.display = 'none';
        document.getElementById('mlParamsArea').innerHTML = '';
    });
    document.getElementById('mlModelTypeSelect').dispatchEvent(new Event('change'));

    document.getElementById('mlToggleParamsBtn').onclick = function() {
        const area = document.getElementById('mlParamsArea');
        if (area.style.display === 'none') {
            const type = document.getElementById('mlModelTypeSelect').value;
            if (type === 'clustering') {
                area.innerHTML = '<div><label>聚类数 (n_clusters):</label><input type="number" id="mlParam_n_clusters" value="3" min="2" max="10"></div>';
            } else {
                area.innerHTML = '<div><label>随机种子 (random_state):</label><input type="number" id="mlParam_random_state" value="42"></div>';
            }
            area.style.display = 'block';
        } else {
            area.style.display = 'none';
        }
    };

    document.getElementById('mlTrainBtn').onclick = async function() {
        const modelType = document.getElementById('mlModelTypeSelect').value;
        const algorithm = document.getElementById('mlAlgorithmSelect').value;
        const targetCol = document.getElementById('mlTargetCol').value;
        const featureSelect = document.getElementById('mlFeatureCols');
        const featureCols = Array.from(featureSelect.selectedOptions).map(opt => opt.value);
        const testSize = parseFloat(document.getElementById('mlTestSize').value);
        const params = {};
        if (modelType === 'clustering') {
            const nClusters = document.getElementById('mlParam_n_clusters')?.value;
            if (nClusters) params.n_clusters = parseInt(nClusters);
        } else {
            const randomState = document.getElementById('mlParam_random_state')?.value;
            if (randomState) params.random_state = parseInt(randomState);
        }
        const payload = {
            model_type: modelType,
            algorithm: algorithm,
            target_col: targetCol,
            feature_cols: featureCols,
            test_size: testSize,
            params: params,
            selected_rows: Array.from(currentData.selectedRows)
        };
        const btn = document.getElementById('mlTrainBtn');
        btn.innerHTML = '<i class="fas fa-spinner fa-pulse"></i> 训练中...';
        const res = await fetch('/api/ml/train', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const json = await res.json();
        btn.innerHTML = '训练模型';
        if (json.success) {
            let html = `<p><strong>模型ID:</strong> ${json.model_id}</p><p><strong>算法:</strong> ${json.algorithm}</p><p><strong>特征列:</strong> ${json.feature_cols.join(', ')}</p>`;
            if (json.model_type === 'classification') {
                html += `<p><strong>准确率:</strong> ${json.metrics.accuracy.toFixed(4)}</p><p><strong>混淆矩阵:</strong> ${JSON.stringify(json.metrics.confusion_matrix)}</p><p><strong>分类报告:</strong> <pre>${JSON.stringify(json.metrics.classification_report, null, 2)}</pre></p>`;
            } else if (json.model_type === 'regression') {
                html += `<p><strong>R²:</strong> ${json.metrics.r2.toFixed(4)}</p><p><strong>RMSE:</strong> ${json.metrics.rmse.toFixed(4)}</p>`;
            } else {
                html += `<p><strong>轮廓系数:</strong> ${json.silhouette_score !== null ? json.silhouette_score.toFixed(4) : 'N/A'}</p><p><strong>聚类标签 (前20个):</strong> ${json.cluster_labels.slice(0,20).join(', ')}</p>`;
            }
            document.getElementById('mlMetricsDisplay').innerHTML = html;
            updateMLModelSelect();
        } else {
            alert('训练失败: ' + json.error);
            document.getElementById('mlMetricsDisplay').innerHTML = `<p style="color:red;">错误: ${json.error}</p>`;
        }
    };

    document.getElementById('mlPredictBtn').onclick = async function() {
        const modelId = document.getElementById('mlPredictModelSelect').value;
        if (!modelId) { alert('请选择已训练的模型'); return; }
        const res = await fetch('/api/ml/predict', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ model_id: modelId }) });
        const json = await res.json();
        if (json.success) {
            document.getElementById('mlPredictResult').innerHTML = `<pre>预测结果 (前50个):\n${json.predictions.slice(0,50).join(', ')}</pre>`;
        } else {
            alert('预测失败: ' + json.error);
        }
    };

    document.getElementById('mlPredictFileBtn').onclick = function() {
        document.getElementById('mlPredictFile').click();
    };
    document.getElementById('mlPredictFile').onchange = async function(e) {
        const file = e.target.files[0];
        if (!file) return;
        const text = await file.text();
        const lines = text.trim().split('\n');
        const headers = lines[0].split(',').map(s => s.trim());
        const dataRows = lines.slice(1).map(line => {
            const vals = line.split(',');
            const obj = {};
            headers.forEach((h, idx) => obj[h] = vals[idx]);
            return obj;
        });
        const modelId = document.getElementById('mlPredictModelSelect').value;
        if (!modelId) { alert('请选择模型'); return; }
        const res = await fetch('/api/ml/predict', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ model_id: modelId, new_data: dataRows }) });
        const json = await res.json();
        if (json.success) {
            document.getElementById('mlPredictResult').innerHTML = `<pre>预测结果:\n${json.predictions.join(', ')}</pre>`;
        } else {
            alert('预测失败: ' + json.error);
        }
    };

    // 数据按钮绑定
    document.getElementById('uploadBtn').onclick = function() { document.getElementById('fileInput').click(); };
    document.getElementById('fileInput').onchange = async function(e) {
        const file = e.target.files[0];
        if (!file) return;
        const fd = new FormData();
        fd.append('file', file);
        const res = await fetch('/api/upload', { method: 'POST', body: fd });
        const json = await res.json();
        if (json.error) alert(json.error);
        else { currentData.columns = json.columns; currentData.rows = json.data; currentData.selectedRows.clear(); renderTable(); alert('导入成功，共 ' + json.rows + ' 行'); }
    };
    document.getElementById('exportBtn').onclick = async function() {
        const res = await fetch('/api/export', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ format: 'csv' }) });
        const json = await res.json();
        if (json.success && json.data) {
            const blob = new Blob([json.data], { type: 'text/csv' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'data_export.csv';
            a.click();
            URL.revokeObjectURL(blob);
        } else alert('导出失败');
    };
    document.getElementById('addRowBtn').onclick = async function() { await fetch('/api/add_row', { method: 'POST' }); loadData(); };
    document.getElementById('addColBtn').onclick = async function() { const name = prompt('新列名'); if (name) await fetch('/api/add_column', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ col_name: name }) }); loadData(); };
    document.getElementById('delRowBtn').onclick = async function() {
        if (currentData.selectedRows.size === 0) { alert('请先勾选要删除的行'); return; }
        const indices = Array.from(currentData.selectedRows);
        await fetch('/api/delete_rows', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ indices: indices }) });
        loadData();
    };
    document.getElementById('detectMissingBtn').onclick = async function() {
        const res = await fetch('/api/detect_missing');
        const json = await res.json();
        alert(json.missing_count ? '发现 ' + json.missing_count + ' 个缺失值\n' + JSON.stringify(json.details) : '✅ 无缺失值');
    };
    document.getElementById('fillMeanBtn').onclick = async function() { await fetch('/api/fill_missing', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ method: 'mean' }) }); loadData(); alert('均值填充完成'); };
    document.getElementById('fillMedianBtn').onclick = async function() { await fetch('/api/fill_missing', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ method: 'median' }) }); loadData(); alert('中位数填充完成'); };
    document.getElementById('fillModeBtn').onclick = async function() { await fetch('/api/fill_missing', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ method: 'mode' }) }); loadData(); alert('众数填充完成'); };
    document.getElementById('detectOutlierBtn').onclick = async function() {
        const res = await fetch('/api/detect_outliers', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ method: 'iqr' }) });
        const json = await res.json();
        currentOutliers = json.outliers;
        alert(currentOutliers.length ? '发现 ' + currentOutliers.length + ' 个异常值' : '未检测到异常值');
    };
    document.getElementById('clearOutlierBtn').onclick = async function() {
        if (!currentOutliers.length) { alert('请先检测异常值'); return; }
        await fetch('/api/clear_outliers', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ outliers: currentOutliers }) });
        loadData();
        currentOutliers = [];
        alert('异常值已清除');
    };

    // 固定表头控制
    const fixHeaderCheckbox = document.getElementById('fixHeaderCheckbox');
    function applyStickyHeader() {
        if (!fixHeaderCheckbox) return;
        const thead = document.querySelector('#dataTable thead');
        if (!thead) return;
        if (fixHeaderCheckbox.checked) {
            thead.style.position = 'sticky';
            thead.style.top = '0';
            thead.style.zIndex = '10';
        } else {
            thead.style.position = '';
            thead.style.top = '';
            thead.style.zIndex = '';
        }
    }
    if (fixHeaderCheckbox) {
        fixHeaderCheckbox.addEventListener('change', applyStickyHeader);
        applyStickyHeader();
    }

    // 启动
    loadData();
    showPanel('data');
    updateLRMode();
});