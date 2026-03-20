"""Schedule parsing and merge logic."""

from __future__ import annotations

import copy
import csv
import datetime as dt
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

from .constants import (
    MONTHS_RU,
    ROMAN_ORDER,
    RU_DENOMINATOR,
    RU_NO,
    RU_NUMERATOR,
    WEEKDAY_RU,
    WEEKDAYS_WORKING,
    W_NS,
)


def normalize_group(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()


def normalize_week_type(value: str) -> str:
    text = value.casefold()
    if "\u0447\u0438\u0441\u043b" in text:
        return RU_NUMERATOR
    if "\u0437\u043d\u0430\u043c\u0435\u043d" in text:
        return RU_DENOMINATOR
    raise ValueError(f"Cannot detect week type from: {value!r}")


def normalize_pair(value: str) -> str:
    return re.sub(r"[^IVX]", "", value.upper())


def parse_flexible_date(value: str) -> dt.date:
    raw = value.strip()
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%d.%m.%Y"):
        try:
            return dt.datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {value}")


def text_from_node(node: ET.Element) -> str:
    parts: list[str] = []
    for item in node.findall(".//w:t", W_NS):
        if item.text:
            parts.append(item.text)
    return "".join(parts).strip()


def extract_xml_root_from_docx_bytes(docx_bytes: bytes) -> ET.Element:
    with zipfile.ZipFile(io.BytesIO(docx_bytes), "r") as archive:
        xml_bytes = archive.read("word/document.xml")
    return ET.fromstring(xml_bytes)


def extract_xml_root_from_docx_file(docx_path: Path) -> ET.Element:
    with zipfile.ZipFile(docx_path, "r") as archive:
        xml_bytes = archive.read("word/document.xml")
    return ET.fromstring(xml_bytes)


def parse_header_info(root: ET.Element) -> dict[str, Any]:
    paragraphs = [text_from_node(p) for p in root.findall(".//w:p", W_NS)]
    joined = "\n".join([p for p in paragraphs if p])
    upper_text = joined.upper()

    if "\u0427\u0418\u0421\u041b" in upper_text:
        week_type = RU_NUMERATOR
    elif "\u0417\u041d\u0410\u041c\u0415\u041d" in upper_text:
        week_type = RU_DENOMINATOR
    else:
        raise ValueError("Week type not found in document header")

    date_match = re.search(
        r"(\d{1,2})\s+([\u0410-\u042f\u0401]+)\s+(\d{4})\s*\u0433?\.?",
        joined,
        flags=re.IGNORECASE,
    )
    date_value: dt.date | None = None
    if date_match:
        day = int(date_match.group(1))
        month_raw = date_match.group(2).casefold()
        month = MONTHS_RU.get(month_raw)
        year = int(date_match.group(3))
        if month:
            date_value = dt.date(year, month, day)

    weekday_value: str | None = None
    for idx, weekday in WEEKDAY_RU.items():
        if idx > 6:
            continue
        if weekday.upper() in upper_text:
            weekday_value = weekday
            break
    if not weekday_value and date_value:
        weekday_value = WEEKDAY_RU[date_value.weekday()]

    return {"week_type": week_type, "date": date_value, "weekday": weekday_value}


def parse_replacements(root: ET.Element, target_group: str) -> list[dict[str, str]]:
    target = normalize_group(target_group)
    items: list[dict[str, str]] = []

    for table in root.findall(".//w:tbl", W_NS):
        for row in table.findall("./w:tr", W_NS):
            cells = [text_from_node(cell) for cell in row.findall("./w:tc", W_NS)]
            if len(cells) < 5:
                continue

            first_two = " ".join(cells[:2]).lower()
            if "\u043f\u0430\u0440\u0430" in first_two and "\u0433\u0440\u0443\u043f" in first_two:
                continue

            pair, group, old_item, new_item, room = [c.strip() for c in cells[:5]]
            if normalize_group(group) != target:
                continue

            items.append(
                {
                    "pair": pair,
                    "group": group,
                    "from": old_item,
                    "to": new_item,
                    "room": room,
                }
            )
    return items


def load_base_schedule(path: Path, group: str) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as fh:
        data = json.load(fh)
    if group not in data:
        raise KeyError(f"Group {group!r} not found in base schedule file")
    return data[group]


def empty_week_block() -> dict[str, list[dict[str, Any]]]:
    return {day: [] for day in WEEKDAYS_WORKING}


def apply_replacements(
    base_pairs: list[dict[str, Any]], replacements: list[dict[str, str]]
) -> list[dict[str, Any]]:
    result = [copy.deepcopy(item) for item in base_pairs]
    by_pair: dict[str, dict[str, str]] = {}

    for repl in replacements:
        pair_key = normalize_pair(repl["pair"])
        if pair_key:
            by_pair[pair_key] = repl

    seen: set[str] = set()
    for item in result:
        pair_key = normalize_pair(str(item.get("pair", "")))
        repl = by_pair.get(pair_key)
        if not repl:
            continue

        seen.add(pair_key)
        item["replacement"] = repl
        item["status"] = "cancelled" if repl["to"].strip().casefold() == RU_NO else "replaced"
        if item["status"] == "replaced":
            item["subject"] = repl["to"]
        if repl["room"] and repl["room"] != "-":
            item["room"] = repl["room"]

    for pair_key, repl in by_pair.items():
        if pair_key in seen:
            continue
        result.append(
            {
                "pair": repl["pair"],
                "subject": repl["to"],
                "teacher": "",
                "room": repl["room"],
                "status": "replacement_only",
                "replacement": repl,
            }
        )

    result.sort(key=lambda row: ROMAN_ORDER.get(normalize_pair(str(row.get("pair", ""))), 99))
    return result


def build_final_schedule_from_root(root: ET.Element, base_schedule_path: Path, group: str) -> dict[str, Any]:
    header = parse_header_info(root)
    replacements = parse_replacements(root, group)
    base = load_base_schedule(base_schedule_path, group)
    weekday = header["weekday"]
    if not weekday:
        raise ValueError("Cannot detect weekday from DOCX")

    week_block = base.get(header["week_type"], {})
    base_pairs = week_block.get(weekday, [])
    final_pairs = apply_replacements(base_pairs, replacements)

    return {
        "group": group,
        "date": header["date"].isoformat() if header["date"] else None,
        "weekday": weekday,
        "week_type": header["week_type"],
        "replacements_count": len(replacements),
        "pairs": final_pairs,
        "raw_replacements": replacements,
        "source": "docx",
    }


def build_final_schedule_from_docx_file(docx_path: Path, base_schedule_path: Path, group: str) -> dict[str, Any]:
    root = extract_xml_root_from_docx_file(docx_path)
    return build_final_schedule_from_root(root, base_schedule_path, group)


def build_base_only_schedule(
    target_date: dt.date,
    base_schedule_path: Path,
    group: str,
    week_type: str,
) -> dict[str, Any]:
    weekday = WEEKDAY_RU[target_date.weekday()]
    base = load_base_schedule(base_schedule_path, group)
    week_block = base.get(week_type, empty_week_block())
    pairs = [copy.deepcopy(item) for item in week_block.get(weekday, [])]
    return {
        "group": group,
        "date": target_date.isoformat(),
        "weekday": weekday,
        "week_type": week_type,
        "replacements_count": 0,
        "pairs": pairs,
        "raw_replacements": [],
        "source": "base",
    }


def format_schedule_text(result: dict[str, Any], title: str | None = None) -> str:
    lines: list[str] = []
    if title:
        lines.append(title)
    lines.append(f"\u0413\u0440\u0443\u043f\u043f\u0430: {result['group']}")
    lines.append(f"\u0414\u0430\u0442\u0430: {result['date'] or '(?)'}")
    lines.append(f"\u0414\u0435\u043d\u044c: {result['weekday']}")
    lines.append(f"\u041d\u0435\u0434\u0435\u043b\u044f: {result['week_type']}")
    lines.append(f"\u0417\u0430\u043c\u0435\u043d: {result['replacements_count']}")
    lines.append("")

    if not result["pairs"]:
        lines.append("\u041f\u0430\u0440 \u043d\u0430 \u044d\u0442\u043e\u0442 \u0434\u0435\u043d\u044c \u0432 \u0431\u0430\u0437\u043e\u0432\u043e\u043c \u0440\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u0438 \u043d\u0435\u0442.")
        return "\n".join(lines)

    for pair in result["pairs"]:
        pair_no = pair.get("pair", "?")
        subject = pair.get("subject", "")
        teacher = pair.get("teacher", "")
        room = pair.get("room", "")
        status = pair.get("status", "base")

        line = f"{pair_no}. {subject}"
        if teacher:
            line += f" ({teacher})"
        if room:
            line += f" | \u0430\u0443\u0434. {room}"
        if status == "replaced":
            line += " | \u0417\u0410\u041c\u0415\u041d\u0410"
        elif status == "cancelled":
            line += " | \u041e\u0422\u041c\u0415\u041d\u0410"
        elif status == "replacement_only":
            line += " | \u0422\u041e\u041b\u042c\u041a\u041e \u0412 \u0417\u0410\u041c\u0415\u041d\u0410\u0425"
        lines.append(line)
    return "\n".join(lines)


def build_json_from_csv(csv_path: Path, group: str, out_path: Path) -> None:
    base = {group: {RU_NUMERATOR: empty_week_block(), RU_DENOMINATOR: empty_week_block()}}

    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        required = {"week_type", "weekday", "pair", "subject", "teacher", "room"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("CSV must contain columns: week_type,weekday,pair,subject,teacher,room")

        for row in reader:
            week_type = normalize_week_type(row["week_type"])
            weekday = row["weekday"].strip().casefold()
            if weekday not in WEEKDAYS_WORKING:
                raise ValueError(f"Unknown weekday in CSV: {weekday!r}")

            lesson = {
                "pair": row["pair"].strip().upper(),
                "subject": row["subject"].strip(),
                "teacher": row["teacher"].strip(),
                "room": row["room"].strip(),
            }
            if not lesson["pair"] or not lesson["subject"]:
                continue
            base[group][week_type][weekday].append(lesson)

    for week_type in (RU_NUMERATOR, RU_DENOMINATOR):
        for weekday in WEEKDAYS_WORKING:
            base[group][week_type][weekday].sort(
                key=lambda item: ROMAN_ORDER.get(normalize_pair(item["pair"]), 99)
            )

    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(base, fh, ensure_ascii=False, indent=2)
