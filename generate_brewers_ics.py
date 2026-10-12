#!/usr/bin/env python3
"""Build a subscribable .ics feed of the Milwaukee Brewers schedule.

Data source: MLB's official schedule data (the same data that powers
mlb.com/brewers/schedule), including its broadcast listings.

Covers spring training, the regular season and the postseason. It reads the
current year and the next year, so next season's games appear automatically
once MLB publishes them.

Event title:  "⚾ {Away Team} @ {Home Team}" (team names only, no city)
Time zone:    America/Chicago (Central Time)
Description:  Watch: how to watch the game, from MLB's broadcast listings:
                1. national TV/streaming channel(s), if the game has any
                   (for example FOX, Apple TV+, ESPN, Peacock, FS1);
                2. otherwise the Brewers' own in-market TV channel(s), such as
                   a local broadcast station and/or Brewers.TV;
                3. otherwise "Brewers.TV".
              If there is a game type (Spring Training, a playoff series and
              game number, etc.) it follows after a blank line.
              The ballpark goes in the event's Location field.

Usage:
    python3 generate_brewers_ics.py --output public/brewers.ics
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

API = "https://statsapi.mlb.com/api/v1"
BREWERS_ID = 158

# Shown when MLB lists no TV information for a game yet.
FALLBACK_CHANNEL = "Brewers.TV"

CENTRAL = ZoneInfo("America/Chicago")
GAME_LENGTH = timedelta(hours=3)
CAL_NAME = "Milwaukee Brewers"

# Games that MLB lists but that are not being played on that date.
SKIP_STATES = {"Postponed", "Cancelled"}

# Labels for game types that aren't the regular season.
TYPE_LABELS = {"S": "Spring Training", "E": "Exhibition"}
POSTSEASON_TYPES = {"F", "D", "L", "W"}  # wild card, division, league, world series

VTIMEZONE = """BEGIN:VTIMEZONE
TZID:America/Chicago
X-LIC-LOCATION:America/Chicago
BEGIN:DAYLIGHT
TZOFFSETFROM:-0600
TZOFFSETTO:-0500
TZNAME:CDT
DTSTART:19700308T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:-0500
TZOFFSETTO:-0600
TZNAME:CST
DTSTART:19701101T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
END:VTIMEZONE"""


def get_json(url, tries=4):
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 brewers-calendar", "Accept": "application/json"}
    )
    last = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            last = e
            time.sleep(2 ** attempt)
    print(f"warning: could not fetch {url}: {last}", file=sys.stderr)
    return None


def parse_utc(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def fetch_games(years):
    games = {}
    for year in years:
        url = (f"{API}/schedule?sportId=1&teamId={BREWERS_ID}"
               f"&startDate={year}-01-01&endDate={year}-12-31&hydrate=broadcasts,team,venue")
        data = get_json(url)
        for d in (data or {}).get("dates", []):
            for g in d.get("games", []):
                games[str(g["gamePk"])] = g
    return games


def brewers_side(game):
    home = ((game.get("teams") or {}).get("home") or {}).get("team") or {}
    return "home" if home.get("id") == BREWERS_ID else "away"


def clean_name(name):
    """Drop sponsor tails such as 'Brewers.TV Presented by ...'."""
    return re.sub(r"\s+presented by\s+.*$", "", name or "", flags=re.I).strip()


def watch_channels(game):
    """National channels, else the Brewers' in-market TV channels, else the fallback."""
    side = brewers_side(game)
    national, local = [], []
    for b in game.get("broadcasts") or []:
        if str(b.get("type") or "").upper() != "TV":
            continue
        if str(b.get("language") or "en").lower() != "en":
            continue
        name = clean_name(b.get("name"))
        if not name:
            continue
        code = str((b.get("availability") or {}).get("availabilityCode") or "").lower()
        if b.get("isNational"):
            if name not in national:
                national.append(name)
        elif b.get("homeAway") == side and "out_of_market" not in code:
            if name not in local:
                local.append(name)
    return national or local or [FALLBACK_CHANNEL]


def esc(text):
    return (str(text).replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\n", "\\n"))


def fold(line):
    """RFC 5545 line folding at 75 octets."""
    if len(line.encode("utf-8")) <= 75:
        return line
    parts, cur = [], b""
    for ch in line:
        enc = ch.encode("utf-8")
        limit = 75 if not parts else 74
        if len(cur) + len(enc) > limit:
            parts.append(cur)
            cur = b""
        cur += enc
    parts.append(cur)
    return "\r\n ".join(p.decode("utf-8") for p in parts)


def team_name(game, side):
    team = ((game.get("teams") or {}).get(side) or {}).get("team") or {}
    name = team.get("teamName") or team.get("clubName") or team.get("name") or ""
    return name if name and name.upper() != "TBD" else "TBD"


def game_details(game):
    """Lines describing the kind of game (empty for ordinary regular-season games)."""
    gt = game.get("gameType")
    details = []
    if gt in TYPE_LABELS:
        details.append(TYPE_LABELS[gt])
    elif gt in POSTSEASON_TYPES:
        text = game.get("seriesDescription") or "Postseason"
        if game.get("seriesGameNumber"):
            text += f" - Game {game['seriesGameNumber']}"
        details.append(text)
    if game.get("ifNecessary") == "Y":
        details.append("If necessary")
    return details


def build_event(game, stamp):
    status = game.get("status") or {}
    if status.get("detailedState") in SKIP_STATES:
        return None

    title = f"\u26BE {team_name(game, 'away')} @ {team_name(game, 'home')}"

    lines = ["Watch: " + ", ".join(watch_channels(game))]
    details = game_details(game)
    if details:
        lines.append("")  # blank line between the channel and the game type
        lines.extend(details)

    # The ballpark is used for the event's Location field, not the description.
    venue_name = (game.get("venue") or {}).get("name")
    home_team = ((game.get("teams") or {}).get("home") or {}).get("team") or {}
    park = ", ".join(x for x in (venue_name, home_team.get("locationName")) if x)

    start = parse_utc(game.get("gameDate"))
    tbd = status.get("startTimeTBD") is True or start is None

    out = ["BEGIN:VEVENT",
           f"UID:mlb-{game['gamePk']}@brewers-calendar",
           f"DTSTAMP:{stamp}",
           f"SUMMARY:{esc(title)}"]
    if park:
        out.append(f"LOCATION:{esc(park)}")
    if tbd:
        # MLB's own local game date. (Not the placeholder time converted to
        # Central, which can land on the previous day.)
        day = None
        if game.get("officialDate"):
            try:
                day = date.fromisoformat(game["officialDate"])
            except ValueError:
                day = None
        if day is None and start is not None:
            day = start.date()
        if day is None:
            return None
        lines.insert(0, "Start time TBD")
        out.append(f"DTSTART;VALUE=DATE:{day:%Y%m%d}")
        out.append(f"DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}")
    else:
        local = start.astimezone(CENTRAL)
        end = (start + GAME_LENGTH).astimezone(CENTRAL)
        out.append(f"DTSTART;TZID=America/Chicago:{local:%Y%m%dT%H%M%S}")
        out.append(f"DTEND;TZID=America/Chicago:{end:%Y%m%dT%H%M%S}")
    out.insert(4, f"DESCRIPTION:{esc(chr(10).join(lines))}")
    # Show as "free" so games don't block out time on your calendar.
    out.append("TRANSP:TRANSPARENT")
    out.append("X-MICROSOFT-CDO-BUSYSTATUS:FREE")
    out.append("END:VEVENT")
    return out


def build_calendar(games):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = ["BEGIN:VCALENDAR", "VERSION:2.0",
           "PRODID:-//brewers-calendar//MLB schedule feed//EN",
           "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
           f"X-WR-CALNAME:{CAL_NAME}",
           "X-WR-TIMEZONE:America/Chicago",
           "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
           "X-PUBLISHED-TTL:PT6H", VTIMEZONE.replace("\n", "\r\n")]
    count = 0
    for pk in sorted(games, key=lambda i: games[i].get("gameDate", "")):
        ev = build_event(games[pk], stamp)
        if ev:
            out.extend(ev)
            count += 1
    out.append("END:VCALENDAR")
    body = "\r\n".join(fold(l) if "\n" not in l else l for l in out) + "\r\n"
    return body, count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="brewers.ics")
    args = ap.parse_args()

    today = date.today()
    games = fetch_games((today.year, today.year + 1))
    if not games:
        raise SystemExit("No Brewers games returned by MLB; refusing to overwrite the feed.")
    body, count = build_calendar(games)
    if count == 0:
        raise SystemExit("No usable games; refusing to overwrite the feed.")
    with open(args.output, "w", encoding="utf-8", newline="") as f:
        f.write(body)
    print(f"Wrote {count} events to {args.output}")


if __name__ == "__main__":
    sys.exit(main())
