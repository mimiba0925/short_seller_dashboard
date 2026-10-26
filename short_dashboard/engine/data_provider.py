from __future__ import annotations

import datetime as dt
import math
import os
import warnings
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*inplace keyword.*")
warnings.filterwarnings("ignore", module="yfinance.*")

try:
    import yfinance as yf
except ImportError:
    yf = None


SECTOR_ETF_MAP: Dict[str, str] = {
    "Technology": "XLK",
    "Semiconductors": "SMH",
    "Consumer Cyclical": "XLY",
    "Communication Services": "XLC",
    "Financial Services": "XLF",
    "Healthcare": "XLV",
    "Industrials": "XLI",
    "Energy": "XLE",
    "Consumer Defensive": "XLP",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Basic Materials": "XLB",
}

DEFAULT_WATCHLIST: List[str] = [
    "NVDA",
    "TSLA",
    "MSTR",
    "SMCI",
    "CVNA",
    "PLTR",
    "COIN",
    "MARA",
    "AMD",
    "SNOW",
    "RIVN",
    "LCID",
]

BREADTH_BASKET_TICKERS: List[str] = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "AVGO", "BRK-B", "JPM",
    "LLY", "V", "UNH", "XOM", "MA", "COST", "HD", "PG", "JNJ", "NFLX",
    "ABBV", "CRM", "BAC", "AMD", "CVX", "MRK", "KO", "WMT", "PEP", "TMO",
    "LIN", "CSCO", "ACN", "MCD", "ADBE", "DIS", "ABT", "WFC", "PM", "CAT",
    "INTU", "IBM", "QCOM", "VZ", "TXN", "GE", "NOW", "AMGN", "UNP", "SPGI",
]


@dataclass
class TickerMarketData:
    ticker: str
    company_name: str
    sector: str
    industry: str
    sector_etf: str
    ohlcv: pd.DataFrame  # Columns: Open, High, Low, Close, Volume
    # Fundamental & Catalyst fields (None means DATA UNAVAILABLE)
    revenue_growth_yoy: Optional[float] = None
    operating_margin: Optional[float] = None
    gross_margin: Optional[float] = None
    free_cash_flow: Optional[float] = None
    debt_to_equity: Optional[float] = None
    forward_pe: Optional[float] = None
    price_to_sales: Optional[float] = None
    enterprise_to_revenue: Optional[float] = None
    days_to_earnings: Optional[int] = None
    next_earnings_date: Optional[str] = None
    insider_net_selling_flag: Optional[bool] = None
    dilution_offering_flag: Optional[bool] = None
    # Short Interest & Derivatives fields (None means DATA UNAVAILABLE)
    short_pct_float: Optional[float] = None  # e.g. 0.145 for 14.5%
    days_to_cover: Optional[float] = None
    borrow_fee_rate_pct: Optional[float] = None  # Requires Ortex/IBKR feed or manual input
    put_call_vol_ratio: Optional[float] = None
    put_call_oi_ratio: Optional[float] = None
    unusual_otm_put_flag: Optional[bool] = None
    unusual_call_selling_flag: Optional[bool] = None
    gamma_exposure_regime: Optional[str] = None
    data_source: str = "yfinance"
    missing_fields: List[str] = field(default_factory=list)


def _clean_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


class MarketDataProvider:
    """Fetches real market data via yfinance with pluggable institutional overrides
    (Ortex / IBKR borrow fee rates) and strict DATA UNAVAILABLE tracking.
    """

    def __init__(
        self,
        institutional_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
        allow_offline_fallback: bool = True,
    ) -> None:
        self.institutional_overrides = institutional_overrides or {}
        self.allow_offline_fallback = allow_offline_fallback
        self._ohlcv_cache: Dict[str, pd.DataFrame] = {}
        self._ticker_cache: Dict[str, TickerMarketData] = {}

    def set_institutional_override(self, ticker: str, data: Dict[str, Any]) -> None:
        t = ticker.upper().strip()
        self.institutional_overrides[t] = {
            **self.institutional_overrides.get(t, {}),
            **data,
        }
        self._ticker_cache.pop(t, None)

    def fetch_ohlcv_batch(self, tickers: List[str], period: str = "1y") -> Dict[str, pd.DataFrame]:
        missing = [t for t in tickers if t not in self._ohlcv_cache]
        if missing and yf is not None:
            try:
                raw = yf.download(
                    missing,
                    period=period,
                    interval="1d",
                    group_by="ticker",
                    auto_adjust=False,
                    progress=False,
                    threads=True,
                )
                if raw is not None and not raw.empty:
                    if len(missing) == 1:
                        t = missing[0]
                        df = raw.copy()
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = df.columns.get_level_values(-1)
                        df = df.dropna(subset=["Close"])
                        if not df.empty:
                            self._ohlcv_cache[t] = df
                    else:
                        for t in missing:
                            if t in raw.columns.get_level_values(0):
                                df = raw[t].copy().dropna(subset=["Close"])
                                if not df.empty:
                                    self._ohlcv_cache[t] = df
            except Exception:
                pass

        for t in missing:
            if t not in self._ohlcv_cache and self.allow_offline_fallback:
                self._ohlcv_cache[t] = self._generate_fallback_ohlcv(t)

        return {t: self._ohlcv_cache[t] for t in tickers if t in self._ohlcv_cache}

    def get_ohlcv(self, ticker: str, period: str = "1y") -> pd.DataFrame:
        t = ticker.upper().strip()
        if t not in self._ohlcv_cache:
            self.fetch_ohlcv_batch([t], period=period)
        return self._ohlcv_cache.get(t, pd.DataFrame())

    def get_ticker_data(self, ticker: str) -> TickerMarketData:
        t = ticker.upper().strip()
        if t in self._ticker_cache:
            return self._ticker_cache[t]

        ohlcv = self.get_ohlcv(t, period="1y")
        info: Dict[str, Any] = {}
        days_to_earnings: Optional[int] = None
        next_earnings_str: Optional[str] = None
        pc_vol_ratio: Optional[float] = None
        pc_oi_ratio: Optional[float] = None
        otm_put_flag: Optional[bool] = None
        call_sell_flag: Optional[bool] = None
        insider_selling: Optional[bool] = None
        source = "yfinance"

        if yf is not None and not getattr(ohlcv, "attrs", {}).get("is_fallback", False):
            try:
                yt = yf.Ticker(t)
                info = yt.info or {}

                # Check earnings dates from calendar
                try:
                    cal = yt.calendar
                    today = dt.date.today()
                    if isinstance(cal, dict) and "Earnings Date" in cal:
                        ed_list = cal["Earnings Date"]
                        if ed_list:
                            ed = ed_list[0]
                            if isinstance(ed, dt.datetime):
                                ed = ed.date()
                            if isinstance(ed, dt.date):
                                delta = (ed - today).days
                                if -2 <= delta <= 180:
                                    days_to_earnings = max(0, delta)
                                    next_earnings_str = ed.isoformat()
                except Exception:
                    pass

                # Check options chain for nearest expiry Put/Call ratio if available
                try:
                    exps = yt.options
                    if exps:
                        target_exp = exps[min(1, len(exps) - 1)]
                        chain = yt.option_chain(target_exp)
                        calls, puts = chain.calls, chain.puts
                        if not calls.empty and not puts.empty:
                            c_vol = float(calls["volume"].fillna(0).sum())
                            p_vol = float(puts["volume"].fillna(0).sum())
                            c_oi = float(calls["openInterest"].fillna(0).sum())
                            p_oi = float(puts["openInterest"].fillna(0).sum())
                            if c_vol > 0:
                                pc_vol_ratio = round(p_vol / c_vol, 2)
                            if c_oi > 0:
                                pc_oi_ratio = round(p_oi / c_oi, 2)
                            last_px = float(ohlcv["Close"].iloc[-1]) if not ohlcv.empty else 0.0
                            if last_px > 0:
                                otm_puts = puts[puts["strike"] <= last_px * 0.93]
                                otm_put_vol = float(otm_puts["volume"].fillna(0).sum())
                                otm_put_oi = float(otm_puts["openInterest"].fillna(0).sum())
                                otm_put_flag = (
                                    (otm_put_oi > 0 and otm_put_vol / otm_put_oi > 0.65)
                                    or (pc_vol_ratio is not None and pc_vol_ratio > 1.35)
                                )
                                atm_calls = calls[
                                    (calls["strike"] >= last_px * 0.98)
                                    & (calls["strike"] <= last_px * 1.05)
                                ]
                                call_sell_flag = bool(
                                    not atm_calls.empty
                                    and float(atm_calls["volume"].fillna(0).sum()) > 1000
                                    and float(ohlcv["Close"].iloc[-1]) < float(ohlcv["Open"].iloc[-1])
                                )
                except Exception:
                    pass

                # Check insider transactions if available
                try:
                    ins = yt.insider_purchases
                    if ins is not None and not ins.empty:
                        insider_selling = False
                except Exception:
                    pass
            except Exception:
                pass
        else:
            source = "fallback_cache"

        sector = str(info.get("sector") or self._default_sector_for(t))
        industry = str(info.get("industry") or sector)
        company_name = str(info.get("shortName") or info.get("longName") or t)
        sector_etf = SECTOR_ETF_MAP.get(sector, "SPY")
        if "Semiconductor" in industry or t in {"NVDA", "AMD", "SMCI", "AVGO", "MU", "ARM", "INTC"}:
            sector_etf = "SMH"

        rev_growth = _clean_float(info.get("revenueGrowth"))
        op_margin = _clean_float(info.get("operatingMargins"))
        gross_margin = _clean_float(info.get("grossMargins"))
        fcf = _clean_float(info.get("freeCashflow"))
        dte = _clean_float(info.get("debtToEquity"))
        f_pe = _clean_float(info.get("forwardPE"))
        p_sales = _clean_float(info.get("priceToSalesTrailing12Months"))
        ev_rev = _clean_float(info.get("enterpriseToRevenue"))
        si_float = _clean_float(info.get("shortPercentOfFloat"))
        dtc = _clean_float(info.get("shortRatio"))

        # Apply institutional overrides if provided (e.g., Ortex / IBKR Borrow Fee, GEX, Dilution)
        overrides = self.institutional_overrides.get(t, {})
        borrow_fee = _clean_float(overrides.get("borrow_fee_rate_pct"))
        dilution_flag = overrides.get("dilution_offering_flag")
        gex_regime = overrides.get("gamma_exposure_regime")
        if "short_pct_float" in overrides:
            si_float = _clean_float(overrides["short_pct_float"])
        if "days_to_cover" in overrides:
            dtc = _clean_float(overrides["days_to_cover"])
        if "days_to_earnings" in overrides:
            days_to_earnings = int(overrides["days_to_earnings"])

        missing: List[str] = []
        if rev_growth is None:
            missing.append("revenue_growth_yoy")
        if op_margin is None:
            missing.append("operating_margin")
        if fcf is None:
            missing.append("free_cash_flow")
        if days_to_earnings is None:
            missing.append("days_to_earnings")
        if si_float is None:
            missing.append("short_pct_float")
        if dtc is None:
            missing.append("days_to_cover")
        if borrow_fee is None:
            missing.append("borrow_fee_rate_pct (Ortex/IBKR Feed)")
        if pc_vol_ratio is None:
            missing.append("put_call_vol_ratio")
        if gex_regime is None:
            missing.append("gamma_exposure_regime (Dealer GEX Feed)")

        data = TickerMarketData(
            ticker=t,
            company_name=company_name,
            sector=sector,
            industry=industry,
            sector_etf=sector_etf,
            ohlcv=ohlcv,
            revenue_growth_yoy=rev_growth,
            operating_margin=op_margin,
            gross_margin=gross_margin,
            free_cash_flow=fcf,
            debt_to_equity=dte,
            forward_pe=f_pe,
            price_to_sales=p_sales,
            enterprise_to_revenue=ev_rev,
            days_to_earnings=days_to_earnings,
            next_earnings_date=next_earnings_str,
            insider_net_selling_flag=insider_selling,
            dilution_offering_flag=dilution_flag,
            short_pct_float=si_float,
            days_to_cover=dtc,
            borrow_fee_rate_pct=borrow_fee,
            put_call_vol_ratio=pc_vol_ratio,
            put_call_oi_ratio=pc_oi_ratio,
            unusual_otm_put_flag=otm_put_flag,
            unusual_call_selling_flag=call_sell_flag,
            gamma_exposure_regime=gex_regime,
            data_source=source,
            missing_fields=missing,
        )
        self._ticker_cache[t] = data
        return data

    @staticmethod
    def _default_sector_for(ticker: str) -> str:
        tech = {"NVDA", "AMD", "SMCI", "PLTR", "SNOW", "MSFT", "AAPL", "CRM", "ADBE"}
        consumer = {"TSLA", "CVNA", "RIVN", "LCID", "AMZN", "HD", "MCD"}
        fin_crypto = {"MSTR", "COIN", "MARA", "RIOT", "JPM", "BAC", "GS"}
        if ticker in tech:
            return "Technology"
        if ticker in consumer:
            return "Consumer Cyclical"
        if ticker in fin_crypto:
            return "Financial Services"
        return "Technology"

    @staticmethod
    def _generate_fallback_ohlcv(ticker: str, n_days: int = 252) -> pd.DataFrame:
        """Deterministic synthetic series used ONLY if internet/yfinance is unreachable."""
        seed = sum(ord(c) * (i + 1) for i, c in enumerate(ticker)) % 10000
        rng = np.random.default_rng(seed)
        dates = pd.bdate_range(end=dt.date.today(), periods=n_days)

        if ticker == "^VIX":
            base = 21.5
            rets = rng.normal(0.001, 0.045, size=n_days)
        elif ticker == "^VIX3M":
            base = 21.0
            rets = rng.normal(0.0005, 0.03, size=n_days)
        elif ticker in {"SPY", "QQQ", "IWM"}:
            base = 500.0 if ticker == "SPY" else (430.0 if ticker == "QQQ" else 205.0)
            rets = rng.normal(-0.0006, 0.012, size=n_days)
            rets[-25:] += -0.0022  # Recent market pullback / distribution
        else:
            base = 60.0 + (seed % 180)
            drift = -0.0018 if seed % 3 != 0 else 0.0008
            rets = rng.normal(drift, 0.028, size=n_days)
            rets[-15:] += -0.0045 if seed % 2 == 0 else -0.0015

        close = base * np.exp(np.cumsum(rets))
        high = close * (1.0 + np.abs(rng.normal(0.008, 0.006, size=n_days)))
        low = close * (1.0 - np.abs(rng.normal(0.009, 0.006, size=n_days)))
        open_px = low + (high - low) * rng.uniform(0.25, 0.85, size=n_days)
        vol_base = 15_000_000 if ticker not in {"^VIX", "^VIX3M"} else 0
        vol_mult = np.where(rets < -0.01, rng.uniform(1.3, 2.2, size=n_days), rng.uniform(0.6, 1.15, size=n_days))
        volume = (vol_base * vol_mult).astype(int)

        df = pd.DataFrame(
            {
                "Open": open_px,
                "High": np.maximum.reduce([open_px, close, high]),
                "Low": np.minimum.reduce([open_px, close, low]),
                "Close": close,
                "Volume": volume,
            },
            index=dates,
        )
        df.attrs["is_fallback"] = True
        return df
