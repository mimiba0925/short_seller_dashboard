from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .data_provider import MarketDataProvider, TickerMarketData
from .models import (
    DATA_UNAVAILABLE,
    ExecutionAction,
    ExecutionPlan,
    FactorScores,
    MarketRegimeReport,
    SignalRating,
    StockShortEvaluation,
)
from .screener import (
    _score_factor_a_trend,
    _score_factor_b_rs,
    _score_factor_c_volume,
    _score_factor_d_fundamental_catalyst,
    _score_factor_e_squeeze_and_options,
    assign_rating,
    compute_atr,
)


def format_decision_template(eval_obj: StockShortEvaluation) -> str:
    """Strictly formats the stock analysis into the exact template defined in PROMPT.md."""
    ex = eval_obj.execution
    f = eval_obj.factors
    return (
        "⸻\n"
        f"TICKER: {eval_obj.ticker}\n"
        f"SHORT SCORE: {eval_obj.short_score:.1f} / RATING: {eval_obj.rating.value}\n"
        f"MARKET REGIME: {eval_obj.market_regime_summary}\n"
        f"SECTOR: {eval_obj.sector_status}\n"
        f"TREND: {f.trend_status}\n"
        f"MOMENTUM: {f.momentum_status}\n"
        f"RELATIVE STRENGTH: {f.relative_strength_status}\n"
        f"VOLUME: {f.volume_status}\n"
        f"FUNDAMENTAL & CATALYST: {f.fundamental_catalyst_status}\n"
        f"SHORT SQUEEZE RISK: {f.short_squeeze_status}\n"
        "\n"
        f"ENTRY ZONE: {ex.entry_zone}\n"
        f"TRIGGER: {ex.trigger_condition}\n"
        f"STOP: ${ex.stop_price:.2f} ({ex.stop_basis} | Suggested Size: {ex.suggested_shares} sh / Max Risk ${ex.max_risk_dollars:.0f})\n"
        f"TARGET 1: ${ex.target_1:.2f} / TARGET 2: ${ex.target_2:.2f}\n"
        f"RISK / REWARD: 1 : {ex.risk_reward_ratio:.2f} (Bearish Prob: {ex.bearish_probability_pct:.1f}%)\n"
        f"CONFIDENCE: {ex.confidence_pct:.1f}%\n"
        "\n"
        f"ACTION: {ex.action}\n"
        f"INVALIDATION: {ex.invalidation}\n"
        "⸻"
    )


def evaluate_execution_and_triggers(
    tdata: TickerMarketData,
    df: pd.DataFrame,
    atr14: float,
    short_score: float,
    rating: SignalRating,
    factors: FactorScores,
    tech_metrics: Dict[str, Any],
    vol_metrics: Dict[str, Any],
    regime: MarketRegimeReport,
    account_size: float = 100_000.0,
    base_risk_pct: float = 0.0075,
    correlation_penalty_mult: float = 1.0,
    existing_position_entry: Optional[float] = None,
) -> ExecutionPlan:
    close = float(df["Close"].iloc[-1])
    open_px = float(df["Open"].iloc[-1])
    high_px = float(df["High"].iloc[-1])
    low_px = float(df["Low"].iloc[-1])
    prev_low = float(df["Low"].iloc[-2]) if len(df) >= 2 else low_px

    ema20 = tech_metrics["ema20"]
    sma50 = tech_metrics["sma50"]
    sma200 = tech_metrics["sma200"]
    support_20d = tech_metrics["support_20d"]
    support_60d = tech_metrics["support_60d"]
    swing_high_5d = tech_metrics["swing_high_5d"]
    rel_vol = vol_metrics["rel_vol_today"]

    # Approximate 5-day rolling VWAP as institutional intraday/swing reference
    tp = (df["High"] + df["Low"] + df["Close"]) / 3.0
    vwap5 = float((tp.iloc[-5:] * df["Volume"].iloc[-5:]).sum() / max(1.0, float(df["Volume"].iloc[-5:].sum())))

    # 1. Detect specific Entry Triggers
    bar_range = max(0.01, high_px - low_px)
    close_pos_in_bar = (close - low_px) / bar_range

    # Trigger A: Breakdown below 20D support on expanded volume
    trig_breakdown = (
        (close < support_20d)
        and (rel_vol >= 1.30 or vol_metrics["down_up_vol_ratio"] >= 1.25)
        and (close_pos_in_bar <= 0.40)
        and (not tech_metrics["overextended"])
    )

    # Trigger B: Failed Bounce / Rejection at 20EMA or 5D-VWAP with Lower High
    near_20ema_or_vwap = (high_px >= min(ema20, vwap5) - 0.35 * atr14) and (close < max(ema20, vwap5))
    bearish_rejection_bar = (close < open_px) or (close_pos_in_bar <= 0.35) or (close < prev_low)
    trig_failed_bounce = (
        (close < sma50)
        and near_20ema_or_vwap
        and bearish_rejection_bar
        and (not tech_metrics["overextended"])
    )

    # Trigger C: Trend continuation Lower High breakdown below 5D VWAP & 20EMA
    trig_lh_continuation = (
        (close < ema20)
        and (close < sma50)
        and (close < prev_low)
        and (tech_metrics["topping_pattern"] or tech_metrics["support_broken"])
        and (not tech_metrics["overextended"])
    )

    trigger_fired = bool(trig_breakdown or trig_failed_bounce or trig_lh_continuation)

    if trig_breakdown:
        entry_zone = f"${support_20d * 0.985:.2f} – ${support_20d:.2f} (20D Breakdown Zone)"
        trigger_desc = (
            f"CONFIRMED: Break below 20D support ${support_20d:.2f} with RelVol {rel_vol:.2f}x "
            f"( Target >=1.30x / Down-Up Vol {vol_metrics['down_up_vol_ratio']:.2f}x)"
        )
        entry_ref = close
    elif trig_failed_bounce:
        ref_res = max(ema20, vwap5)
        entry_zone = f"${close * 0.995:.2f} – ${ref_res:.2f} (20EMA / 5D-VWAP Rejection Band)"
        trigger_desc = (
            f"CONFIRMED: Failed bounce / rejection at 20EMA (${ema20:.2f}) & 5D-VWAP (${vwap5:.2f}) "
            f"with break below prior low ${prev_low:.2f}"
        )
        entry_ref = close
    else:
        # Prospective trigger to wait for
        bounce_zone_low = min(ema20, vwap5) - 0.25 * atr14
        bounce_zone_high = max(ema20, vwap5) + 0.15 * atr14
        entry_zone = (
            f"Breakdown < ${support_20d:.2f} OR Weak Bounce into ${bounce_zone_low:.2f} – ${bounce_zone_high:.2f}"
        )
        trigger_desc = (
            f"Await break below ${support_20d:.2f} on >1.5x volume OR Failed Bounce rejection at "
            f"20EMA (${ema20:.2f}) / VWAP (${vwap5:.2f}) with Lower High confirmation"
        )
        entry_ref = min(close, support_20d) if close > support_20d else close

    # 2. Dynamic Volatility-Based Stop-Loss Model (Strictly NO fixed percentage!)
    atr_stop = entry_ref + 1.75 * atr14
    structural_stop = max(swing_high_5d + 0.25 * atr14, ema20 + 0.85 * atr14)
    # Choose the stop that respects key resistance while bounding risk between 1.5x and 2.5x ATR
    stop_price = max(atr_stop, min(structural_stop, entry_ref + 2.40 * atr14))
    risk_per_share = max(0.05, stop_price - entry_ref)
    stop_atr_mult = risk_per_share / atr14
    stop_basis = f"{stop_atr_mult:.2f}x ATR14 (${atr14:.2f}) above Entry / 5D Swing High ${swing_high_5d:.2f}"

    # 3. Targets & R-Multiples
    # Target 1: 2.0R or major 60D structural support (whichever provides at least 1.6R, else 2.0R)
    raw_t1 = entry_ref - 2.0 * risk_per_share
    if support_60d < entry_ref - 1.5 * risk_per_share and support_60d > raw_t1:
        target_1 = max(0.01, support_60d)
    else:
        target_1 = max(0.01, raw_t1)

    target_2 = max(0.01, entry_ref - 3.5 * risk_per_share)
    reward_t1 = max(0.01, entry_ref - target_1)
    rr_ratio = reward_t1 / risk_per_share

    # 4. Compute SHORT_EXIT_SCORE (0-100) for Take-Profit & Cover Rules
    exit_score = 0.0
    exit_reasons: List[str] = []

    if existing_position_entry is not None and existing_position_entry > 0:
        initial_r = max(0.05, stop_price - existing_position_entry)
        current_r = (existing_position_entry - close) / initial_r
        if current_r >= 3.0:
            exit_score += 35.0
            exit_reasons.append(f"Target 2 Reached (+{current_r:.1f}R)")
        elif current_r >= 1.8:
            exit_score += 22.0
            exit_reasons.append(f"Target 1 Reached (+{current_r:.1f}R)")

    if tech_metrics["rsi14"] < 28.0:
        exit_score += 28.0
        exit_reasons.append(f"Oversold Momentum Convergence (RSI {tech_metrics['rsi14']:.1f} < 28)")
    if close > ema20 and close > sma50:
        exit_score += 45.0
        exit_reasons.append("Reclaimed both 20EMA and 50DMA")
    elif close > sma50:
        exit_score += 28.0
        exit_reasons.append("Reclaimed 50DMA")

    if factors.squeeze_warning_active:
        exit_score = max(exit_score, 85.0)
        exit_reasons.append("EMERGENCY EXIT: High Squeeze Risk / Borrow Spike")
    if factors.earnings_red_warning:
        exit_score = max(exit_score, 80.0)
        exit_reasons.append(f"BINARY EVENT RISK: Earnings within {factors.days_to_earnings} days")

    exit_score = float(np.clip(exit_score, 0.0, 100.0))

    # 5. Distinguish "Fundamentally Bearish" vs "Actionable Short / Safe to Short"
    is_fundamentally_bearish = (
        factors.fundamental_catalyst_score >= 52.0 or short_score >= 62.0
    )
    is_actionable_short = (
        rating in {SignalRating.A_PLUS, SignalRating.A}
        and regime.market_regime_score >= 45.0
        and not factors.squeeze_warning_active
        and not factors.earnings_red_warning
        and rr_ratio >= 1.80
    )

    # 6. Determine exact 8-state Execution Action (WAIT, WATCH, SHORT SETUP, ENTRY, ADD, HOLD, REDUCE, EXIT)
    if existing_position_entry is not None:
        if exit_score >= 75.0 or close >= stop_price:
            raw_state = ExecutionAction.EXIT
            action_str = f"EXIT — Immediate Cover ({'; '.join(exit_reasons) or 'Stop Hit'})"
        elif exit_score >= 50.0 or regime.mandatory_de_gross:
            raw_state = ExecutionAction.REDUCE
            action_str = f"REDUCE (Cover 50% & Trail Stop to Breakeven | Exit Score {exit_score:.0f}/100)"
        elif (
            regime.market_regime_score >= 70.0
            and trigger_fired
            and (existing_position_entry - close) >= risk_per_share
        ):
            raw_state = ExecutionAction.ADD
            action_str = "ADD (Pyramid +50% Size on Confirmed Lower High; Trail Initial Stop to Entry)"
        else:
            raw_state = ExecutionAction.HOLD
            action_str = f"HOLD SHORT (Trail Stop at ${stop_price:.2f} | Exit Score {exit_score:.0f}/100)"
    else:
        if factors.earnings_red_warning:
            raw_state = ExecutionAction.WAIT
            action_str = f"WAIT — RED WARNING: Binary Earnings Event in {factors.days_to_earnings}d (Avoid New Short)"
        elif factors.squeeze_warning_active:
            raw_state = ExecutionAction.WAIT
            action_str = f"WAIT — SQUEEZE RISK VETO (Squeeze Score {factors.squeeze_risk_score:.0f}/100)"
        elif regime.market_regime_score <= 40.0:
            raw_state = ExecutionAction.WAIT
            action_str = f"WAIT — Market Regime is RISK-ON ({regime.market_regime_score:.0f}/100); New Shorts Blocked"
        elif tech_metrics["overextended"] or tech_metrics["rsi14"] < 28.0:
            raw_state = ExecutionAction.WATCH
            action_str = (
                f"WATCH — Fundamentally/Technically Bearish but Short-Term Oversold "
                f"(RSI {tech_metrics['rsi14']:.1f}); Wait for Bounce to 20EMA (${ema20:.2f})"
            )
        elif is_actionable_short and trigger_fired:
            raw_state = ExecutionAction.ENTRY
            action_str = (
                f"ENTRY — Actionable Short Trigger Fired (Rating {rating.value}, "
                f"Short Score {short_score:.1f})"
            )
        elif rating in {SignalRating.A_PLUS, SignalRating.A} and regime.market_regime_score >= 41.0:
            raw_state = ExecutionAction.SHORT_SETUP
            action_str = (
                f"SHORT SETUP — Stalking Entry Trigger (Fundamentally/Structurally Bearish; "
                f"Wait for Break < ${support_20d:.2f} or Rejection at ${ema20:.2f})"
            )
        elif short_score >= 56.0 or is_fundamentally_bearish:
            raw_state = ExecutionAction.WATCH
            action_str = (
                "WATCH — Structurally Bearish Candidate, but Trigger/Regime Alignment Incomplete"
            )
        else:
            raw_state = ExecutionAction.WAIT
            action_str = f"WAIT — Low Short Score ({short_score:.1f}/100, Rating {rating.value}); Avoid Shorting"

    # 7. Position Sizing Calculation
    squeeze_mult = (
        0.0
        if factors.squeeze_warning_active
        else (0.65 if factors.squeeze_risk_score >= 45.0 else 1.0)
    )
    effective_mult = (
        regime.regime_sizing_multiplier
        * squeeze_mult
        * correlation_penalty_mult
        * (1.0 if rating in {SignalRating.A_PLUS, SignalRating.A} else 0.0)
    )
    max_risk_dollars = account_size * base_risk_pct * effective_mult
    raw_shares = int(math.floor(max_risk_dollars / risk_per_share)) if max_risk_dollars > 0 else 0
    max_notional_shares = int(math.floor((account_size * 0.12) / max(0.01, entry_ref)))
    suggested_shares = min(raw_shares, max_notional_shares)
    suggested_notional = round(suggested_shares * entry_ref, 2)

    # 8. Bearish Probability & Confidence Score (accounting for missing fields!)
    total_tracked_fields = 9
    avail_ratio = max(0.55, (total_tracked_fields - len(tdata.missing_fields)) / total_tracked_fields)
    regime_align = min(100.0, regime.market_regime_score * 1.15)
    bearish_prob = float(
        np.clip(
            0.55 * short_score + 0.25 * regime.market_regime_score + (8.0 if trigger_fired else 0.0) - (12.0 if factors.squeeze_warning_active else 0.0),
            15.0,
            92.0,
        )
    )
    confidence = float(
        np.clip(
            avail_ratio * (0.55 * short_score + 0.30 * regime_align + (15.0 if trigger_fired else 5.0)),
            20.0,
            95.0,
        )
    )

    invalidation_px = max(stop_price, ema20 + 0.50 * atr14)
    invalidation_str = (
        f"Daily close above ${invalidation_px:.2f} (Structural Stop / 20EMA + 0.5x ATR) "
        f"or 50DMA reclaim (${sma50:.2f})"
    )

    return ExecutionPlan(
        action=action_str,
        raw_state=raw_state,
        is_fundamentally_bearish=is_fundamentally_bearish,
        is_actionable_short=is_actionable_short,
        bearish_probability_pct=round(bearish_prob, 1),
        entry_zone=entry_zone,
        entry_reference_price=round(entry_ref, 2),
        trigger_condition=trigger_desc,
        trigger_fired=trigger_fired,
        stop_price=round(stop_price, 2),
        stop_basis=stop_basis,
        target_1=round(target_1, 2),
        target_2=round(target_2, 2),
        risk_per_share=round(risk_per_share, 2),
        reward_per_share_t1=round(reward_t1, 2),
        risk_reward_ratio=round(rr_ratio, 2),
        confidence_pct=round(confidence, 1),
        invalidation=invalidation_str,
        short_exit_score=round(exit_score, 1),
        exit_reasons=exit_reasons,
        suggested_shares=suggested_shares,
        suggested_notional=suggested_notional,
        max_risk_dollars=round(max_risk_dollars, 2),
    )


def evaluate_stock(
    ticker: str,
    provider: MarketDataProvider,
    regime: MarketRegimeReport,
    account_size: float = 100_000.0,
    base_risk_pct: float = 0.0075,
    correlation_penalty_mult: float = 1.0,
    existing_position_entry: Optional[float] = None,
) -> StockShortEvaluation:
    tdata = provider.get_ticker_data(ticker)
    df = tdata.ohlcv
    spy_df = provider.get_ohlcv("SPY")
    sec_df = provider.get_ohlcv(tdata.sector_etf)

    atr14 = compute_atr(df, 14)
    close = float(df["Close"].iloc[-1])

    # Score Factors A, B, C, D, E
    f_a, trend_str, mom_str, tech_metrics = _score_factor_a_trend(df, atr14)
    f_b, rs_str, rs_metrics = _score_factor_b_rs(df, spy_df, sec_df, tdata.sector_etf, tech_metrics)
    f_c, vol_str, vol_metrics = _score_factor_c_volume(df)
    f_d, cat_risk_score, fund_str, earn_red = _score_factor_d_fundamental_catalyst(tdata)
    f_e, sqz_risk_score, sqz_str, sqz_warn = _score_factor_e_squeeze_and_options(tdata, df, tech_metrics)

    # Exact weights per PROMPT.md: A=25%, B=15%, C=15%, D=25%, E=20%
    short_score = (
        0.25 * f_a
        + 0.15 * f_b
        + 0.15 * f_c
        + 0.25 * f_d
        + 0.20 * f_e
    )
    short_score = round(float(np.clip(short_score, 0.0, 100.0)), 1)
    rating = assign_rating(short_score, sqz_warn, earn_red)

    factors = FactorScores(
        trend_breakdown_score=round(f_a, 1),
        trend_status=trend_str,
        momentum_status=mom_str,
        relative_weakness_score=round(f_b, 1),
        relative_strength_status=rs_str,
        volume_distribution_score=round(f_c, 1),
        volume_status=vol_str,
        fundamental_catalyst_score=round(f_d, 1),
        catalyst_risk_score=cat_risk_score,
        fundamental_catalyst_status=fund_str,
        days_to_earnings=tdata.days_to_earnings,
        earnings_red_warning=earn_red,
        derivatives_bearish_score=round(f_e, 1),
        squeeze_risk_score=sqz_risk_score,
        short_squeeze_status=sqz_str,
        squeeze_warning_active=sqz_warn,
    )

    execution = evaluate_execution_and_triggers(
        tdata=tdata,
        df=df,
        atr14=atr14,
        short_score=short_score,
        rating=rating,
        factors=factors,
        tech_metrics=tech_metrics,
        vol_metrics=vol_metrics,
        regime=regime,
        account_size=account_size,
        base_risk_pct=base_risk_pct,
        correlation_penalty_mult=correlation_penalty_mult,
        existing_position_entry=existing_position_entry,
    )

    # Sector status string
    sec_info = next((s for s in regime.sector_weakness_ranking if s["etf"] == tdata.sector_etf), None)
    if sec_info:
        sector_status = (
            f"{tdata.sector} ({tdata.sector_etf}) | 20D Ret: {sec_info['ret_20d_pct']:+.1f}% "
            f"(vs SPY {sec_info['rs_vs_spy_20d_pct']:+.1f}%) | Weakness Score: {sec_info['weakness_score']}/100"
        )
    else:
        sector_status = f"{tdata.sector} ({tdata.sector_etf})"

    regime_summary = (
        f"{regime.market_regime_score:.1f}/100 — {regime.regime_label} | "
        f"Breadth Weakness {regime.breadth.breadth_weakness_score:.0f}/100 | "
        f"VIX {regime.volatility.vix:.2f} (VIX/VIX3M {regime.volatility.vix_term_ratio:.2f})"
    )

    eval_obj = StockShortEvaluation(
        ticker=tdata.ticker,
        company_name=tdata.company_name,
        sector=tdata.sector,
        sector_etf=tdata.sector_etf,
        sector_status=sector_status,
        close=round(close, 2),
        atr14=round(atr14, 2),
        short_score=short_score,
        rating=rating,
        market_regime_summary=regime_summary,
        factors=factors,
        execution=execution,
        missing_fields=tdata.missing_fields,
        raw_metrics={**tech_metrics, **rs_metrics, **vol_metrics},
    )
    eval_obj.formatted_decision_card = format_decision_template(eval_obj)
    return eval_obj
