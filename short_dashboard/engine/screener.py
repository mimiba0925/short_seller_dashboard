from __future__ import annotations

from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd

from .data_provider import MarketDataProvider, TickerMarketData
from .models import (
    DATA_UNAVAILABLE,
    INSUFFICIENT_DATA,
    FactorScores,
    MarketRegimeReport,
    SignalRating,
    StockShortEvaluation,
)
from .regime import _calc_distribution_days


def compute_atr(df: pd.DataFrame, period: int = 14) -> float:
    if len(df) < 3:
        return 1.0
    high = df["High"]
    low = df["Low"]
    prev_close = df["Close"].shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = float(tr.rolling(period, min_periods=2).mean().iloc[-1])
    return max(0.01, atr)


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    roll_up = up.ewm(alpha=1.0 / period, adjust=False).mean()
    roll_down = down.ewm(alpha=1.0 / period, adjust=False).mean()
    rs = roll_up / roll_down.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def _score_factor_a_trend(df: pd.DataFrame, atr14: float) -> Tuple[float, str, str, Dict[str, Any]]:
    """Factor A: Price Trend & Structural Breakdown (25% weight)."""
    close = float(df["Close"].iloc[-1])
    ema20_s = df["Close"].ewm(span=20, adjust=False).mean()
    sma50_s = df["Close"].rolling(50, min_periods=15).mean()
    sma200_s = df["Close"].rolling(200, min_periods=30).mean()

    ema20 = float(ema20_s.iloc[-1])
    sma50 = float(sma50_s.iloc[-1])
    sma200 = float(sma200_s.iloc[-1])

    slope20 = ((ema20 / float(ema20_s.iloc[-6])) - 1.0) * 100.0 if len(ema20_s) >= 6 else 0.0
    slope50 = ((sma50 / float(sma50_s.iloc[-11])) - 1.0) * 100.0 if len(sma50_s) >= 11 else 0.0

    dist_20_atr = (close - ema20) / atr14
    dist_50_pct = ((close / sma50) - 1.0) * 100.0 if sma50 > 0 else 0.0
    dist_200_pct = ((close / sma200) - 1.0) * 100.0 if sma200 > 0 else 0.0

    # Prior 20-day structural support and 60-day neckline (excluding current bar to avoid look-ahead)
    prior_df = df.iloc[:-1] if len(df) > 2 else df
    support_20d = float(prior_df["Low"].iloc[-min(20, len(prior_df)) :].min())
    support_60d = float(prior_df["Low"].iloc[-min(60, len(prior_df)) :].min())
    high_20d = float(prior_df["High"].iloc[-min(20, len(prior_df)) :].max())
    high_60d = float(prior_df["High"].iloc[-min(60, len(prior_df)) :].max())
    swing_high_5d = float(prior_df["High"].iloc[-min(5, len(prior_df)) :].max())

    # Pattern detection
    support_broken = close < support_20d
    near_breakdown = (not support_broken) and (close <= support_20d + 0.65 * atr14)

    # Double Top / Lower High Topping structure over last 40 bars
    win40 = df.iloc[-min(45, len(df)) :]
    mid_idx = len(win40) // 2
    h1 = float(win40["High"].iloc[:mid_idx].max()) if mid_idx > 2 else high_60d
    h2 = float(win40["High"].iloc[mid_idx:].max()) if mid_idx > 2 else high_20d
    neckline = float(win40["Low"].iloc[max(0, mid_idx - 5) : min(len(win40), mid_idx + 6)].min())
    topping_pattern = (h2 <= h1 * 1.02) and (close < neckline or close < sma50)

    # Failed Breakout / Bull Trap in last 10 bars
    recent_high_10d = float(df["High"].iloc[-min(10, len(df)) :].max())
    prior_res = float(df["High"].iloc[-min(55, len(df)) : -min(10, len(df))].max()) if len(df) > 20 else high_60d
    failed_breakout = (recent_high_10d > prior_res * 1.005) and (close < prior_res * 0.985)

    score = 0.0
    if close < ema20:
        score += 15.0
    if slope20 < 0:
        score += 10.0
    if close < sma50:
        score += 18.0
    if slope50 < 0:
        score += 8.0
    if close < sma200 or ema20 < sma50:
        score += 12.0

    patterns = []
    if support_broken:
        score += 24.0
        patterns.append(f"20D Support Breakdown (<${support_20d:.2f})")
    elif near_breakdown:
        score += 14.0
        patterns.append(f"Testing 20D Neckline (${support_20d:.2f})")

    if topping_pattern:
        score += 15.0
        patterns.append("Lower-High / Double-Top Structure")
    if failed_breakout:
        score += 12.0
        patterns.append("Failed Breakout (Bull Trap)")

    # Overextension penalty if stretched > 3.0 ATR below 20EMA
    overextended = dist_20_atr < -3.0
    if overextended:
        score -= 15.0
        patterns.append(f"Short-Term Overextended ({dist_20_atr:.1f}x ATR vs 20EMA)")

    score = float(np.clip(score, 0.0, 100.0))
    pat_str = ", ".join(patterns) if patterns else "No Structural Breakdown Confirmed"
    trend_status = (
        f"Score {score:.0f}/100 | Close ${close:.2f} vs 20EMA ${ema20:.2f} ({dist_20_atr:+.1f} ATR), "
        f"50DMA ${sma50:.2f} ({dist_50_pct:+.1f}%), 200DMA ${sma200:.2f} ({dist_200_pct:+.1f}%) | {pat_str}"
    )

    # Momentum calculations (RSI & MACD)
    rsi_s = compute_rsi(df["Close"], 14)
    rsi14 = float(rsi_s.iloc[-1])
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    sig_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = float((macd_line - sig_line).iloc[-1])
    macd_val = float(macd_line.iloc[-1])

    # RSI Bearish Divergence check
    rsi_div = (h2 >= h1 * 0.99) and (float(rsi_s.iloc[-min(15, len(rsi_s)) :].max()) < float(rsi_s.iloc[-min(45, len(rsi_s)) : -min(15, len(rsi_s))].max()) - 4.0) if len(rsi_s) > 30 else False
    mom_status = (
        f"RSI(14): {rsi14:.1f} "
        + ("[OVERSOLD <30 - Bounce Risk]" if rsi14 < 30 else "[Bearish Zone 32-52]" if 32 <= rsi14 <= 52 else "[Neutral/High]")
        + f" | MACD: {macd_val:.2f} (Hist {macd_hist:+.2f})"
        + (" | RSI Bearish Divergence Detected" if rsi_div else "")
    )

    metrics = {
        "ema20": round(ema20, 2),
        "sma50": round(sma50, 2),
        "sma200": round(sma200, 2),
        "support_20d": round(support_20d, 2),
        "support_60d": round(support_60d, 2),
        "swing_high_5d": round(swing_high_5d, 2),
        "dist_20_atr": round(dist_20_atr, 2),
        "support_broken": support_broken,
        "near_breakdown": near_breakdown,
        "topping_pattern": topping_pattern,
        "failed_breakout": failed_breakout,
        "overextended": overextended,
        "rsi14": round(rsi14, 1),
        "macd_hist": round(macd_hist, 3),
        "rsi_bearish_div": rsi_div,
    }
    return score, trend_status, mom_status, metrics


def _score_factor_b_rs(
    df: pd.DataFrame,
    spy_df: pd.DataFrame,
    sector_df: pd.DataFrame,
    sector_etf: str,
    tech_metrics: Dict[str, Any],
) -> Tuple[float, str, Dict[str, Any]]:
    """Factor B: Relative Weakness & Momentum (15% weight)."""
    close = df["Close"]
    ret_20d = ((float(close.iloc[-1]) / float(close.iloc[-min(21, len(close))])) - 1.0) * 100.0
    spy_ret_20d = (
        ((float(spy_df["Close"].iloc[-1]) / float(spy_df["Close"].iloc[-min(21, len(spy_df))])) - 1.0) * 100.0
        if not spy_df.empty
        else 0.0
    )
    sec_ret_20d = (
        ((float(sector_df["Close"].iloc[-1]) / float(sector_df["Close"].iloc[-min(21, len(sector_df))])) - 1.0) * 100.0
        if not sector_df.empty
        else spy_ret_20d
    )

    alpha_vs_spy = ret_20d - spy_ret_20d
    alpha_vs_sec = ret_20d - sec_ret_20d

    # Downside Beta Asymmetry (60D)
    aligned = pd.DataFrame({"stock": close.pct_change(), "spy": spy_df["Close"].pct_change()}).dropna().iloc[-60:]
    if len(aligned) >= 20:
        down_days = aligned[aligned["spy"] < 0]
        up_days = aligned[aligned["spy"] > 0]
        beta_down = (
            float((down_days["stock"].cov(down_days["spy"])) / max(1e-8, down_days["spy"].var()))
            if len(down_days) >= 5
            else 1.0
        )
        beta_up = (
            float((up_days["stock"].cov(up_days["spy"])) / max(1e-8, up_days["spy"].var()))
            if len(up_days) >= 5
            else 1.0
        )
        beta_asym = beta_down / max(0.25, abs(beta_up))
    else:
        beta_down, beta_up, beta_asym = 1.0, 1.0, 1.0

    # Leading new low vs SPY
    spy_above_20d_low = (
        float(spy_df["Close"].iloc[-1]) > float(spy_df["Low"].iloc[-min(20, len(spy_df)) :].min()) * 1.015
        if not spy_df.empty
        else False
    )
    new_low_ahead_of_spy = spy_above_20d_low and (
        float(close.iloc[-1]) <= float(df["Low"].iloc[-min(20, len(df)) :].min()) * 1.005
    )

    score = 0.0
    if alpha_vs_spy < -8.0:
        score += 28.0
    elif alpha_vs_spy < -3.0:
        score += 18.0
    elif alpha_vs_spy < 0.0:
        score += 10.0

    if alpha_vs_sec < -4.0:
        score += 17.0
    elif alpha_vs_sec < 0.0:
        score += 8.0

    if new_low_ahead_of_spy:
        score += 15.0

    if beta_down > 1.15 and beta_asym > 1.20:
        score += 20.0
    elif beta_down > 1.0:
        score += 10.0

    # Momentum contribution (RSI + MACD + Divergence)
    rsi14 = tech_metrics["rsi14"]
    if 30.0 <= rsi14 <= 50.0:
        score += 10.0
    if tech_metrics["macd_hist"] < 0:
        score += 10.0
    if tech_metrics["rsi_bearish_div"]:
        score += 10.0

    score = float(np.clip(score, 0.0, 100.0))
    status = (
        f"Score {score:.0f}/100 | 20D Rel vs SPY: {alpha_vs_spy:+.1f}%, vs {sector_etf}: {alpha_vs_sec:+.1f}% | "
        f"Downside Beta: {beta_down:.2f} (Asym {beta_asym:.2f}x)"
        + (" | Leading New Low vs SPY" if new_low_ahead_of_spy else "")
    )
    return score, status, {
        "ret_20d_pct": round(ret_20d, 2),
        "alpha_vs_spy_20d": round(alpha_vs_spy, 2),
        "alpha_vs_sector_20d": round(alpha_vs_sec, 2),
        "beta_down": round(beta_down, 2),
        "beta_asymmetry": round(beta_asym, 2),
        "new_low_ahead_of_spy": new_low_ahead_of_spy,
    }


def _score_factor_c_volume(df: pd.DataFrame) -> Tuple[float, str, Dict[str, Any]]:
    """Factor C: Volume & Institutional Distribution (15% weight)."""
    vol = df["Volume"]
    close = df["Close"]
    vol_ma20 = float(vol.rolling(20, min_periods=5).mean().iloc[-1])
    rel_vol_today = float(vol.iloc[-1]) / max(1.0, vol_ma20)

    sub20 = df.iloc[-min(20, len(df)) :].copy()
    rets = sub20["Close"].pct_change()
    down_vols = sub20.loc[rets < 0, "Volume"]
    up_vols = sub20.loc[rets > 0, "Volume"]
    avg_down_vol = float(down_vols.mean()) if not down_vols.empty else vol_ma20
    avg_up_vol = float(up_vols.mean()) if not up_vols.empty else vol_ma20
    ud_vol_ratio = avg_down_vol / max(1.0, avg_up_vol)

    dist_days_25d = _calc_distribution_days(df, window=25, drop_thresh=-0.01)

    # 20D Chaikin Money Flow (CMF)
    hl_range = (df["High"] - df["Low"]).replace(0, np.nan)
    mfm = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / hl_range
    mfv = mfm.fillna(0.0) * df["Volume"]
    cmf20 = float(mfv.iloc[-20:].sum() / max(1.0, float(df["Volume"].iloc[-20:].sum())))

    score = 0.0
    if ud_vol_ratio >= 1.35:
        score += 38.0
    elif ud_vol_ratio >= 1.10:
        score += 24.0
    elif ud_vol_ratio >= 0.95:
        score += 10.0

    score += min(37.0, dist_days_25d * 7.5)
    if cmf20 < -0.12:
        score += 25.0
    elif cmf20 < -0.03:
        score += 14.0

    score = float(np.clip(score, 0.0, 100.0))
    status = (
        f"Score {score:.0f}/100 | 25D Distribution Days: {dist_days_25d} | "
        f"Down/Up Vol Ratio: {ud_vol_ratio:.2f}x | RelVol Today: {rel_vol_today:.2f}x | CMF(20): {cmf20:+.2f}"
    )
    return score, status, {
        "vol_ma20": round(vol_ma20, 0),
        "rel_vol_today": round(rel_vol_today, 2),
        "down_up_vol_ratio": round(ud_vol_ratio, 2),
        "dist_days_25d": dist_days_25d,
        "cmf20": round(cmf20, 3),
    }


def _score_factor_d_fundamental_catalyst(
    tdata: TickerMarketData,
) -> Tuple[float, float, str, bool]:
    """Factor D: Fundamental & Catalyst Risk (25% weight) + CATALYST_RISK_SCORE."""
    fund_pts = 0.0
    avail_checks = 0
    notes = []

    if tdata.revenue_growth_yoy is not None:
        avail_checks += 1
        rg = tdata.revenue_growth_yoy * 100.0
        if rg < 0:
            fund_pts += 25.0
            notes.append(f"Rev contraction ({rg:+.1f}% YoY)")
        elif rg < 8.0:
            fund_pts += 14.0
            notes.append(f"Slow Rev growth ({rg:+.1f}% YoY)")
        else:
            notes.append(f"Rev growth {rg:+.1f}% YoY")
    else:
        notes.append(f"Rev Growth: {DATA_UNAVAILABLE}")

    if tdata.operating_margin is not None:
        avail_checks += 1
        om = tdata.operating_margin * 100.0
        if om < 0:
            fund_pts += 25.0
            notes.append(f"Negative OpMargin ({om:.1f}%)")
        elif om < 8.0:
            fund_pts += 12.0
            notes.append(f"Thin OpMargin ({om:.1f}%)")
        else:
            notes.append(f"OpMargin {om:.1f}%")
    else:
        notes.append(f"OpMargin: {DATA_UNAVAILABLE}")

    if tdata.free_cash_flow is not None:
        avail_checks += 1
        if tdata.free_cash_flow < 0:
            fund_pts += 22.0
            notes.append("Negative FCF (Cash Burn)")
        else:
            notes.append("FCF Positive")
    else:
        notes.append(f"FCF: {DATA_UNAVAILABLE}")

    # Valuation check
    val_mult = tdata.enterprise_to_revenue or tdata.price_to_sales
    if val_mult is not None or tdata.forward_pe is not None:
        avail_checks += 1
        if (val_mult is not None and val_mult > 12.0) or (tdata.forward_pe is not None and tdata.forward_pe > 45.0):
            fund_pts += 20.0
            notes.append(
                f"Stretched Valuation (EV/Rev {val_mult:.1f}x)" if val_mult else f"High Fwd P/E ({tdata.forward_pe:.1f}x)"
            )
        elif val_mult is not None and val_mult > 6.0:
            fund_pts += 10.0

    # Catalyst Risk Score (0-100)
    catalyst_score = 25.0
    earnings_red_warning = False
    if tdata.days_to_earnings is not None:
        if tdata.days_to_earnings <= 3:
            earnings_red_warning = True
            catalyst_score = 95.0
            notes.append(f"RED WARNING: EARNINGS IN {tdata.days_to_earnings} DAYS ({tdata.next_earnings_date})")
        elif tdata.days_to_earnings <= 7:
            catalyst_score = 65.0
            notes.append(f"Earnings approaching in {tdata.days_to_earnings}d ({tdata.next_earnings_date})")
        else:
            notes.append(f"Next Earnings in {tdata.days_to_earnings}d")
    else:
        notes.append(f"Earnings Calendar: {DATA_UNAVAILABLE}")

    if tdata.dilution_offering_flag:
        catalyst_score = min(100.0, catalyst_score + 30.0)
        fund_pts += 15.0
        notes.append("Dilution/Shelf Offering Active")
    if tdata.insider_net_selling_flag:
        catalyst_score = min(100.0, catalyst_score + 20.0)
        fund_pts += 10.0
        notes.append("Insider Cluster Selling")

    if avail_checks == 0:
        composite = 35.0  # Conservative neutral-low when fundamentals are unavailable
        status = f"Score {composite:.0f}/100 ({INSUFFICIENT_DATA}) | " + " | ".join(notes)
    else:
        norm_fund = min(100.0, fund_pts * (4.0 / max(1, avail_checks)))
        composite = float(np.clip(0.75 * norm_fund + 0.25 * min(70.0, catalyst_score), 0.0, 100.0))
        status = f"Score {composite:.0f}/100 (Catalyst Risk: {catalyst_score:.0f}/100) | " + " | ".join(notes)

    return round(composite, 1), round(catalyst_score, 1), status, earnings_red_warning


def _score_factor_e_squeeze_and_options(
    tdata: TickerMarketData,
    df: pd.DataFrame,
    tech_metrics: Dict[str, Any],
) -> Tuple[float, float, str, bool]:
    """Factor E: Short Squeeze & Options Risk (20% weight) + independent SQUEEZE_RISK_SCORE."""
    notes = []

    # 1. Calculate SQUEEZE_RISK_SCORE (0-100, higher = MORE DANGEROUS to short)
    si_pct = tdata.short_pct_float * 100.0 if tdata.short_pct_float is not None else None
    if si_pct is not None and si_pct > 100.0:
        # Handle cases where provider already scaled by 100
        si_pct = tdata.short_pct_float

    if si_pct is not None:
        if si_pct >= 25.0:
            si_sub = 95.0
        elif si_pct >= 18.0:
            si_sub = 75.0
        elif si_pct >= 10.0:
            si_sub = 45.0
        else:
            si_sub = 15.0
        notes.append(f"SI Float: {si_pct:.1f}%")
    else:
        si_sub = 35.0
        notes.append(f"SI% Float: {DATA_UNAVAILABLE}")

    if tdata.days_to_cover is not None:
        dtc = tdata.days_to_cover
        dtc_sub = min(100.0, max(10.0, dtc * 12.5))
        notes.append(f"Days to Cover: {dtc:.1f}d")
    else:
        dtc_sub = 30.0
        notes.append(f"DTC: {DATA_UNAVAILABLE}")

    if tdata.borrow_fee_rate_pct is not None:
        bf = tdata.borrow_fee_rate_pct
        bf_sub = 95.0 if bf >= 15.0 else (70.0 if bf >= 5.0 else (40.0 if bf >= 2.0 else 10.0))
        notes.append(f"Borrow Fee: {bf:.2f}%")
    else:
        bf_sub = 25.0
        notes.append(f"Borrow Fee: {DATA_UNAVAILABLE}")

    # Price upward thrust check (breakout above 20EMA or +6% surge in 3 days)
    ret_3d = ((float(df["Close"].iloc[-1]) / float(df["Close"].iloc[-min(4, len(df))])) - 1.0) * 100.0
    price_above_20ema = float(df["Close"].iloc[-1]) > tech_metrics["ema20"]
    thrust_sub = 85.0 if (ret_3d > 6.0 and price_above_20ema) else (45.0 if price_above_20ema else 10.0)

    squeeze_risk_score = float(np.clip(0.38 * si_sub + 0.25 * dtc_sub + 0.22 * bf_sub + 0.15 * thrust_sub, 0.0, 100.0))
    squeeze_warning = (
        squeeze_risk_score >= 62.0
        or ((si_pct or 0.0) >= 20.0 and price_above_20ema)
        or ((tdata.borrow_fee_rate_pct or 0.0) >= 12.0)
    )

    # 2. Derivatives Bearish Flow Score (0-100, higher = stronger bearish options flow & safe to short)
    deriv_score = 45.0
    if tdata.put_call_vol_ratio is not None:
        pcr = tdata.put_call_vol_ratio
        notes.append(f"Opt P/C Vol: {pcr:.2f}")
        if pcr >= 1.30:
            deriv_score += 25.0
        elif pcr >= 1.00:
            deriv_score += 12.0
        elif pcr < 0.65:
            deriv_score -= 10.0
    else:
        notes.append(f"Opt P/C Ratio: {DATA_UNAVAILABLE}")

    if tdata.unusual_otm_put_flag:
        deriv_score += 18.0
        notes.append("Unusual OTM Put Buying")
    if tdata.unusual_call_selling_flag:
        deriv_score += 12.0
        notes.append("Heavy ATM Call Supply")

    if tdata.gamma_exposure_regime is not None:
        notes.append(f"GEX: {tdata.gamma_exposure_regime}")
    else:
        notes.append(f"GEX: {DATA_UNAVAILABLE}")

    # Penalize Factor E heavily if Squeeze Risk is elevated
    if squeeze_warning:
        deriv_score = max(5.0, deriv_score - 35.0)
        notes.append("[SQUEEZE WARNING ACTIVE]")

    deriv_score = float(np.clip(deriv_score, 0.0, 100.0))
    status = (
        f"Squeeze Risk {squeeze_risk_score:.0f}/100 "
        + ("[HIGH SQUEEZE DANGER]" if squeeze_warning else "[Controlled]")
        + f" | Options Bearish Score {deriv_score:.0f}/100 | "
        + " | ".join(notes)
    )
    return round(deriv_score, 1), round(squeeze_risk_score, 1), status, squeeze_warning


def assign_rating(short_score: float, squeeze_warning: bool, earnings_red_warning: bool) -> SignalRating:
    if squeeze_warning and short_score < 78:
        return SignalRating.C if short_score >= 50 else SignalRating.D
    if short_score >= 82.0 and not squeeze_warning and not earnings_red_warning:
        return SignalRating.A_PLUS
    if short_score >= 70.0 and not squeeze_warning:
        return SignalRating.A
    if short_score >= 56.0:
        return SignalRating.B
    if short_score >= 40.0:
        return SignalRating.C
    return SignalRating.D
