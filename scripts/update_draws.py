#!/usr/bin/env python3
"""Ask the official GLO service for recent lottery results and add any
missing draws to draws.json. It is safe to run every day: it does nothing on
days without a draw, and running it twice does no harm.

NOTE: the message and answer shape here follow GLO's own example. It has
been working in the daily GitHub Action; this project's test machine can not
reach glo.or.th, so test any change with workflow_dispatch.
"""
import json
import sys
from datetime import datetime, timezone, timedelta

import requests

PATH = "draws.json"
GLO_ADDRESS = "https://www.glo.or.th/api/checking/getLotteryResult"
RECENT_DAYS = 7

THAI_MONTHS = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
]


def bangkok_time():
    return datetime.now(timezone.utc) + timedelta(hours=7)


def thai_text(day):
    return f"{day.day} {THAI_MONTHS[day.month]} {day.year + 543}"


def get_last_two(day):
    message = {
        "date": day.strftime("%d"),
        "month": day.strftime("%m"),
        "year": day.strftime("%Y"),
    }
    answer = requests.post(GLO_ADDRESS, json=message, timeout=20)
    answer.raise_for_status()
    data = answer.json()

    # Open each outer part of the answer. Change this part if GLO's real
    # answer looks different when we test it for real.
    result = data
    for key in ("response", "result", "data"):
        if isinstance(result, dict) and key in result:
            result = result[key]

    last_two_part = result.get("last2") if isinstance(result, dict) else None
    if not last_two_part:
        return None
    numbers = last_two_part.get("number") if isinstance(last_two_part, dict) else last_two_part
    if not numbers:
        return None
    first = numbers[0]
    value = first.get("value") if isinstance(first, dict) else first
    return str(value).zfill(2) if value is not None else None


def recent_days(today):
    return [today - timedelta(days=step) for step in range(RECENT_DAYS + 1)]


def main():
    today = bangkok_time()

    with open(PATH, encoding="utf-8") as file:
        content = json.load(file)
    draws = content["draws"]
    recorded_dates = {date for date, _ in draws}
    new_draws = []
    problems = []

    for draw_day in recent_days(today):
        draw_text = draw_day.strftime("%Y-%m-%d")
        if draw_text in recorded_dates:
            continue

        try:
            last_two = get_last_two(draw_day)
        except Exception as problem:
            problems.append(f"{draw_text}: {problem}")
            continue

        if last_two is not None:
            new_draws.append([draw_text, last_two])

    if problems:
        for problem in problems:
            print(f"Could not reach GLO for {problem}")
        sys.exit(1)

    if not new_draws:
        print("No new draws in the recent days.")
        return

    draws.extend(new_draws)
    draws.sort(key=lambda draw: draw[0])
    content["draws"] = draws
    newest_text = max(draw_text for draw_text, _ in new_draws)
    newest_day = datetime.strptime(newest_text, "%Y-%m-%d")
    content["updatedDisplay"] = thai_text(newest_day)

    with open(PATH, "w", encoding="utf-8") as file:
        json.dump(content, file, ensure_ascii=False, separators=(",", ":"))

    for draw_text, last_two in new_draws:
        print(f"Added {draw_text} -> {last_two}")


if __name__ == "__main__":
    main()
