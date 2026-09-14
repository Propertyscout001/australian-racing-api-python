#!/usr/bin/env python3
"""
tour.py -- call every method on RacingAPI once and print a compact real result.

Needs PE_API_KEY. Documentation by execution: if this prints, the client works
against the live API. Total cost is roughly 18 credits (2+1+1+2+3+3+3+3).

    export PE_API_KEY=...
    python3 tour.py
"""

from __future__ import annotations

import datetime as dt
import sys
from collections import Counter

from racing_api import RacingAPI, RacingAPIError, NeedsKey, SIGNUP_URL, books_in_race


def rule(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def credits(api: RacingAPI) -> str:
    c = api.last_credits
    return "  [cost %s, remaining %s]" % (c.cost, c.remaining)


def main() -> int:
    api = RacingAPI()
    if api.demo:
        print("tour.py needs a key. Free tier, 1,500 credits/month: %s" % SIGNUP_URL)
        return 1

    with api:
        rule("next_to_go(country='AU')  -- 2 credits")
        races = api.next_to_go(country="AU", num_races=3)
        for r in races:
            print("  %-16s R%-2s %-10s %s  %2d books" % (
                r["venue"], r["race_number"], r["category"], r["start_time"],
                len(books_in_race(r))))
        print(credits(api))

        rule("next_to_go(country=None)  -- the filter matters")
        unfiltered = api.next_to_go(country=None, num_races=6)
        for r in unfiltered:
            print("  %-3s %-20s R%-2s %s" % (
                r.get("country"), r["venue"], r["race_number"], r["start_time"]))
        au = sum(1 for r in unfiltered if r.get("country") == "AU")
        print("  -> %d of these %d races are Australian" % (au, len(unfiltered)))
        print(credits(api))

        rule("events(country='AU')  -- 1 credit, no prices")
        evs = api.events(country="AU", hours_ahead=4)
        print("  %d races in the next 4h" % len(evs))
        for e in evs[:4]:
            print("    %-16s R%-2s %-10s %s" % (
                e.get("venue"), e.get("race_number"), e.get("category"),
                e.get("start_time")))
        print(credits(api))

        rule("venues()  -- 1 credit, the join table")
        vs = api.venues()
        print("  %d venues: %s" % (
            len(vs),
            ", ".join("%s=%d" % kv for kv in
                      Counter(v["country"] for v in vs).most_common())))
        multi = [v for v in vs if len(v["spellings"]) > 1]
        print("  %d venues emit more than one spelling, e.g." % len(multi))
        for v in multi[:3]:
            print("    %-20s spellings=%s" % (v["venue_canonical"], v["spellings"]))
        split = [v for v in vs if v["venue_site"] != v["venue_id"]]
        print("  %d venues have venue_site != venue_id, e.g." % len(split))
        for v in split[:4]:
            print("    %-24s venue_id=%-24s venue_site=%s" % (
                v["venue_canonical"], v["venue_id"], v["venue_site"]))
        print(credits(api))

        rule("results(country='AU')  -- 2 credits")
        res = api.results(country="AU", limit=200, hours_back=24)
        print("  %d settled AU races in the last 24h: %s" % (
            len(res),
            ", ".join("%s=%d" % kv for kv in
                      Counter(r["category"] for r in res).most_common())))
        print("  %d of them have race_id=null (join on venue_site + race_number + date)"
              % sum(1 for r in res if r.get("race_id") is None))
        for r in res[:2]:
            top = (r.get("placings") or [{}])[0]
            print("    %-16s R%-2s  won by %-20s @ %s" % (
                r["venue"], r["race_number"], top.get("name"), top.get("win_price")))
        print(credits(api))

        rule("best_odds(country='AU')  -- 3 credits")
        bo = api.best_odds(country="AU", num_races=2)
        for r in bo:
            print("  %-16s R%-2s  market %.1f%% across %s books" % (
                r["venue"], r["race_number"], r["market_percentage"],
                r["books_compared"]))
            for runner in (r.get("runners") or [])[:3]:
                bw = runner.get("best_win") or {}
                print("     %-22s %-6s at %-12s (%s books, spread %s%%)" % (
                    runner.get("name"), bw.get("price"), bw.get("bookmaker"),
                    runner.get("books_quoting_win"), runner.get("price_spread_pct")))
        print(credits(api))

        rule("movers(country='AU', direction='firming')  -- 3 credits")
        mv = api.movers(country="AU", direction="firming", min_move_pct=10, limit=5)
        if not mv:
            print("  0 rows. Normal before a card opens -- no consensus has formed yet.")
        for m in mv[:5]:
            print("  %-16s R%-2s %-20s %s%% %s" % (
                m.get("venue"), m.get("race_number"), m.get("runner") or m.get("name"),
                m.get("move_pct"), m.get("direction")))
        print(credits(api))

        rule("price_history(...)  -- 5 credits, the free-tier closing line")
        # Ask for a settled race that carries the price feed's race_id. A
        # results row with race_id=null was never matched into the price feed,
        # and no venue-name spelling will conjure history for it -- verified
        # below against "the-q" and "Q Straight" alike.
        settled = next((r for r in res if r.get("race_id")), None)
        day = settled["start_time"][:10]
        try:
            ph = api.price_history(race_id=settled["race_id"], max_points=100)
            print("  %s R%s on %s  (%d points returned, truncated=%s)" % (
                ph["venue"], ph["race_number"], day,
                ph["points_returned"], ph["truncated"]))
            print("  results spelled this venue %r, price_history spelled it %r."
                  % (settled["venue"], ph["venue"]))
            print("  Join on venue_id (%r) / venue_site (%r), never on the label."
                  % (ph["venue_id"], ph["venue_site"]))
            for runner in (ph.get("runners") or [])[:2]:
                print("    %s" % runner["name"])
                for b in (runner.get("bookmakers") or [])[:4]:
                    print("      %-12s open %-6s close %-6s move %+6.1f%%  (%d pts)" % (
                        b["key"], b["open_price"], b["close_price"],
                        b["move_pct"], b["points_count"]))
        except RacingAPIError as exc:
            print("  %s %s" % (exc.status, exc.detail))
        print(credits(api))

        orphan = next((r for r in res if r.get("race_id") is None), None)
        if orphan:
            print("  and a results row with race_id=null has no history under any")
            print("  spelling -- %r (venue_id=%r, venue_site=%r):" % (
                orphan["venue"], orphan["venue_id"], orphan["venue_site"]))
            for label in (orphan["venue"], orphan["venue_site"]):
                try:
                    api.price_history(venue=label,
                                      race_number=orphan["race_number"],
                                      date=orphan["start_time"][:10],
                                      max_points=100)
                    print("    venue=%-14r -> 200" % label)
                except RacingAPIError as exc:
                    print("    venue=%-14r -> %s" % (label, exc.status))

        rule("horse_form(...)  -- 3 credits, and a name is not a key")
        first = api.horse_form("Lord Of Valor")
        if first.get("ambiguous"):
            print("  ambiguous=True, %d candidates share that name:"
                  % len(first["candidates"]))
            for c in first["candidates"]:
                print("    %-22s last seen %s via %s" % (
                    c["runner_ref"], c["last_seen"], c["source"]))
            ref = first["candidates"][0]["runner_ref"]
            print("  re-calling with runner_ref=%s" % ref)
            form = api.horse_form(ref)
        else:
            form = first
        prof, car = form.get("profile") or {}, form.get("career") or {}
        print("  %s -- %s, by %s out of %s, trained by %s" % (
            form.get("horse_name"), prof.get("age_sex"), prof.get("sire"),
            prof.get("dam"), prof.get("trainer")))
        print("  career %s starts, %s wins, %s seconds, $%s prizemoney" % (
            car.get("starts"), car.get("wins"), car.get("seconds"),
            car.get("prizemoney")))
        for run in (form.get("runs") or [])[:3]:
            print("    %s  %-5s R%-2s  %s  %sm %s  jockey %s  SP %s" % (
                run["date"], run["track"], run["race_number"], run["result_raw"],
                run["distance_m"], run["going"], run["jockey"], run["sp"]))
        print(credits(api))

        rule("errors are RFC 9457 problem+json")
        try:
            api.price_history(race_id="00000000-0000-0000-0000-000000000000")
        except RacingAPIError as exc:
            print("  status : %s" % exc.status)
            print("  type   : %s" % exc.type)
            print("  detail : %s" % exc.detail)

        rule("guard rails that cost you nothing (no request is sent)")
        for call, label in (
            (lambda: api.movers(direction="steam"), 'movers(direction="steam")'),
            (lambda: api.price_history(venue="Randwick"), 'price_history(venue only)'),
            (lambda: api.price_history(race_id="x", max_points=10), 'max_points=10'),
        ):
            try:
                call()
            except ValueError as exc:
                print("  %-34s -> ValueError: %s" % (label, exc))

        print()
        print("done. final credit state: %r" % (api.last_credits,))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
