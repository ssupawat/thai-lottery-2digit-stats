#!/usr/bin/env python3
"""Check the official GLO API for today's lottery result and append it to
draws.json if it's new. Safe to run every day: does nothing on non-draw
days, and does nothing if today's draw is already recorded (so re-runs
and manual triggers are harmless).

NOTE: the request/response shape here is based on GLO's documented
example (curl + a published Google Apps Script snippet), not a live call
-- this repo's environment can't reach glo.or.th to test it directly.
Run this once by hand (workflow_dispatch) after a real draw and check the
output before trusting the daily schedule.
"""
import json
import sys
from datetime import datetime, timezone, timedelta

import requests

DRAWS_PATH = "draws.json"
GLO_URL = "https://www.glo.or.th/api/checking/getLotteryResult"

THAI_MONTHS = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
]


def bangkok_now():
    return datetime.now(timezone.utc) + timedelta(hours=7)


def thai_display(dt):
    return f"{dt.day} {THAI_MONTHS[dt.month]} {dt.year + 543}"


def fetch_last2(dt):
    payload = {
        "date": dt.strftime("%d"),
        "month": dt.strftime("%m"),
        "year": dt.strftime("%Y"),
    }
    resp = requests.post(GLO_URL, json=payload, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    # Best-effort unwrap -- adjust this block if GLO's actual response
    # shape turns out to differ once tested for real.
    result = data
    for key in ("response", "result", "data"):
        if isinstance(result, dict) and key in result:
            result = result[key]

    last2_block = result.get("last2") if isinstance(result, dict) else None
    if not last2_block:
        return None
    numbers = last2_block.get("number") if isinstance(last2_block, dict) else last2_block
    if not numbers:
        return None
    first = numbers[0]
    value = first.get("value") if isinstance(first, dict) else first
    return str(value).zfill(2) if value is not None else None


def main():
    today = bangkok_now()
    today_iso = today.strftime("%Y-%m-%d")

    with open(DRAWS_PATH, encoding="utf-8") as f:
        payload = json.load(f)
    draws = payload["draws"]

    if any(d == today_iso for d, _ in draws):
        print(f"{today_iso} already recorded -- nothing to do.")
        return

    try:
        last2 = fetch_last2(today)
    except Exception as exc:
        print(f"Could not reach GLO API for {today_iso}: {exc}")
        sys.exit(0)  # don't fail the workflow on a network hiccup

    if last2 is None:
        print(f"No draw posted for {today_iso} yet (or not a draw day).")
        return

    draws.append([today_iso, last2])
    draws.sort(key=lambda x: x[0])
    payload["draws"] = draws
    payload["updatedDisplay"] = thai_display(today)

    with open(DRAWS_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Added {today_iso} -> {last2}")


if __name__ == "__main__":
    main()
