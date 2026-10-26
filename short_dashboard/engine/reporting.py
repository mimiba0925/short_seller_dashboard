from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

from .models import (
    AlertPriority,
    ExecutionAction,
    MarketRegimeReport,
    SignalRating,
    StockShortEvaluation,
)
from .portfolio_backtest import PortfolioRiskSummary


def generate_alerts(
    regime: MarketRegimeReport,
    evaluations: List[StockShortEvaluation],
    portfolio_risk: PortfolioRiskSummary,
) -> List[Dict[str, Any]]:
    """Generates prioritized real-time Webhook/Alert payloads in Traditional Chinese."""
    alerts: List[Dict[str, Any]] = []
    now_iso = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if regime.volatility.term_structure_inverted:
        alerts.append(
            {
                "timestamp": now_iso,
                "priority": AlertPriority.HIGH.value,
                "category": "VOLATILITY_REGIME",
                "ticker": "VIX/VIX3M",
                "title": f"VIX 期限結構倒掛 ({regime.volatility.vix_term_ratio:.2f}x) — 強烈有利空方",
                "message": (
                    f"近月 VIX ({regime.volatility.vix:.2f}) 高於遠月 VIX3M ({regime.volatility.vix3m:.2f})，"
                    "機構緊急買進現貨避險保護，系統自動調高空方權重。"
                ),
                "webhook_payload": {
                    "event": "VIX_BACKWARDATION",
                    "vix": regime.volatility.vix,
                    "ratio": regime.volatility.vix_term_ratio,
                },
            }
        )

    if regime.mandatory_de_gross:
        alerts.append(
            {
                "timestamp": now_iso,
                "priority": AlertPriority.CRITICAL.value,
                "category": "MARKET_REGIME",
                "ticker": "SPY/QQQ",
                "title": f"大盤多頭強勢 ({regime.market_regime_score:.1f}/100，有利多方) — 強制空單減倉",
                "message": "大盤環境評分低於 35 分（越低越有利多方），系統禁止開立新空單並建議既有空單強制減倉 50%。",
                "webhook_payload": {
                    "event": "MANDATORY_SHORT_DEGROSS",
                    "regime_score": regime.market_regime_score,
                },
            }
        )

    for ev in evaluations:
        if ev.factors.earnings_red_warning:
            alerts.append(
                {
                    "timestamp": now_iso,
                    "priority": AlertPriority.CRITICAL.value,
                    "category": "CATALYST_BINARY_RISK",
                    "ticker": ev.ticker,
                    "title": f"🔴 財報紅色警告：{ev.ticker} 距離財報僅剩 {ev.factors.days_to_earnings} 天",
                    "message": (
                        f"{ev.ticker} 將於 {ev.factors.days_to_earnings} 天內公佈財報（事件風險分 95/100，不利空方留倉），"
                        "強制凍結新空單進場，既有空單請提前平倉或買入買權保護以避開跳空軋空。"
                    ),
                    "webhook_payload": {
                        "event": "EARNINGS_RED_WARNING",
                        "ticker": ev.ticker,
                        "days_to_earnings": ev.factors.days_to_earnings,
                        "action": "EXIT_OR_AVOID",
                    },
                }
            )

        if ev.factors.squeeze_warning_active:
            alerts.append(
                {
                    "timestamp": now_iso,
                    "priority": AlertPriority.CRITICAL.value,
                    "category": "SQUEEZE_RISK",
                    "ticker": ev.ticker,
                    "title": f"⚠️ 嚴重軋空警告：{ev.ticker}（軋空風險分 {ev.factors.squeeze_risk_score:.0f}/100，分數越高越危險）",
                    "message": ev.factors.short_squeeze_status,
                    "webhook_payload": {
                        "event": "SHORT_SQUEEZE_WARNING",
                        "ticker": ev.ticker,
                        "squeeze_risk_score": ev.factors.squeeze_risk_score,
                        "action": "AVOID_OR_EMERGENCY_COVER",
                    },
                }
            )

        if ev.execution.raw_state == ExecutionAction.ENTRY:
            alerts.append(
                {
                    "timestamp": now_iso,
                    "priority": AlertPriority.HIGH.value,
                    "category": "EXECUTION_TRIGGER",
                    "ticker": ev.ticker,
                    "title": f"🎯 可執行做空觸發 (ENTRY)：{ev.ticker} [評級 {ev.rating.value}｜空方評分 {ev.short_score:.1f} 有利空方]",
                    "message": (
                        f"{ev.execution.trigger_condition}｜參考進場 ${ev.execution.entry_reference_price:.2f}、"
                        f"動態停損 ${ev.execution.stop_price:.2f}、第一目標價 ${ev.execution.target_1:.2f} "
                        f"(風報比 1:{ev.execution.risk_reward_ratio:.2f})"
                    ),
                    "webhook_payload": {
                        "event": "SHORT_ENTRY_TRIGGER",
                        "ticker": ev.ticker,
                        "rating": ev.rating.value,
                        "short_score": ev.short_score,
                        "regime_score": regime.market_regime_score,
                        "entry": ev.execution.entry_reference_price,
                        "stop": ev.execution.stop_price,
                        "target_1": ev.execution.target_1,
                        "target_2": ev.execution.target_2,
                        "shares": ev.execution.suggested_shares,
                    },
                }
            )
        elif ev.execution.raw_state == ExecutionAction.SHORT_SETUP:
            alerts.append(
                {
                    "timestamp": now_iso,
                    "priority": AlertPriority.MEDIUM.value,
                    "category": "SHORT_SETUP",
                    "ticker": ev.ticker,
                    "title": f"👀 空方 Setup 候選就緒：{ev.ticker} [評級 {ev.rating.value}｜空方評分 {ev.short_score:.1f}]",
                    "message": f"等待觸發條件：{ev.execution.trigger_condition}",
                    "webhook_payload": {
                        "event": "SHORT_SETUP_WATCH",
                        "ticker": ev.ticker,
                        "rating": ev.rating.value,
                        "entry_zone": ev.execution.entry_zone,
                        "stop": ev.execution.stop_price,
                    },
                }
            )

    if portfolio_risk.correlated_short_risk_score >= 50.0:
        alerts.append(
            {
                "timestamp": now_iso,
                "priority": AlertPriority.HIGH.value,
                "category": "PORTFOLIO_CORRELATION",
                "ticker": "PORTFOLIO",
                "title": f"組合共線性風險偏高 ({portfolio_risk.correlated_short_risk_score:.0f}/100，越高代表空單越集中)",
                "message": (
                    f"目前 {portfolio_risk.nominal_positions_count} 檔空方候選股僅相當於 "
                    f"{portfolio_risk.effective_independent_bets:.2f} 筆有效獨立部位 "
                    f"(60日平均相關係數: {portfolio_risk.avg_pairwise_correlation:.2f})，請避免同板塊重複重倉。"
                ),
                "webhook_payload": {
                    "event": "CORRELATED_SHORT_RISK_HIGH",
                    "effective_bets": portfolio_risk.effective_independent_bets,
                    "nominal_bets": portfolio_risk.nominal_positions_count,
                },
            }
        )

    priority_rank = {
        AlertPriority.CRITICAL.value: 0,
        AlertPriority.HIGH.value: 1,
        AlertPriority.MEDIUM.value: 2,
        AlertPriority.LOW.value: 3,
    }
    alerts.sort(key=lambda a: priority_rank.get(a["priority"], 9))
    return alerts


def format_daily_short_market_report(
    regime: MarketRegimeReport,
    evaluations: List[StockShortEvaluation],
    portfolio_risk: PortfolioRiskSummary,
    alerts: List[Dict[str, Any]],
) -> str:
    """Produces the comprehensive DAILY SHORT MARKET REPORT in Traditional Chinese Markdown."""
    actionable = [
        e
        for e in evaluations
        if e.rating in {SignalRating.A_PLUS, SignalRating.A}
        and not e.factors.squeeze_warning_active
        and not e.factors.earnings_red_warning
    ]
    fund_bearish_not_safe = [
        e
        for e in evaluations
        if e.execution.is_fundamentally_bearish and e not in actionable
    ]
    squeeze_watch = [e for e in evaluations if e.factors.squeeze_warning_active or e.factors.squeeze_risk_score >= 48.0]
    catalysts = [
        e for e in evaluations if e.factors.days_to_earnings is not None or e.factors.catalyst_risk_score >= 50.0
    ]

    lines: List[str] = [
        "# DAILY SHORT MARKET REPORT (美股量化空方每日決策日報)",
        f"**產出時間**：`{regime.as_of}`",
        "",
        "> **📊 評分方向性總覽（閱讀指南）**：",
        "> - **`MARKET REGIME SCORE` / `BREADTH WEAKNESS` / `VOLATILITY REGIME` / 個股 `SHORT SCORE` / 因子 A~D**：**分數越高（接近 100）代表越有利空方**；**分數越低（接近 0）代表越有利多方**。",
        "> - **`SQUEEZE RISK SCORE` (軋空風險) / `CATALYST RISK` (二元事件) / `CORRELATED SHORT RISK` (共線性風險)**：**⚠️ 分數越高代表做空危險度越高（不利空方 / 易被多方逼空），超過門檻時系統自動一票否決禁空！**",
        "",
        "## 1. 大盤總體環境監控 (Macro & Market Regime Filter)",
        f"- **大盤環境評分 (`MARKET REGIME SCORE`)**：**{regime.market_regime_score:.1f} / 100**（越高越有利空方，<=40 有利多方）— `{regime.regime_label}`",
        f"- **空方部位操作準則**：{regime.short_book_policy}",
        f"- **總空頭曝險上限**：`{regime.max_gross_short_exposure_pct:.0f}%`｜**大盤部位規模乘數**：`{regime.regime_sizing_multiplier:.2f}x`",
        f"- **市場寬度惡化評分 (`BREADTH WEAKNESS SCORE`)**：`{regime.breadth.breadth_weakness_score:.1f}/100` — {regime.breadth.summary}",
        f"- **波動與避險情緒 (`VOLATILITY REGIME SCORE`)**：`{regime.volatility.volatility_regime_score:.1f}/100` — {regime.volatility.summary}｜{regime.volatility.put_call_status}",
        "",
        "### 三大基準指數均線與派發日明細",
        "| 指數 | 收盤價 | 20EMA (位置) | 50SMA (位置) | 200SMA | 20日報酬 | 近25日派發天數 | 指數空方分 (越高越利空) |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for k in ["SPY", "QQQ", "IWM"]:
        if k in regime.indices:
            ix = regime.indices[k]
            lines.append(
                f"| **{ix.ticker}** | ${ix.close:.2f} | ${ix.ema20:.2f} ({'跌破利空' if ix.below_ema20 else '站上利多'}) | "
                f"${ix.sma50:.2f} ({'跌破利空' if ix.below_sma50 else '站上利多'}) | ${ix.sma200:.2f} | "
                f"{ix.ret_20d_pct:+.2f}% | {ix.dist_days_25d} 天 | **{ix.sub_score:.1f}** |"
            )

    lines.extend(
        [
            "",
            "## 2. GICS 板塊相對弱勢排行 (Sector Weakness Ranking)",
            "| 板塊 ETF | 收盤價 | 5日報酬 | 20日報酬 | 20日相對 SPY 強弱 | 近25日派發日 | 板塊弱勢分 (越高越利空) |",
            "| :--- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for sec in regime.sector_weakness_ranking[:6]:
        lines.append(
            f"| **{sec['etf']}** | ${sec['close']:.2f} | {sec['ret_5d_pct']:+.2f}% | {sec['ret_20d_pct']:+.2f}% | "
            f"{sec['rs_vs_spy_20d_pct']:+.2f}% | {sec['dist_days_25d']} 天 | **{sec['weakness_score']:.1f}** |"
        )

    lines.extend(
        [
            "",
            "## 3. 現在可執行做空清單 (Actionable Short List — 僅限 A+ / A 級且安全過關)",
            "> 必須同時滿足：`SHORT SCORE` 高分（有利空方）、評級達 `A+` 或 `A`、無軋空警報、且距離財報 > 3 天。",
            "",
        ]
    )
    if actionable:
        lines.extend(
            [
                "| 代碼 | 空方總分 (越高越利空) | 評級 | 執行狀態 | 現價 | 動態停損 (ATR) | 目標價 1 | 風報比 | 空方勝率 | 信心水準 |",
                "| :--- | ---: | :---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for ev in actionable:
            ex = ev.execution
            lines.append(
                f"| **{ev.ticker}** | **{ev.short_score:.1f}** | `{ev.rating.value}` | `{ex.raw_state.value}` | "
                f"${ev.close:.2f} | ${ex.stop_price:.2f} | ${ex.target_1:.2f} | 1:{ex.risk_reward_ratio:.2f} | "
                f"{ex.bearish_probability_pct:.1f}% | {ex.confidence_pct:.1f}% |"
            )
    else:
        lines.append("*目前無標的同時通過 A+/A 級與安全濾網。*")

    lines.extend(
        [
            "",
            "## 4. 結構/基本面看空但「暫不適合進場」名單 (Fundamentally Bearish — Wait/Watch)",
            "| 代碼 | 空方總分 (越高越利空) | 評級 | 狀態 | 暫不進場原因與等待條件 |",
            "| :--- | ---: | :---: | :---: | :--- |",
        ]
    )
    for ev in fund_bearish_not_safe:
        lines.append(
            f"| **{ev.ticker}** | {ev.short_score:.1f} | `{ev.rating.value}` | `{ev.execution.raw_state.value}` | {ev.execution.action} |"
        )

    lines.extend(
        [
            "",
            "## 5. 軋空風險監控與二元催化劑事件日曆 (Squeeze Risk & Catalyst Watch)",
        ]
    )
    if squeeze_watch:
        for ev in squeeze_watch:
            lines.append(f"- **軋空警戒 — `{ev.ticker}`**：{ev.factors.short_squeeze_status}")
    else:
        lines.append("- *目前監控清單中無極端軋空警報標的。*")

    if catalysts:
        for ev in catalysts:
            lines.append(f"- **基本面與催化劑 — `{ev.ticker}`**：{ev.factors.fundamental_catalyst_status}")

    lines.extend(
        [
            "",
            "## 6. 投資組合共線性風險 (`CORRELATED_SHORT_RISK`)",
            f"- **組合共線性風險分**：`{portfolio_risk.correlated_short_risk_score:.1f}/100`（⚠️ 分數越高代表空單越集中於同溫層，越不利組合風控）",
            f"- **名目候選數 vs 有效獨立部位數 ($N_{{\\text{{eff}}}}$)**：名目 `{portfolio_risk.nominal_positions_count}` 檔 $\\rightarrow$ **實際僅相當於 `{portfolio_risk.effective_independent_bets:.2f}` 筆獨立部位**（60日平均兩兩相關係數：`{portfolio_risk.avg_pairwise_correlation:.2f}`）",
            f"- **建議總空頭曝險**：`{portfolio_risk.gross_short_exposure_pct:.1f}%`（Beta 加權調整後：`{portfolio_risk.beta_adjusted_short_exposure_pct:.1f}%`）",
        ]
    )
    for w in portfolio_risk.risk_warnings:
        lines.append(f"  - ⚠️ {w}")

    lines.extend(["", "## 7. 個股標準化決策輸出卡 (Standardized Stock Decision Cards)"])
    for ev in evaluations[:6]:
        lines.append("```text")
        lines.append(ev.formatted_decision_card)
        lines.append("```")

    return "\n".join(lines)
