from __future__ import annotations

from typing import Any, Dict, List, Optional

from .data_provider import DEFAULT_WATCHLIST, MarketDataProvider
from .execution import evaluate_stock
from .models import StockShortEvaluation
from .portfolio_backtest import compute_portfolio_risk, run_walk_forward_backtest
from .regime import compute_market_regime
from .reporting import format_daily_short_market_report, generate_alerts


class ShortSellerDashboardEngine:
    """End-to-end top-down orchestrator:
    MARKET -> SECTOR -> STOCK -> TECHNICAL SETUP -> CATALYST -> TRIGGER -> SIZE -> STOP -> TARGET -> EXIT
    """

    def __init__(
        self,
        watchlist: Optional[List[str]] = None,
        account_size: float = 100_000.0,
        base_risk_pct: float = 0.0075,
        institutional_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        self.watchlist: List[str] = [
            t.upper().strip() for t in (watchlist or list(DEFAULT_WATCHLIST))
        ]
        self.account_size = account_size
        self.base_risk_pct = base_risk_pct
        self.provider = MarketDataProvider(institutional_overrides=institutional_overrides)
        self.active_positions: Dict[str, float] = {}  # ticker -> entry_price

    def add_ticker(self, ticker: str) -> List[str]:
        t = ticker.upper().strip()
        if t and t not in self.watchlist:
            self.watchlist.append(t)
        return self.watchlist

    def remove_ticker(self, ticker: str) -> List[str]:
        t = ticker.upper().strip()
        self.watchlist = [x for x in self.watchlist if x != t]
        return self.watchlist

    def set_override(self, ticker: str, overrides: Dict[str, Any]) -> None:
        self.provider.set_institutional_override(ticker, overrides)

    def run_full_scan(self) -> Dict[str, Any]:
        # Pre-fetch watchlist + benchmark batch
        self.provider.fetch_ohlcv_batch(
            self.watchlist + ["SPY", "QQQ", "IWM", "^VIX", "^VIX3M"],
            period="1y",
        )

        # 1. Macro & Market Regime Filter
        regime = compute_market_regime(self.provider, watchlist=self.watchlist)

        # 2. First pass stock evaluations
        evals: List[StockShortEvaluation] = []
        for t in self.watchlist:
            try:
                ev = evaluate_stock(
                    ticker=t,
                    provider=self.provider,
                    regime=regime,
                    account_size=self.account_size,
                    base_risk_pct=self.base_risk_pct,
                    existing_position_entry=self.active_positions.get(t),
                )
                evals.append(ev)
            except Exception:
                continue

        # Sort by Short Score descending
        evals.sort(key=lambda x: x.short_score, reverse=True)

        # 3. Portfolio-Level Correlated Short Risk
        portfolio_risk = compute_portfolio_risk(
            evaluations=evals,
            provider=self.provider,
            account_size=self.account_size,
        )

        # Apply correlation sizing haircut if average correlation is high
        if portfolio_risk.avg_pairwise_correlation > 0.60:
            corr_mult = max(0.50, 1.0 - (portfolio_risk.avg_pairwise_correlation - 0.50) * 0.85)
            evals = [
                evaluate_stock(
                    ticker=ev.ticker,
                    provider=self.provider,
                    regime=regime,
                    account_size=self.account_size,
                    base_risk_pct=self.base_risk_pct,
                    correlation_penalty_mult=corr_mult,
                    existing_position_entry=self.active_positions.get(ev.ticker),
                )
                for ev in evals
            ]
            evals.sort(key=lambda x: x.short_score, reverse=True)
            portfolio_risk = compute_portfolio_risk(
                evaluations=evals,
                provider=self.provider,
                account_size=self.account_size,
            )

        # 4. Walk-Forward Signal Backtest
        backtest = run_walk_forward_backtest(
            tickers=self.watchlist,
            provider=self.provider,
        )

        # 5. Alerts & Daily Report
        alerts = generate_alerts(regime, evals, portfolio_risk)
        daily_report_md = format_daily_short_market_report(
            regime=regime,
            evaluations=evals,
            portfolio_risk=portfolio_risk,
            alerts=alerts,
        )

        actionable_list = [
            ev.to_dict()
            for ev in evals
            if ev.rating.value in {"A+", "A"}
            and not ev.factors.squeeze_warning_active
            and not ev.factors.earnings_red_warning
        ]

        return {
            "regime": regime.to_dict(),
            "stocks": [ev.to_dict() for ev in evals],
            "actionable_short_list": actionable_list,
            "portfolio_risk": portfolio_risk.to_dict(),
            "backtest": backtest,
            "alerts": alerts,
            "daily_report_markdown": daily_report_md,
            "account_size": self.account_size,
            "base_risk_pct": self.base_risk_pct * 100.0,
        }

    def analyze_single_ticker(self, ticker: str) -> StockShortEvaluation:
        t = ticker.upper().strip()
        self.provider.fetch_ohlcv_batch([t, "SPY", "QQQ", "IWM", "^VIX", "^VIX3M"], period="1y")
        regime = compute_market_regime(self.provider, watchlist=self.watchlist)
        return evaluate_stock(
            ticker=t,
            provider=self.provider,
            regime=regime,
            account_size=self.account_size,
            base_risk_pct=self.base_risk_pct,
            existing_position_entry=self.active_positions.get(t),
        )
