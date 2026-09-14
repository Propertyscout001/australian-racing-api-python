"""
racing_api.py -- a single-file Python client for Australian racing odds data.

Stdlib only. No pip install. Python 3.8+.

    from racing_api import RacingAPI

    api = RacingAPI()                  # reads PE_API_KEY from the environment
    for race in api.next_to_go(country="AU", num_races=5):
        print(race["venue"], race["race_number"], race["start_time"])

With no PE_API_KEY set the client runs in demo mode against the keyless
sandbox endpoints, so a stranger can clone this and see real data without
registering. Demo mode only serves next_to_go(); everything else raises
NeedsKey with a link to the free tier.

API docs:  https://puntersedge.online/developers/getting-started?utm_source=australian-racing-api-python&utm_medium=code
Free key:  https://puntersedge.online/api?utm_source=australian-racing-api-python&utm_medium=code
"""

from __future__ import annotations

import gzip
import http.client
import io
import json
import os
import ssl
import urllib.parse
import zlib
from typing import Any, Dict, Iterable, List, Optional

__all__ = [
    "RacingAPI",
    "RacingAPIError",
    "RateLimited",
    "NeedsKey",
    "Credits",
    "BOOKMAKERS",
    "SIGNUP_URL",
]

API_HOST = "api.puntersedge.online"
API_PREFIX = "/v1"
USER_AGENT = "australian-racing-api-python/1.0 (+https://github.com/Propertyscout001/australian-racing-api-python)"

SIGNUP_URL = (
    "https://puntersedge.online/api"
    "?utm_source=australian-racing-api-python&utm_medium=code"
)

# The 14 Australian bookmakers served by the feed, measured 2026-09-15.
# All 14 appeared in a 200-race unfiltered pull at 2026-09-14T23:39Z.
# Live coverage report: https://puntersedge.online/coverage-report?utm_source=australian-racing-api-python&utm_medium=code
# Betfair and Pinnacle are NOT in the feed -- there is no exchange price here.
BOOKMAKERS = (
    "tab", "tabtouch", "betdeluxe", "betr_au", "pointsbetau", "betright",
    "playup", "palmerbet", "unibet", "neds", "ladbrokes_au", "sportsbet",
    "betgold", "boostbet",
)


class Credits:
    """Credit accounting read off the response headers of the last call."""

    __slots__ = ("cost", "used", "remaining", "limit")

    def __init__(self, cost=None, used=None, remaining=None, limit=None):
        self.cost = cost            # credits this call consumed
        self.used = used            # credits used this billing period
        self.remaining = remaining  # int, or the string "unlimited"
        self.limit = limit

    def __repr__(self) -> str:
        return (
            "Credits(cost=%r, used=%r, remaining=%r, limit=%r)"
            % (self.cost, self.used, self.remaining, self.limit)
        )


class RacingAPIError(Exception):
    """An RFC 9457 problem+json error returned by the API.

    The API always answers a failure with
    {"type": ..., "title": ..., "status": ..., "detail": ...}
    so the useful text is on .detail, not in a stack trace.
    """

    def __init__(self, status: int, problem: Dict[str, Any], url: str):
        self.status = status
        self.problem = problem
        self.url = url
        self.type = problem.get("type")
        self.title = problem.get("title")
        self.detail = problem.get("detail") or problem.get("title") or ""
        super().__init__("HTTP %s from %s: %s" % (status, url, self.detail))


class RateLimited(RacingAPIError):
    """HTTP 429. The keyless demo allows 30 requests/minute per IP.

    Deliberately NOT retried for you. A hidden retry on a price endpoint can
    hand you a price that was recorded before a market move, and you would
    never know it happened. Catch this and decide.
    """


class NeedsKey(Exception):
    """Raised when a keyed-only endpoint is called in demo mode."""

    def __init__(self, method: str, endpoint: str):
        super().__init__(
            "%s() calls %s, which needs an API key.\n"
            "Set PE_API_KEY in your environment. Free tier is 1,500 "
            "credits/month, no credit card: %s" % (method, endpoint, SIGNUP_URL)
        )


def _decode(raw: bytes, encoding: Optional[str]) -> bytes:
    if not raw:
        return raw
    enc = (encoding or "").lower()
    if enc == "gzip":
        return gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    if enc == "deflate":
        try:
            return zlib.decompress(raw)
        except zlib.error:
            return zlib.decompress(raw, -zlib.MAX_WBITS)
    return raw


def _clean(params: Dict[str, Any]) -> Dict[str, str]:
    """Drop None, render bools as the lowercase strings the API expects,
    and join sequences on commas (country=['AU','NZ'] -> 'AU,NZ')."""
    out: Dict[str, str] = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            out[key] = "true" if value else "false"
        elif isinstance(value, (list, tuple, set)):
            items = [str(v) for v in value if v is not None]
            if items:
                out[key] = ",".join(items)
        else:
            out[key] = str(value)
    return out


class RacingAPI:
    """Client for the PuntersEdge Australian racing endpoints.

    One HTTPS connection is opened and reused for the life of the instance.
    Measured on this machine at 2026-09-14T23:45Z: a fresh client, and so a
    fresh TLS handshake, per call ran a median of 220.3 ms against
    /v1/racing/venues; the same call on a reused connection ran 77.6 ms
    (n=5 each). Reuse the client; don't build one per request.

    Responses are requested gzipped. The same /v1/racing/next-to-go?country=AU
    &num_races=50 payload measured 1,376,121 bytes with Accept-Encoding:
    identity and 115,220 bytes with gzip -- 11.9x, same timestamp.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        host: str = API_HOST,
    ):
        # Key comes from the environment. Never hardcode it, never commit it.
        self.api_key = api_key if api_key is not None else os.environ.get("PE_API_KEY")
        self.demo = not self.api_key
        self.timeout = timeout
        self.host = host
        self.last_credits = Credits()
        self._conn: Optional[http.client.HTTPSConnection] = None

    # -- plumbing ---------------------------------------------------------

    def _connect(self) -> http.client.HTTPSConnection:
        if self._conn is None:
            self._conn = http.client.HTTPSConnection(
                self.host, timeout=self.timeout, context=ssl.create_default_context()
            )
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            finally:
                self._conn = None

    def __enter__(self) -> "RacingAPI":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        query = urllib.parse.urlencode(_clean(params or {}))
        url = API_PREFIX + path + ("?" + query if query else "")
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "User-Agent": USER_AGENT,
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        raw, status, resp_headers = self._request(url, headers)
        body = _decode(raw, resp_headers.get("content-encoding"))

        # Header names are case-insensitive per RFC 9110, but http.client
        # hands you the verbatim wire casing. This API sends them lowercase:
        # measured 2026-09-14T23:47Z, `x-credits-remaining` over both HTTP/1.1
        # and HTTP/2. Index the title-cased name and you silently read None
        # off every response -- which the first version of this client did.
        self.last_credits = Credits(
            cost=_maybe_int(resp_headers.get("x-credits-cost")),
            used=_maybe_int(resp_headers.get("x-credits-used")),
            remaining=_maybe_int(resp_headers.get("x-credits-remaining")),
            limit=_maybe_int(resp_headers.get("x-credits-limit")),
        )

        if status >= 400:
            try:
                problem = json.loads(body.decode("utf-8"))
            except Exception:
                problem = {"title": body[:400].decode("utf-8", "replace"), "status": status}
            cls = RateLimited if status == 429 else RacingAPIError
            raise cls(status, problem, "https://%s%s" % (self.host, url))

        return json.loads(body.decode("utf-8"))

    def _request(self, url: str, headers: Dict[str, str]):
        """Issue the GET, reopening the socket once if the pooled one died.

        This retry is connection-level only -- it fires when the server closed
        an idle keep-alive socket and no bytes were ever sent. It is not a
        retry on an HTTP status, which is why a 429 or a 5xx reaches you.
        """
        for attempt in (0, 1):
            conn = self._connect()
            try:
                conn.request("GET", url, headers=headers)
                resp = conn.getresponse()
                hdrs = {k.lower(): v for k, v in resp.getheaders()}
                return resp.read(), resp.status, hdrs
            except (http.client.HTTPException, OSError):
                self.close()
                if attempt == 1:
                    raise
        raise AssertionError("unreachable")

    # -- endpoints --------------------------------------------------------

    def next_to_go(
        self,
        country: Optional[str] = "AU",
        num_races: int = 10,
        categories: Optional[str] = None,
        venue: Optional[str] = None,
        bookmakers: Optional[Iterable[str]] = None,
        include_unresolved: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """Races closest to jumping, each with every bookmaker's price per runner.

        Costs 2 credits keyed, 0 in demo mode.

        country defaults to "AU" on purpose. The endpoint is NOT Australia-only.
        Measured at 2026-09-14T23:39Z (09:39 AEST on 2026-09-15) on an
        unfiltered pull of 200 races: 194 AU, 5 US, 1 CA. The list is sorted by
        time to jump, and the FIVE races nearest to jumping were the American
        and Canadian ones -- none Australian. Drop the filter and your
        "Australian racing" screen opens on Mountaineer Park (US) and
        Assiniboia Downs (CA).

        Returns a list either way. In demo mode this unwraps the sandbox
        envelope -- six top-level keys, {"demo":..,"note":..,"shape":..,
        "cached":..,"signup_url":..,"races":[..]} -- so calling code sees the
        same bare list the keyed endpoint returns.
        """
        if self.demo:
            payload = self._get("/demo/racing/next-to-go")
            races = payload.get("races", []) if isinstance(payload, dict) else payload
            if country:
                wanted = {c.strip().upper() for c in str(country).split(",")}
                races = [r for r in races if (r.get("country") or "").upper() in wanted]
            return races[:num_races]
        return self._get(
            "/racing/next-to-go",
            {
                "country": country,
                "num_races": num_races,
                "categories": categories,
                "venue": venue,
                "bookmakers": bookmakers,
                "include_unresolved": include_unresolved,
            },
        )

    def events(
        self,
        country: Optional[str] = "AU",
        hours_ahead: int = 4,
        categories: Optional[str] = None,
        include_unresolved: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """Upcoming race list without prices. 1 credit. hours_ahead max 24.

        Cheap way to build a schedule before spending 2-3 credits pulling
        prices for the races you actually care about.
        """
        if self.demo:
            raise NeedsKey("events", "/v1/racing/events")
        return self._get(
            "/racing/events",
            {
                "country": country,
                "hours_ahead": hours_ahead,
                "categories": categories,
                "include_unresolved": include_unresolved,
            },
        )

    def venues(self) -> List[Dict[str, Any]]:
        """The canonical venue directory. 1 credit.

        Read this before you try to join the price feed to the results feed by
        venue name. Each row carries venue_id, venue_canonical, venue_site and
        a `spellings` list of every string the upstream feeds actually emit.

        Measured at 2026-09-14T23:42Z (09:42 AEST on 2026-09-15): 187 venues
        (156 AU, 25 NZ, 4 GB, 1 CA, 1 US); 20 emitted more than one spelling;
        11 had a venue_site differing from their venue_id -- four of those
        (q-straight, q1-lakeside, q1-lakeside-extra, q2-parklands) share the
        single venue_site 'the-q'.

        The row count is NOT stable. The same call returned 188 earlier the
        same morning, 189 at 23:39Z and 187 three minutes after that, as
        foreign meetings entered and left the window. Call this endpoint;
        don't hardcode its contents.
        """
        if self.demo:
            raise NeedsKey("venues", "/v1/racing/venues")
        return self._get("/racing/venues")

    def results(
        self,
        country: Optional[str] = "AU",
        hours_back: int = 24,
        date: Optional[str] = None,
        categories: Optional[str] = None,
        venue: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Settled results: placings, dividends, deductions. 2 credits.

        limit maxes at 200; hours_back maxes at 168. `date` (YYYY-MM-DD, AET
        meeting date) is mutually exclusive with hours_back.

        A result does not always carry the price feed's race_id. Measured at
        2026-09-14T23:41Z over 179 settled AU races in the last 24h, 6 had
        race_id null -- they were never matched into the price feed, and no
        venue-name spelling conjures history for them. Join on venue_site +
        race_number + date when race_id is absent, and treat a null race_id
        as 'no price history' rather than as a bug in your join.
        """
        if self.demo:
            raise NeedsKey("results", "/v1/racing/results")
        params: Dict[str, Any] = {
            "country": country,
            "categories": categories,
            "venue": venue,
            "status": status,
            "limit": limit,
            "offset": offset,
        }
        if date:
            params["date"] = date
        else:
            params["hours_back"] = hours_back
        return self._get("/racing/results", params)

    def best_odds(
        self,
        country: Optional[str] = "AU",
        num_races: int = 10,
        categories: Optional[str] = None,
        venue: Optional[str] = None,
        bookmakers: Optional[Iterable[str]] = None,
        include_unresolved: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """Top price per runner across books, plus market_percentage. 3 credits.

        num_races maxes at 150. Each race also reports books_compared, which
        you should check before trusting market_percentage -- a percentage
        computed from one book is not a market.
        """
        if self.demo:
            raise NeedsKey("best_odds", "/v1/racing/best-odds")
        return self._get(
            "/racing/best-odds",
            {
                "country": country,
                "num_races": num_races,
                "categories": categories,
                "venue": venue,
                "bookmakers": bookmakers,
                "include_unresolved": include_unresolved,
            },
        )

    def movers(
        self,
        country: Optional[str] = "AU",
        direction: Optional[str] = None,
        min_move_pct: float = 10.0,
        min_books: int = 3,
        categories: Optional[str] = None,
        max_mins_to_jump: int = 360,
        include_unresolved: Optional[bool] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Runners whose consensus price has moved. 3 credits.

        direction is "firming" or "drifting". Not "steam", not "drift" --
        those spellings are a free 422, but they are still a wasted round trip.

        An empty list is normal, not a fault. Before a card opens there is no
        consensus to move yet: at 2026-09-14 23:40 UTC (09:40 AEST on
        2026-09-15) this returned 0 rows at min_move_pct=10 for AU, for AU
        with include_unresolved=true, and for every country.
        """
        if direction is not None and direction not in ("firming", "drifting"):
            raise ValueError(
                "direction must be 'firming' or 'drifting', got %r" % (direction,)
            )
        if self.demo:
            raise NeedsKey("movers", "/v1/racing/movers")
        return self._get(
            "/racing/movers",
            {
                "country": country,
                "direction": direction,
                "min_move_pct": min_move_pct,
                "min_books": min_books,
                "categories": categories,
                "max_mins_to_jump": max_mins_to_jump,
                "include_unresolved": include_unresolved,
                "limit": limit,
            },
        )

    def price_history(
        self,
        race_id: Optional[str] = None,
        venue: Optional[str] = None,
        race_number: Optional[int] = None,
        date: Optional[str] = None,
        bookmakers: Optional[Iterable[str]] = None,
        include_points: bool = True,
        max_points: int = 5000,
    ) -> Dict[str, Any]:
        """Open/close/high/low/move_pct per runner-book, with the raw points. 5 credits.

        Address a race either by race_id, or by venue + race_number + date.
        max_points has a floor of 100, not 1; the response sets
        "truncated": true when it clipped.

        This is the free-tier way to get a closing price.
        /v1/racing/closing-lines is documented as plan-gated and is expected
        to 403 below the required plan -- NOT verified by this client, which
        was built with an unlimited key. close_price here is the same number
        and is not plan-gated.

        A race that has not been quoted yet 404s. Measured at 2026-09-14
        23:40Z, the six AU races nearest to jumping all 404'd on
        price_history while returning live prices from next_to_go -- history
        accrues from the first capture, so a just-opened market has none.
        """
        if self.demo:
            raise NeedsKey("price_history", "/v1/racing/price-history")
        if not race_id and not (venue and race_number and date):
            raise ValueError(
                "pass race_id, or all three of venue + race_number + date"
            )
        if max_points < 100:
            raise ValueError("max_points has a minimum of 100 (got %r)" % (max_points,))
        return self._get(
            "/racing/price-history",
            {
                "race_id": race_id,
                "venue": venue,
                "race_number": race_number,
                "date": date,
                "bookmakers": bookmakers,
                "include_points": include_points,
                "max_points": max_points,
            },
        )

    def horse_form(self, horse: str) -> Dict[str, Any]:
        """Thoroughbred profile, career record and recent runs. 3 credits.

        `horse` is a name, or the stable "ra:" code from runner_ref.

        A name is not a key. When two horses share a name the response comes
        back with {"ambiguous": true, "candidates": [...]} and empty runs --
        check that flag before reading .runs, then re-call with the
        candidate's runner_ref. Measured 2026-09-15: "Lord Of Valor" resolved
        to two distinct ra: codes.
        """
        if self.demo:
            raise NeedsKey("horse_form", "/v1/racing/horses/form")
        return self._get("/racing/horses/form", {"horse": horse})


def _maybe_int(value: Optional[str]):
    """Credit headers are integers, except on an unlimited plan where the API
    sends the literal string 'unlimited'. Pass that through rather than
    swallowing it into None."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


# -- convenience helpers used by quickstart.py ---------------------------

def books_in_race(race: Dict[str, Any]) -> List[str]:
    """Bookmaker keys that actually quoted this race, in feed order."""
    seen: List[str] = []
    for runner in race.get("runners") or []:
        for book in runner.get("bookmakers") or []:
            if book["key"] not in seen:
                seen.append(book["key"])
    return seen


def prices_by_book(runner: Dict[str, Any]) -> Dict[str, float]:
    """{bookmaker_key: win_price} for one runner, skipping books with no win price."""
    out: Dict[str, float] = {}
    for book in runner.get("bookmakers") or []:
        price = book.get("win_price")
        if price is not None:
            out[book["key"]] = price
    return out


def scratched_numbers(race: Dict[str, Any]) -> set:
    """Saddlecloth/box numbers withdrawn from this race.

    Greyhound fields carry {"vacant": true} placeholders named "Vacant Box"
    rather than a real scratched dog, so a raw len(scratchings) overstates how
    many runners were actually withdrawn.
    """
    return {s.get("number") for s in (race.get("scratchings") or []) if s.get("number")}
