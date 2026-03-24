"""Telegram bot runtime and command handlers."""

from __future__ import annotations

import datetime as dt
import html
import json
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .constants import RU_DENOMINATOR, RU_NUMERATOR
from .schedule_service import (
    build_base_only_schedule,
    build_final_schedule_from_root,
    extract_xml_root_from_docx_bytes,
    format_schedule_text_telegram,
    parse_flexible_date,
)
from .yandex_disk import find_replacement_docx_for_date, yandex_download_docx

TELEGRAM_API_BASE = "https://api.telegram.org"


def telegram_api_request(token: str, method: str, params: dict[str, Any]) -> dict[str, Any]:
    url = f"{TELEGRAM_API_BASE}/bot{token}/{method}"
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not payload.get("ok"):
        raise RuntimeError(f"Telegram API error for {method}: {payload}")
    return payload


def telegram_get_updates(token: str, offset: int | None) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"timeout": 30}
    if offset is not None:
        params["offset"] = offset
    payload = telegram_api_request(token, "getUpdates", params)
    return payload.get("result", [])


def telegram_send_message(token: str, chat_id: int, text: str) -> None:
    telegram_api_request(token, "sendMessage", {"chat_id": chat_id, "text": text})


def telegram_send_message_in_topic(
    token: str,
    chat_id: int,
    text: str,
    message_thread_id: int | None = None,
) -> None:
    params: dict[str, Any] = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if message_thread_id is not None:
        params["message_thread_id"] = message_thread_id
    telegram_api_request(token, "sendMessage", params)


def build_from_yandex(
    target_date: dt.date,
    base_schedule_path: Path,
    group: str,
    yandex_public_url: str,
    fallback_week1_start: dt.date | None = None,
) -> tuple[dict[str, Any], str]:
    file_item = find_replacement_docx_for_date(yandex_public_url, target_date)
    if file_item:
        docx_bytes = yandex_download_docx(yandex_public_url, file_item)
        root = extract_xml_root_from_docx_bytes(docx_bytes)
        result = build_final_schedule_from_root(root, base_schedule_path, group)
        note = ""
        return result, note

    if fallback_week1_start is not None:
        delta_weeks = (target_date - fallback_week1_start).days // 7
        week_type = RU_NUMERATOR if delta_weeks % 2 == 0 else RU_DENOMINATOR
        suffix = f" ({fallback_week1_start.isoformat()})."
    else:
        # No anchor date provided. Use ISO week parity as a best-effort fallback:
        # odd week -> numerator, even week -> denominator.
        iso_week = target_date.isocalendar().week
        week_type = RU_NUMERATOR if iso_week % 2 == 1 else RU_DENOMINATOR
        suffix = (
            ". \u041d\u0435\u0434\u0435\u043b\u044f \u043e\u043f\u0440\u0435\u0434\u0435\u043b\u0435\u043d\u0430 \u043f\u043e ISO-\u043f\u0430\u0440\u0438\u0442\u0435\u0442\u0443 "
            f"(\u043d\u0435\u0434\u0435\u043b\u044f {iso_week})."
        )

    result = build_base_only_schedule(target_date, base_schedule_path, group, week_type)
    note = (
        "\u0424\u0430\u0439\u043b \u0437\u0430\u043c\u0435\u043d \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d, "
        "\u043f\u043e\u043a\u0430\u0437\u0430\u043d\u043e \u0442\u043e\u043b\u044c\u043a\u043e \u0431\u0430\u0437\u043e\u0432\u043e\u0435 "
        "\u0440\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u0435"
        f"{suffix}"
    )
    return result, note


def on_telegram_command(
    token: str,
    chat_id: int,
    text: str,
    now: dt.datetime,
    base_schedule_path: Path,
    group: str,
    yandex_public_url: str,
    fallback_week1_start: dt.date | None,
    message_thread_id: int | None,
) -> None:
    command = text.strip().split()[0].lower()

    if command in {"/start", "/help"}:
        msg = (
            "\u0414\u043e\u0441\u0442\u0443\u043f\u043d\u044b\u0435 \u043a\u043e\u043c\u0430\u043d\u0434\u044b:\n"
            "/today - \u0440\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u043d\u0430 \u0441\u0435\u0433\u043e\u0434\u043d\u044f\n"
            "/tomorrow - \u0440\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u043d\u0430 \u0437\u0430\u0432\u0442\u0440\u0430\n"
            "/date YYYY-MM-DD - \u043d\u0430 \u043d\u0443\u0436\u043d\u0443\u044e \u0434\u0430\u0442\u0443\n"
            "\u0422\u0430\u043a\u0436\u0435 \u043f\u043e\u0434\u0434\u0435\u0440\u0436\u0438\u0432\u0430\u044e\u0442\u0441\u044f: YYYY.MM.DD, DD.MM.YYYY"
        )
        telegram_send_message_in_topic(token, chat_id, msg, message_thread_id=message_thread_id)
        return

    if command == "/today":
        target_date = now.date()
    elif command == "/tomorrow":
        target_date = (now + dt.timedelta(days=1)).date()
    elif command == "/date":
        parts = text.strip().split()
        if len(parts) != 2:
            telegram_send_message_in_topic(
                token,
                chat_id,
                "Format: /date YYYY-MM-DD (also YYYY.MM.DD, DD.MM.YYYY)",
                message_thread_id=message_thread_id,
            )
            return
        try:
            target_date = parse_flexible_date(parts[1])
        except ValueError:
            telegram_send_message_in_topic(
                token,
                chat_id,
                "Date format must be YYYY-MM-DD (or YYYY.MM.DD, DD.MM.YYYY)",
                message_thread_id=message_thread_id,
            )
            return
    else:
        telegram_send_message_in_topic(
            token,
            chat_id,
            "Unknown command. Use /help",
            message_thread_id=message_thread_id,
        )
        return

    try:
        result, note = build_from_yandex(
            target_date=target_date,
            base_schedule_path=base_schedule_path,
            group=group,
            yandex_public_url=yandex_public_url,
            fallback_week1_start=fallback_week1_start,
        )
        text_out = format_schedule_text_telegram(result)
        if note:
            text_out = f"{text_out}\n\n{html.escape(note)}"
        telegram_send_message_in_topic(token, chat_id, text_out, message_thread_id=message_thread_id)
    except Exception:
        print("[ERROR] Failed to handle command:")
        print(traceback.format_exc())
        telegram_send_message_in_topic(
            token,
            chat_id,
            "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043f\u043e\u043b\u0443\u0447\u0438\u0442\u044c \u0440\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u0435. \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439 \u0435\u0449\u0435 \u0440\u0430\u0437 \u0447\u0443\u0442\u044c \u043f\u043e\u0437\u0436\u0435.",
            message_thread_id=message_thread_id,
        )


def _resolve_timezone(timezone: str) -> dt.tzinfo:
    try:
        return ZoneInfo(timezone)
    except Exception:
        if timezone == "Europe/Saratov":
            fallback = dt.timezone(dt.timedelta(hours=4), name="UTC+04:00")
        else:
            fallback = dt.timezone.utc
        print(f"Timezone '{timezone}' is unavailable, using fallback: {fallback}.")
        return fallback


def run_telegram_bot(
    token: str,
    base_schedule_path: Path,
    group: str,
    yandex_public_url: str,
    timezone: str,
    fallback_week1_start: dt.date | None,
    forced_thread_id: int | None = None,
) -> None:
    tz = _resolve_timezone(timezone)
    offset: int | None = None

    print("Bot started. Polling Telegram updates...")
    while True:
        try:
            updates = telegram_get_updates(token, offset)
            for update in updates:
                offset = int(update["update_id"]) + 1
                message = update.get("message") or {}
                chat = message.get("chat") or {}
                chat_id = chat.get("id")
                text = message.get("text")
                if not chat_id or not text:
                    continue
                incoming_thread_id = message.get("message_thread_id")
                outgoing_thread_id = forced_thread_id if forced_thread_id is not None else incoming_thread_id

                on_telegram_command(
                    token=token,
                    chat_id=int(chat_id),
                    text=str(text),
                    now=dt.datetime.now(tz=tz),
                    base_schedule_path=base_schedule_path,
                    group=group,
                    yandex_public_url=yandex_public_url,
                    fallback_week1_start=fallback_week1_start,
                    message_thread_id=outgoing_thread_id,
                )
        except urllib.error.URLError as exc:
            print(f"Network error: {exc}. Retry in 5 sec.")
            time.sleep(5)
        except Exception:
            print("[ERROR] Bot runtime failure:")
            print(traceback.format_exc())
            time.sleep(5)
