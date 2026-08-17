#!/usr/bin/env python3
"""
Pulls this week's public skating times ("yleisöluistelu") for Espoo's ice
rinks and writes them out as a simple static webpage (docs/index.html).

How it works
------------
Espoo's booking system (resurssivaraus.espoo.fi) has a JSON feed behind
its calendar pages. This script calls that feed directly for every known
rink, keeps only events titled "Yleisöluistelu" (as opposed to hockey
practice, school gym class, senior skating, maintenance, etc.), and
renders the result as an HTML table.

This is deliberately simple, as intended for a first project:
- It only looks at the CURRENT week (Mon-Sun), not future weeks.
- It re-runs on a schedule (see .github/workflows/update.yml) rather than
  watching for changes in real time.
- If Espoo adds a brand-new rink, someone has to add its resource ID to
  the RINKS dict below by hand - this script won't discover it on its own.

Only uses the Python standard library, so no `pip install` is needed.
"""
import json
import urllib.request
from datetime import datetime, timedelta
from html import escape
from zoneinfo import ZoneInfo

# Each ice rink in Espoo's booking system has a numeric "resource ID".
# These were found by looking at the links on:
# https://www.espoo.fi/fi/espoo-liikkuu/sisaliikuntatilat/jaahallit/yleisoluisteluajat
RINKS = {
    15849: "Espoonlahti, jäähalli (Forum)",
    15851: "Espoonlahti, harjoitusjäähalli",
    15909: "Laaksolahti, harjoitusjäähalli",
    24707: "Matinkylä, Ilmatar I",
    24728: "Matinkylä, Ilmatar II",
    24729: "Matinkylä, Ilmatar III",
    16119: "Leppävaara, Genano Areena",
}

# Link back to each rink's own booking calendar, in case someone wants to
# double check a time or see further ahead than this week.
RINK_URLS = {
    rid: f"https://resurssivaraus.espoo.fi/liikunnantilavaraus/haku/?ResourceIDs={rid}"
    for rid in RINKS
}

API_URL = (
    "https://resurssivaraus.espoo.fi/Tailored/prime_product_intranet/"
    "espoo/web/Calendar/ReservationData.aspx"
)

HELSINKI = ZoneInfo("Europe/Helsinki")
WEEKDAYS_FI = ["Ma", "Ti", "Ke", "To", "Pe", "La", "Su"]
MONTHS_FI = [
    "tammikuuta", "helmikuuta", "maaliskuuta", "huhtikuuta", "toukokuuta",
    "kesäkuuta", "heinäkuuta", "elokuuta", "syyskuuta", "lokakuuta",
    "marraskuuta", "joulukuuta",
]


def week_bounds(today=None):
    """Return (start, end) datetimes for the Mon-Sun week containing `today`."""
    today = today or datetime.now(HELSINKI)
    monday = (today - timedelta(days=today.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    next_monday = monday + timedelta(days=7)
    return monday, next_monday


def fetch_events(start, end):
    """Call Espoo's booking feed for all known rinks, return the raw event list."""
    params = "&".join(f"resourceid%5B%5D={rid}" for rid in RINKS)
    url = f"{API_URL}?{params}&start={int(start.timestamp())}&end={int(end.timestamp())}"
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (public-skating-schedule script)"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def extract_public_skating(events):
    """Keep only 'Yleisöluistelu' (public skating) events, with the fields we need."""
    rows = []
    for ev in events:
        title = (ev.get("title") or "").strip()
        if not title.lower().startswith("yleisöluistelu"):
            continue

        lowered = title.lower()
        if "mailaton" in lowered:
            kind = "Mailaton"
        elif "mailallinen" in lowered:
            kind = "Mailallinen"
        else:
            kind = "Yleisöluistelu"

        rink_id = ev.get("resourceID")
        rows.append(
            {
                "start": datetime.fromisoformat(ev["start"]),
                "end": datetime.fromisoformat(ev["end"]),
                "rink": RINKS.get(rink_id, f"Tuntematon halli ({rink_id})"),
                "rink_url": RINK_URLS.get(rink_id),
                "kind": kind,
            }
        )

    rows.sort(key=lambda r: (r["start"], r["rink"]))
    return rows


def render_html(rows, week_start, week_end, generated_at):
    week_end_display = week_end - timedelta(days=1)
    title_range = f"{week_start.day}.{week_start.month}.–{week_end_display.day}.{week_end_display.month}.{week_end_display.year}"

    def fmt_generated(dt):
        return (
            f"{dt.day}. {MONTHS_FI[dt.month - 1]} {dt.year} klo "
            f"{dt.strftime('%H:%M')}"
        )

    if rows:
        body_rows = []
        for r in rows:
            day_label = f"{WEEKDAYS_FI[r['start'].weekday()]} {r['start'].day}.{r['start'].month}."
            time_label = f"{r['start'].strftime('%H:%M')}–{r['end'].strftime('%H:%M')}"
            rink_cell = escape(r["rink"])
            if r["rink_url"]:
                rink_cell = f'<a href="{escape(r["rink_url"])}" target="_blank" rel="noopener">{rink_cell}</a>'
            kind_class = "mailaton" if r["kind"] == "Mailaton" else "mailallinen"
            body_rows.append(
                f"<tr><td>{escape(day_label)}</td><td>{escape(time_label)}</td>"
                f"<td>{rink_cell}</td>"
                f'<td><span class="tag {kind_class}">{escape(r["kind"])}</span></td></tr>'
            )
        table_html = (
            "<table>"
            "<thead><tr><th>Päivä</th><th>Klo</th><th>Halli</th><th>Tyyppi</th></tr></thead>"
            f"<tbody>{''.join(body_rows)}</tbody>"
            "</table>"
        )
    else:
        table_html = (
            '<p class="empty">Ei löytynyt yleisöluisteluvuoroja tälle viikolle. '
            "Tarkista tilanne "
            '<a href="https://www.espoo.fi/fi/espoo-liikkuu/sisaliikuntatilat/jaahallit/yleisoluisteluajat" '
            'target="_blank" rel="noopener">Espoon virallisilta sivuilta</a>.</p>'
        )

    return f"""<!DOCTYPE html>
<html lang="fi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Yleisöluistelu Espoossa – {escape(title_range)}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{
    font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
    max-width: 720px;
    margin: 2rem auto;
    padding: 0 1rem;
    line-height: 1.5;
  }}
  h1 {{ font-size: 1.5rem; margin-bottom: 0.1rem; }}
  .subtitle {{ color: #666; margin-top: 0; margin-bottom: 1.5rem; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ text-align: left; padding: 0.5rem 0.6rem; border-bottom: 1px solid #ddd; }}
  th {{ background: #f2f2f2; }}
  tr:hover td {{ background: #fafafa; }}
  a {{ color: #0060df; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .tag {{
    display: inline-block;
    padding: 0.1rem 0.5rem;
    border-radius: 999px;
    font-size: 0.85rem;
  }}
  .tag.mailallinen {{ background: #e6f0ff; color: #0047ab; }}
  .tag.mailaton {{ background: #e8f7e6; color: #1a7a1a; }}
  .empty {{ color: #666; }}
  footer {{ margin-top: 2rem; font-size: 0.85rem; color: #888; }}
  @media (prefers-color-scheme: dark) {{
    th {{ background: #222; }}
    tr:hover td {{ background: #1a1a1a; }}
    td, th {{ border-bottom-color: #333; }}
  }}
</style>
</head>
<body>
  <h1>🛼 Yleisöluistelu Espoossa</h1>
  <p class="subtitle">Viikko {escape(title_range)}</p>
  {table_html}
  <footer>
    Päivitetty {escape(fmt_generated(generated_at))} Suomen aikaa. Tämä on epävirallinen,
    automaattisesti kerätty koonti — tarkista ajat aina tarvittaessa
    <a href="https://www.espoo.fi/fi/espoo-liikkuu/sisaliikuntatilat/jaahallit/yleisoluisteluajat" target="_blank" rel="noopener">Espoon virallisilta sivuilta</a>,
    sillä vuorot voivat muuttua.
  </footer>
</body>
</html>
"""


def main():
    start, end = week_bounds()
    events = fetch_events(start, end)
    rows = extract_public_skating(events)
    generated_at = datetime.now(HELSINKI)
    html = render_html(rows, start, end, generated_at)

    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Wrote {len(rows)} public skating slots to docs/index.html")


if __name__ == "__main__":
    main()
