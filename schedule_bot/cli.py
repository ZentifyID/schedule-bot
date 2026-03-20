"""CLI entrypoints for schedule bot."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path

from .schedule_service import build_final_schedule_from_docx_file, build_json_from_csv
from .telegram_bot import run_telegram_bot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Schedule bot for Telegram + Yandex Disk replacements")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check-docx", help="Build schedule from local DOCX file")
    check.add_argument("--docx", required=True, help="Path to replacement DOCX file")
    check.add_argument("--base", default="schedule.base.json", help="Path to base JSON")
    check.add_argument("--group", default="31 \u0418\u0421", help="Target group")
    check.add_argument("--json", action="store_true", help="Print JSON output")

    bot = sub.add_parser("run-bot", help="Run Telegram bot in long-polling mode")
    bot.add_argument("--base", default="schedule.base.json", help="Path to base JSON")
    bot.add_argument("--group", default=os.getenv("TARGET_GROUP", "31 \u0418\u0421"), help="Target group")
    bot.add_argument("--yandex-public-url", default=os.getenv("YANDEX_PUBLIC_URL", ""), help="Public Yandex Disk URL")
    bot.add_argument("--timezone", default=os.getenv("BOT_TIMEZONE", "Europe/Saratov"))
    bot.add_argument("--token", default=os.getenv("TELEGRAM_BOT_TOKEN", ""))
    bot.add_argument(
        "--week1-start-date",
        default=os.getenv("WEEK1_START_DATE", ""),
        help="Optional YYYY-MM-DD where week is numerator; fallback if replacement file missing",
    )

    csv_cmd = sub.add_parser("csv-to-json", help="Convert base CSV to JSON format")
    csv_cmd.add_argument("--csv", default="schedule.base.csv", help="Input CSV path")
    csv_cmd.add_argument("--out", default="schedule.base.json", help="Output JSON path")
    csv_cmd.add_argument("--group", default="31 \u0418\u0421", help="Target group")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.command == "check-docx":
        result = build_final_schedule_from_docx_file(
            docx_path=Path(args.docx),
            base_schedule_path=Path(args.base),
            group=args.group,
        )
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            from .schedule_service import format_schedule_text  # local import to keep CLI lightweight

            print(format_schedule_text(result))
        return

    if args.command == "csv-to-json":
        build_json_from_csv(Path(args.csv), args.group, Path(args.out))
        print(f"Saved: {args.out}")
        return

    if args.command == "run-bot":
        if not args.token:
            raise ValueError("Set TELEGRAM_BOT_TOKEN or pass --token")
        if not args.yandex_public_url:
            raise ValueError("Set YANDEX_PUBLIC_URL or pass --yandex-public-url")

        week1_start = None
        if args.week1_start_date:
            week1_start = dt.datetime.strptime(args.week1_start_date, "%Y-%m-%d").date()

        run_telegram_bot(
            token=args.token,
            base_schedule_path=Path(args.base),
            group=args.group,
            yandex_public_url=args.yandex_public_url,
            timezone=args.timezone,
            fallback_week1_start=week1_start,
        )
