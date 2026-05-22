# 🧊 MindMath Studio

**一个集数据清洗、方程建模、数值求解与可视化于一体的全功能科学计算平台。**  
支持代数方程、常微分方程（ODE）、偏微分方程（PDE）的交互式求解，并提供独立的线性回归工具。  
采用 **磨砂玻璃质感** 的 Web 界面，兼顾美观与实用。

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

---

## ✨ 功能特性

### 📊 数据处理工坊
- **CSV / TSV 导入导出**（自动识别分隔符，支持大文件线程化导入）
- **可编辑数据表格**（添加/删除行列、双击单元格直接编辑）
- **缺失值处理**：检测、均值/中位数/众数/常数/前向/后向/插值填充
- **异常值处理**：基于 IQR 或 Z-score 检测，一键清除（转为缺失）
- **行多选**：任意选择数据行参与后续建模

### 📐 方程编辑工坊
- **50+ 预设方程库**（线性、多项式、指数、对数、逻辑斯蒂、周期函数、物理/化学/金融方程等）
- **自定义方程**：用户可保存自己的方程（名称、表达式、参数列表）
- **方程搜索**：快速定位所需方程
- **参数映射**：支持常数、数据列、变量 x、时间 t 四种映射方式
- **实时预览**：调整参数后立即显示曲线变化（防抖优化）
- **变量范围设置**：独立设置 x 和 t 的范围

### 📈 结果输出工坊
- **代数方程求解**：自动计算 y = f(x) 并绘图
- **常微分方程（ODE）求解**：支持一阶/二阶 ODE（衰减、增长、逻辑斯蒂、阻尼振动等）
- **偏微分方程（PDE）求解**：热传导、波动方程、反应扩散（有限差分法）
- **多种图表类型**：折线图、散点图、条形图、阶梯图、填充图、残差图、Q-Q 图
- **拟合统计量**：R²、RMSE、AIC、BIC
- **PDE 专用可视化**：热力图 + 时间切片曲线（滑块交互）
- **结果导出**：支持 CSV 格式导出计算结果

### 📉 独立线性回归工具
- **三种模式**：
  - 列模式：选择 X 列和 Y 列进行回归
  - 单列模式：自动以行序号为 X，分析单列变化趋势
  - 行模式：选中一行数据，以列序号为 X 分析横向分布
- **完整统计量**：斜率、截距、R²、RMSE、AIC、BIC
- **可视化**：散点图 + 拟合直线

### 🎨 界面特色
- **磨砂玻璃质感**：半透明背景 + 模糊效果 + 柔和阴影
- **完全无边框按钮**：扁平化设计，悬停动画
- **响应式布局**：适配不同屏幕尺寸
- **模态框帮助**：“关于”和“常见问题”对话框

---

## 🛠 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.8+, Flask, Flask-CORS |
| 科学计算 | NumPy, Pandas, SciPy (odeint, 稀疏矩阵), Scikit-learn |
| 前端 | HTML5, CSS3 (Grid/Flex, backdrop-filter), JavaScript (ES6) |
| 图表 | Chart.js (代数/ODE), Canvas 自绘热力图 (PDE) |
| 打包 | PyInstaller (可选，生成独立 exe) |

---

## 📦 安装与运行

### 1. 克隆仓库
```bash
git clone https://github.com/yourname/hajimi-modeling.git
cd hajimi-modeling
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 运行应用
```bash
python app.py
```
浏览器自动打开 `http://127.0.0.1:5000` 即可使用。

> **提示**：如果未自动打开，请手动访问该地址。

### 4. （可选）打包为独立 exe
```bash
pyinstaller --onefile --add-data "templates;templates" --hidden-import=flask_cors app.py
```
生成的 `dist/app.exe` 可脱离 Python 环境运行（首次启动稍慢）。

---

## 📸 界面预览

> 由于 README 无法直接嵌入动态图片，请访问 [项目 Wiki] 或自行运行查看。

| 模块 | 描述 |
|------|------|
| 数据工坊 | 可编辑表格、缺失/异常检测、填充工具 |
| 方程工坊 | 方程库、参数映射、实时预览、线性回归工具 |
| 结果工坊 | 代数/ODE 图表、PDE 热力图、统计量面板 |

---

## 🧪 使用示例

### 导入数据
1. 点击 **“导入CSV/TSV”** 选择文件。
2. 表格自动显示前 100 行，双击单元格可修改数据。
3. 勾选需要的行（用于后续建模）。

### 拟合线性回归
1. 进入 **方程工坊** 页面。
2. 滚动到底部 **线性回归工具**。
3. 选择模式（如“单列模式”），选择 Y 列（例如“温度”）。
4. 点击 **“执行线性回归”**，结果自动显示在结果页面。

### 求解微分方程
1. 在方程库中选择 **“一阶ODE-衰减”**。
2. 设置参数 k（例如 0.5）。
3. 点击 **“开始求解”**，结果页面显示曲线和统计量。

---

## 📁 项目结构

```
hajimi-modeling/
├── app.py                 # Flask 后端主程序
├── solver.py              # 代数/ODE/PDE 求解核心
├── utils.py               # 预设方程库、表达式转换工具
├── requirements.txt       # Python 依赖列表
├── templates/
│   └── index.html         # 前端单页面应用
└── README.md              # 本文件
```

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request。  
- 代码风格遵循 PEP 8。
- 前端修改请确保在 Chrome/Edge 最新版上测试。
- 新增方程请同时更新 `PRESET_EQUATIONS` 字典。

---

## 📄 许可证

本项目采用 **MIT 许可证**。  
> 软件仅供学习交流，未经允许不得用于商业用途。版权归原作者所有。

---

## 📧 联系方式

- 官网：[https://www.mindmathstudio.com](https://www.mindmathstudio.com)
- 问题反馈：请在 GitHub Issues 中提出

---

## 🌟 致谢

- 感谢所有开源项目（Flask, Chart.js, SciPy, scikit-learn）的开发者。
- 特别感谢“哈基米”精神支持。

**Enjoy modeling! 🧊**
```

您可以根据实际仓库地址修改其中的 `https://github.com/yourname/hajimi-modeling.git` 以及官网链接。如果需要添加**截图占位符**，可以将 `![截图](screenshots/data.png)` 放入对应位置并创建 `screenshots/` 文件夹。
