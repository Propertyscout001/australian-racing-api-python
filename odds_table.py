#!/usr/bin/env python3
"""
odds_table.py -- an Australian racing odds comparison table in one file.

For each of the next Australian races it prints every runner down the side and every
bookmaker quoting the race across the top, and marks the best win price per runner.

    export PUNTERSEDGE_API_KEY=your_key      # free key, no card:
                                             # https://puntersedge.online/api?utm_source=demo&utm_medium=github&utm_campaign=odds-table&utm_content=script#signup
    python3 odds_table.py                    # next 3 Australian races, all codes
    python3 odds_table.py --category horse --races 5
    python3 odds_table.py --venue Caulfield --race 9          # one race on today's card
    python3 odds_table.py --html odds.html --csv odds.csv     # also write a web page and a CSV
    python3 odds_table.py --sample           # no key: the keyless sandbox teaser
                                             # (3 races, 5 runners, 3 prices each), NOT the full feed

Standard library only, Python 3.9+. One request per run to GET /v1/racing/next-to-go,
which costs 2 credits for up to 20 races. The free plan's 3,000 credits a month is about
1,500 runs.

Licence: running this for yourself is personal use, which every plan covers. Showing the
table to other people (on a website, in an app, in a paid group) is the Display licence on
the Plus plan, and needs the "Prices by PuntersEdge" credit the --html page carries. Read
section 8.1 of https://puntersedge.online/terms before you publish it.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import html
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

API = "https://api.puntersedge.online/v1"
SIGNUP = "https://puntersedge.online/api?utm_source=demo&utm_medium=github&utm_campaign=odds-table&utm_content=script#signup"
UA = "puntersedge-examples/odds-table (+https://github.com/Propertyscout001/australian-racing-api-python)"
SYDNEY = ZoneInfo("Australia/Sydney")

# Short column headers so a 15-book race still fits a terminal. Unknown keys fall back
# to the first five letters of the key, so a newly added bookmaker still shows up.
ABBREV = {
    "tab": "TAB", "tabtouch": "TTCH", "betdeluxe": "BDLX", "betr_au": "BETR",
    "pointsbetau": "PBET", "betright": "BRGT", "playup": "NEXTB", "palmerbet": "PALM",
    "unibet": "UNI", "neds": "NEDS", "ladbrokes_au": "LADB", "sportsbet": "SPBT",
    "betgold": "BGLD", "boostbet": "BOOST", "bet365_au": "B365", "bet365": "B365",
}


class ApiError(Exception):
    pass


def fetch(path: str, params: dict, key: str | None) -> tuple[object, dict]:
    """GET one endpoint and return (json, headers). Retries once on 429, 5xx or a dropped
    connection; turns every other failure into a message a person can act on."""
    url = f"{API}{path}?{urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})}"
    headers = {"User-Agent": UA, "Accept-Encoding": "gzip"}
    if key:
        headers["X-API-Key"] = key
    for attempt in (1, 2):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                return json.loads(body), {k.lower(): v for k, v in resp.headers.items()}
        except urllib.error.HTTPError as e:
            raw = e.read()
            if e.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            try:
                problem = json.loads(raw)
                detail = problem.get("detail") or problem.get("title") or raw.decode()[:300]
            except (ValueError, AttributeError):
                detail = raw.decode("utf-8", "replace")[:300]
            if (e.code == 429 or e.code >= 500) and attempt == 1:
                wait = min(int(e.headers.get("Retry-After") or 5), 30)
                print(f"HTTP {e.code}, retrying in {wait}s ...", file=sys.stderr)
                time.sleep(wait)
                continue
            hint = {
                401: "The key was not accepted. Check PUNTERSEDGE_API_KEY, and note a new free key "
                     "only works after you click the link in its verification email.",
                402: "This key has used its credits for the month. They reset on the 1st; GET /v1/usage is free.",
                403: "This endpoint or option is not on your plan.",
                422: "A parameter was rejected; the message above names the valid values.",
                429: "Rate limited twice in a row. Wait a minute and run it again.",
            }.get(e.code, "")
            raise ApiError(f"HTTP {e.code}: {detail}\n{hint}".strip())
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == 1:
                print(f"network error ({e}), retrying in 3s ...", file=sys.stderr)
                time.sleep(3)
                continue
            raise ApiError(f"Could not reach {API}: {e}")
    raise ApiError("unreachable")


def load_races(args, key: str | None) -> tuple[list, dict, bool]:
    """Return (races, response headers, is_sample)."""
    if args.sample:
        data, hdrs = fetch("/demo/racing/next-to-go", {}, None)
        return data.get("races", []), hdrs, True
    params = {
        "country": "AU",
        # Most of an Australian card has no country label until the meeting is confirmed,
        # so country=AU on its own silently drops races. include_unresolved brings them
        # back; we keep only AU and still-unlabelled races below.
        "include_unresolved": "true",
        "categories": args.category,
        "venue": args.venue,
        "num_races": 20,  # 20 is the most a 2-credit call returns; we trim locally
    }
    data, hdrs = fetch("/racing/next-to-go", params, key)
    races = [r for r in data if r.get("country") in ("AU", None)]
    if args.race:
        races = [r for r in races if r.get("race_number") == args.race]
    return races[: args.races], hdrs, False


def best_price(runner: dict) -> tuple[float | None, list[str]]:
    """Highest fresh win price for a runner and every book offering it."""
    fresh = [b for b in runner.get("bookmakers", []) if b.get("win_price") and not b.get("stale")]
    if not fresh:
        return None, []
    top = max(b["win_price"] for b in fresh)
    return top, sorted(b["key"] for b in fresh if b["win_price"] == top)


def book_columns(race: dict) -> list[str]:
    """Bookmakers quoting this race, most runners priced first."""
    counts: dict[str, int] = {}
    for r in race.get("runners", []):
        for b in r.get("bookmakers", []):
            if b.get("win_price"):
                counts[b["key"]] = counts.get(b["key"], 0) + 1
    return sorted(counts, key=lambda k: (-counts[k], k))


def race_heading(race: dict, now: dt.datetime) -> str:
    start = dt.datetime.fromisoformat(race["start_time"].replace("Z", "+00:00"))
    mins = round((start - now).total_seconds() / 60)
    jump = f"jumps in {mins} min" if mins >= 0 else f"due {-mins} min ago"
    local = start.astimezone(SYDNEY)
    country = race.get("country") or "country not yet confirmed"
    return (f"{race['venue']} R{race['race_number']}  {local:%a %H:%M} {local.tzname()}  {jump}"
            f"  ({race.get('category', '?')}, {country})")


def print_race(race: dict, now: dt.datetime) -> None:
    books = book_columns(race)
    head = race_heading(race, now)
    print(f"\n{head}\n{'-' * len(head)}")
    if not books:
        print("no bookmaker prices yet")
        return
    cols = [ABBREV.get(k, k[:5].upper()) for k in books]
    print(f"{'#':>3}  {'runner':<20}" + "".join(f"{c:>7}" for c in cols) + f"{'best':>8}  book")
    for r in sorted(race.get("runners", []), key=lambda x: x.get("number") or 0):
        top, top_books = best_price(r)
        legs = {b["key"]: b for b in r.get("bookmakers", []) if b.get("win_price")}
        cells = []
        for k in books:
            b = legs.get(k)
            if not b:
                cells.append(f"{'-':>7}")
            elif b.get("stale"):
                cells.append(f"{'(%.2f)' % b['win_price']:>7}")
            else:
                mark = "*" if k in top_books else " "
                cells.append(f"{b['win_price']:>6.2f}{mark}")
        best = f"{top:>8.2f}" if top else f"{'-':>8}"
        names = ",".join(ABBREV.get(k, k) for k in top_books[:3])
        print(f"{r.get('number', ''):>3}  {r.get('name', '')[:20]:<20}" + "".join(cells) + f"{best}  {names}")
    scratched = race.get("scratchings") or []
    if scratched:
        print("scratched: " + ", ".join(f"{s.get('number', '')} {s.get('name', '')}".strip() for s in scratched))


def write_csv(path: str, races: list) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["race_id", "venue", "race_number", "start_time_utc", "category", "runner_number",
                    "runner", "bookmaker", "win_price", "place_price", "age_seconds", "stale", "is_best"])
        for race in races:
            for r in race.get("runners", []):
                _, top_books = best_price(r)
                for b in r.get("bookmakers", []):
                    if not b.get("win_price"):
                        continue
                    w.writerow([race.get("race_id"), race.get("venue"), race.get("race_number"),
                                race.get("start_time"), race.get("category"), r.get("number"), r.get("name"),
                                b["key"], b.get("win_price"), b.get("place_price"), b.get("age_seconds"),
                                bool(b.get("stale")), b["key"] in top_books])


def write_html(path: str, races: list, now: dt.datetime, sample: bool) -> None:
    e = html.escape
    parts = []
    for race in races:
        books = book_columns(race)
        rows = []
        for r in sorted(race.get("runners", []), key=lambda x: x.get("number") or 0):
            top, top_books = best_price(r)
            legs = {b["key"]: b for b in r.get("bookmakers", []) if b.get("win_price")}
            tds = []
            for k in books:
                b = legs.get(k)
                if not b:
                    tds.append('<td class="na">–</td>')
                elif b.get("stale"):
                    tds.append(f'<td class="stale" title="stale quote">{b["win_price"]:.2f}</td>')
                else:
                    cls = ' class="best"' if k in top_books else ""
                    tds.append(f"<td{cls}>{b['win_price']:.2f}</td>")
            best = f"{top:.2f}" if top else "–"
            rows.append(f'<tr><th scope="row"><span class="no">{e(str(r.get("number", "")))}</span> '
                        f'{e(r.get("name", ""))}</th>{"".join(tds)}<td class="bestcol">{best}</td></tr>')
        hdr = "".join(f'<th scope="col">{e(ABBREV.get(k, k[:5].upper()))}</th>' for k in books)
        parts.append(f'<section><h2>{e(race_heading(race, now))}</h2><div class="scroll"><table>'
                     f'<thead><tr><th scope="col">Runner</th>{hdr}<th scope="col">Best</th></tr></thead>'
                     f'<tbody>{"".join(rows)}</tbody></table></div></section>')
    banner = ('<p class="banner">Sample data from the keyless sandbox (3 races, 5 runners, best 3 prices '
              'per runner). Not the full feed.</p>') if sample else ""
    captured = now.astimezone(SYDNEY)
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Australian racing odds comparison</title>
<style>
:root{{--ink:#14201a;--muted:#5b6b62;--line:#d9e0db;--best:#e6f4ea;--bestink:#0b6b2e;--bg:#fbfcfb}}
body{{margin:0;padding:24px 16px;font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--ink);background:var(--bg)}}
main{{max-width:1100px;margin:0 auto}} h1{{font-size:22px;margin:0 0 4px}} h2{{font-size:16px;margin:28px 0 8px}}
.meta{{color:var(--muted);margin:0 0 8px}} .banner{{background:#fff4d6;border:1px solid #e8c774;padding:8px 12px;border-radius:6px}}
.scroll{{overflow-x:auto}} table{{border-collapse:collapse;font-variant-numeric:tabular-nums;min-width:100%}}
th,td{{padding:6px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}}
thead th{{font-size:12px;color:var(--muted);font-weight:600}} thead th:first-child{{text-align:left}} tbody th{{text-align:left;font-weight:500}}
.no{{display:inline-block;min-width:1.6em;color:var(--muted)}} td.best{{background:var(--best);color:var(--bestink);font-weight:700}}
td.stale{{color:#9aa59f;text-decoration:line-through}} td.na{{color:#b8c1bb}} td.bestcol{{font-weight:700}}
footer{{margin-top:28px;color:var(--muted);font-size:13px}} footer a{{color:inherit}}
</style></head><body><main>
<h1>Australian racing odds comparison</h1>
<p class="meta">Win prices captured {captured:%a %d %b %Y %H:%M} {captured.tzname()}. Best fresh price per runner highlighted;
struck-through prices are stale quotes. Prices move constantly; check the bookmaker before acting.</p>
{banner}
{"".join(parts) or "<p>No Australian races with prices in the window.</p>"}
<footer><p><a href="https://puntersedge.online">Prices by PuntersEdge</a></p>
<p>18+. Gambling involves risk. Gambling Help 1800 858 858 · gamblinghelponline.org.au</p></footer>
</main></body></html>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)


def main() -> int:
    p = argparse.ArgumentParser(description="Australian racing odds comparison table (PuntersEdge API)")
    p.add_argument("--races", type=int, default=3, help="how many races to show (default 3, max 20)")
    p.add_argument("--category", choices=["horse", "greyhound", "harness"], help="one racing code only")
    p.add_argument("--venue", help="one meeting, spelt as the API spells it, e.g. Caulfield")
    p.add_argument("--race", type=int, help="race number at --venue")
    p.add_argument("--html", metavar="FILE", help="also write the tables as a web page")
    p.add_argument("--csv", metavar="FILE", help="also write every price as CSV rows")
    p.add_argument("--sample", action="store_true", help="keyless sandbox sample instead of the live feed")
    args = p.parse_args()
    args.races = max(1, min(args.races, 20))

    key = os.environ.get("PUNTERSEDGE_API_KEY") or os.environ.get("PE_API_KEY")
    if not key and not args.sample:
        print("Set PUNTERSEDGE_API_KEY first. A free key takes a minute and needs no card:\n"
              f"  {SIGNUP}\nOr run with --sample to see the keyless sandbox teaser.", file=sys.stderr)
        return 2

    try:
        races, hdrs, sample = load_races(args, key)
    except ApiError as err:
        print(err, file=sys.stderr)
        return 1

    now = dt.datetime.now(dt.timezone.utc)
    if sample:
        print("SAMPLE: keyless sandbox, truncated to 3 races, 5 runners and the best 3 prices per runner.\n"
              f"It is a teaser, not the full feed. Free key for the real table: {SIGNUP}")
    if not races:
        where = f" at {args.venue}" if args.venue else ""
        print(f"No Australian races with prices{where} in the next 24 hours. Venue names must match the "
              "API's spelling: run without --venue to see them.")
        return 0
    for race in races:
        print_race(race, now)
    print("\n* best fresh win price   (x.xx) stale quote, left out of 'best'   - not quoted")

    cost, left, limit = (hdrs.get(h) for h in ("x-credits-cost", "x-credits-remaining", "x-credits-limit"))
    if cost:
        print(f"credits: this call {cost}, remaining {left} of {limit}", file=sys.stderr)
    if args.csv:
        write_csv(args.csv, races)
        print(f"wrote {args.csv}", file=sys.stderr)
    if args.html:
        write_html(args.html, races, now, sample)
        print(f"wrote {args.html}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
