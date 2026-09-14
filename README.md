# Australian racing API — Python client

A single-file Python client for Australian and New Zealand racing odds: thoroughbred,
harness and greyhound, with every quoting bookmaker's price per runner. Stdlib only —
no `pip install`, no virtualenv, no dependency tree. Clone it and run it.

It reads the [PuntersEdge](https://puntersedge.online/developers/getting-started?utm_source=australian-racing-api-python&utm_medium=readme)
racing feed: live prices for AU thoroughbred/harness/greyhound and NZ thoroughbred/harness,
plus settled results, per-runner price history, and thoroughbred form. 14 Australian
bookmakers were served when this was built (`served_bookmaker_count: 14` on the
[coverage report](https://puntersedge.online/coverage-report?utm_source=australian-racing-api-python&utm_medium=readme),
measured over the 7 days to 2026-09-14; the same field for NZ reads 12). Read that report
rather than trusting the number here — it is recomputed every 30 minutes, this file is not.

There is **no exchange price in this feed**. The coverage report lists Betfair Exchange and
Pinnacle as explicitly excluded, so if you need exchange liquidity or an overround-free
reference price, this is not the source for it.

## Run it without an API key

```sh
git clone https://github.com/Propertyscout001/australian-racing-api-python
cd australian-racing-api-python
python3 quickstart.py
```

That's it. No registration, no key, no install. The client falls back to the keyless
sandbox endpoint when `PE_API_KEY` is unset. That sandbox is rate limited to 30 requests a
minute per IP — easy to trip if you loop on it. `quickstart.py` catches the 429, prints the
API's message and exits 2 (section 4 of [`docs/output.txt`](docs/output.txt) is a real
transcript of that). Recovery is quick — a 200 came back inside 15 seconds on two probes —
so wait a moment and re-run, or
[take a free key](https://puntersedge.online/api?utm_source=australian-racing-api-python&utm_medium=readme)
and skip the queue.

Real output, verbatim, captured 2026-09-15 09:50 AEST (whole transcript in
[`docs/output.txt`](docs/output.txt)):

```
mode: DEMO (no PE_API_KEY set) -- keyless sandbox, 0 credits,
      3 races / 5 runners / best 3 prices, rate limited to 30 req/min per IP.
      Free key unlocks the full feed: https://puntersedge.online/api?utm_source=australian-racing-api-python&utm_medium=code

Angle Park R1  11:38 AEST  +107 min (greyhound, AU)
---------------------------------------------------
#   runner             LADB   NEDS   PBET   SPBT   BRGT   PALM    UNI   BDLX    TAB    best
1   Alia Rose        14.00* 14.00* 14.00*      -      -      -      -      -      -   14.00
2   Sandy Knuckles    5.00*  5.00*      -  5.00*      -      -      -      -      -    5.00
4   Adhana Remi           -      -      -      -  3.00*  3.00*   2.90      -      -    3.00
5   Whiplash Emmett       -      - 29.00*      -      -  26.00      -  26.00      -   29.00
7   Twitching          2.20      -      -      -  2.25*      -      -      -  2.25*    2.25

Hobart R1  11:45 AEST  +114 min (greyhound, AU)
-----------------------------------------------
#   runner              TAB   BRGT   SPBT   PALM   BDLX   LADB    UNI   PBET   NEDS    best
1   Juneau Quadrant   6.00*  6.00*   5.50      -      -      -      -      -      -    6.00
2   Miss Bern             -      -  5.00*  5.00*  5.00*      -      -      -      -    5.00
3   Miss Sue Lee          -      -      -      -      - 12.00* 12.00* 12.00*      -   12.00
4   Listen Spider         -  5.00*      -      -      -  5.00*  5.00*      -      -    5.00
5   Jamella Storm         -      -      -  4.40*      -      -      -  4.40*  4.40*    4.40

Angle Park R2  11:55 AEST  +124 min (greyhound, AU)
---------------------------------------------------
#   runner            BRGT    TAB   NEDS   TTCH   BDLX   PALM   PBET    best
1   Canya Jump       2.40*  2.40*   2.35      -      -      -      -    2.40
4   Blue Energy      3.90*  3.90*      -   3.80      -      -      -    3.90
5   Velaris          3.80*   3.70      -      -   3.60      -      -    3.80
7   Adhana Phillip  31.00*      -      -      -      -  26.00  26.00   31.00
8   King Fearless    3.80*  3.80*      -      -      -      -   3.70    3.80

3 race(s). Demo responses carry no X-Credits-* headers -- they cost 0.
```

`*` marks the top price on that runner among the books quoting it. Missing runner numbers
(3 and 6 in the first race there) are scratchings.

## With a free key

```sh
export PE_API_KEY="your key"
python3 quickstart.py --races 2 --category horse
```

The sandbox truncates to 3 races, 5 runners, and each runner's best 3 prices. A key removes
all three limits and unlocks results, price history, form, movers and the venue directory.
Free tier is 1,500 credits/month with no credit card:
**[get a key](https://puntersedge.online/api?utm_source=australian-racing-api-python&utm_medium=readme)**.

Keyed output from the same run. All 14 served bookmakers are quoting this race, every cell
filled, no truncation. (The sandbox block above is not short of *books* either — its three
races show 9, 9 and 7 book columns. What it caps is prices *per runner*, at the best 3,
which is why most of those cells are empty.)

```
mode: KEYED -- live feed, all quoting bookmakers

[... WELLINGTON R1 cut here; it is in docs/output.txt in full ...]

MORUYA R1  13:25 AEST  +214 min (horse, AU)
-------------------------------------------
#   runner             SPBT   BRGT    TAB   PLAY   LADB   PALM    UNI   BOST   TTCH   PBET   NEDS   BGLD   BETR   BDLX    best
1   Colorado Sun      3.60*   3.50   3.50   3.10   3.50   3.40   3.40   3.30  3.60*  3.60*   3.50   3.30   3.50  3.60*    3.60
2   Mr Reiby          7.50*  7.50*  7.50*   6.00  7.50*   6.00   6.00   6.50  7.50*  7.50*  7.50*   6.50  7.50*  7.50*    7.50
3   Nothing Special  12.00*  11.00 12.00*   9.00 12.00*   9.50   9.50  10.00 12.00* 12.00* 12.00*  10.00 12.00* 12.00*   12.00
4   Waves Of Wisdom   4.20*   3.70   4.00   3.40   4.00   3.90   3.90   3.80  4.20*  4.20*   4.00   3.80   4.00  4.20*    4.20
5   Zippy Lion        5.50*  5.50*  5.50*   4.60  5.50*   4.60   4.60   4.80  5.50*  5.50*  5.50*   4.80  5.50*  5.50*    5.50
6   Better Bloom      5.00*   4.80  5.00*   4.20  5.00*   4.40   4.40   4.60  5.00*  5.00*  5.00*   4.60  5.00*  5.00*    5.00
7   Frosted Amour     15.00 26.00*  23.00  19.00  19.00  16.00  16.00  18.00  19.00  19.00  19.00  18.00  19.00  19.00   26.00
8   Reveillon        10.00*   9.50 10.00*   8.00   9.50   8.50   8.50   9.00 10.00* 10.00*   9.50   9.00 10.00* 10.00*   10.00
  oldest price 1346s old

2 race(s). X-Credits-Cost: 2  X-Credits-Remaining: unlimited
('unlimited' means this key has no monthly cap. A free-tier key reports
 the integer left of its 1,500 credits/month here.)
```

### What each call costs

| Method | Endpoint | Credits |
| --- | --- | --- |
| `next_to_go()` in demo mode | `/v1/demo/racing/next-to-go` | 0 |
| `events()` | `/v1/racing/events` | 1 |
| `venues()` | `/v1/racing/venues` | 1 |
| `next_to_go()` | `/v1/racing/next-to-go` | 2 |
| `results()` | `/v1/racing/results` | 2 |
| `best_odds()` | `/v1/racing/best-odds` | 3 |
| `movers()` | `/v1/racing/movers` | 3 |
| `horse_form()` | `/v1/racing/horses/form` | 3 |
| `price_history()` | `/v1/racing/price-history` | 5 |

`tour.py` calls every one of them — about **25 credits** — and prints a real result for
each. `next_to_go()`, `horse_form()` and `price_history()` are each called more than once,
because the gotchas they illustrate need two calls to see, so the run issues **13 HTTP
requests, not 8**. Counted by instrumenting `RacingAPI._get`: next-to-go x2, events,
venues, results, best-odds, movers, price-history x4, horses/form x2. Ten of those return
200 and bill 2+2+1+1+2+3+3+5+3+3 = 25 credits. The other three are `price_history` calls
made deliberately to provoke a 404, and may add up to 15 more depending on whether your
plan bills failed calls. It is documentation by execution: if it prints, the client works.

```sh
export PE_API_KEY="your key"
python3 tour.py
```

## Using it as a library

```python
from racing_api import RacingAPI

with RacingAPI() as api:                      # reads PE_API_KEY from the environment
    for race in api.next_to_go(country="AU", num_races=5):
        print(race["venue"], race["race_number"], race["start_time"])
        for runner in race["runners"]:
            best = max((b["win_price"] for b in runner["bookmakers"]
                        if b.get("win_price")), default=None)
            print("  ", runner["number"], runner["name"], best)
    print("credits left:", api.last_credits.remaining)
```

Methods: `next_to_go()`, `events()`, `venues()`, `results()`, `best_odds()`, `movers()`,
`price_history()`, `horse_form()`. Every one returns parsed JSON exactly as the API sends
it — no ORM, no model classes, nothing to learn twice. It is one file,
[`racing_api.py`](racing_api.py), short enough to read end to end, and most of it is
docstrings recording what each endpoint actually does.

## How it works

`racing_api.py` is one `http.client.HTTPSConnection` held open for the life of the client,
with `Accept-Encoding: gzip` on every request and a `dict` of query parameters cleaned of
`None`s. Responses are `json.loads`ed and handed back raw. That's the whole architecture.

Both of those choices were measured on this machine at 2026-09-14T23:45Z, not assumed:

- **Connection reuse.** Five sequential `/v1/racing/venues` calls, each on a fresh client and
  therefore a fresh TLS handshake, ran a median of **220.3 ms**. The same five on one reused
  connection ran **77.6 ms**. Build one client and keep it; don't construct one per request.
- **gzip.** `/v1/racing/next-to-go?country=AU&num_races=50` was **1,376,121 bytes** with
  `Accept-Encoding: identity` and **115,220 bytes** with gzip — 11.9x. The client always asks
  for gzip.

The parts that took actual reading of responses to get right:

- **`country="AU"` is the default, deliberately.** `/v1/racing/next-to-go` is not an
  Australian endpoint; it is a racing endpoint that contains Australia. Unfiltered at
  2026-09-14T23:39Z (09:39 AEST on the 15th) it returned 200 races — **194 AU, 5 US, 1 CA** —
  but sorted by time to jump, so *the five races nearest to jumping were the American and
  Canadian ones, and none were Australian*. `tour.py` prints that side by side and its
  captured run says `0 of these 6 races are Australian`. Drop the filter and your "next
  Australian races" panel opens on Mountaineer Park (US) and Assiniboia Downs (CA).
- **The demo envelope vs the bare array.** The keyless endpoints return an object with six
  top-level keys — `{"demo":…, "note":…, "shape":…, "cached":…, "signup_url":…, "races":[…]}`
  — and the keyed endpoints return a bare array. `next_to_go()` unwraps the envelope so
  calling code sees a list either way, and the demo branch applies the `country` filter
  client-side because the sandbox takes no query parameters.
- **Credit headers arrive lowercase, and `http.client` doesn't normalise.** Header names
  are case-insensitive per RFC 9110, but `http.client` hands you the verbatim wire
  casing, and this API writes `x-credits-remaining` — lowercase over both HTTP/1.1 and
  HTTP/2, checked with `curl -D -` at 2026-09-14T23:47Z. The first version of this client
  read `None` off every single response because it looked up `X-Credits-Remaining`
  verbatim. Lowercase the keys before you index them.
- **No silent retries on prices.** The client reconnects once if a pooled socket was closed
  while idle and no bytes were sent — that is connection-level. It never retries an HTTP
  status. A hidden retry on a price endpoint can hand you a quote recorded before a market
  move with nothing in the response to tell you.
- **Errors are RFC 9457 `problem+json`.** `{"type","title","status","detail"}`. Catch
  `RacingAPIError` and read `.detail`; it is written for a human. 429 raises the
  `RateLimited` subclass — the keyless demo allows 30 requests/minute per IP, and this
  build tripped it while probing.
- **Client-side guards that cost nothing.** `movers(direction="steam")`,
  `price_history(venue=…)` without a date, and `max_points=10` all raise `ValueError`
  before a request is sent. The API would refuse them for free anyway, but a wasted round
  trip is still 100 ms you don't get back.

## Why Australian racing data is awkward

This is the part a generic odds-API wrapper won't tell you. Every number below was measured
against the live API on 2026-09-15, between 09:39 and 09:45 AEST (2026-09-14T23:39Z–23:45Z).

**The same track has several names, and the feeds disagree.** The results feed and the
price feed are separately sourced, and they do not agree on spelling. In one pair of calls
in `tour.py`, `results()` returned the venue as `Sandown Park` and `price_history()`
returned the same race as `SANDOWN PARK`. The venue directory is the join table: each row
carries `venue_id`, `venue_canonical`, `venue_site` and a `spellings` list of everything
the upstream feeds actually emit. Of 187 venues, **20 emit more than one spelling**.

**`venue_id` and `venue_site` are different keys and 11 rows need both.** Several greyhound
tracks — `q-straight`, `q1-lakeside`, `q1-lakeside-extra` and `q2-parklands` — share the
venue_site `the-q`, because they are configurations of one venue. Likewise `sandown-park` →
`sandown`, `gold-coast-poly` → `gold-coast`, `murray-bridge-straight` → `murray-bridge`,
`richmond-straight` → `richmond`, `cambridge-synthetic` → `cambridge`. Join on the ID, never
on the label.

**Form data introduces a *third* naming convention.** `horse_form()` returns past runs with
`"track": "COR"` — Racing Australia's three-letter code, which matches neither
`venue_canonical` nor `venue_site`. Budget for a mapping step if you are joining form to
prices.

**A horse's name is not its key.** `horse_form("Lord Of Valor")` came back
`{"ambiguous": true, "candidates": [...]}` with two distinct `ra:` codes for that one name
and an empty `runs` list. Check `ambiguous` before you read `runs`, then re-call with the
candidate's `runner_ref`. A client that doesn't will silently report a horse with no form.

**Results don't always carry the price feed's `race_id`.** Over 179 settled Australian
races in 24 hours, **6 had `race_id: null`** — they were never matched into the price feed.
No spelling rescues them: `tour.py` tries `price_history` for one such race under both
`Q Straight` and `the-q` and gets 404 from each. Treat a result with a null `race_id` as
having no price history rather than as a bug in your join.

**Scratchings need two different reads.** A thoroughbred race lists real withdrawals
(five of them at Wellington R1 in `docs/output.txt`). A greyhound race pads the field with
`{"name": "Vacant Box", "vacant": true}` placeholders. `len(scratchings)` therefore
overstates withdrawals on the dogs. `scratched_numbers()` and the quickstart footer
separate the two.

**A runner can arrive with no saddlecloth number.** Rare — 1 of 29 AU thoroughbred races in
one pull — and always one book quoting a field the others do not carry, so the merge keeps
the prices with `"number": null`. Wellington R1 in `docs/output.txt` shows eight such rows,
every one of them priced by `betr_au` alone. Don't key runners on `number` without a null
check, and don't treat those rows as a comparison: one book quoting is not a market.

**AU and NZ are not symmetric.** Of those 187 venues, 156 were AU and 25 NZ — and the
categories differ. The AU venues carried `horse` 101, `greyhound` 48, `harness` 40. The NZ
venues carried `horse` 15 and `harness` 10, and **no greyhound at all**. If you are
iterating categories, an NZ greyhound query is not an outage, it is an empty set by design.

**Book count is a function of time to jump, not of the feed.** This one costs people a
morning of debugging, because the coverage report says the AU median is **14 books per
race** and a snapshot taken before the card opens says **7**. Both are right: the report
measures every book that quoted a race across its whole life, and a snapshot measures the
books that have opened their market *so far*. Across 200 AU races at 2026-09-14T23:45Z:

| time to jump | races | median books | min | max |
| --- | --- | --- | --- | --- |
| 2–4 h | 18 | 11 | 7 | 14 |
| 4–8 h | 82 | 9 | 1 | 13 |
| more than 8 h | 98 | 6 | 3 | 9 |

So don't treat a thin grid on a race eleven hours out as missing data, and don't benchmark
your coverage against the report using a pull taken overnight.

**Foreign meetings are quoted by almost nobody.** In that same unfiltered 200-race pull,
median books per race was **US 1** (n=5) and **CA 1** (n=1) against AU's 7. A cross-book
price comparison on a race a single bookmaker quotes is not a comparison, so
`country="AU"` is not just about relevance — it is about whether the numbers mean anything.

**An empty list is usually the market, not a fault.** `movers()` returned 0 rows at
2026-09-14 23:40Z (09:40 AEST) for `country=AU`, for `country=AU&include_unresolved=true`,
and for every country — because the card had not opened and no consensus existed to move
yet. Similarly, the six AU races nearest to jumping all 404'd on `price_history` while
returning live prices from `next_to_go`: history accrues from the first capture, so a
just-opened market has none. The 404 body itself is terse — `No price history for race_id
'…'` — and says nothing about depth; the depth figure lives on the coverage report, whose
`price_history_depth` read `earliest_race_start_utc: 2026-08-04T09:22:00Z` (42 days,
retention target 45) when this was written.

**`closing-lines` is plan-gated; `price_history` isn't.** `/v1/racing/closing-lines` is
documented as plan-gated and is expected to return 403 below the required plan — not
something this build could verify, since it was captured with an unlimited key. That is why
this client wraps `price_history()` instead: it returns `open_price`, `close_price`, `high`,
`low` and `move_pct` per runner-book at 5 credits, which is the same closing number without
the gate. `max_points` has a floor of **100**, not 1, and the response sets
`"truncated": true` when it clips.

## Related

Guides:

- [Horse racing API Australia — guide](https://puntersedge.online/blog/horse-racing-api-australia-guide?utm_source=australian-racing-api-python&utm_medium=readme)
- [Australian odds API with Python](https://puntersedge.online/blog/australian-odds-api-python-guide?utm_source=australian-racing-api-python&utm_medium=readme)
- [How to compare bookmaker odds in Australia](https://puntersedge.online/blog/how-to-compare-bookmaker-odds-australia?utm_source=australian-racing-api-python&utm_medium=readme)
- [Horse racing odds API reference](https://puntersedge.online/developers/horse-racing-odds-api-australia?utm_source=australian-racing-api-python&utm_medium=readme)
- [Greyhound racing API](https://puntersedge.online/developers/greyhound-racing-api?utm_source=australian-racing-api-python&utm_medium=readme) ·
  [NZ racing odds API](https://puntersedge.online/developers/nz-racing-odds-api?utm_source=australian-racing-api-python&utm_medium=readme) ·
  [Historical racing odds API](https://puntersedge.online/developers/historical-racing-odds-api?utm_source=australian-racing-api-python&utm_medium=readme)
- [Getting started](https://puntersedge.online/developers/getting-started?utm_source=australian-racing-api-python&utm_medium=readme) ·
  [API reference](https://puntersedge.online/developers/api-reference?utm_source=australian-racing-api-python&utm_medium=readme) ·
  [OpenAPI 3.1 spec](https://api.puntersedge.online/openapi.json) (60 paths)

Sibling repositories:

- [puntersedge-python](https://github.com/Propertyscout001/puntersedge-python) — the full
  PyPI SDK, covering sports and arbitrage endpoints as well as racing. Use that if you want
  a maintained package; use this repo if you want one file you can read end to end.
- [puntersedge-node](https://github.com/Propertyscout001/puntersedge-node) — npm SDK
- [puntersedge-mcp](https://github.com/Propertyscout001/puntersedge-mcp) — MCP server
- [au-racing-odds-dashboard](https://github.com/Propertyscout001/au-racing-odds-dashboard)
  — renders next-to-go as a terminal or HTML dashboard
- [puntersedge-examples](https://github.com/Propertyscout001/puntersedge-examples) —
  standalone task-shaped scripts

## Limitations

Things this repo does not do, so you can stop reading early if it isn't what you need:

- **Racing only.** No sports endpoints. The feed serves AFL, NRL, NBA, tennis, cricket and
  more under `/v1/sports/*`, but this client deliberately covers `/v1/racing/*` and nothing
  else. Use [puntersedge-python](https://github.com/Propertyscout001/puntersedge-python)
  for the full surface.
- **Win prices in the grid.** The API returns place, top2, top3 and top4 prices too, and
  they are in the parsed JSON, but `quickstart.py` only tabulates `win_price`.
- **Read-only, no credentials.** It fetches a data feed. It has no bookmaker accounts,
  places nothing, and stores nothing.
- **No caching, no async, no rate limiter.** One synchronous connection. If you need
  concurrency or a token bucket, wrap it — the client is small enough to read first.
- **No retry or backoff.** Deliberate, per the note above. You decide what to do with a
  429 or a 503.
- **Greyhound and harness form are not covered.** `horse_form()` hits
  `/v1/racing/horses/form`, which is thoroughbred-only. There is a separate
  `/v1/racing/greyhounds/form` endpoint this client does not wrap.
- **Not tested against a free-tier key.** It was built and captured with an internal
  unlimited key, so `X-Credits-Remaining` reads `unlimited` in `docs/output.txt`, the free
  tier's 403 on plan-gated endpoints was not exercised first-hand, and whether a failed call
  decrements anything is unknown here. Credit costs in the table above come from the
  published pricing, not from watching a counter decrement.
- **Every measurement is a single snapshot, and they move fast.** The venue directory
  returned 188 rows on one pull, 189 a few minutes later and 187 three minutes after that,
  all inside one hour on 2026-09-15. Book counts, medians and race mixes move the same way.
  Call the endpoints; don't trust these numbers as constants.
- **No test suite.** `tour.py` is the smoke test, and it needs a key and a live API.

---

18+ only. Gambling can be addictive — please gamble responsibly.
Gambling Help: 1800 858 858 · https://www.gambleaware.nsw.gov.au
This repository is a developer example for reading an odds data feed. It is not betting
advice, it places no bets and it holds no bookmaker credentials.
