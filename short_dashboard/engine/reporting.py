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
    """Generates prioritized real-time Webhook/Alert payloads according to Module 5 spec."""
    alerts: List[Dict[str, Any]] = []
    now_iso = dt.datetime.now().isoformat(timespec="seconds")

    # 1. Macro Regime Alerts
    if regime.volatility.term_structure_inverted:
        alerts.append(
            {
                "timestamp": now_iso,
                "priority": AlertPriority.HIGH.value,
                "category": "VOLATILITY_REGIME",
                "ticker": "VIX/VIX3M",
                "title": f"VIX Term Structure Inverted ({regime.volatility.vix_term_ratio:.2f}x)",
                "message": (
                    f"VIX ({regime.volatility.vix:.2f}) > VIX3M ({regime.volatility.vix3m:.2f}). "
                    "Institutional near-term hedging surge — Short weighting boosted."
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
                "title": f"Risk-On Regime ({regime.market_regime_score:.1f}/100) — Mandatory Short Reduction",
                "message": "Market Regime Score < 35. Block new speculative shorts and reduce gross short exposure by 50%.",
                "webhook_payload": {
                    "event": "MANDATORY_SHORT_DEGROSS",
                    "regime_score": regime.market_regime_score,
                },
            }
        )

    # 2. Stock-Level Alerts
    for ev in evaluations:
        # CRITICAL: Earnings within 3 days
        if ev.factors.earnings_red_warning:
            alerts.append(
                {
                    "timestamp": now_iso,
                    "priority": AlertPriority.CRITICAL.value,
                    "category": "CATALYST_BINARY_RISK",
                    "ticker": ev.ticker,
                    "title": f"RED WARNING: {ev.ticker} Earnings in {ev.factors.days_to_earnings} Days",
                    "message": (
                        f"{ev.ticker} reports earnings within <= 3 days. Freeze new short entries; "
                        "cover or hedge existing short exposure to avoid binary gap risk."
                    ),
                    "webhook_payload": {
                        "event": "EARNINGS_RED_WARNING",
                        "ticker": ev.ticker,
                        "days_to_earnings": ev.factors.days_to_earnings,
                        "action": "EXIT_OR_AVOID",
                    },
                }
            )

        # CRITICAL: High Squeeze Risk Warning
        if ev.factors.squeeze_warning_active:
            alerts.append(
                {
                    "timestamp": now_iso,
                    "priority": AlertPriority.CRITICAL.value,
                    "category": "SQUEEZE_RISK",
                    "ticker": ev.ticker,
                    "title": f"SQUEEZE RISK ALERT: {ev.ticker} (Score {ev.factors.squeeze_risk_score:.0f}/100)",
                    "message": ev.factors.short_squeeze_status,
                    "webhook_payload": {
                        "event": "SHORT_SQUEEZE_WARNING",
                        "ticker": ev.ticker,
                        "squeeze_risk_score": ev.factors.squeeze_risk_score,
                        "action": "AVOID_OR_EMERGENCY_COVER",
                    },
                }
            )

        # HIGH PRIORITY: Actionable Short Entry Trigger (Regime >= 60 or A+/A with Trigger Fired)
        if ev.execution.raw_state == ExecutionAction.ENTRY:
            alerts.append(
                {
                    "timestamp": now_iso,
                    "priority": AlertPriority.HIGH.value,
                    "category": "EXECUTION_TRIGGER",
                    "ticker": ev.ticker,
                    "title": f"ACTIONABLE SHORT ENTRY: {ev.ticker} [{ev.rating.value} | Score {ev.short_score:.1f}]",
                    "message": (
                        f"{ev.execution.trigger_condition} | Entry Ref ${ev.execution.entry_reference_price:.2f}, "
                        f"Stop ${ev.execution.stop_price:.2f}, T1 ${ev.execution.target_1:.2f} "
                        f"(R/R 1:{ev.execution.risk_reward_ratio:.2f})"
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
                    "title": f"SHORT SETUP READY: {ev.ticker} [{ev.rating.value} | Score {ev.short_score:.1f}]",
                    "message": f"Stalking trigger: {ev.execution.trigger_condition}",
                    "webhook_payload": {
                        "event": "SHORT_SETUP_WATCH",
                        "ticker": ev.ticker,
                        "rating": ev.rating.value,
                        "entry_zone": ev.execution.entry_zone,
                        "stop": ev.execution.stop_price,
                    },
                }
            )

    # 3. Portfolio Correlation Alert
    if portfolio_risk.correlated_short_risk_score >= 55.0:
        alerts.append(
            {
                "timestamp": now_iso,
                "priority": AlertPriority.HIGH.value,
                "category": "PORTFOLIO_CORRELATION",
                "ticker": "PORTFOLIO",
                "title": f"Elevated Correlated Short Risk ({portfolio_risk.correlated_short_risk_score:.0f}/100)",
                "message": (
                    f"{portfolio_risk.nominal_positions_count} nominal candidates equal only "
                    f"{portfolio_risk.effective_independent_bets:.2f} effective independent bets "
                    f"(Avg 60D Corr: {portfolio_risk.avg_pairwise_correlation:.2f})."
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
    """Produces the comprehensive DAILY SHORT MARKET REPORT in Markdown format."""
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
    squeeze_watch = [e for e in evaluations if e.factors.squeeze_warning_active or e.factors.squeeze_risk_score >= 50.0]
    catalysts = [
        e for e in evaluations if e.factors.days_to_earnings is not None or e.factors.catalyst_risk_score >= 50.0
    ]

    lines: List[str] = [
        "# DAILY SHORT MARKET REPORT (美股量化空方每日決策日報)",
        f"**Generated At**: `{regime.as_of}`",
        "",
        "## 1. Macro & Market Regime Filter (大盤環境與做空總閘門)",
        f"- **MARKET REGIME SCORE**: **{regime.market_regime_score:.1f} / 100** — `{regime.regime_label}`",
        f"- **Short Book Policy**: {regime.short_book_policy}",
        f"- **Max Gross Short Exposure Cap**: `{regime.max_gross_short_exposure_pct:.0f}%` | **Regime Risk Multiplier**: `{regime.regime_sizing_multiplier:.2f}x`",
        f"- **Market Breadth (`BREADTH_WEAKNESS_SCORE`)**: `{regime.breadth.breadth_weakness_score:.1f}/100` — {regime.breadth.summary}",
        f"- **Volatility Regime (`VOLATILITY_REGIME_SCORE`)**: `{regime.volatility.volatility_regime_score:.1f}/100` — {regime.volatility.summary} | {regime.volatility.put_call_status}",
        "",
        "### Benchmark Index Breakdown",
        "| Index | Close | 20EMA | 50SMA | 200SMA | 20D Ret | 25D Dist Days | Index Bear Score |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for k in ["SPY", "QQQ", "IWM"]:
        if k in regime.indices:
            ix = regime.indices[k]
            lines.append(
                f"| **{ix.ticker}** | ${ix.close:.2f} | ${ix.ema20:.2f} ({'Below' if ix.below_ema20 else 'Above'}) | "
                f"${ix.sma50:.2f} ({'Below' if ix.below_sma50 else 'Above'}) | ${ix.sma200:.2f} | "
                f"{ix.ret_20d_pct:+.2f}% | {ix.dist_days_25d}d | **{ix.sub_score:.1f}** |"
            )

    lines.extend(
        [
            "",
            "## 2. Sector Relative Weakness Ranking (板塊弱勢排行)",
            "| Sector ETF | Close | 5D Ret | 20D Ret | 20D RS vs SPY | 25D Dist Days | Weakness Score |",
            "| :--- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for sec in regime.sector_weakness_ranking[:6]:
        lines.append(
            f"| **{sec['etf']}** | ${sec['close']:.2f} | {sec['ret_5d_pct']:+.2f}% | {sec['ret_20d_pct']:+.2f}% | "
            f"{sec['rs_vs_spy_20d_pct']:+.2f}% | {sec['dist_days_25d']}d | **{sec['weakness_score']:.1f}** |"
        )

    lines.extend(
        [
            "",
            "## 3. Actionable Short List (A+ / A 級可執行空方候選池)",
            "> 僅包含通過安全濾網（無軋空警告、財報 > 3 天、評級 A/A+）之標的。",
            "",
        ]
    )
    if actionable:
        lines.extend(
            [
                "| Ticker | Short Score | Rating | State | Price | Stop (ATR) | Target 1 | R/R | Bear Prob | Confidence |",
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
        lines.append("*No stocks currently pass the strict A+/A Actionable Short safety gate.*")

    lines.extend(
        [
            "",
            "## 4. Fundamentally / Structurally Bearish BUT Not Yet Actionable (看空但暫不適合做空)",
            "| Ticker | Short Score | Rating | Current State | Reason Not Actionable Today |",
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
            "## 5. Short Squeeze Risk & Upcoming Binary Catalysts (軋空警告與事件日曆)",
        ]
    )
    if squeeze_watch:
        for ev in squeeze_watch:
            lines.append(f"- **Squeeze Watch — `{ev.ticker}`**: {ev.factors.short_squeeze_status}")
    else:
        lines.append("- *No extreme short squeeze alerts active across current watchlist.*")

    if catalysts:
        for ev in catalysts:
            lines.append(f"- **Catalyst Watch — `{ev.ticker}`**: {ev.factors.fundamental_catalyst_status}")

    lines.extend(
        [
            "",
            "## 6. Portfolio-Level Correlated Short Risk (`CORRELATED_SHORT_RISK`)",
            f"- **Correlated Short Risk Score**: `{portfolio_risk.correlated_short_risk_score:.1f}/100`",
            f"- **Nominal Candidates vs Effective Independent Bets ($N_{{\\text{{eff}}}}$)**: `{portfolio_risk.nominal_positions_count}` nominal $\\rightarrow$ **`{portfolio_risk.effective_independent_bets:.2f}` effective independent bets** (Avg 60D Pairwise Correlation: `{portfolio_risk.avg_pairwise_correlation:.2f}`)",
            f"- **Gross Short Exposure (Suggested)**: `{portfolio_risk.gross_short_exposure_pct:.1f}%` (Beta-Adjusted: `{portfolio_risk.beta_adjusted_short_exposure_pct:.1f}%`)",
        ]
    )
    for w in portfolio_risk.risk_warnings:
        lines.append(f"  - ⚠️ {w}")

    lines.extend(["", "## 7. Standardized Stock Decision Cards (個股標準化決策輸出)"])
    for ev in evaluations[:5]:
        lines.append("```text")
        lines.append(ev.formatted_decision_card)
        lines.append("```")

    return "\n".join(lines)
