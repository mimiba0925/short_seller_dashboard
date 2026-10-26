# DAILY SHORT MARKET REPORT (美股量化空方每日決策日報)
**Generated At**: `2026-10-26 00:56:59`

## 1. Macro & Market Regime Filter (大盤環境與做空總閘門)
- **MARKET REGIME SCORE**: **61.6 / 100** — `RISK-OFF (Bearish Regime / Active Short Window)`
- **Short Book Policy**: SHORT BOOK OPEN for A+ and A rated setups. Full 1.0x risk sizing allowed. Pyramiding (ADD) enabled on Lower High confirmation if score > 70.
- **Max Gross Short Exposure Cap**: `100%` | **Regime Risk Multiplier**: `1.00x`
- **Market Breadth (`BREADTH_WEAKNESS_SCORE`)**: `32.8/100` — Breadth Weakness 32.8/100 | >50MA: 54.5%, >200MA: 70.5%, Net NH-NL: +6.8%, 10D A/D: 1.04
- **Volatility Regime (`VOLATILITY_REGIME_SCORE`)**: `45.2/100` — Vol Score 45.2/100 | VIX: 19.45 (5D -2.7%), VIX/VIX3M: 0.95 [CONTANGO] | SPY P/C Ratio: 1.18 (Bearish Hedging Active)

### Benchmark Index Breakdown
| Index | Close | 20EMA | 50SMA | 200SMA | 20D Ret | 25D Dist Days | Index Bear Score |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **SPY** | $759.97 | $768.83 (Below) | $767.81 (Below) | $727.01 | -1.48% | 7d | **79.0** |
| **QQQ** | $704.40 | $727.11 (Below) | $725.81 (Below) | $677.30 | -5.39% | 7d | **79.0** |
| **IWM** | $275.75 | $277.72 (Below) | $286.41 (Below) | $278.23 | -2.21% | 5d | **100.0** |

## 2. Sector Relative Weakness Ranking (板塊弱勢排行)
| Sector ETF | Close | 5D Ret | 20D Ret | 20D RS vs SPY | 25D Dist Days | Weakness Score |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| **SMH** | $527.20 | -2.33% | -13.08% | -11.60% | 11d | **114.5** |
| **XLC** | $105.51 | -4.36% | -6.60% | -5.12% | 5d | **111.3** |
| **XLI** | $164.62 | -1.87% | -3.41% | -1.93% | 8d | **104.2** |
| **XLK** | $183.23 | -0.13% | -6.64% | -5.16% | 9d | **90.4** |
| **XLY** | $113.10 | +0.57% | +2.30% | +3.78% | 5d | **69.7** |
| **XLRE** | $42.57 | +0.97% | +2.43% | +3.91% | 11d | **59.4** |

## 3. Actionable Short List (A+ / A 級可執行空方候選池)
> 僅包含通過安全濾網（無軋空警告、財報 > 3 天、評級 A/A+）之標的。

*No stocks currently pass the strict A+/A Actionable Short safety gate.*

## 4. Fundamentally / Structurally Bearish BUT Not Yet Actionable (看空但暫不適合做空)
| Ticker | Short Score | Rating | Current State | Reason Not Actionable Today |
| :--- | ---: | :---: | :---: | :--- |
| **COIN** | 82.2 | `A` | `WAIT` | WAIT — RED WARNING: Binary Earnings Event in 3d (Avoid New Short) |
| **MARA** | 66.2 | `B` | `WATCH` | WATCH — Fundamentally/Technically Bearish but Short-Term Oversold (RSI 24.3); Wait for Bounce to 20EMA ($9.05) |
| **RIVN** | 64.0 | `B` | `WAIT` | WAIT — RED WARNING: Binary Earnings Event in 3d (Avoid New Short) |
| **MSTR** | 57.0 | `B` | `WAIT` | WAIT — RED WARNING: Binary Earnings Event in 3d (Avoid New Short) |

## 5. Short Squeeze Risk & Upcoming Binary Catalysts (軋空警告與事件日曆)
- **Squeeze Watch — `MARA`**: Squeeze Risk 50/100 [Controlled] | Options Bearish Score 35/100 | SI Float: 29.8% | Days to Cover: 2.3d | Borrow Fee: DATA UNAVAILABLE | Opt P/C Vol: 0.28 | GEX: DATA UNAVAILABLE
- **Squeeze Watch — `LCID`**: Squeeze Risk 68/100 [HIGH SQUEEZE DANGER] | Options Bearish Score 5/100 | SI Float: 57.2% | Days to Cover: 8.5d | Borrow Fee: DATA UNAVAILABLE | Opt P/C Vol: 0.39 | GEX: DATA UNAVAILABLE | [SQUEEZE WARNING ACTIVE]
- **Catalyst Watch — `COIN`**: Score 70/100 (Catalyst Risk: 95/100) | Rev contraction (-17.3% YoY) | Negative OpMargin (-13.9%) | FCF Positive | Stretched Valuation (EV/Rev 6.8x) | RED WARNING: EARNINGS IN 3 DAYS (2026-10-29)
- **Catalyst Watch — `MARA`**: Score 68/100 (Catalyst Risk: 25/100) | Rev contraction (-26.7% YoY) | Negative OpMargin (-265.2%) | Negative FCF (Cash Burn) | Next Earnings in 9d
- **Catalyst Watch — `RIVN`**: Score 53/100 (Catalyst Risk: 95/100) | Rev growth +27.2% YoY | Negative OpMargin (-50.4%) | Negative FCF (Cash Burn) | RED WARNING: EARNINGS IN 3 DAYS (2026-10-29)
- **Catalyst Watch — `MSTR`**: Score 78/100 (Catalyst Risk: 95/100) | Slow Rev growth (+6.9% YoY) | Negative OpMargin (-6808.1%) | Negative FCF (Cash Burn) | Stretched Valuation (EV/Rev 150.2x) | RED WARNING: EARNINGS IN 3 DAYS (2026-10-29)
- **Catalyst Watch — `CVNA`**: Score 18/100 (Catalyst Risk: 95/100) | Rev growth +52.4% YoY | OpMargin 9.2% | FCF Positive | RED WARNING: EARNINGS IN 2 DAYS (2026-10-28)
- **Catalyst Watch — `SNOW`**: Score 40/100 (Catalyst Risk: 25/100) | Rev growth +35.1% YoY | Negative OpMargin (-17.0%) | FCF Positive | Stretched Valuation (EV/Rev 21.2x) | Next Earnings in 37d
- **Catalyst Watch — `NVDA`**: Score 21/100 (Catalyst Risk: 25/100) | Rev growth +105.9% YoY | OpMargin 66.2% | FCF Positive | Stretched Valuation (EV/Rev 16.7x) | Next Earnings in 22d
- **Catalyst Watch — `SMCI`**: Score 23/100 (Catalyst Risk: 25/100) | Rev growth +93.2% YoY | OpMargin 13.4% | Negative FCF (Cash Burn) | Next Earnings in 8d
- **Catalyst Watch — `AMD`**: Score 21/100 (Catalyst Risk: 25/100) | Rev growth +50.1% YoY | OpMargin 17.2% | FCF Positive | Stretched Valuation (EV/Rev 20.2x) | Next Earnings in 8d
- **Catalyst Watch — `LCID`**: Score 42/100 (Catalyst Risk: 25/100) | Rev growth +56.2% YoY | Negative OpMargin (-261.0%) | Negative FCF (Cash Burn) | Next Earnings in 14d
- **Catalyst Watch — `PLTR`**: Score 31/100 (Catalyst Risk: 65/100) | Rev growth +92.8% YoY | OpMargin 47.1% | FCF Positive | Stretched Valuation (EV/Rev 75.3x) | Earnings approaching in 7d (2026-11-02)

## 6. Portfolio-Level Correlated Short Risk (`CORRELATED_SHORT_RISK`)
- **Correlated Short Risk Score**: `52.4/100`
- **Nominal Candidates vs Effective Independent Bets ($N_{\text{eff}}$)**: `6` nominal $\rightarrow$ **`1.81` effective independent bets** (Avg 60D Pairwise Correlation: `0.46`)
- **Gross Short Exposure (Suggested)**: `35.6%` (Beta-Adjusted: `119.3%`)
  - ⚠️ CORRELATED SHORT RISK WARNING: 6 nominal shorts behave like only 1.81 independent positions (Avg 60D Corr 0.46).
  - ⚠️ Top Correlated Pair: COIN / MSTR (60D rho = 0.87) — Apply correlation sizing haircut.

## 7. Standardized Stock Decision Cards (個股標準化決策輸出)
```text
⸻
TICKER: COIN
SHORT SCORE: 82.2 / RATING: A
MARKET REGIME: 61.6/100 — RISK-OFF (Bearish Regime / Active Short Window) | Breadth Weakness 33/100 | VIX 19.45 (VIX/VIX3M 0.95)
SECTOR: Financial Services (XLF) | 20D Ret: +1.9% (vs SPY +3.4%) | Weakness Score: 49.5/100
TREND: Score 94/100 | Close $164.45 vs 20EMA $176.94 (-1.3 ATR), 50DMA $179.55 (-8.4%), 200DMA $180.50 (-8.9%) | 20D Support Breakdown (<$165.80), Lower-High / Double-Top Structure
MOMENTUM: RSI(14): 41.5 [Bearish Zone 32-52] | MACD: -3.45 (Hist -1.88)
RELATIVE STRENGTH: Score 85/100 | 20D Rel vs SPY: -14.2%, vs XLF: -17.6% | Downside Beta: 3.23 (Asym 4.15x)
VOLUME: Score 72/100 | 25D Distribution Days: 7 | Down/Up Vol Ratio: 1.02x | RelVol Today: 0.84x | CMF(20): -0.31
FUNDAMENTAL & CATALYST: Score 70/100 (Catalyst Risk: 95/100) | Rev contraction (-17.3% YoY) | Negative OpMargin (-13.9%) | FCF Positive | Stretched Valuation (EV/Rev 6.8x) | RED WARNING: EARNINGS IN 3 DAYS (2026-10-29)
SHORT SQUEEZE RISK: Squeeze Risk 32/100 [Controlled] | Options Bearish Score 88/100 | SI Float: 11.1% | Days to Cover: 2.5d | Borrow Fee: DATA UNAVAILABLE | Opt P/C Vol: 2.16 | Unusual OTM Put Buying | GEX: DATA UNAVAILABLE

ENTRY ZONE: $163.63 – $176.94 (20EMA / 5D-VWAP Rejection Band)
TRIGGER: CONFIRMED: Failed bounce / rejection at 20EMA ($176.94) & 5D-VWAP ($170.83) with break below prior low $166.73
STOP: $185.89 (2.16x ATR14 ($9.94) above Entry / 5D Swing High $183.40 | Suggested Size: 34 sh / Max Risk $750)
TARGET 1: $121.58 / TARGET 2: $89.43
RISK / REWARD: 1 : 2.00 (Bearish Prob: 68.6%)
CONFIDENCE: 63.4%

ACTION: WAIT — RED WARNING: Binary Earnings Event in 3d (Avoid New Short)
INVALIDATION: Daily close above $185.89 (Structural Stop / 20EMA + 0.5x ATR) or 50DMA reclaim ($179.55)
⸻
```
```text
⸻
TICKER: MARA
SHORT SCORE: 66.2 / RATING: B
MARKET REGIME: 61.6/100 — RISK-OFF (Bearish Regime / Active Short Window) | Breadth Weakness 33/100 | VIX 19.45 (VIX/VIX3M 0.95)
SECTOR: Financial Services (XLF) | 20D Ret: +1.9% (vs SPY +3.4%) | Weakness Score: 49.5/100
TREND: Score 87/100 | Close $7.02 vs 20EMA $9.05 (-3.2 ATR), 50DMA $10.64 (-34.0%), 200DMA $10.89 (-35.5%) | 20D Support Breakdown (<$7.11), Lower-High / Double-Top Structure, Short-Term Overextended (-3.2x ATR vs 20EMA)
MOMENTUM: RSI(14): 24.3 [OVERSOLD <30 - Bounce Risk] | MACD: -1.16 (Hist -0.25)
RELATIVE STRENGTH: Score 75/100 | 20D Rel vs SPY: -42.6%, vs XLF: -46.0% | Downside Beta: 3.09 (Asym 1.75x)
VOLUME: Score 62/100 | 25D Distribution Days: 9 | Down/Up Vol Ratio: 0.88x | RelVol Today: 0.97x | CMF(20): -0.39
FUNDAMENTAL & CATALYST: Score 68/100 (Catalyst Risk: 25/100) | Rev contraction (-26.7% YoY) | Negative OpMargin (-265.2%) | Negative FCF (Cash Burn) | Next Earnings in 9d
SHORT SQUEEZE RISK: Squeeze Risk 50/100 [Controlled] | Options Bearish Score 35/100 | SI Float: 29.8% | Days to Cover: 2.3d | Borrow Fee: DATA UNAVAILABLE | Opt P/C Vol: 0.28 | GEX: DATA UNAVAILABLE

ENTRY ZONE: Breakdown < $7.11 OR Weak Bounce into $7.31 – $9.15
TRIGGER: Await break below $7.11 on >1.5x volume OR Failed Bounce rejection at 20EMA ($9.05) / VWAP ($7.47) with Lower High confirmation
STOP: $8.56 (2.40x ATR14 ($0.64) above Entry / 5D Swing High $8.23 | Suggested Size: 0 sh / Max Risk $0)
TARGET 1: $3.95 / TARGET 2: $1.64
RISK / REWARD: 1 : 2.00 (Bearish Prob: 51.8%)
CONFIDENCE: 48.7%

ACTION: WATCH — Fundamentally/Technically Bearish but Short-Term Oversold (RSI 24.3); Wait for Bounce to 20EMA ($9.05)
INVALIDATION: Daily close above $9.37 (Structural Stop / 20EMA + 0.5x ATR) or 50DMA reclaim ($10.64)
⸻
```
```text
⸻
TICKER: RIVN
SHORT SCORE: 64.0 / RATING: B
MARKET REGIME: 61.6/100 — RISK-OFF (Bearish Regime / Active Short Window) | Breadth Weakness 33/100 | VIX 19.45 (VIX/VIX3M 0.95)
SECTOR: Consumer Cyclical (XLY) | 20D Ret: +2.3% (vs SPY +3.8%) | Weakness Score: 69.7/100
TREND: Score 87/100 | Close $11.83 vs 20EMA $13.37 (-3.3 ATR), 50DMA $14.89 (-20.6%), 200DMA $15.64 (-24.4%) | 20D Support Breakdown (<$11.97), Lower-High / Double-Top Structure, Short-Term Overextended (-3.3x ATR vs 20EMA)
MOMENTUM: RSI(14): 20.9 [OVERSOLD <30 - Bounce Risk] | MACD: -0.86 (Hist -0.14)
RELATIVE STRENGTH: Score 75/100 | 20D Rel vs SPY: -22.1%, vs XLY: -25.8% | Downside Beta: 1.78 (Asym 1.90x)
VOLUME: Score 72/100 | 25D Distribution Days: 9 | Down/Up Vol Ratio: 1.09x | RelVol Today: 0.93x | CMF(20): -0.24
FUNDAMENTAL & CATALYST: Score 53/100 (Catalyst Risk: 95/100) | Rev growth +27.2% YoY | Negative OpMargin (-50.4%) | Negative FCF (Cash Burn) | RED WARNING: EARNINGS IN 3 DAYS (2026-10-29)
SHORT SQUEEZE RISK: Squeeze Risk 49/100 [Controlled] | Options Bearish Score 35/100 | SI Float: 14.9% | Days to Cover: 8.0d | Borrow Fee: DATA UNAVAILABLE | Opt P/C Vol: 0.31 | GEX: DATA UNAVAILABLE

ENTRY ZONE: Breakdown < $11.97 OR Weak Bounce into $12.12 – $13.44
TRIGGER: Await break below $11.97 on >1.5x volume OR Failed Bounce rejection at 20EMA ($13.37) / VWAP ($12.23) with Lower High confirmation
STOP: $12.94 (2.40x ATR14 ($0.46) above Entry / 5D Swing High $13.19 | Suggested Size: 0 sh / Max Risk $0)
TARGET 1: $9.61 / TARGET 2: $7.94
RISK / REWARD: 1 : 2.00 (Bearish Prob: 50.6%)
CONFIDENCE: 47.8%

ACTION: WAIT — RED WARNING: Binary Earnings Event in 3d (Avoid New Short)
INVALIDATION: Daily close above $13.60 (Structural Stop / 20EMA + 0.5x ATR) or 50DMA reclaim ($14.89)
⸻
```
```text
⸻
TICKER: MSTR
SHORT SCORE: 57.0 / RATING: B
MARKET REGIME: 61.6/100 — RISK-OFF (Bearish Regime / Active Short Window) | Breadth Weakness 33/100 | VIX 19.45 (VIX/VIX3M 0.95)
SECTOR: Technology (XLK) | 20D Ret: -6.6% (vs SPY -5.2%) | Weakness Score: 90.4/100
TREND: Score 25/100 | Close $146.01 vs 20EMA $147.95 (-0.2 ATR), 50DMA $139.70 (+4.5%), 200DMA $135.26 (+8.0%) | No Structural Breakdown Confirmed
MOMENTUM: RSI(14): 49.5 [Bearish Zone 32-52] | MACD: 0.61 (Hist -1.87) | RSI Bearish Divergence Detected
RELATIVE STRENGTH: Score 76/100 | 20D Rel vs SPY: -6.5%, vs XLK: -1.3% | Downside Beta: 4.71 (Asym 2.18x)
VOLUME: Score 72/100 | 25D Distribution Days: 8 | Down/Up Vol Ratio: 1.03x | RelVol Today: 0.95x | CMF(20): -0.16
FUNDAMENTAL & CATALYST: Score 78/100 (Catalyst Risk: 95/100) | Slow Rev growth (+6.9% YoY) | Negative OpMargin (-6808.1%) | Negative FCF (Cash Burn) | Stretched Valuation (EV/Rev 150.2x) | RED WARNING: EARNINGS IN 3 DAYS (2026-10-29)
SHORT SQUEEZE RISK: Squeeze Risk 17/100 [Controlled] | Options Bearish Score 45/100 | SI Float: 7.3% | Days to Cover: 1.2d | Borrow Fee: DATA UNAVAILABLE | Opt P/C Vol: 0.95 | GEX: DATA UNAVAILABLE

ENTRY ZONE: Breakdown < $133.60 OR Weak Bounce into $143.03 – $149.43
TRIGGER: Await break below $133.60 on >1.5x volume OR Failed Bounce rejection at 20EMA ($147.95) / VWAP ($145.49) with Lower High confirmation
STOP: $157.23 (2.40x ATR14 ($9.84) above Entry / 5D Swing High $155.69 | Suggested Size: 0 sh / Max Risk $0)
TARGET 1: $89.21 / TARGET 2: $50.91
RISK / REWARD: 1 : 1.88 (Bearish Prob: 46.8%)
CONFIDENCE: 44.8%

ACTION: WAIT — RED WARNING: Binary Earnings Event in 3d (Avoid New Short)
INVALIDATION: Daily close above $157.23 (Structural Stop / 20EMA + 0.5x ATR) or 50DMA reclaim ($139.70)
⸻
```
```text
⸻
TICKER: CVNA
SHORT SCORE: 56.8 / RATING: B
MARKET REGIME: 61.6/100 — RISK-OFF (Bearish Regime / Active Short Window) | Breadth Weakness 33/100 | VIX 19.45 (VIX/VIX3M 0.95)
SECTOR: Consumer Cyclical (XLY) | 20D Ret: +2.3% (vs SPY +3.8%) | Weakness Score: 69.7/100
TREND: Score 92/100 | Close $57.81 vs 20EMA $61.24 (-1.2 ATR), 50DMA $66.61 (-13.2%), 200DMA $69.92 (-17.3%) | Testing 20D Neckline ($56.28), Lower-High / Double-Top Structure
MOMENTUM: RSI(14): 37.5 [Bearish Zone 32-52] | MACD: -2.20 (Hist -0.05)
RELATIVE STRENGTH: Score 85/100 | 20D Rel vs SPY: -9.7%, vs XLY: -13.4% | Downside Beta: 3.47 (Asym 4.53x)
VOLUME: Score 51/100 | 25D Distribution Days: 8 | Down/Up Vol Ratio: 0.90x | RelVol Today: 0.74x | CMF(20): -0.08
FUNDAMENTAL & CATALYST: Score 18/100 (Catalyst Risk: 95/100) | Rev growth +52.4% YoY | OpMargin 9.2% | FCF Positive | RED WARNING: EARNINGS IN 2 DAYS (2026-10-28)
SHORT SQUEEZE RISK: Squeeze Risk 49/100 [Controlled] | Options Bearish Score 45/100 | SI Float: 12.6% | Days to Cover: 9.2d | Borrow Fee: DATA UNAVAILABLE | Opt P/C Vol: 0.93 | GEX: DATA UNAVAILABLE

ENTRY ZONE: $57.52 – $61.24 (20EMA / 5D-VWAP Rejection Band)
TRIGGER: CONFIRMED: Failed bounce / rejection at 20EMA ($61.24) & 5D-VWAP ($58.99) with break below prior low $58.44
STOP: $63.71 (2.03x ATR14 ($2.91) above Entry / 5D Swing High $62.22 | Suggested Size: 0 sh / Max Risk $0)
TARGET 1: $46.01 / TARGET 2: $37.16
RISK / REWARD: 1 : 2.00 (Bearish Prob: 54.6%)
CONFIDENCE: 52.5%

ACTION: WAIT — RED WARNING: Binary Earnings Event in 2d (Avoid New Short)
INVALIDATION: Daily close above $63.71 (Structural Stop / 20EMA + 0.5x ATR) or 50DMA reclaim ($66.61)
⸻
```