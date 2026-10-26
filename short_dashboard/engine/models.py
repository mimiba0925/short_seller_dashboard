from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


DATA_UNAVAILABLE = "DATA UNAVAILABLE"
INSUFFICIENT_DATA = "INSUFFICIENT DATA"


class ExecutionAction(str, Enum):
    WAIT = "WAIT"
    WATCH = "WATCH"
    SHORT_SETUP = "SHORT SETUP"
    ENTRY = "ENTRY"
    ADD = "ADD"
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    EXIT = "EXIT"


class SignalRating(str, Enum):
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class AlertPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class IndexSnapshot:
    ticker: str
    close: float
    ema20: float
    sma50: float
    sma200: float
    ema20_slope_pct: float
    sma50_slope_pct: float
    dist_days_25d: int
    ret_5d_pct: float
    ret_20d_pct: float
    below_ema20: bool
    below_sma50: bool
    below_sma200: bool
    sub_score: float


@dataclass
class BreadthMetrics:
    pct_above_50ma: float
    pct_above_200ma: float
    net_new_highs_lows_pct: float
    adv_dec_10d_ratio: float
    breadth_divergence: bool
    breadth_weakness_score: float
    summary: str
    source_note: str


@dataclass
class VolatilityMetrics:
    vix: float
    vix_5d_roc_pct: float
    vix3m: float
    vix_term_ratio: float
    term_structure_inverted: bool
    volatility_climax_warning: bool
    equity_put_call_ratio: Optional[float]
    put_call_status: str
    volatility_regime_score: float
    summary: str


@dataclass
class MarketRegimeReport:
    as_of: str
    market_regime_score: float
    regime_label: str  # "RISK-ON", "NEUTRAL", "RISK-OFF"
    short_book_policy: str
    max_gross_short_exposure_pct: float
    regime_sizing_multiplier: float
    mandatory_de_gross: bool
    indices: Dict[str, IndexSnapshot]
    breadth: BreadthMetrics
    volatility: VolatilityMetrics
    sector_weakness_ranking: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FactorScores:
    # A. Price Trend & Breakdown (25%)
    trend_breakdown_score: float
    trend_status: str
    momentum_status: str
    # B. Relative Weakness & Momentum (15%)
    relative_weakness_score: float
    relative_strength_status: str
    # C. Volume & Distribution (15%)
    volume_distribution_score: float
    volume_status: str
    # D. Fundamental & Catalyst Risk (25%)
    fundamental_catalyst_score: float
    catalyst_risk_score: float
    fundamental_catalyst_status: str
    days_to_earnings: Optional[int]
    earnings_red_warning: bool
    # E. Short Squeeze & Options Risk (20%)
    derivatives_bearish_score: float
    squeeze_risk_score: float
    short_squeeze_status: str
    squeeze_warning_active: bool


@dataclass
class ExecutionPlan:
    action: str  # One of ExecutionAction values + contextual note
    raw_state: ExecutionAction
    is_fundamentally_bearish: bool
    is_actionable_short: bool
    bearish_probability_pct: float
    entry_zone: str
    entry_reference_price: float
    trigger_condition: str
    trigger_fired: bool
    stop_price: float
    stop_basis: str
    target_1: float
    target_2: float
    risk_per_share: float
    reward_per_share_t1: float
    risk_reward_ratio: float
    confidence_pct: float
    invalidation: str
    short_exit_score: float
    exit_reasons: List[str]
    suggested_shares: int
    suggested_notional: float
    max_risk_dollars: float


@dataclass
class StockShortEvaluation:
    ticker: str
    company_name: str
    sector: str
    sector_etf: str
    sector_status: str
    close: float
    atr14: float
    short_score: float
    rating: SignalRating
    market_regime_summary: str
    factors: FactorScores
    execution: ExecutionPlan
    missing_fields: List[str] = field(default_factory=list)
    raw_metrics: Dict[str, Any] = field(default_factory=dict)
    formatted_decision_card: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["rating"] = self.rating.value
        d["execution"]["raw_state"] = self.execution.raw_state.value
        return d
