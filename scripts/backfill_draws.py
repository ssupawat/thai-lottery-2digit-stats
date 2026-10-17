#!/usr/bin/env python3
"""Rebuild the draw history from GLO's official API and compare it with
the current draws.json.

Writes two files and never touches draws.json:
  draws.glo.json   -- every draw GLO confirmed, in draws.json's shape
  backfill_report.txt -- what matched, what differs, what GLO didn't know

Candidate dates are the dates already in draws.json plus the nominal
1st/16th of every month in range, so shifted holiday draws are covered
without querying every day. Dates GLO returns nothing for are skipped
unless they were already in draws.json, in which case they're reported.

Like update_draws.py, this can't be tested from the dev environment
(glo.or.th is blocked); run it with workflow_dispatch.
"""
import importlib.util
import json
import sys
import time
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("update_draws", ROOT / "scripts" / "update_draws.py")
update_draws = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update_draws)

DRAWS_PATH = ROOT / "draws.json"
OUT_PATH = ROOT / "draws.glo.json"
REPORT_PATH = ROOT / "backfill_report.txt"
START = date(2006, 12, 1)
DELAY_SECONDS = 0.5
RETRIES = 3


def candidate_dates(existing_dates, today):
    candidates = {datetime.strptime(d, "%Y-%m-%d").date() for d in existing_dates}
    year, month = START.year, START.month
    while (year, month) <= (today.year, today.month):
        for day in (1, 16):
            candidate = date(year, month, day)
            if START <= candidate <= today:
                candidates.add(candidate)
        month += 1
        if month > 12:
            year, month = year + 1, 1
    return sorted(candidates)


def fetch_with_retry(draw_date, fetch=update_draws.fetch_last2, sleep=time.sleep):
    last_error = None
    for attempt in range(RETRIES):
        try:
            return fetch(draw_date)
        except Exception as exc:
            last_error = exc
            sleep(2 ** attempt)
    raise last_error


def compare(existing, official):
    """existing/official: {iso_date: last2}. Returns report buckets."""
    return {
        "matched": sorted(d for d in existing if official.get(d) == existing[d]),
        "mismatched": sorted((d, existing[d], official[d]) for d in existing
                             if d in official and official[d] != existing[d]),
        "missing_from_glo": sorted(d for d in existing if d not in official),
        "new_from_glo": sorted((d, official[d]) for d in official if d not in existing),
    }


def main():
    payload = json.loads(DRAWS_PATH.read_text(encoding="utf-8"))
    existing = {d: v for d, v in payload["draws"]}
    today = update_draws.bangkok_now().date()
    official = {}
    errors = []

    dates = candidate_dates(existing, today)
    print(f"Querying {len(dates)} candidate dates...")
    for index, draw_date in enumerate(dates, 1):
        iso = draw_date.strftime("%Y-%m-%d")
        try:
            value = fetch_with_retry(datetime.combine(draw_date, datetime.min.time()))
        except Exception as exc:
            errors.append(f"{iso}: {exc}")
            continue
        if value is not None:
            official[iso] = value
        if index % 50 == 0:
            print(f"  {index}/{len(dates)}")
        time.sleep(DELAY_SECONDS)

    report = compare(existing, official)
    lines = [
        f"candidates queried : {len(dates)}",
        f"confirmed by GLO   : {len(official)}",
        f"matches draws.json : {len(report['matched'])}",
        f"mismatched         : {len(report['mismatched'])}",
        f"missing from GLO   : {len(report['missing_from_glo'])}",
        f"new from GLO       : {len(report['new_from_glo'])}",
        f"request errors     : {len(errors)}",
        "",
    ]
    for label, key in (("MISMATCH (date, ours, GLO)", "mismatched"),
                       ("MISSING FROM GLO", "missing_from_glo"),
                       ("NEW FROM GLO", "new_from_glo")):
        if report[key]:
            lines.append(label)
            lines.extend(f"  {item}" for item in report[key])
            lines.append("")
    if errors:
        lines.append("REQUEST ERRORS")
        lines.extend(f"  {e}" for e in errors)

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = {
        "source": "สำนักงานสลากกินแบ่งรัฐบาล (glo.or.th)",
        "draws": sorted([d, v] for d, v in official.items()),
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n".join(lines))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
