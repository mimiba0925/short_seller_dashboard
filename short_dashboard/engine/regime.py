from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .data_provider import BREADTH_BASKET_TICKERS, SECTOR_ETF_MAP, MarketDataProvider
from .models import (
    DATA_UNAVAILABLE,
    BreadthMetrics,
    IndexSnapshot,
    MarketRegimeReport,
    VolatilityMetrics,
)


def _calc_distribution_days(df: pd.DataFrame, window: int = 25, drop_thresh: float = -0.002) -> int:
    if len(df) < window + 2:
        return 0
    sub = df.iloc[-(window + 1) :].copy()
    ret = sub["Close"].pct_change()
    vol_up = sub["Volume"] > sub["Volume"].shift(1)
    vol_ma = sub["Volume"].rolling(20, min_periods=5).mean()
    above_avg_vol = sub["Volume"] >= vol_ma * 0.95
    dist = (ret <= drop_thresh) & (vol_up | above_avg_vol)
    return int(dist.iloc[1:].sum())


def _eval_index(ticker: str, df: pd.DataFrame) -> IndexSnapshot:
    close = float(df["Close"].iloc[-1])
    ema20_series = df["Close"].ewm(span=20, adjust=False).mean()
    sma50_series = df["Close"].rolling(50, min_periods=15).mean()
    sma200_series = df["Close"].rolling(200, min_periods=30).mean()

    ema20 = float(ema20_series.iloc[-1])
    sma50 = float(sma50_series.iloc[-1])
    sma200 = float(sma200_series.iloc[-1])

    ema20_prev = float(ema20_series.iloc[-6]) if len(ema20_series) >= 6 else ema20
    sma50_prev = float(sma50_series.iloc[-11]) if len(sma50_series) >= 11 else sma50
    ema20_slope_pct = ((ema20 / ema20_prev) - 1.0) * 100.0 if ema20_prev else 0.0
    sma50_slope_pct = ((sma50 / sma50_prev) - 1.0) * 100.0 if sma50_prev else 0.0

    ret_5d = ((close / float(df["Close"].iloc[-6])) - 1.0) * 100.0 if len(df) >= 6 else 0.0
    ret_20d = ((close / float(df["Close"].iloc[-21])) - 1.0) * 100.0 if len(df) >= 21 else 0.0
    dist_days = _calc_distribution_days(df, window=25, drop_thresh=-0.002)

    below_ema20 = close < ema20
    below_sma50 = close < sma50
    below_sma200 = close < sma200

    # Index Bearish Sub-score (0-100)
    score = 0.0
    if below_ema20:
        score += 22.0
    elif close < ema20 * 1.008:
        score += 10.0
    if ema20_slope_pct < 0:
        score += 10.0

    if below_sma50:
        score += 22.0
    if sma50_slope_pct < 0:
        score += 10.0

    if below_sma200:
        score += 11.0

    # Distribution days contribution (up to 25 pts)
    score += min(25.0, dist_days * 5.0)
    score = float(np.clip(score, 0.0, 100.0))

    return IndexSnapshot(
        ticker=ticker,
        close=round(close, 2),
        ema20=round(ema20, 2),
        sma50=round(sma50, 2),
        sma200=round(sma200, 2),
        ema20_slope_pct=round(ema20_slope_pct, 2),
        sma50_slope_pct=round(sma50_slope_pct, 2),
        dist_days_25d=dist_days,
        ret_5d_pct=round(ret_5d, 2),
        ret_20d_pct=round(ret_20d, 2),
        below_ema20=below_ema20,
        below_sma50=below_sma50,
        below_sma200=below_sma200,
        sub_score=round(score, 1),
    )


def compute_breadth_metrics(
    provider: MarketDataProvider,
    spy_snap: IndexSnapshot,
    custom_tickers: List[str] | None = None,
) -> BreadthMetrics:
    basket = list(dict.fromkeys((custom_tickers or []) + BREADTH_BASKET_TICKERS[:35]))
    batch = provider.fetch_ohlcv_batch(basket, period="1y")

    above_50 = 0
    above_200 = 0
    new_highs = 0
    new_lows = 0
    adv_10d = 0
    dec_10d = 0
    valid = 0

    for _, df in batch.items():
        if df is None or len(df) < 55:
            continue
        valid += 1
        c = float(df["Close"].iloc[-1])
        s50 = float(df["Close"].rolling(50, min_periods=20).mean().iloc[-1])
        s200 = float(df["Close"].rolling(200, min_periods=40).mean().iloc[-1])
        if c > s50:
            above_50 += 1
        if c > s200:
            above_200 += 1

        hi_252 = float(df["High"].iloc[-min(252, len(df)) :].max())
        lo_252 = float(df["Low"].iloc[-min(252, len(df)) :].min())
        if c >= hi_252 * 0.985:
            new_highs += 1
        if c <= lo_252 * 1.02:
            new_lows += 1

        diffs = df["Close"].diff().iloc[-10:]
        adv_10d += int((diffs > 0).sum())
        dec_10d += int((diffs < 0).sum())

    if valid == 0:
        return BreadthMetrics(
            pct_above_50ma=50.0,
            pct_above_200ma=50.0,
            net_new_highs_lows_pct=0.0,
            adv_dec_10d_ratio=1.0,
            breadth_divergence=False,
            breadth_weakness_score=50.0,
            summary=DATA_UNAVAILABLE,
            source_note="Insufficient constituent history",
        )

    pct_50 = (above_50 / valid) * 100.0
    pct_200 = (above_200 / valid) * 100.0
    nh_nl_pct = ((new_highs - new_lows) / valid) * 100.0
    ad_ratio = adv_10d / max(1, dec_10d)

    # Sub-scores for Breadth Weakness (0-100, higher = weaker breadth = better for shorts)
    b50_score = np.clip(100.0 - pct_50, 0.0, 100.0)
    b200_score = np.clip(100.0 - pct_200, 0.0, 100.0)
    # Net New Highs/Lows: if net negative, >50 score
    nhnl_score = np.clip(50.0 - nh_nl_pct * 1.8, 0.0, 100.0)
    ad_score = np.clip((1.15 - ad_ratio) * 90.0, 0.0, 100.0)

    divergence = (not spy_snap.below_sma50) and (pct_50 < 48.0)
    raw_score = 0.32 * b50_score + 0.23 * b200_score + 0.25 * nhnl_score + 0.20 * ad_score
    if divergence:
        raw_score = min(100.0, raw_score + 10.0)

    weakness_score = round(float(raw_score), 1)
    summary = (
        f"Breadth Weakness {weakness_score}/100 | >50MA: {pct_50:.1f}%, >200MA: {pct_200:.1f}%, "
        f"Net NH-NL: {nh_nl_pct:+.1f}%, 10D A/D: {ad_ratio:.2f}"
        + (" [BREADTH DIVERGENCE WARNING]" if divergence else "")
    )
    return BreadthMetrics(
        pct_above_50ma=round(pct_50, 1),
        pct_above_200ma=round(pct_200, 1),
        net_new_highs_lows_pct=round(nh_nl_pct, 1),
        adv_dec_10d_ratio=round(ad_ratio, 2),
        breadth_divergence=divergence,
        breadth_weakness_score=weakness_score,
        summary=summary,
        source_note=f"Computed across {valid}-stock S&P/Nasdaq leader basket",
    )


def compute_volatility_metrics(provider: MarketDataProvider) -> VolatilityMetrics:
    batch = provider.fetch_ohlcv_batch(["^VIX", "^VIX3M", "SPY"], period="1y")
    vix_df = batch.get("^VIX", pd.DataFrame())
    vix3m_df = batch.get("^VIX3M", pd.DataFrame())

    if vix_df.empty:
        vix = 18.5
        vix_5d_roc = 0.0
        climax = False
    else:
        vix = float(vix_df["Close"].iloc[-1])
        vix_prev5 = float(vix_df["Close"].iloc[-6]) if len(vix_df) >= 6 else vix
        vix_5d_roc = ((vix / vix_prev5) - 1.0) * 100.0 if vix_prev5 > 0 else 0.0
        hi_today = float(vix_df["High"].iloc[-1])
        climax = (vix > 35.0) and (hi_today > vix * 1.08)

    if vix3m_df.empty:
        vix3m = max(16.0, vix * 1.04)
    else:
        vix3m = float(vix3m_df["Close"].iloc[-1])

    term_ratio = vix / vix3m if vix3m > 0 else 0.92
    inverted = term_ratio >= 1.00

    # Derive SPY Option Put/Call Ratio if available
    spy_data = provider.get_ticker_data("SPY")
    eq_pcr = spy_data.put_call_vol_ratio
    if eq_pcr is not None:
        pcr_status = f"SPY P/C Ratio: {eq_pcr:.2f} (" + (
            "Bearish Hedging Active" if eq_pcr >= 1.05 else "Neutral/Balanced"
        ) + ")"
        pcr_sub = np.clip((eq_pcr - 0.75) * 110.0, 0.0, 100.0)
    else:
        pcr_status = f"Equity Put/Call Ratio: {DATA_UNAVAILABLE}"
        pcr_sub = 45.0

    # VIX level & RoC sub-score (0-100)
    vix_lvl_score = np.clip((vix - 12.5) * 4.5, 0.0, 75.0)
    if vix_5d_roc > 15.0:
        vix_lvl_score = min(100.0, vix_lvl_score + 25.0)
    elif vix_5d_roc > 7.5:
        vix_lvl_score = min(100.0, vix_lvl_score + 12.0)

    # Term structure sub-score (0-100)
    if inverted:
        ts_score = min(100.0, 82.0 + (term_ratio - 1.0) * 180.0)
    elif term_ratio >= 0.92:
        ts_score = 45.0 + (term_ratio - 0.92) * 400.0
    else:
        ts_score = max(5.0, (term_ratio - 0.80) * 300.0)

    vol_score = round(float(0.38 * vix_lvl_score + 0.42 * ts_score + 0.20 * pcr_sub), 1)
    summary = (
        f"Vol Score {vol_score}/100 | VIX: {vix:.2f} (5D {vix_5d_roc:+.1f}%), "
        f"VIX/VIX3M: {term_ratio:.2f} "
        + ("[BACKWARDATION / INVERTED]" if inverted else "[CONTANGO]")
        + (" [VOL CLIMAX]" if climax else "")
    )
    return VolatilityMetrics(
        vix=round(vix, 2),
        vix_5d_roc_pct=round(vix_5d_roc, 2),
        vix3m=round(vix3m, 2),
        vix_term_ratio=round(term_ratio, 3),
        term_structure_inverted=inverted,
        volatility_climax_warning=climax,
        equity_put_call_ratio=eq_pcr,
        put_call_status=pcr_status,
        volatility_regime_score=vol_score,
        summary=summary,
    )


def compute_market_regime(
    provider: MarketDataProvider,
    watchlist: List[str] | None = None,
) -> MarketRegimeReport:
    sector_etfs = sorted(set(SECTOR_ETF_MAP.values()))
    all_idx = ["SPY", "QQQ", "IWM"] + sector_etfs
    batch = provider.fetch_ohlcv_batch(all_idx, period="1y")

    indices: Dict[str, IndexSnapshot] = {}
    for idx_t in ["SPY", "QQQ", "IWM"]:
        df = batch.get(idx_t)
        if df is not None and not df.empty:
            indices[idx_t] = _eval_index(idx_t, df)

    spy_snap = indices["SPY"]
    qqq_snap = indices["QQQ"]
    iwm_snap = indices["IWM"]

    breadth = compute_breadth_metrics(provider, spy_snap, custom_tickers=watchlist)
    vol = compute_volatility_metrics(provider)

    # Composite Market Regime Score (0-100)
    idx_composite = (
        0.40 * spy_snap.sub_score
        + 0.35 * qqq_snap.sub_score
        + 0.25 * iwm_snap.sub_score
    )
    regime_score = (
        0.50 * idx_composite
        + 0.25 * breadth.breadth_weakness_score
        + 0.25 * vol.volatility_regime_score
    )
    if vol.term_structure_inverted:
        regime_score = min(100.0, regime_score + 7.5)
    regime_score = round(float(np.clip(regime_score, 0.0, 100.0)), 1)

    if regime_score <= 40.0:
        regime_label = "RISK-ON (Bullish Tape / Short Filter Closed)"
        policy = (
            "BLOCK NEW SPECULATIVE SHORTS. Max gross short <= 15% (hedge only). "
            + ("MANDATORY 50% SHORT REDUCTION ACTIVE (Score < 30)." if regime_score < 30.0 else "Tighten stops on existing shorts.")
        )
        max_exp = 15.0
        sizing_mult = 0.0
        de_gross = regime_score < 35.0
    elif regime_score <= 60.0:
        regime_label = "NEUTRAL (Selective Dispersion / Watch Mode)"
        policy = (
            "SELECTIVE SHORTING ONLY (Rating A+ / Relative Weakness leaders). "
            "Position sizing reduced to 0.50x standard risk. Max gross short <= 45%."
        )
        max_exp = 45.0
        sizing_mult = 0.55
        de_gross = False
    else:
        regime_label = "RISK-OFF (Bearish Regime / Active Short Window)"
        policy = (
            "SHORT BOOK OPEN for A+ and A rated setups. Full 1.0x risk sizing allowed. "
            "Pyramiding (ADD) enabled on Lower High confirmation if score > 70."
        )
        max_exp = 100.0
        sizing_mult = 1.0
        de_gross = False

    # Rank sector ETFs by relative weakness vs SPY
    sector_rankings: List[Dict[str, Any]] = []
    for etf in sector_etfs:
        df = batch.get(etf)
        if df is None or len(df) < 25:
            continue
        snap = _eval_index(etf, df)
        rs_20d = snap.ret_20d_pct - spy_snap.ret_20d_pct
        sector_rankings.append(
            {
                "etf": etf,
                "close": snap.close,
                "ret_5d_pct": snap.ret_5d_pct,
                "ret_20d_pct": snap.ret_20d_pct,
                "rs_vs_spy_20d_pct": round(rs_20d, 2),
                "below_ema20": snap.below_ema20,
                "below_sma50": snap.below_sma50,
                "dist_days_25d": snap.dist_days_25d,
                "weakness_score": round(snap.sub_score - rs_20d * 2.2, 1),
            }
        )
    sector_rankings.sort(key=lambda x: x["weakness_score"], reverse=True)

    return MarketRegimeReport(
        as_of=dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        market_regime_score=regime_score,
        regime_label=regime_label,
        short_book_policy=policy,
        max_gross_short_exposure_pct=max_exp,
        regime_sizing_multiplier=sizing_mult,
        mandatory_de_gross=de_gross,
        indices=indices,
        breadth=breadth,
        volatility=vol,
        sector_weakness_ranking=sector_rankings,
    )
