from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .data_provider import MarketDataProvider
from .models import ExecutionAction, SignalRating, StockShortEvaluation
from .screener import compute_rsi


@dataclass
class PortfolioRiskSummary:
    account_size: float
    total_short_notional: float
    gross_short_exposure_pct: float
    beta_adjusted_short_exposure_pct: float
    nominal_positions_count: int
    effective_independent_bets: float
    avg_pairwise_correlation: float
    correlated_short_risk_score: float
    correlation_clusters: List[Dict[str, Any]]
    sector_exposures: Dict[str, float]
    correlation_matrix: Dict[str, Dict[str, float]]
    risk_warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_portfolio_risk(
    evaluations: List[StockShortEvaluation],
    provider: MarketDataProvider,
    account_size: float = 100_000.0,
) -> PortfolioRiskSummary:
    """Computes Portfolio-Level Short Exposure and CORRELATED_SHORT_RISK across active/candidate shorts."""
    active_or_actionable = [
        ev
        for ev in evaluations
        if ev.execution.raw_state
        in {
            ExecutionAction.ENTRY,
            ExecutionAction.SHORT_SETUP,
            ExecutionAction.HOLD,
            ExecutionAction.ADD,
        }
        or ev.rating in {SignalRating.A_PLUS, SignalRating.A}
    ]
    if len(active_or_actionable) < 2:
        active_or_actionable = evaluations[: min(6, len(evaluations))]

    tickers = [ev.ticker for ev in active_or_actionable]
    ret_dict: Dict[str, pd.Series] = {}
    for t in tickers:
        df = provider.get_ohlcv(t)
        if not df.empty:
            ret_dict[t] = df["Close"].pct_change().dropna().iloc[-60:]

    ret_df = pd.DataFrame(ret_dict).dropna(how="all")
    if len(ret_df.columns) >= 2 and len(ret_df) >= 10:
        corr_df = ret_df.corr().fillna(0.0)
    else:
        corr_df = pd.DataFrame(np.eye(len(tickers)), index=tickers, columns=tickers)

    n = len(corr_df.columns)
    if n >= 2:
        vals = corr_df.values
        upper_tri = vals[np.triu_indices(n, k=1)]
        avg_corr = float(np.mean(upper_tri)) if len(upper_tri) > 0 else 0.0
        pos_corr_sum = float(np.sum(np.maximum(0.0, vals)))
        n_eff = (n * n) / max(1.0, pos_corr_sum)
    else:
        avg_corr = 0.0
        n_eff = float(n)

    clusters: List[Dict[str, Any]] = []
    cols = list(corr_df.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            rho = float(corr_df.iloc[i, j])
            if rho >= 0.65:
                clusters.append(
                    {
                        "pair": f"{cols[i]} / {cols[j]}",
                        "correlation_60d": round(rho, 2),
                        "warning": "高度共線性同溫層集群（齊漲齊跌風險高）" if rho >= 0.75 else "中度相關集群",
                    }
                )
    clusters.sort(key=lambda x: x["correlation_60d"], reverse=True)

    sector_notional: Dict[str, float] = {}
    total_notional = 0.0
    weighted_beta_notional = 0.0
    for ev in active_or_actionable:
        notional = ev.execution.suggested_notional or (account_size * 0.06)
        total_notional += notional
        sector_notional[ev.sector] = sector_notional.get(ev.sector, 0.0) + notional
        beta_d = float(ev.raw_metrics.get("beta_down", 1.1))
        weighted_beta_notional += notional * beta_d

    gross_exp_pct = (total_notional / account_size) * 100.0
    beta_exp_pct = (weighted_beta_notional / account_size) * 100.0
    sector_exp_pct = {k: round((v / account_size) * 100.0, 1) for k, v in sector_notional.items()}

    # Correlated Short Risk Score (0-100: ⚠️ 分數越高代表組合共線性風險越高，越容易被同步軋空，不利空方組合)
    max_sec_pct = max(sector_exp_pct.values()) if sector_exp_pct else 0.0
    diversity_loss = 1.0 - (n_eff / max(1.0, float(n)))
    corr_risk_score = float(
        np.clip(
            45.0 * max(0.0, avg_corr)
            + 35.0 * diversity_loss
            + (25.0 if max_sec_pct > 25.0 else max_sec_pct * 0.6),
            0.0,
            100.0,
        )
    )

    warnings: List[str] = []
    if n >= 3 and n_eff < n * 0.55:
        warnings.append(
            f"組合共線性警告 (CORRELATED SHORT RISK)：名目上 {n} 檔空方候選股，實際僅相當於 {n_eff:.2f} 筆獨立部位（60D 平均相關係數 {avg_corr:.2f}），切勿視為獨立風險重複重倉！"
        )
    for sec, pct in sector_exp_pct.items():
        if pct > 25.0:
            warnings.append(
                f"單一板塊集中度超標：{sec} 板塊空頭曝險達 {pct:.1f}%（風控上限 25.0%），請避免同時堆疊同產業空單。"
            )
    if clusters:
        top_c = clusters[0]
        warnings.append(
            f"最高共線性股票對：{top_c['pair']} (60D 相關係數 ρ = {top_c['correlation_60d']:.2f}) — 系統已自動啟動部位縮減折價。"
        )

    corr_dict = {
        r: {c: round(float(corr_df.loc[r, c]), 2) for c in corr_df.columns}
        for r in corr_df.index
    }

    return PortfolioRiskSummary(
        account_size=account_size,
        total_short_notional=round(total_notional, 2),
        gross_short_exposure_pct=round(gross_exp_pct, 1),
        beta_adjusted_short_exposure_pct=round(beta_exp_pct, 1),
        nominal_positions_count=n,
        effective_independent_bets=round(n_eff, 2),
        avg_pairwise_correlation=round(avg_corr, 2),
        correlated_short_risk_score=round(corr_risk_score, 1),
        correlation_clusters=clusters[:8],
        sector_exposures=sector_exp_pct,
        correlation_matrix=corr_dict,
        risk_warnings=warnings,
    )


def run_walk_forward_backtest(
    tickers: List[str],
    provider: MarketDataProvider,
    slippage_bps: float = 10.0,
    assumed_borrow_fee_annual_pct: float = 2.0,
) -> Dict[str, Any]:
    trades: List[Dict[str, Any]] = []

    for ticker in tickers:
        df = provider.get_ohlcv(ticker)
        if df is None or len(df) < 80:
            continue

        close = df["Close"]
        open_s = df["Open"]
        high_s = df["High"]
        low_s = df["Low"]
        vol_s = df["Volume"]

        ema20 = close.ewm(span=20, adjust=False).mean()
        sma50 = close.rolling(50, min_periods=20).mean()
        vol_ma20 = vol_s.rolling(20, min_periods=10).mean()
        rsi14 = compute_rsi(close, 14)

        prev_c = close.shift(1)
        tr = pd.concat(
            [(high_s - low_s).abs(), (high_s - prev_c).abs(), (low_s - prev_c).abs()],
            axis=1,
        ).max(axis=1)
        atr14 = tr.rolling(14, min_periods=5).mean()
        support20 = low_s.shift(1).rolling(20, min_periods=10).min()

        cooldown_until = -1
        for t in range(55, len(df) - 2):
            if t < cooldown_until:
                continue

            c_t = float(close.iloc[t])
            e20_t = float(ema20.iloc[t])
            s50_t = float(sma50.iloc[t])
            sup_t = float(support20.iloc[t])
            atr_t = max(0.05, float(atr14.iloc[t]))
            rsi_t = float(rsi14.iloc[t])
            v_t = float(vol_s.iloc[t])
            vma_t = max(1.0, float(vol_ma20.iloc[t]))

            score_t = 0.0
            if c_t < e20_t:
                score_t += 22.0
            if e20_t < float(ema20.iloc[t - 5]):
                score_t += 12.0
            if c_t < s50_t:
                score_t += 22.0
            if c_t < sup_t:
                score_t += 22.0
            if v_t >= 1.25 * vma_t and c_t < float(close.iloc[t - 1]):
                score_t += 12.0
            if 32.0 <= rsi_t <= 52.0:
                score_t += 10.0

            breakdown_trig = (c_t < sup_t) and (v_t >= 1.25 * vma_t) and (rsi_t >= 30.0)
            failed_bounce_trig = (
                (c_t < s50_t)
                and (float(high_s.iloc[t]) >= e20_t - 0.3 * atr_t)
                and (c_t < e20_t)
                and (c_t < float(open_s.iloc[t]))
                and (rsi_t >= 32.0)
            )

            if not (breakdown_trig or failed_bounce_trig):
                continue

            grade = (
                "A+"
                if score_t >= 84
                else ("A" if score_t >= 72 else ("B" if score_t >= 58 else "C"))
            )

            raw_entry = float(open_s.iloc[t + 1])
            slip_factor = slippage_bps / 10_000.0
            entry_px = raw_entry * (1.0 - slip_factor)
            risk_per_sh = 1.75 * atr_t
            stop_px = entry_px + risk_per_sh
            target_px = entry_px - 2.0 * risk_per_sh

            exit_px = float(close.iloc[min(len(df) - 1, t + 12)])
            exit_idx = min(len(df) - 1, t + 12)
            exit_reason = "時間停損出場 (12日)"

            for k in range(t + 1, min(len(df), t + 13)):
                hi_k = float(high_s.iloc[k])
                lo_k = float(low_s.iloc[k])
                cl_k = float(close.iloc[k])
                if hi_k >= stop_px:
                    exit_px = stop_px * (1.0 + slip_factor)
                    exit_idx = k
                    exit_reason = "觸發 ATR 動態停損"
                    break
                if lo_k <= target_px:
                    exit_px = target_px * (1.0 + slip_factor)
                    exit_idx = k
                    exit_reason = "達標 +2.0R 停利"
                    break
                if k > t + 2 and cl_k > float(ema20.iloc[k]) and cl_k > float(sma50.iloc[k]):
                    exit_px = cl_k * (1.0 + slip_factor)
                    exit_idx = k
                    exit_reason = "重新站回均線平倉"
                    break

            hold_days = max(1, exit_idx - (t + 1) + 1)
            borrow_cost_pct = (assumed_borrow_fee_annual_pct / 252.0) * hold_days
            gross_ret_pct = ((entry_px - exit_px) / entry_px) * 100.0
            net_ret_pct = gross_ret_pct - borrow_cost_pct
            r_mult = ((entry_px - exit_px) / risk_per_sh) - (
                (borrow_cost_pct / 100.0 * entry_px) / risk_per_sh
            )

            trades.append(
                {
                    "ticker": ticker,
                    "signal_date": str(df.index[t].date()),
                    "entry_date": str(df.index[t + 1].date()),
                    "exit_date": str(df.index[exit_idx].date()),
                    "grade": grade,
                    "score": round(score_t, 1),
                    "trigger_type": "帶量破支撐" if breakdown_trig else "20EMA反抽受阻",
                    "entry_price": round(entry_px, 2),
                    "exit_price": round(exit_px, 2),
                    "holding_days": hold_days,
                    "net_return_pct": round(net_ret_pct, 2),
                    "r_multiple": round(r_mult, 2),
                    "exit_reason": exit_reason,
                    "actionable_grade": grade in {"A+", "A"},
                }
            )
            cooldown_until = exit_idx + 2

    trades.sort(key=lambda x: x["entry_date"], reverse=True)

    def _summarize_subset(sub: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not sub:
            return {
                "trades_count": 0,
                "win_rate_pct": 0.0,
                "avg_r_multiple": 0.0,
                "profit_factor": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown_pct": 0.0,
            }
        rets = np.array([x["net_return_pct"] for x in sub], dtype=float)
        rs = np.array([x["r_multiple"] for x in sub], dtype=float)
        wins = rets[rets > 0]
        losses = rets[rets <= 0]
        win_rate = float(len(wins) / len(rets) * 100.0)
        pf = float(wins.sum() / abs(losses.sum())) if len(losses) > 0 and losses.sum() != 0 else (9.99 if len(wins) > 0 else 0.0)
        std_r = float(np.std(rets)) if len(rets) > 1 else 1.0
        sharpe = float((np.mean(rets) / max(0.01, std_r)) * np.sqrt(min(50, len(rets))))

        eq = np.cumprod(1.0 + (rs * 0.0075))
        peak = np.maximum.accumulate(eq)
        dd = ((eq - peak) / peak) * 100.0
        max_dd = float(abs(dd.min())) if len(dd) > 0 else 0.0

        return {
            "trades_count": len(sub),
            "win_rate_pct": round(win_rate, 1),
            "avg_r_multiple": round(float(np.mean(rs)), 2),
            "avg_net_return_pct": round(float(np.mean(rets)), 2),
            "profit_factor": round(pf, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_pct": round(max_dd, 2),
        }

    actionable_trades = [t for t in trades if t["grade"] in {"A+", "A"}]
    by_grade = {
        g: _summarize_subset([t for t in trades if t["grade"] == g])
        for g in ["A+", "A", "B", "C"]
    }

    return {
        "methodology": (
            f"無前視偏誤滾動回測｜訊號於第 t 日收盤確認，統一於 t+1 日開盤進場｜"
            f"已扣除雙邊滑價 {slippage_bps:.0f} bps 與年化 {assumed_borrow_fee_annual_pct:.1f}% 借券成本"
        ),
        "bias_safeguards": [
            "防範前視偏誤 (No Look-Ahead Bias)：支撐價、均線與 ATR 僅使用 <= t 日數據，進場價為 t+1 日開盤價。",
            "日內保守原則：若同一根 K 線同時觸及停損與停利，優先判定觸發停損。",
            "僅 A+ 與 A 級訊號（高空方評分）允許列入可執行名單 (Actionable Short List)。",
        ],
        "actionable_a_plus_a_summary": _summarize_subset(actionable_trades),
        "all_signals_summary": _summarize_subset(trades),
        "performance_by_grade": by_grade,
        "recent_signal_history": trades[:25],
    }
