"""
Local context service.
Fetches recent news and conditions from South Lake Tahoe, Reno, and Sacramento
so Maya's posts and chat feel grounded in real current events.

Uses free RSS feeds — no API key needed.
Snow conditions use the Open-Meteo API (also free).
"""
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone


# ── RSS feeds — free, no key required ────────────────────────────────────────

RSS_FEEDS = [
    {
        "name":  "Tahoe Daily Tribune",
        "url":   "https://www.tahoedailytribune.com/feed/",
        "area":  "tahoe",
    },
    {
        "name":  "SFGATE Tahoe",
        "url":   "https://www.sfgate.com/search/?action=search&channel=tahoe&inaction=sitewide&searchindex=solr&query=tahoe&x=0&y=0&startTime=&endTime=&byline=&sort=relevance&rss=1",
        "area":  "tahoe",
    },
    {
        "name":  "Reno Gazette Journal",
        "url":   "https://reno.com/feed/",
        "area":  "reno",
    },
    {
        "name":  "Sacramento Bee",
        "url":   "https://www.sacbee.com/latest-news/?widgetName=rssfeed&widgetContentId=735481&getXmlFeed=true",
        "area":  "sacramento",
    },
]

# Squaw Valley / Palisades snow report (Open-Meteo — free, no key)
# Coordinates for Palisades Tahoe summit area
TAHOE_LAT  = 39.1965
TAHOE_LON  = -120.2356


def _fetch_rss(url: str, max_items: int = 3) -> list[str]:
    """Fetch RSS feed and return list of recent headline strings."""
    try:
        r = requests.get(url, timeout=10,
                         headers={"User-Agent": "Mozilla/5.0 (compatible)"})
        r.raise_for_status()
        root  = ET.fromstring(r.content)
        items = root.findall(".//item")[:max_items]
        headlines = []
        for item in items:
            title = item.findtext("title", "").strip()
            if title:
                headlines.append(title)
        return headlines
    except Exception as e:
        print(f"RSS ERROR ({url[:40]}...): {e}")
        return []


def _fetch_snow_conditions() -> str:
    """
    Fetch current snow/weather at Tahoe summit via Open-Meteo.
    Returns a plain-English summary string.
    """
    try:
        params = {
            "latitude":   TAHOE_LAT,
            "longitude":  TAHOE_LON,
            "current":    "temperature_2m,precipitation,snowfall,snow_depth,wind_speed_10m,weather_code",
            "temperature_unit": "fahrenheit",
            "wind_speed_unit":  "mph",
            "precipitation_unit": "inch",
        }
        r = requests.get("https://api.open-meteo.com/v1/forecast",
                         params=params, timeout=10)
        r.raise_for_status()
        data    = r.json()
        current = data.get("current", {})

        temp       = current.get("temperature_2m")
        snowfall   = current.get("snowfall", 0)
        snow_depth = current.get("snow_depth", 0)
        wind       = current.get("wind_speed_10m")
        code       = current.get("weather_code", 0)

        # Weather code to plain English (WMO codes)
        conditions = _wmo_to_text(code)

        parts = [f"Current conditions at Squaw: {conditions}."]
        if temp is not None:
            parts.append(f"{temp:.0f}°F.")
        if snowfall and snowfall > 0:
            parts.append(f"Snowing — {snowfall:.1f}\" in the last hour.")
        if snow_depth and snow_depth > 0:
            parts.append(f"Snow depth {snow_depth * 39.37:.0f}\" (approx).")
        if wind:
            parts.append(f"Wind {wind:.0f} mph.")

        return " ".join(parts)

    except Exception as e:
        print(f"SNOW CONDITIONS ERROR: {e}")
        return ""


def _wmo_to_text(code: int) -> str:
    if code == 0:    return "clear sky"
    if code <= 3:    return "partly cloudy"
    if code <= 9:    return "overcast"
    if code <= 19:   return "foggy"
    if code <= 29:   return "light drizzle"
    if code <= 39:   return "light snow"
    if code <= 49:   return "freezing fog"
    if code <= 59:   return "drizzle"
    if code <= 69:   return "rain"
    if code <= 79:   return "heavy snow"
    if code <= 84:   return "rain showers"
    if code <= 86:   return "snow showers"
    if code <= 89:   return "hail"
    if code <= 99:   return "thunderstorm"
    return "mixed conditions"


def get_local_context(max_headlines: int = 6) -> str:
    """
    Pull together recent local news + snow conditions into a
    plain-English context block for injecting into the LLM prompt.
    Returns empty string if everything fails (safe to call always).
    """
    lines = []

    # Snow conditions first — most relevant to Maya
    snow = _fetch_snow_conditions()
    if snow:
        lines.append(f"MOUNTAIN CONDITIONS: {snow}")

    # Local headlines
    all_headlines = []
    for feed in RSS_FEEDS:
        headlines = _fetch_rss(feed["url"], max_items=2)
        for h in headlines:
            all_headlines.append(f"[{feed['area'].upper()}] {h}")

    if all_headlines:
        lines.append("RECENT LOCAL NEWS:")
        lines.extend(all_headlines[:max_headlines])

    if not lines:
        return ""

    today = datetime.now(timezone.utc).strftime("%A, %B %d")
    return f"Today is {today}.\n" + "\n".join(lines)


def inject_context_into_chat(user_id: str, message: str, system_prompt: str) -> str:
    """
    Optionally append local context to the system prompt.
    Only fetches if the message seems to be about local topics.
    This keeps latency low for unrelated messages.
    """
    local_triggers = [
        "snow", "mountain", "squaw", "palisades", "tahoe", "powder",
        "weather", "reno", "sacramento", "today", "tonight", "outside",
        "cold", "storm", "blizzard", "ski", "board", "resort", "conditions",
        "what's it like", "how's the", "news", "happening",
    ]
    lowered = message.lower()
    if not any(t in lowered for t in local_triggers):
        return system_prompt

    context = get_local_context()
    if not context:
        return system_prompt

    return system_prompt + f"\n\n---\nLOCAL CONTEXT (use naturally, don't recite it):\n{context}"
