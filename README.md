# thai-lottery-2digit-stats

PWA for Thai government lottery 2-digit stats. No backend (browser + GitHub Action only).

## Features

- All 100 two-digit numbers sorted by frequency (default) or by number (toggle)
- Filter by year range: 5 / 10 / 20 years — computed client-side from `draws.json`
- Search box — type 2 digits and scroll to that row with highlight
- Tap any number to see the actual draw dates within the selected range
- "Most frequent" / "Never drawn" chips update automatically for the selected range
- Installable on mobile (manifest + 3 icon sizes + apple-touch-icon)
- Offline support (service worker with stale-while-revalidate caching)
- Auto-updates data daily via GitHub Action polling the official GLO API

**Not included**: push notifications (requires a server to store subscriptions — conflicts with the no-backend requirement).

## Data (`draws.json`)

466 draws from 30 Dec 2006 to 16 Jul 2026:

| Period | Source | Verification |
|---|---|---|
| 2006–2024 | sanook.com (via CSV from [heart/Data-Set-Thai-Lotto](https://github.com/heart/Data-Set-Thai-Lotto)) | Frequency cross-checked against myhora.com 10-year stats — every number matches |
| 2025–2026 | myhora.com (year pages: `result-2568.aspx`, `result-2569.aspx`) | Transcribed dates and numbers, cross-checked against the "count" table on the same page — every number matches |

File structure:
```json
{
  "updatedDisplay": "16 กรกฎาคม 2569",
  "source": "sanook.com (2549-2567) + myhora.com (2568-2569)",
  "draws": [["2006-12-30","07"], ["2007-01-16","39"], ..., ["2026-07-16","71"]]
}
```

## Remaining

- GitHub Action has not run yet. Trigger manually: Actions tab → "Update lottery draws" → "Run workflow". The `update_draws.py` script has been tested against the live GLO API and parses responses correctly.
