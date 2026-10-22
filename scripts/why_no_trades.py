"""Print why the last Telegram signals did not open MT5 positions.

    py scripts\\why_no_trades.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_config  # noqa: E402

KEYWORDS = (
    "Signal from",
    "Not a signal",
    "Ignored chat_id",
    "Skipped",
    "Order failed",
    "all_orders",
    "busy_group",
    "group_disabled",
    "stale_active",
    "Using open gold",
    "Connected to MT5",
    "Telegram signed",
    "Starting ",
    "authorization",
    "AuthKey",
)


def main() -> int:
    cfg = load_config()
    print("=== קבוצות ===")
    for group in cfg.groups:
        state = "פעילה" if group.enabled else "מושבתת"
        print(f"  {group.name}  chat_id={group.chat_id}  lot={group.lot}  [{state}]")
    print(f"מסחר ראשי: {cfg.trading_enabled}   סימול: {cfg.symbol_override or '(גרף פתוח)'}")

    db_path = cfg.data_dir / "bot.db"
    print(f"\n=== איתותים אחרונים ({db_path}) ===")
    if not db_path.exists():
        print("  אין bot.db — הבוט כנראה עוד לא רץ מהתיקייה הזו.")
    else:
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            """
            SELECT received_at, group_name, status, skipped_reason, side, symbol
            FROM signals ORDER BY received_at DESC LIMIT 15
            """
        ).fetchall()
        if not rows:
            print("  אין איתותים ב-DB. הטלגרם כנראה לא נקלט כסיגנל (תבנית / קבוצה לא בקונפיג).")
        else:
            for row in rows:
                print("  " + " | ".join("" if v is None else str(v) for v in row))
        active = conn.execute(
            "SELECT id, group_name, received_at FROM signals WHERE status='active'"
        ).fetchall()
        print(f"איתותים פתוחים ב-DB: {len(active)}")
        for row in active:
            print("  ACTIVE", *row)
        open_trades = conn.execute(
            "SELECT group_name, ticket, side, status FROM trades WHERE status='open'"
        ).fetchall()
        print(f"עסקאות פתוחות ב-DB: {len(open_trades)}")
        for row in open_trades:
            print("  OPEN", *row)
        conn.close()

    log_path = cfg.logs_dir / "bot.log"
    print(f"\n=== שורות לוג רלוונטיות ({log_path}) ===")
    if not log_path.exists():
        print("  אין bot.log")
        return 0
    hits = []
    for path in (log_path, log_path.with_suffix(".log.1")):
        if not path.exists():
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            if any(key.lower() in line.lower() for key in KEYWORDS):
                hits.append(line)
    if not hits:
        print("  אין שורות מתאימות — ייתכן שהבוט לא רץ.")
    else:
        for line in hits[-40:]:
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
