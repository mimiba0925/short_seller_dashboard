"use strict";

let dashboardState = null;
let activeFilter = "ALL";
let tickerSearchQuery = "";

// MANDATORY Fallback for browsers without <dialog closedby="any"> support (modern-web-guidance: light-dismiss-a-dialog)
function attachDialogLightDismissFallback(dialog) {
  if (!dialog) return;
  if (!("closedBy" in HTMLDialogElement.prototype)) {
    dialog.addEventListener("click", (event) => {
      if (event.target !== dialog) return;
      const rect = dialog.getBoundingClientRect();
      const isDialogContent =
        rect.top <= event.clientY &&
        event.clientY <= rect.top + rect.height &&
        rect.left <= event.clientX &&
        event.clientX <= rect.left + rect.width;
      if (isDialogContent) return;
      dialog.close();
    });
  }
}

document.querySelectorAll("dialog").forEach(attachDialogLightDismissFallback);

function scorePillClass(score, inverse = false) {
  if (!inverse) {
    if (score >= 65) return "pill-danger";
    if (score >= 42) return "pill-warn";
    return "pill-ok";
  } else {
    if (score >= 60) return "pill-danger";
    if (score >= 40) return "pill-warn";
    return "pill-ok";
  }
}

function polarityLabelBearish(score) {
  if (score >= 65) return "有利空方";
  if (score >= 42) return "多空拉鋸";
  return "有利多方";
}

const STATE_ZH_MAP = {
  "ENTRY": "ENTRY (觸發進場)",
  "SHORT SETUP": "SHORT SETUP (候選就緒)",
  "WATCH": "WATCH (觀察等待)",
  "WAIT": "WAIT (暫緩/禁空)",
  "ADD": "ADD (順勢加碼)",
  "HOLD": "HOLD (續抱空單)",
  "REDUCE": "REDUCE (減倉停利)",
  "EXIT": "EXIT (回補出場)",
};

function renderRegime(regime, portfolioRisk) {
  const modeTag = window.__SHORT_DASHBOARD_SNAPSHOT__ ? " [GitHub Pages 靜態快照]" : " [本機即時連線]";
  document.getElementById("asOfTimestamp").textContent = `資料更新時間：${regime.as_of}${modeTag}`;

  const rScore = regime.market_regime_score;
  document.getElementById("regimeScoreVal").textContent = `${rScore.toFixed(1)}`;
  const rBadge = document.getElementById("regimeLabelBadge");
  rBadge.textContent =
    rScore >= 61
      ? "RISK-OFF 空方主場（有利空方）"
      : rScore >= 41
      ? "NEUTRAL 震盪觀察（多空拉鋸）"
      : "RISK-ON 多頭強勢（有利多方）";
  rBadge.className = `status-pill ${scorePillClass(rScore)}`;
  document.getElementById("regimePolicyText").textContent = regime.short_book_policy;

  const bScore = regime.breadth.breadth_weakness_score;
  document.getElementById("breadthScoreVal").textContent = `${bScore.toFixed(1)}`;
  const bBadge = document.getElementById("breadthDivBadge");
  bBadge.textContent = regime.breadth.breadth_divergence
    ? "⚠️ 寬度背離（有利空方）"
    : `${polarityLabelBearish(bScore)} (>50MA: ${regime.breadth.pct_above_50ma}%)`;
  bBadge.className = `status-pill ${scorePillClass(bScore)}`;
  document.getElementById("breadthSummaryText").textContent = regime.breadth.summary;

  const vScore = regime.volatility.volatility_regime_score;
  document.getElementById("volScoreVal").textContent = `${vScore.toFixed(1)}`;
  const vBadge = document.getElementById("vixTermBadge");
  vBadge.textContent = regime.volatility.term_structure_inverted
    ? `⚠️ 期限倒掛 (${regime.volatility.vix_term_ratio.toFixed(2)}x 有利空方)`
    : `VIX ${regime.volatility.vix.toFixed(2)} (${polarityLabelBearish(vScore)})`;
  vBadge.className = `status-pill ${
    regime.volatility.term_structure_inverted ? "pill-danger" : scorePillClass(vScore)
  }`;
  document.getElementById("volSummaryText").textContent =
    `${regime.volatility.summary}｜${regime.volatility.put_call_status}`;

  const cScore = portfolioRisk.correlated_short_risk_score;
  document.getElementById("corrScoreVal").textContent = `${cScore.toFixed(1)}`;
  const cBadge = document.getElementById("effBetsBadge");
  cBadge.textContent = `有效獨立部位 N_eff: ${portfolioRisk.effective_independent_bets.toFixed(2)} / ${portfolioRisk.nominal_positions_count} 檔`;
  cBadge.className = `status-pill ${scorePillClass(cScore, true)}`;
  document.getElementById("corrSummaryText").textContent =
    `建議總空頭曝險：${portfolioRisk.gross_short_exposure_pct.toFixed(1)}%（Beta 調整後：${portfolioRisk.beta_adjusted_short_exposure_pct.toFixed(1)}%）｜60日平均相關係數：${portfolioRisk.avg_pairwise_correlation.toFixed(2)}`;

  // Index table
  const idxBody = document.getElementById("indexTableBody");
  idxBody.innerHTML = "";
  ["SPY", "QQQ", "IWM"].forEach((k) => {
    const ix = regime.indices[k];
    if (!ix) return;
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <th scope="row">${ix.ticker}</th>
      <td>$${ix.close.toFixed(2)} (${ix.ret_5d_pct >= 0 ? "+" : ""}${ix.ret_5d_pct.toFixed(2)}%)</td>
      <td>$${ix.ema20.toFixed(2)} <span class="status-pill ${ix.below_ema20 ? "pill-danger" : "pill-ok"}">${ix.below_ema20 ? "跌破 (有利空方)" : "站上 (有利多方)"}</span></td>
      <td>$${ix.sma50.toFixed(2)} <span class="status-pill ${ix.below_sma50 ? "pill-danger" : "pill-ok"}">${ix.below_sma50 ? "跌破 (有利空方)" : "站上 (有利多方)"}</span></td>
      <td>$${ix.sma200.toFixed(2)} <small style="color:var(--text-muted);">(${ix.below_sma200 ? "跌破" : "站上"})</small></td>
      <td>${ix.dist_days_25d} 天</td>
      <td><strong>${ix.sub_score.toFixed(1)}</strong> <span class="status-pill ${scorePillClass(ix.sub_score)}">${polarityLabelBearish(ix.sub_score)}</span></td>
    `;
    idxBody.appendChild(tr);
  });

  // Sector table
  const secBody = document.getElementById("sectorTableBody");
  secBody.innerHTML = "";
  (regime.sector_weakness_ranking || []).slice(0, 8).forEach((s) => {
    const tr = document.createElement("tr");
    const secBias = s.weakness_score >= 65 ? "弱勢 (有利空方)" : s.weakness_score >= 45 ? "中性" : "強勢 (有利多方)";
    tr.innerHTML = `
      <th scope="row">${s.etf}</th>
      <td>$${s.close.toFixed(2)}</td>
      <td>${s.ret_5d_pct >= 0 ? "+" : ""}${s.ret_5d_pct.toFixed(2)}%</td>
      <td>${s.ret_20d_pct >= 0 ? "+" : ""}${s.ret_20d_pct.toFixed(2)}%</td>
      <td><span class="status-pill ${s.rs_vs_spy_20d_pct < 0 ? "pill-danger" : "pill-ok"}">${s.rs_vs_spy_20d_pct >= 0 ? "+" : ""}${s.rs_vs_spy_20d_pct.toFixed(2)}% (${s.rs_vs_spy_20d_pct < 0 ? "落後大盤" : "領先大盤"})</span></td>
      <td>${s.dist_days_25d} 天</td>
      <td><strong>${s.weakness_score.toFixed(1)}</strong> <small style="color:var(--text-muted);">(${secBias})</small></td>
    `;
    secBody.appendChild(tr);
  });
}

function renderScreener(stocks) {
  const tbody = document.getElementById("screenerTableBody");
  tbody.innerHTML = "";

  const filtered = stocks.filter((st) => {
    if (tickerSearchQuery && !st.ticker.includes(tickerSearchQuery)) {
      return false;
    }
    if (activeFilter === "ACTIONABLE") {
      return (
        (st.rating === "A+" || st.rating === "A") &&
        !st.factors.squeeze_warning_active &&
        !st.factors.earnings_red_warning
      );
    }
    if (activeFilter === "FUND_BEARISH") {
      return (
        st.execution.is_fundamentally_bearish &&
        !st.execution.is_actionable_short
      );
    }
    if (activeFilter === "SQUEEZE") {
      return (
        st.factors.squeeze_warning_active ||
        st.factors.earnings_red_warning ||
        st.factors.squeeze_risk_score >= 50
      );
    }
    return true;
  });

  filtered.forEach((st) => {
    const tr = document.createElement("tr");
    const f = st.factors;
    const ex = st.execution;

    let classBadge = "";
    if (ex.is_actionable_short) {
      classBadge = `<span class="status-pill pill-danger">✅ 現在可執行做空 (Actionable)</span>`;
    } else if (f.earnings_red_warning) {
      classBadge = `<span class="status-pill pill-warn">🔴 財報 &le;3天 禁空</span>`;
    } else if (f.squeeze_warning_active) {
      classBadge = `<span class="status-pill pill-warn">⚠️ 高軋空危險 禁空</span>`;
    } else if (ex.is_fundamentally_bearish) {
      classBadge = `<span class="status-pill pill-warn">👀 結構看空 / 等待觸發</span>`;
    } else {
      classBadge = `<span class="status-pill pill-ok">🛡️ 偏多或中性 / 避開做空</span>`;
    }

    const statePillClass =
      ex.raw_state === "ENTRY" || ex.raw_state === "SHORT SETUP"
        ? "pill-danger"
        : ex.raw_state === "WATCH"
        ? "pill-warn"
        : "pill-ok";

    const scoreBiasText =
      st.short_score >= 70
        ? "強烈有利空方"
        : st.short_score >= 56
        ? "偏空方"
        : st.short_score >= 42
        ? "多空拉鋸"
        : "有利多方";

    const sqzText = f.squeeze_warning_active
      ? "⚠️極易被軋空(不利空)"
      : f.squeeze_risk_score >= 45
      ? "中度軋空風險"
      : "低軋空(有利空)";

    tr.innerHTML = `
      <th scope="row">${st.ticker} <small style="display:block;color:var(--text-muted);font-weight:400;">${st.sector_etf}</small></th>
      <td>
        <strong>${st.short_score.toFixed(1)}</strong> / <span class="status-pill ${scorePillClass(st.short_score)}">${st.rating}</span>
        <small style="display:block;color:var(--text-muted);">${scoreBiasText}</small>
      </td>
      <td><span class="status-pill ${statePillClass}">${STATE_ZH_MAP[ex.raw_state] || ex.raw_state}</span></td>
      <td>${classBadge}</td>
      <td>$${st.close.toFixed(2)} <small style="display:block;color:var(--text-muted);">ATR $${st.atr14.toFixed(2)}</small></td>
      <td>${f.trend_breakdown_score.toFixed(0)}/100 <small style="display:block;color:var(--text-muted);">${polarityLabelBearish(f.trend_breakdown_score)}</small></td>
      <td>${f.relative_weakness_score.toFixed(0)}/100 <small style="display:block;color:var(--text-muted);">${polarityLabelBearish(f.relative_weakness_score)}</small></td>
      <td>${f.volume_distribution_score.toFixed(0)}/100 <small style="display:block;color:var(--text-muted);">${polarityLabelBearish(f.volume_distribution_score)}</small></td>
      <td>${f.fundamental_catalyst_score.toFixed(0)}/100 ${f.earnings_red_warning ? "🔴財報&le;3d" : `<small style="display:block;color:var(--text-muted);">${polarityLabelBearish(f.fundamental_catalyst_score)}</small>`}</td>
      <td>
        <span class="status-pill ${f.squeeze_warning_active ? "pill-danger" : "pill-ok"}">${f.squeeze_risk_score.toFixed(0)}/100</span>
        <small style="display:block;color:var(--text-muted);">${sqzText}</small>
      </td>
      <td>進場 $${ex.entry_reference_price.toFixed(2)}｜停損 $${ex.stop_price.toFixed(2)}｜T1 $${ex.target_1.toFixed(2)}</td>
      <td>1 : ${ex.risk_reward_ratio.toFixed(2)} <small style="display:block;color:var(--text-muted);">建議 ${ex.suggested_shares} 股</small></td>
      <td><button type="button" class="btn primary view-card-btn">檢視決策卡</button></td>
    `;

    tr.addEventListener("click", () => openDecisionModal(st));
    tbody.appendChild(tr);
  });
}

function renderPortfolioAndBacktest(portfolioRisk, backtest) {
  const warnBox = document.getElementById("portfolioWarningsBox");
  warnBox.innerHTML = "";
  (portfolioRisk.risk_warnings || []).forEach((w) => {
    const div = document.createElement("div");
    div.className = "warning-banner";
    div.textContent = w;
    warnBox.appendChild(div);
  });

  const cBody = document.getElementById("clusterTableBody");
  cBody.innerHTML = "";
  const clusters = portfolioRisk.correlation_clusters || [];
  if (clusters.length === 0) {
    cBody.innerHTML = `<tr><th scope="row">無</th><td colspan="2">目前無 60日相關係數 &ge; 0.65 之高度共線性組合</td></tr>`;
  } else {
    clusters.forEach((c) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <th scope="row">${c.pair}</th>
        <td><strong>${c.correlation_60d.toFixed(2)}</strong></td>
        <td><span class="status-pill pill-warn">${c.warning}</span></td>
      `;
      cBody.appendChild(tr);
    });
  }

  document.getElementById("backtestMethodNote").textContent = backtest.methodology || "";
  const gBody = document.getElementById("gradeBacktestBody");
  gBody.innerHTML = "";
  ["A+", "A", "B", "C"].forEach((g) => {
    const row = (backtest.performance_by_grade || {})[g];
    if (!row) return;
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <th scope="row">評級 ${g} ${g === "A+" || g === "A" ? "（准許進場級別）" : "（過濾觀望級別）"}</th>
      <td>${row.trades_count} 筆</td>
      <td>${row.win_rate_pct.toFixed(1)}%</td>
      <td>${row.avg_r_multiple >= 0 ? "+" : ""}${row.avg_r_multiple.toFixed(2)}R</td>
      <td>${row.profit_factor.toFixed(2)}</td>
      <td>${row.sharpe_ratio.toFixed(2)}</td>
      <td>-${row.max_drawdown_pct.toFixed(2)}%</td>
    `;
    gBody.appendChild(tr);
  });
}

function renderAlerts(alerts) {
  const container = document.getElementById("alertsContainer");
  container.innerHTML = "";
  if (!alerts || alerts.length === 0) {
    container.innerHTML = `<p class="panel-desc">目前無高優先級觸發警報。</p>`;
    return;
  }
  const prioZh = {
    CRITICAL: "最高緊急 (CRITICAL)",
    HIGH: "高優先級 (HIGH)",
    MEDIUM: "中優先級 (MEDIUM)",
    LOW: "一般通知 (LOW)",
  };
  alerts.forEach((a) => {
    const card = document.createElement("article");
    card.className = `alert-card priority-${a.priority}`;
    const pillClass =
      a.priority === "CRITICAL" || a.priority === "HIGH" ? "pill-danger" : "pill-warn";
    card.innerHTML = `
      <div class="alert-top">
        <span class="status-pill ${pillClass}">${prioZh[a.priority] || a.priority} · ${a.category}</span>
        <span class="meta-tag">${a.ticker}</span>
      </div>
      <div class="alert-title">${a.title}</div>
      <p class="alert-msg">${a.message}</p>
    `;
    container.appendChild(card);
  });
}

function openDecisionModal(stock) {
  const dialog = document.getElementById("decisionModal");
  document.getElementById("modalTickerTitle").textContent =
    `${stock.ticker} (${stock.company_name}) — 標準化空方決策輸出模板`;
  document.getElementById("modalDecisionPre").textContent = stock.formatted_decision_card;

  const missingBox = document.getElementById("modalMissingFieldsBox");
  if (stock.missing_fields && stock.missing_fields.length > 0) {
    missingBox.style.display = "block";
    missingBox.textContent =
      `公開資料缺漏標記 (DATA UNAVAILABLE): ` + stock.missing_fields.join(", ");
  } else {
    missingBox.style.display = "none";
  }

  // MANDATORY per modern-web-guidance: open modal dialogs with showModal()
  dialog.showModal();
}

function renderAll() {
  if (!dashboardState) return;
  renderRegime(dashboardState.regime, dashboardState.portfolio_risk);
  renderScreener(dashboardState.stocks);
  renderPortfolioAndBacktest(dashboardState.portfolio_risk, dashboardState.backtest);
  renderAlerts(dashboardState.alerts);
}

async function loadDashboard(refresh = false) {
  const btn = document.getElementById("refreshBtn");
  btn.textContent = "載入中...";
  btn.disabled = true;
  try {
    if (!refresh && window.__SHORT_DASHBOARD_SNAPSHOT__) {
      dashboardState = JSON.parse(JSON.stringify(window.__SHORT_DASHBOARD_SNAPSHOT__));
      renderAll();
      return;
    }
    const res = await fetch(`/api/dashboard?refresh=${refresh ? "true" : "false"}`);
    if (res.ok) {
      dashboardState = await res.json();
      renderAll();
      return;
    }
  } catch (err) {
    if (window.__SHORT_DASHBOARD_SNAPSHOT__) {
      dashboardState = JSON.parse(JSON.stringify(window.__SHORT_DASHBOARD_SNAPSHOT__));
      renderAll();
    } else {
      console.error("Failed to load dashboard:", err);
    }
  } finally {
    btn.textContent = "重新掃描 (Refresh)";
    btn.disabled = false;
  }
}

// Event Listeners
document.getElementById("refreshBtn").addEventListener("click", () => loadDashboard(true));

document.getElementById("openReportBtn").addEventListener("click", () => {
  if (!dashboardState) return;
  document.getElementById("dailyReportPre").textContent = dashboardState.daily_report_markdown;
  document.getElementById("reportModal").showModal();
});

document.getElementById("addTickerForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("tickerInput");
  const ticker = input.value.trim().toUpperCase();
  if (!ticker) {
    tickerSearchQuery = "";
    renderAll();
    return;
  }
  try {
    const res = await fetch("/api/watchlist/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker }),
    });
    if (res.ok) {
      input.value = "";
      tickerSearchQuery = "";
      dashboardState = await res.json();
      renderAll();
      return;
    }
  } catch (_) {
    // Static GitHub Pages mode: filter table by ticker
  }
  tickerSearchQuery = ticker;
  renderAll();
});

document.querySelectorAll(".filter-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    activeFilter = btn.dataset.filter;
    tickerSearchQuery = "";
    if (dashboardState) {
      renderScreener(dashboardState.stocks);
    }
  });
});

loadDashboard(false);
