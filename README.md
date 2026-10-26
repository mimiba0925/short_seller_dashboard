# US Equity Quant Short-Biased Trading Monitor & Decision Dashboard

一套具備實戰與機構風控邏輯的 **美股量化空方交易監控與決策系統 (Short-Biased Quant Dashboard)**。系統嚴格遵循由上而下的決策流：
`MARKET REGIME → SECTOR → STOCK → TECHNICAL SETUP → CATALYST → TRIGGER → SIZE → STOP → TARGET → EXIT`

---

## 專案結構 (Project Structure)

- [ARCHITECTURE_AND_SPEC.md](file:///Users/ryanyang/my_code/code/Projects/Project.short_seller_dashboard/ARCHITECTURE_AND_SPEC.md)：完整五模組量化指標定義、數學公式、進退場有限狀態機 (8-State FSM) 與風控回測規格書。
- [pinescript/short_seller_regime_and_setup.pine](file:///Users/ryanyang/my_code/code/Projects/Project.short_seller_dashboard/pinescript/short_seller_regime_and_setup.pine)：TradingView Pine Script v5 腳本（含 SPY/QQQ/IWM 環境濾網、VIX/VIX3M 期限結構倒掛偵測、20D 結構破位與 20EMA Failed Bounce 觸發器、ATR 動態停損目標與 Webhook `alertcondition`）。
- [short_dashboard/engine/](file:///Users/ryanyang/my_code/code/Projects/Project.short_seller_dashboard/short_dashboard/engine)：Python 量化規則引擎：
  - [models.py](file:///Users/ryanyang/my_code/code/Projects/Project.short_seller_dashboard/short_dashboard/engine/models.py)：資料模型與 `DATA UNAVAILABLE` 誠信標記。
  - [data_provider.py](file:///Users/ryanyang/my_code/code/Projects/Project.short_seller_dashboard/short_dashboard/engine/data_provider.py)：`yfinance` 實盤數據擷取 + Ortex / IBKR 機構借券費率與衍生品覆寫介面。
  - [regime.py](file:///Users/ryanyang/my_code/code/Projects/Project.short_seller_dashboard/short_dashboard/engine/regime.py)：模組 1 大盤環境評分 (`MARKET_REGIME_SCORE`)、市場寬度 (`BREADTH_WEAKNESS_SCORE`)、波動度與 VIX 期限結構 (`VOLATILITY_REGIME_SCORE`)。
  - [screener.py](file:///Users/ryanyang/my_code/code/Projects/Project.short_seller_dashboard/short_dashboard/engine/screener.py)：模組 2 個股五維度空方因子 (`SHORT_SCORE` 0–100)、催化劑風險 (`CATALYST_RISK_SCORE`) 與獨立軋空警告 (`SQUEEZE_RISK_SCORE`)。
  - [execution.py](file:///Users/ryanyang/my_code/code/Projects/Project.short_seller_dashboard/short_dashboard/engine/execution.py)：模組 3 八階段進退場規則引擎 (`WAIT`, `WATCH`, `SHORT SETUP`, `ENTRY`, `ADD`, `HOLD`, `REDUCE`, `EXIT`)、動態 ATR 停損、部位規模計算與標準化個股決策輸出卡。
  - [portfolio_backtest.py](file:///Users/ryanyang/my_code/code/Projects/Project.short_seller_dashboard/short_dashboard/engine/portfolio_backtest.py)：模組 4 組合共線性風險 (`CORRELATED_SHORT_RISK`、有效獨立部位數 $N_{\text{eff}}$) 與無前視偏誤歷史訊號回測引擎。
  - [reporting.py](file:///Users/ryanyang/my_code/code/Projects/Project.short_seller_dashboard/short_dashboard/engine/reporting.py)：模組 5 每日空方市場報告 (`DAILY SHORT MARKET REPORT`) 與分級 Webhook Alert 產生器。
- [short_dashboard/app.py](file:///Users/ryanyang/my_code/code/Projects/Project.short_seller_dashboard/short_dashboard/app.py) & [short_dashboard/static/](file:///Users/ryanyang/my_code/code/Projects/Project.short_seller_dashboard/short_dashboard/static)：FastAPI 伺服器與現代化響應式 Web Dashboard。
- [cli.py](file:///Users/ryanyang/my_code/code/Projects/Project.short_seller_dashboard/cli.py)：命令列工具。

---

## 快速開始 (Quick Start)

### 1. 產出特定個股之標準化空方決策卡 (`TICKER` Template)
```bash
uv run python cli.py ticker NVDA TSLA MSTR
```
若您擁有 Ortex 或 IBKR 即時借券費率（Borrow Fee Rate %），可透過 `--borrow-fee` 注入：
```bash
uv run python cli.py ticker CVNA --borrow-fee 16.5 --account 250000
```

### 2. 產出每日空方市場報告 (`DAILY_SHORT_REPORT.md`)
```bash
uv run python cli.py report --out DAILY_SHORT_REPORT.md
```

### 3. 啟動互動式 Web Dashboard
```bash
uv run python cli.py serve --port 8000
```
接著於瀏覽器開啟 `http://127.0.0.1:8000`。
