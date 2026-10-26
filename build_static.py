"""
將美股量化空方交易監控與決策系統 (Short-Biased Quant Dashboard) 完整計算結果
匯出為靜態 snapshot.js、DAILY_SHORT_REPORT.md 與根目錄靜態網頁 (index.html, styles.css, app.js)，
讓 GitHub Pages 可直接作為無後端靜態網站瀏覽，並支援 GitHub Actions 自動排程更新。
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import time
from pathlib import Path
from typing import List

from short_dashboard.engine.data_provider import DEFAULT_WATCHLIST
from short_dashboard.engine.pipeline import ShortSellerDashboardEngine

ROOT = Path(__file__).resolve().parent
STATIC_SRC = ROOT / "short_dashboard" / "static"
WATCHLIST_CSV = ROOT / "config" / "watchlist.csv"


def load_and_sort_watchlist() -> List[str]:
    if not WATCHLIST_CSV.exists():
        return list(DEFAULT_WATCHLIST)
    rows = []
    with WATCHLIST_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            sym = (r.get("symbol") or "").strip().upper()
            note = (r.get("note") or "").strip()
            if sym:
                rows.append({"symbol": sym, "note": note})
    rows.sort(key=lambda x: x["symbol"])
    with WATCHLIST_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["symbol", "note"])
        writer.writeheader()
        writer.writerows(rows)
    return [r["symbol"] for r in rows] or list(DEFAULT_WATCHLIST)


def main() -> None:
    watchlist = load_and_sort_watchlist()
    print(f"▶ [1/2] 執行美股空方量化引擎掃描 ({len(watchlist)} 檔標的: {', '.join(watchlist)}) ...")
    engine = ShortSellerDashboardEngine(watchlist=watchlist)
    scan_data = engine.run_full_scan()

    print("▶ [2/2] 輸出靜態網站檔案至根目錄（供 GitHub Pages 直接部署）...")
    ver = int(time.time())
    html = (STATIC_SRC / "index.html").read_text(encoding="utf-8")
    html = re.sub(r'href="\./styles\.css(\?v=\d+)?"', f'href="./styles.css?v={ver}"', html)
    html = re.sub(r'src="\./snapshot\.js(\?v=\d+)?"', f'src="./snapshot.js?v={ver}"', html)
    html = re.sub(r'src="\./app\.js(\?v=\d+)?"', f'src="./app.js?v={ver}"', html)

    (ROOT / "index.html").write_text(html, encoding="utf-8")
    shutil.copyfile(STATIC_SRC / "styles.css", ROOT / "styles.css")
    shutil.copyfile(STATIC_SRC / "app.js", ROOT / "app.js")

    payload = json.dumps(scan_data, ensure_ascii=False, separators=(",", ":"))
    (ROOT / "snapshot.js").write_text(
        f"window.__SHORT_DASHBOARD_SNAPSHOT__={payload};\n",
        encoding="utf-8",
    )
    (ROOT / "DAILY_SHORT_REPORT.md").write_text(
        scan_data["daily_report_markdown"],
        encoding="utf-8",
    )
    print(
        f"✔ 已產生 index.html (v={ver})、styles.css、app.js、DAILY_SHORT_REPORT.md 與 snapshot.js ({len(payload) / 1024:.1f} KB)"
    )


if __name__ == "__main__":
    main()
