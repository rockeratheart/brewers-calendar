# Milwaukee Brewers schedule calendar

A calendar you subscribe to once. Every Brewers game shows up in your calendar app and stays up to date on its own, including spring training and the postseason if the team makes it, and future seasons.

**Subscribe page: https://rockeratheart.github.io/brewers-calendar/index.html**

Calendar link (for apps that ask for a URL): `https://rockeratheart.github.io/brewers-calendar/brewers.ics`

## How to subscribe

The easiest way is to open the subscribe page above and tap the button for your calendar app. If you'd rather do it by hand:

**iPhone or iPad**
1. Open **Settings → Calendar → Accounts → Add Account → Other → Add Subscribed Calendar**.
2. Paste the calendar link and tap **Next**, then **Save**.

**Mac (Calendar app)**
1. Choose **File → New Calendar Subscription**.
2. Paste the calendar link and click **Subscribe**.

**Google Calendar** (do this on a computer; it then appears on your phone too)
1. On the left, next to **Other calendars**, click **+ → From URL**.
2. Paste the calendar link and click **Add calendar**.

**Outlook.com**
1. Choose **Add calendar → Subscribe from web**.
2. Paste the calendar link, name it, and click **Import**.

**Outlook desktop**
1. Choose **Add Calendar → From Internet**, paste the link, and confirm.

**Any other app:** look for "Subscribe to calendar", "Add calendar from URL" or "Internet calendar", and paste the calendar link.

## What you'll see

- Events named like **⚾ Cubs @ Brewers**: a baseball emoji, then the away team, then the home team.
- Times shown in Central Time. Your calendar converts them to your own time zone.
- **Watch:** in each event's description lists where to watch, as MLB lists it. Nationally televised games show the national channel (for example Apple TV+, FOX, ESPN, Peacock or FS1). All other games show the Brewers' own TV channel or channels, such as a local broadcast station and/or **Brewers.TV**.
- The game type (Preseason, NLDS - Game 1, and so on) in the description when it applies.
- Events are marked as **free**, so games don't make you show as busy.
- Games with no start time yet appear as all-day events and move to the right time once it's set. An opponent not yet decided shows as **TBD**.

## Common questions

**How often does it update?** The calendar file refreshes every 6 hours, but your calendar app decides how often it checks for changes. Google Calendar can take up to a day. Apple and Outlook are usually faster.

**A game time changed. Why doesn't my calendar show it?** Give it time. If it's urgent, check the Brewers' website or the MLB app.

**Will I need to subscribe again next season?** No. The same subscription picks up each new season's games automatically.

**How do I remove it?** Delete the subscribed calendar in your calendar app's settings.

*Unofficial, fan-made calendar. Not affiliated with or endorsed by the Milwaukee Brewers or Major League Baseball. Schedule data comes from MLB's public data and may change or contain mistakes.*

---

## For the maintainer

### How it works
`generate_brewers_ics.py` pulls the Brewers schedule and broadcast listings from MLB's official schedule data (the same data behind mlb.com/brewers/schedule) and writes `brewers.ics`. A GitHub Actions workflow runs it every 6 hours and publishes the result, along with `index.html`, to GitHub Pages. It reads the current year and the next year, so a new season appears as soon as MLB publishes it.

For each game's "Watch:" line it uses MLB's labels: national channels first; if there are none, the Brewers' own in-market TV channels (the listing for the Brewers' side of the game); and if MLB lists nothing yet, `Brewers.TV`. Spanish-language and radio listings are skipped, and sponsor wording such as "Presented by ..." is trimmed.

### Setup
1. Create a new public GitHub repository named `brewers-calendar`.
2. Add these files to it: `generate_brewers_ics.py`, `index.html`, `README.md`, and the workflow file at exactly `.github/workflows/update-calendar.yml`. To create the workflow, use **Add file → Create new file** and type that whole path in the name box.
3. In the repo, go to **Settings → Pages** and set **Source** to **GitHub Actions**.
4. Open the **Actions** tab, choose **Update Brewers calendar**, and click **Run workflow**. After that it runs on its own.

### Settings in `generate_brewers_ics.py`
- `FALLBACK_CHANNEL` (default `"Brewers.TV"`): shown on games where MLB lists no TV channel yet.
- `SKIP_STATES`: games marked Postponed or Cancelled are left out; a rescheduled game appears on its new date.
- `GAME_LENGTH`: each event lasts 3 hours, since the data has no end time.
- `CAL_NAME`: the calendar's display name.

### Notes
- Games shown free over the air on a local station appear with that station's name when MLB lists it. If you see one missing, MLB probably hasn't added it yet.
- Playoff games that are only played if a series goes long are marked "If necessary" and disappear if they aren't needed.
- If a run fails, open the failed run in the **Actions** tab and check the red step. If the script can't reach ESPN or finds no games, it stops without replacing the published calendar, so subscribers keep the last good version.
