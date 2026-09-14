# Australian racing API — Python client

A single-file Python client for Australian and New Zealand racing odds: thoroughbred,
harness and greyhound, with every quoting bookmaker's price per runner. Stdlib only —
no `pip install`, no virtualenv, no dependency tree. Clone it and run it.

It reads the [PuntersEdge](https://puntersedge.online/developers/getting-started?utm_source=australian-racing-api-python&utm_medium=readme)
racing feed: live prices for AU thoroughbred/harness/greyhound and NZ thoroughbred/harness,
plus settled results, per-runner price history, and thoroughbred form. 14 Australian
bookmakers were served when this was built (`served_bookmaker_count: 14` on the
[coverage report](https://puntersedge.online/coverage-report?utm_source=australian-racing-api-python&utm_medium=readme),
measured over the 7 days to 2026-09-14 23:06 UTC; NZ was 12). Read that report rather than
trusting the number here — it is recomputed, this file is not.

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
sandbox endpoint when `PE_API_KEY` is unset.

Real output, captured 2026-09-15 (full transcript in [`docs/output.txt`](docs/output.txt)):

```
mode: DEMO (no PE_API_KEY set) -- keyless sandbox, 0 credits,
      3 races / 5 runners / best 3 prices, rate limited to 30 req/min per IP.

Angle Park R1  11:38 AEST  +137 min (greyhound, AU)
---------------------------------------------------
#   runner              TAB   PBET   SPBT   NEDS    UNI   LADB   BDLX   BETR    best
1   Alia Rose        14.00* 14.00*  13.00      -      -      -      -      -   14.00
2   Sandy Knuckles    4.80*      -   4.60   4.60      -      -      -      -    4.80
4   Adhana Remi           -      -      -      -  3.00*  3.00*  3.00*      -    3.00
5   Whiplash Emmett       - 26.00* 26.00* 26.00*      -      -      -      -   26.00
7   Twitching         2.25*      -      -      -      -      -  2.25*  2.25*    2.25

Hobart R1  11:45 AEST  +144 min (greyhound, AU)
-----------------------------------------------
#   runner              TAB   LADB   NEDS   BDLX   TTCH    UNI   PBET   PALM   SPBT    best
1   Juneau Quadrant   6.00*   5.50   5.50      -      -      -      -      -      -    6.00
2   Miss Bern             -  5.00*  5.00*  5.00*      -      -      -      -      -    5.00
3   Miss Sue Lee          - 12.00* 12.00*      - 12.00*      -      -      -      -   12.00
4   Listen Spider         -      -      -      -      -  5.00*  5.00*  5.00*      -    5.00
5   Jamella Storm         -      -      -      -      -  4.40*  4.40*      -  4.40*    4.40

3 race(s). Demo responses carry no X-Credits-* headers -- they cost 0.
```

`*` marks the top price on that runner among the books quoting it. Missing runner numbers
(3, 6 above) are scratchings.

## With a free key

```sh
export PE_API_KEY="your key"
python3 quickstart.py --races 2 --category horse
```

The sandbox truncates to 3 races, 5 runners and the best 3 prices. A key removes all three
limits and unlocks results, price history, form, movers and the venue directory. Free tier
is 1,500 credits/month with no credit card:
**[get a key](https://puntersedge.online/api?utm_source=australian-racing-api-python&utm_medium=readme)**.

Keyed output, same day (12 books quoting instead of the sandbox's 3):

```
mode: KEYED -- live feed, all quoting bookmakers

BOWEN R1  13:33 AEST  +252 min (horse, AU)
------------------------------------------
#   runner           TTCH   LADB    TAB   BGLD   NEDS    UNI   BOST   PALM   BRGT   PBET   SPBT   BETR    best
1   Touch Base       3.20  3.60*   3.20   3.00  3.60*   3.30   3.00   3.50   3.30   3.40   3.30   3.20    3.60
3   The House        7.50   7.50   7.00   6.00   7.50   7.50   6.00   7.50  8.00*   7.50   7.50   7.50    8.00
4   Missile Baby     2.35   2.15   2.40   2.25   2.15   2.30   2.25   2.20  2.45*   2.30   2.30   2.40    2.45
5   Formal Affair    3.20   3.20   3.10   3.00   3.20   3.20   3.00   3.20   3.20   3.20  3.30*   3.10    3.30
7   Exo Miss        81.00  81.00  81.00  71.00  81.00  61.00  71.00  71.00101.00*  91.00  91.00  81.00  101.00
8   Reves Time     16.00*  14.00  15.00  14.00  14.00  15.00  14.00  14.00  15.00  15.00  15.00  14.00   16.00
  oldest price 626s old | scratched: Octopolis (6), Sailing Solo (2)

2 race(s). X-Credits-Cost: 2  X-Credits-Remaining: unlimited
```

(`unlimited` is what the header says for the internal key this was captured with. A
free-tier key reports the integer left of its 1,500.)

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

`tour.py` calls every one of them once — about 18 credits — and prints a real result for
each. It is documentation by execution: if it prints, the client works.

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
it — no ORM, no model classes, nothing to learn twice. The whole client is 549 lines in
[`racing_api.py`](racing_api.py), and most of that is docstrings recording what each
endpoint actually does.

## How it works

`racing_api.py` is one `http.client.HTTPSConnection` held open for the life of the client,
with `Accept-Encoding: gzip` on every request and a `dict` of query parameters cleaned of
`None`s. Responses are `json.loads`ed and handed back raw. That's the whole architecture.

Both of those choices were measured on this machine on 2026-09-15, not assumed:

- **Connection reuse.** Five sequential `/v1/racing/venues` calls, each on a fresh TLS
  handshake, ran a median of **191.4 ms**. The same five on one reused connection ran
  **74.6 ms**. Build one client and keep it; don't construct one per request.
- **gzip.** `/v1/racing/next-to-go?country=AU&num_races=50` was **1,285,799 bytes**
  uncompressed and **105,768 bytes** gzipped — 12.2x. The client always asks for gzip.

The parts that took actual reading of responses to get right:

- **`country="AU"` is the default, deliberately.** `/v1/racing/next-to-go` is not an
  Australian endpoint; it is a racing endpoint that contains Australia. Unfiltered on
  2026-09-15 it returned 200 races — 191 AU, 7 US, 1 AR, 1 BR — but sorted by time to
  jump, so *the six races nearest to jumping were Brazilian, Canadian and American and
  none were Australian*. `tour.py` prints that side by side. Drop the filter and your
  "next Australian races" panel shows Gavea and Mountaineer Park.
- **The demo envelope vs the bare array.** The keyless endpoints return
  `{"demo":…, "note":…, "shape":…, "races":[…]}`. The keyed endpoints return a bare array.
  `next_to_go()` unwraps the envelope so calling code sees a list either way, and the demo
  branch applies the `country` filter client-side because the sandbox has no query
  parameters.
- **Credit headers are case-insensitive, and this API varies.** `X-Credits-Remaining`
  arrives lowercased over HTTP/2 and title-cased over HTTP/1.1. The first version of this
  client read `None` off every single response because it looked up the title-cased name
  against `http.client`'s verbatim header dict. Lowercase the keys before you index them.
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
against the live API while building this repo on 2026-09-15.

**The same track has several names, and the feeds disagree.** The results feed and the
price feed are separately sourced, and they do not agree on spelling. In one pair of calls
in `tour.py`, `results()` returned the venue as `Sandown Park` and `price_history()`
returned the same race as `SANDOWN PARK`. The venue directory is the join table: each row
carries `venue_id`, `venue_canonical`, `venue_site` and a `spellings` list of everything
the upstream feeds actually emit. Of 188 venues, **19 emit more than one spelling**.

**`venue_id` and `venue_site` are different keys and 11 venues need both.** Three separate
greyhound tracks — `q-straight`, `q1-lakeside`, `q2-parklands` — all share the venue_site
`the-q`, because they are configurations of one venue. Likewise `sandown-park` → `sandown`,
`gold-coast-poly` → `gold-coast`, `murray-bridge-straight` → `murray-bridge`. Join on the
ID, never on the label.

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
(`Octopolis (6)`, `Sailing Solo (2)` at Bowen above). A greyhound race pads the field with
`{"name": "Vacant Box", "vacant": true}` placeholders. `len(scratchings)` therefore
overstates withdrawals on the dogs. `scratched_numbers()` and the quickstart footer
separate the two.

**AU and NZ are not symmetric.** Of 188 venues, 156 were AU and 25 NZ — and the categories
differ. The AU venues carried `horse` 101, `greyhound` 48, `harness` 40. The NZ venues
carried `horse` 15 and `harness` 10, and **no greyhound at all**. If you are iterating
categories, an NZ greyhound query is not an outage, it is an empty set by design.

**Foreign meetings are quoted by almost nobody.** Median books per race on 2026-09-15:
**AU 6** (min 1, max 13). US **1**. AR **1**. BR **2**. A cross-book price comparison on a
race a single bookmaker quotes is not a comparison, so `country="AU"` is not just about
relevance — it is about whether the numbers mean anything.

**An empty list is usually the market, not a fault.** `movers()` returned 0 rows at
09:20 AEST for `country=AU`, for `country=AU&include_unresolved=true`, and for every
country — because the card had not opened and no consensus existed to move yet. Similarly,
the six races nearest to jumping all 404'd on `price_history` while returning live prices
from `next_to_go`: history accrues from the first capture. The API's own 404 text says
AU/NZ history begins 2026-08-04.

**`closing-lines` is plan-gated; `price_history` isn't.** `/v1/racing/closing-lines` is
documented as plan-gated and returns 403 below the required plan — not something this build
could verify, since it was captured with an unlimited key. That is why this client wraps
`price_history()` instead: it returns `open_price`, `close_price`, `high`, `low` and
`move_pct` per runner-book at 5 credits, which is the same closing number without the gate.
`max_points` has a floor of **100**, not 1, and the response sets `"truncated": true` when
it clips.

## Related

Guides:

- [Horse racing API Australia — guide](https://puntersedge.online/blog/horse-racing-api-australia-guide?utm_source=australian-racing-api-python&utm_medium=readme)
- [Australian odds API with Python](https://puntersedge.online/blog/australian-odds-api-python-guide?utm_source=australian-racing-api-python&utm_medium=readme)
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
  unlimited key, so `X-Credits-Remaining` reads `unlimited` in `docs/output.txt` and the
  free tier's 403 on plan-gated endpoints was not exercised first-hand. Credit costs in the
  table above come from the published pricing, not from watching a counter decrement.
- **Every measurement is a single snapshot.** The venue count, book counts and medians here
  are one reading on 2026-09-15, taken at about 09:20 AEST. They move: the venue directory
  returned 188 rows and then 189 forty minutes later when a Canadian harness track
  appeared. Call the endpoints; don't trust these numbers as constants.
- **No test suite.** `tour.py` is the smoke test, and it needs a key and a live API.

---

18+ only. Gambling can be addictive — please gamble responsibly.
Gambling Help: 1800 858 858 · https://www.gambleaware.nsw.gov.au
This repository is a developer example for reading an odds data feed. It is not betting
advice, it places no bets and it holds no bookmaker credentials.
