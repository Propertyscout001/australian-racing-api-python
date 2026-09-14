#!/usr/bin/env python3
"""
quickstart.py -- print the next Australian races as a runner x bookmaker price grid.

    python3 quickstart.py                 # keyless demo data, no registration
    export PE_API_KEY=...                 # then the real feed, all 14 books
    python3 quickstart.py --races 3 --category horse

No dependencies. Python 3.8+.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys

from racing_api import (
    RacingAPI,
    RacingAPIError,
    RateLimited,
    SIGNUP_URL,
    books_in_race,
    prices_by_book,
    scratched_numbers,
)

# Four-character column headers, so a 13-book grid still fits a terminal.
ABBREV = {
    "tab": "TAB", "tabtouch": "TTCH", "betdeluxe": "BDLX", "betr_au": "BETR",
    "pointsbetau": "PBET", "betright": "BRGT", "playup": "PLAY",
    "palmerbet": "PALM", "unibet": "UNI", "neds": "NEDS",
    "ladbrokes_au": "LADB", "sportsbet": "SPBT", "betgold": "BGLD",
    "boostbet": "BOST",
}


def abbrev(key: str) -> str:
    return ABBREV.get(key, key[:4].upper())


def local_time(iso_utc: str) -> str:
    """Render a UTC start_time in the reader's local clock.

    The feed is UTC. Australian racing is discussed in AEST/AEDT, so a bare
    UTC timestamp reads as the wrong race to anyone checking it against a form
    guide.
    """
    try:
        when = dt.datetime.strptime(iso_utc, "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return str(iso_utc)
    when = when.replace(tzinfo=dt.timezone.utc).astimezone()
    return when.strftime("%H:%M %Z")


def mins_to_jump(iso_utc: str):
    try:
        when = dt.datetime.strptime(iso_utc, "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return None
    when = when.replace(tzinfo=dt.timezone.utc)
    return (when - dt.datetime.now(dt.timezone.utc)).total_seconds() / 60.0


def print_race(race: dict) -> None:
    books = books_in_race(race)
    scratched = scratched_numbers(race)

    mins = mins_to_jump(race.get("start_time"))
    when = local_time(race.get("start_time"))
    jump = "%+.0f min" % mins if mins is not None else "?"

    header = "%s R%s  %s  %s (%s, %s)" % (
        race.get("venue"),
        race.get("race_number"),
        when,
        jump,
        race.get("category"),
        race.get("country"),
    )
    print()
    print(header)
    print("-" * max(len(header), 30))

    if not books:
        print("  no bookmaker prices on this race yet")
        return

    name_w = max([len(r.get("name", "")) for r in race.get("runners") or []] + [10])
    name_w = min(name_w, 24)

    cols = "".join("%7s" % abbrev(b) for b in books)
    print("%-3s %-*s %s %7s" % ("#", name_w, "runner", cols, "best"))

    for runner in race.get("runners") or []:
        prices = prices_by_book(runner)
        if not prices:
            continue
        best = max(prices.values())
        cells = ""
        for book in books:
            price = prices.get(book)
            if price is None:
                cells += "%7s" % "-"
            elif price == best:
                # the top price on this runner, across the books quoting it
                cells += "%6.2f*" % price
            else:
                cells += "%7.2f" % price
        flag = " SCR" if runner.get("number") in scratched else ""
        name = runner.get("name", "")[:name_w]
        print("%-3s %-*s %s %7.2f%s" % (
            runner.get("number", ""), name_w, name, cells, best, flag))

    stale = race.get("stale_bookmakers")
    age = race.get("data_age_seconds")
    notes = []
    if age is not None:
        notes.append("oldest price %ss old" % age)
    if stale:
        notes.append("stale: %s" % ", ".join(stale))
    vacant = [s for s in (race.get("scratchings") or []) if s.get("vacant")]
    real_scr = [s for s in (race.get("scratchings") or []) if not s.get("vacant")]
    if real_scr:
        notes.append("scratched: %s" % ", ".join(
            "%s (%s)" % (s.get("name"), s.get("number")) for s in real_scr))
    if vacant:
        notes.append("%d vacant box placeholder(s)" % len(vacant))
    if notes:
        print("  " + " | ".join(notes))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--races", type=int, default=3, help="how many races (default 3)")
    parser.add_argument("--country", default="AU", help="ISO codes, comma separated (default AU)")
    parser.add_argument("--category", default=None, help="horse, greyhound or harness")
    parser.add_argument("--venue", default=None, help="venue name, e.g. Randwick")
    parser.add_argument("--json", action="store_true", help="dump raw JSON instead of the grid")
    args = parser.parse_args(argv)

    with RacingAPI() as api:
        if api.demo:
            print("mode: DEMO (no PE_API_KEY set) -- keyless sandbox, 0 credits,")
            print("      3 races / 5 runners / best 3 prices, rate limited to 30 req/min per IP.")
            print("      Free key unlocks the full feed: %s" % SIGNUP_URL)
        else:
            print("mode: KEYED -- live feed, all quoting bookmakers")

        try:
            races = api.next_to_go(
                country=args.country,
                num_races=args.races,
                categories=args.category,
                venue=args.venue,
            )
        except RateLimited as exc:
            print("\nrate limited: %s" % exc.detail, file=sys.stderr)
            return 2
        except RacingAPIError as exc:
            # RFC 9457 problem+json: the useful text is .detail
            print("\nAPI error %s: %s" % (exc.status, exc.detail), file=sys.stderr)
            return 1

        if args.json:
            print(json.dumps(races, indent=2))
            return 0

        if not races:
            print("\nno races returned for country=%s" % args.country)
            return 0

        for race in races:
            print_race(race)

        credits = api.last_credits
        print()
        if api.demo:
            print("%d race(s). Demo responses carry no X-Credits-* headers -- "
                  "they cost 0." % len(races))
        else:
            print("%d race(s). X-Credits-Cost: %s  X-Credits-Remaining: %s" % (
                len(races), credits.cost, credits.remaining))
            if credits.remaining == "unlimited":
                print("('unlimited' means this key has no monthly cap. A free-tier key "
                      "reports")
                print(" the integer left of its 1,500 credits/month here.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
