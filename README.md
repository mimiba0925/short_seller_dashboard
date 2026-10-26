# 美股量化空方交易監控與決策 Dashboard (US Equity Short-Biased Quant Dashboard)

> **核心原則：區分「股票看空（Fundamentally Bearish）」與「現在安全可執行做空（Actionable Short / Safe to Short）」**
>
> 由上而下決策流：`MARKET REGIME → SECTOR → STOCK → TECHNICAL SETUP → CATALYST → TRIGGER → SIZE → STOP → TARGET → EXIT`

- **線上瀏覽（GitHub Pages）**：<https://mimiba0925.github.io/short_seller_dashboard/>
- **GitHub 儲存庫**：<https://github.com/mimiba0925/short_seller_dashboard>
- **量化規格書**：[ARCHITECTURE_AND_SPEC.md](file:///Users/ryanyang/my_code/code/Projects/Project.short_seller_dashboard/ARCHITECTURE_AND_SPEC.md)
- **實作 Walkthrough**：[workthrough.md](file:///Users/ryanyang/my_code/code/Projects/Project.short_seller_dashboard/workthrough.md)
- **最新每日空方日報**：[DAILY_SHORT_REPORT.md](file:///Users/ryanyang/my_code/code/Projects/Project.short_seller_dashboard/DAILY_SHORT_REPORT.md)

---

## 一、 系統定位與評分方向性指南

本系統是一套專為 **美股空方量化交易（Short-Biased Quant Trading）** 設計的多因子監控、進退場狀態機與組合風控決策系統。系統嚴格禁止主觀預測字眼，將所有訊號轉化為可回測之機率、風險報酬比與分級 (`A+ / A / B / C / D`)。

### 📊 評分方向性速查表（閱讀指南）

- **📉 分數越高 ＝ 越有利空方（分數越低 ＝ 越有利多方）**：
  - **大盤環境評分 (`MARKET REGIME SCORE`, 0–100)**：`61–100` 為 **Risk-Off 空方主場**（全面開放 A+/A 級空單）；`41–60` 為 **Neutral 震盪觀察期**（部位減半）；`0–40` 為 **Risk-On 多頭環境**（禁止新開投機空單，`<30` 強制減倉 50%）。
  - **市場寬度惡化分 (`BREADTH WEAKNESS SCORE`, 0–100)**：分數越高代表越多股票跌破 `50MA/200MA`、新低家數擴大，結構越有利空方。
  - **波動與避險情緒分 (`VOLATILITY REGIME SCORE`, 0–100)**：分數越高代表 `VIX` 走升或 `VIX/VIX3M` 期限結構倒掛，避險情緒越有利空方。
  - **個股空方總分 (`SHORT SCORE`, 0–100)** 與子因子 **A 趨勢破位 (30%)**、**B 相對弱勢 (20%)**、**C 籌碼派發 (20%)**、**D 基本面脆弱 (20%)**：分數越高代表空方共振越強（越有利空方）。
- **⚠️ 分數越高 ＝ 逆勢軋空危險度越高（不利空方 / 易被多頭軋空）**：
  - **E 公開放空擁擠度與軋空風險 (`SQUEEZE RISK SCORE`, 0–100，權重 10%)**：100% 基於免費公開資料（`SI% of Float` 空單佔流通盤比、`Days to Cover` 回補天數、價格反彈突破與期權 Put/Call 流量）。**分數越高代表空頭部位越擁擠、越容易發生嘎空反彈（$\ge 62$ 系統自動一票否決禁空）**；分數越低越安全。
  - **催化劑二元事件分 (`CATALYST RISK SCORE`, 0–100)**：當距離財報發布 $\le 3$ 天時飆升至 `95` 並發出**紅色禁空警告**，防範財報跳空風險。
  - **組合共線性風險 (`CORRELATED SHORT RISK`, 0–100)**：分數越高代表多筆空單過度集中於同溫層（有效獨立部位數 $N_{\text{eff}}$ 過低），易遭同產業同步軋空。

---

## 二、 專案目錄結構

```text
Project.short_seller_dashboard/
├── .github/workflows/
│   └── update_data.yml             # GitHub Actions 美股每日三時段自動更新與部署工作流
├── config/
│   └── watchlist.csv               # 自選監控清單 CSV（自動依代碼排序，支援 GitHub 線上編輯觸發更新）
├── pinescript/
│   └── short_seller_regime_and_setup.pine  # TradingView Pine Script v5 實戰指標與 HUD 面板
├── short_dashboard/                # Python 量化規則引擎與 FastAPI 伺服器
│   ├── app.py                      # FastAPI 應用程式與 REST API 端點
│   ├── engine/
│   │   ├── models.py               # 資料模型、8 狀態枚舉與公開資料誠信標記
│   │   ├── data_provider.py        # yfinance 實盤資料擷取（指數、板塊、個股、期權與基本面）
│   │   ├── regime.py               # 模組 1：大盤環境、市場寬度惡化、VIX 期限結構與板塊排行
│   │   ├── screener.py             # 模組 2：個股五維度 SHORT SCORE、催化劑與軋空風險評分
│   │   ├── execution.py            # 模組 3：8 狀態進退場 FSM、ATR 動態停損、部位計算與標準決策卡
│   │   ├── portfolio_backtest.py   # 模組 4：組合共線性風險 (N_eff) 與無前視偏誤滾動回測
│   │   ├── reporting.py            # 模組 5：每日空方日報與分級優先級 Webhook Alerts
│   │   └── pipeline.py             # 由上而下全流程編排器 (ShortSellerDashboardEngine)
│   └── static/                     # 繁體中文響應式 Web 前端原始碼 (index.html / styles.css / app.js)
├── ARCHITECTURE_AND_SPEC.md        # 完整數學公式、因子權重與規則引擎規格書
├── DAILY_SHORT_REPORT.md           # 自動產出之最新每日空方市場報告 (Markdown)
├── workthrough.md                  # 系統設計與實作 Walkthrough 文件
├── build_static.py                 # 產生根目錄靜態網頁與 snapshot.js 供 GitHub Pages 部署
├── sync_github.py                  # 本機一鍵重算快照並透過 SSH 同步推送至 GitHub
├── cli.py                          # 命令列工具（單股決策卡 / 日報產出 / 啟動本機伺服器）
├── index.html                      # GitHub Pages 根目錄靜態入口
└── snapshot.js                     # 預先計算之完整靜態資料快照
```

---

## 三、 自選監控清單管理（`config/watchlist.csv`）

監控股票清單集中管理於 [`config/watchlist.csv`](file:///Users/ryanyang/my_code/code/Projects/Project.short_seller_dashboard/config/watchlist.csv)，格式如下：

```csv
symbol,note
AMD,Semiconductors / AI Beta
COIN,Crypto Exchange High Beta
CVNA,Auto Retail High Short Interest
LCID,EV Cash Burn / High SI
MARA,Bitcoin Miner High Beta
MSTR,Bitcoin Leveraged Proxy
NVDA,Semiconductors Leader
PLTR,High Valuation Software
RIVN,EV Negative FCF
SMCI,AI Server Hardware Volatility
SNOW,Cloud Software Valuation
TSLA,Auto / AI Momentum
```

- **三種更新自選股方式**：
  1. **GitHub 網頁直接編輯（免開電腦）**：直接在 GitHub 線上編輯 `config/watchlist.csv` 並按 `Commit changes`，GitHub Actions 會自動重算所有指標並更新 GitHub Pages 網站與 `DAILY_SHORT_REPORT.md`。
  2. **本機修改 CSV 一鍵同步**：修改 `config/watchlist.csv` 後執行 `uv run python sync_github.py`。
  3. **本機 Web UI 即時新增**：啟動本機伺服器時，於網頁右上角輸入股票代碼點選 `+ 新增自選 / 篩選`。

---

## 四、 雲端全自動更新時程（GitHub Actions）

[`.github/workflows/update_data.yml`](file:///Users/ryanyang/my_code/code/Projects/Project.short_seller_dashboard/.github/workflows/update_data.yml) 會在每個美股交易日自動執行 **3 次** 掃描與部署：

| 台灣時間 (TST) | 美東時間 (ET) | Cron (UTC) | 更新重點 |
| :--- | :--- | :--- | :--- |
| **22:00** (週一至五) | **10:00** | `0 14 * * 1-5` | 美股開盤早盤跳空、`VIX/VIX3M` 期限結構、大盤環境與早盤破位觸發 |
| **01:30** (週二至六) | **13:30** | `30 17 * * 1-5` | 美股盤中 `20EMA / VWAP` Failed Bounce 受阻確認與相對強弱更新 |
| **05:15** (週二至六) | **17:15** | `15 21 * * 1-5` | 美股收盤完整結算 `SHORT SCORE`、機構派發日、回測統計與每日空方日報 |

- 亦可隨時前往 GitHub Actions 頁面點選 **Run workflow** 手動立即觸發更新。

---

## 五、 本機操作與 CLI 指令

### 1. 產出單一或多檔個股之標準化空方決策卡 (`TICKER` Template)
```bash
uv run python cli.py ticker COIN NVDA CVNA MSTR
```

### 2. 產出最新每日空方市場報告 (`DAILY_SHORT_REPORT.md`)
```bash
uv run python cli.py report --out DAILY_SHORT_REPORT.md
```

### 3. 啟動本機互動式 FastAPI Web Dashboard（Port 8000）
```bash
uv run python cli.py serve --port 8000
```
接著於瀏覽器開啟 `http://127.0.0.1:8000`。

### 4. 本機一鍵更新靜態快照並同步推送至 GitHub Pages
```bash
uv run python sync_github.py
```
