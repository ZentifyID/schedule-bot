"""Yandex Disk public link integration."""

from __future__ import annotations

import datetime as dt
import json
import urllib.parse
import urllib.request
from typing import Any

YANDEX_API_RESOURCES = "https://cloud-api.yandex.net/v1/disk/public/resources"
YANDEX_API_DOWNLOAD = "https://cloud-api.yandex.net/v1/disk/public/resources/download"


def http_get_json(url: str, params: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{url}?{query}", method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read().decode("utf-8")
    return json.loads(data)


def http_get_bytes(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def yandex_list_public_files(public_url: str) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    limit = 200
    offset = 0

    while True:
        payload = http_get_json(
            YANDEX_API_RESOURCES,
            {"public_key": public_url, "limit": limit, "offset": offset},
        )
        if payload.get("type") == "file":
            return [payload]

        embedded = payload.get("_embedded", {})
        items = embedded.get("items", [])
        if not items:
            break
        files.extend([item for item in items if item.get("type") == "file"])

        total = embedded.get("total", len(files))
        offset += limit
        if offset >= total:
            break

    return files


def _parse_iso_dt(value: str | None) -> dt.datetime:
    if not value:
        return dt.datetime.min.replace(tzinfo=dt.timezone.utc)
    raw = value.strip().replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(raw)
    except ValueError:
        return dt.datetime.min.replace(tzinfo=dt.timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def find_replacement_docx_for_date(public_url: str, target_date: dt.date) -> dict[str, Any] | None:
    wanted = target_date.strftime("%d.%m.%Y")
    files = yandex_list_public_files(public_url)
    matches: list[dict[str, Any]] = []

    for item in files:
        name = str(item.get("name", ""))
        if not name.lower().endswith(".docx"):
            continue
        if wanted in name:
            matches.append(item)

    if not matches:
        return None

    # Prefer most recently modified file when multiple versions exist for one date.
    matches.sort(
        key=lambda item: (
            _parse_iso_dt(str(item.get("modified", ""))),
            _parse_iso_dt(str(item.get("created", ""))),
            str(item.get("name", "")),
        ),
        reverse=True,
    )
    return matches[0]


def yandex_download_docx(public_url: str, file_item: dict[str, Any]) -> bytes:
    direct = file_item.get("file")
    if direct:
        return http_get_bytes(str(direct))

    path = file_item.get("path")
    if not path:
        raise ValueError("Yandex item has neither direct file URL nor path")

    payload = http_get_json(YANDEX_API_DOWNLOAD, {"public_key": public_url, "path": path})
    href = payload.get("href")
    if not href:
        raise ValueError("No download URL returned by Yandex API")
    return http_get_bytes(str(href))
