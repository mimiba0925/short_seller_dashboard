from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import uvicorn

from short_dashboard.engine.pipeline import ShortSellerDashboardEngine


def main() -> None:
    parser = argparse.ArgumentParser(
        description="US Equity Quant Short-Biased Trading Monitor & Decision Dashboard CLI"
    )
    sub = parser.add_subparsers(dest="cmd")

    # 1. Single or multi-ticker standardized decision card output
    p_ticker = sub.add_parser("ticker", help="Analyze specific ticker(s) using the mandatory output template")
    p_ticker.add_argument("tickers", nargs="+", help="Ticker symbol(s), e.g. NVDA TSLA MSTR")
    p_ticker.add_argument("--account", type=float, default=100_000.0, help="Account size in USD")
    p_ticker.add_argument("--borrow-fee", type=float, default=None, help="Optional Ortex/IBKR borrow fee (%)")

    # 2. Daily Short Market Report
    p_report = sub.add_parser("report", help="Generate the full DAILY SHORT MARKET REPORT")
    p_report.add_argument(
        "--out",
        type=str,
        default="DAILY_SHORT_REPORT.md",
        help="Output markdown file path",
    )

    # 3. Serve Web Dashboard
    p_serve = sub.add_parser("serve", help="Launch the FastAPI Quantitative Short Seller Web Dashboard")
    p_serve.add_argument("--host", type=str, default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()
    engine = ShortSellerDashboardEngine()

    if args.cmd == "ticker":
        engine.account_size = args.account
        for t in args.tickers:
            if args.borrow_fee is not None:
                engine.set_override(t, {"borrow_fee_rate_pct": args.borrow_fee})
            ev = engine.analyze_single_ticker(t)
            print(ev.formatted_decision_card)
    elif args.cmd == "report":
        scan = engine.run_full_scan()
        out_path = Path(args.out)
        out_path.write_text(scan["daily_report_markdown"], encoding="utf-8")
        print(scan["daily_report_markdown"])
        print(f"\n[Saved Daily Short Market Report to {out_path.resolve()}]")
    elif args.cmd == "serve":
        uvicorn.run("short_dashboard.app:app", host=args.host, port=args.port, reload=False)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
