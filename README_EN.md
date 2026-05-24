# 🧊 MindMath Studio

A comprehensive scientific computing platform that integrates data cleaning, equation modeling, numerical solution, and visualization. **  
Supports interactive solving of algebraic equations, ordinary differential equations (ODEs), and partial differential equations (PDEs), and provides a standalone linear regression tool.   
The Web interface adopts a **frosted glass texture**, balancing aesthetics and practicality.

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

---

## ✨ Functional Features

### 📊 Data Processing Workshop
- **CSV / TSV import and export** (automatically recognizes delimiters, supports threaded import of large files)
- **Editable data table** (add/delete rows and columns, double-click cells to edit directly)
- **Missing value handling**: detection, mean/median/mode/constant/forward/backward/interpolation filling
- **Outlier handling**: Based on IQR or Z-score detection, one-click removal (converted to missing)
- **Multiple rows selection**: Select any data rows to participate in subsequent modeling

### 📐 Equation Editing Workshop
- **50+ preset equation libraries** (linear, polynomial, exponential, logarithmic, logistic, periodic function, physical/chemical/financial equations, etc.)
- **Custom Equation**: Users can save their own equations (name, expression, parameter list)
- **Equation Search**: Quickly locate the desired equation
- **Parameter mapping**: Supports four mapping methods: constant, data column, variable x, and time t
- **Real-time preview**: Display curve changes immediately after adjusting parameters (anti-shake optimization)
- **Variable range setting**: Set the ranges of x and t independently

### 📈 Result Output Workshop
- **Algebraic equation solving**: Automatically calculate y = f(x) and plot the graph
- **Ordinary Differential Equation (ODE) Solving**: Supports first-order/second-order ODEs (decay, growth, logistic, damped oscillation, etc.)
- **Partial Differential Equation (PDE) Solving**: Heat Conduction, Wave Equation, Reaction-Diffusion (Finite Difference Method)
- **Multiple chart types**: line chart, scatter plot, bar chart, step chart, filled chart, residual plot, Q-Q plot
- **Fitting statistics**: R², RMSE, AIC, BIC
- **PDE-specific visualization**: heat map + time slice curve (slider interaction)
- **Result Export**: Supports exporting calculation results in CSV format

### 📉 Independent Linear Regression Tool
- **Three modes**:
  - Column mode: Select X and Y columns for regression
  - Single-column mode: Automatically analyze the trend of changes in a single column with row number X
  - Row mode: Select a row of data and analyze the horizontal distribution with column number as X
- **Complete statistical measures**: slope, intercept, R², RMSE, AIC, BIC
- **Visualization**: Scatter plot + Fitted line

### 🎨 Interface Features
- **Frosted glass texture**: translucent background + blur effect + soft shadows
- **Fully borderless button**: Flat design, hover animation
- **Responsive layout**: Adapt to different screen sizes
- **Modal Box Assistance**: "About" and "FAQ" Dialog Boxes

---

## 🛠 Technical stack

| Level | Technology |
|------|------|
| Backend | Python 3.8+, Flask, Flask-CORS |
| Scientific Computing | NumPy, Pandas, SciPy (odeint, sparse matrices), Scikit-learn |
| Front-end | HTML5, CSS3 (Grid/Flex, backdrop-filter), JavaScript (ES6) |
| Chart | Chart.js (Algebra/ODE), Canvas self-drawn heat map (PDE) |
| Packaging | PyInstaller (optional, to generate standalone exe) |

---

## 📦 Installation and Operation

### 1.  Clone repository
```bash
git clone https://github.com/yourname/hajimi-modeling.git
cd hajimi-modeling
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3.  Run the application
```bash
python app.py
```
The browser will automatically open `http://127.0.0.1:5000` for use.

> **Tip**: If it doesn't open automatically, please visit the address manually.

### 4.  (Optional) Package as a standalone exe
```bash
pyinstaller --onefile --add-data "templates;templates" --hidden-import=flask_cors app.py
```
The generated `dist/app.exe` can run independently of the Python environment (it may be slightly slower to start the first time).

---

## 📸 Interface Preview

Since README cannot embed dynamic images directly, please visit [Project Wiki] or run it yourself to view.

| Module | Description |
|------|------|
| Data Workshop | Editable Table, Missing/Anomaly Detection, Filling Tool |
| Equation Workshop | Equation Library, Parameter Mapping, Real-time Preview, Linear Regression Tool |
| Result Workshop | Algebra/ODE Chart, PDE Heatmap, Statistics Panel |

---

## 🧪 Usage Example

### Import Data
1. Click **"Import CSV/TSV"** to select the file.
2. The table automatically displays the first 100 rows, and you can modify the data by double-clicking on the cells.
3. Check the required rows (for subsequent modeling).

### Fitting linear regression
1. Access the **Equation Workshop** page.
2. Scroll to the bottom and find the **Linear Regression Tool**.
3. Select the mode (such as "single column mode") and choose column Y (for example, "temperature").
4. Click **"Perform Linear Regression"**, and the results will be automatically displayed on the results page.

### Solving differential equations
1. Select **"First-order ODE - Decay"** from the equation library.
2. Set the parameter k (e.g., 0.5).
3. Click **"Start Solving"** and the result page will display the curve and statistics.

---

## 📁 Project Structure

```
hajimi-modeling/
├─ app.py                 # Flask backend main program
├─ solver.py              # Algebra/ODE/PDE solving core
├─ utils.py               # Preset equation library, expression conversion tool
├─ requirements.txt       # Python dependency list
├── templates/
│   └── index.html         # Front-end single-page application
└── README.md              # This file
```

---

## 🤝 Contribution Guidelines

Welcome to submit Issues and Pull Requests.   
- The code style follows PEP 8.
- Please ensure to test frontend modifications on the latest version of Chrome/Edge.
- Please update the `PRESET_EQUATIONS` dictionary when adding new equations.

---

## 📄 License

This project adopts the **MIT License**.   

---

## 📧 Contact Information

- Official website: [https://www.mindmathstudio.com](https://www.mindmathstudio.com)
- Feedback: Please raise an issue on GitHub

---

## 🌟 Acknowledgements

- Thank you to all the developers of open source projects (Flask, Chart.js, SciPy, scikit-learn).
- Special thanks to "Hakimi" for their spiritual support.
