#!/usr/bin/env python3
"""Refresh the weather block in README.md from the OpenWeatherMap API.

Reads the region between <!-- WEATHER:START --> and <!-- WEATHER:END --> and
replaces it with a small markdown table. Designed to be run by
.github/workflows/weather.yml, but works locally too:

    OPENWEATHER_API_KEY=xxx WEATHER_CITY="Bogota,CO" python scripts/weather.py
"""

from __future__ import annotations

import os
import sys
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

README = Path(__file__).resolve().parent.parent / "README.md"
START = "<!-- WEATHER:START -->"
END = "<!-- WEATHER:END -->"

API_KEY = os.environ.get("OPENWEATHER_API_KEY")
LAT = os.environ.get("WEATHER_LAT")
LON = os.environ.get("WEATHER_LON")
CITY = os.environ.get("WEATHER_CITY")          # alternativa: "San Gil,CO"
LABEL = os.environ.get("WEATHER_LABEL")        # nombre a mostrar (opcional)
TZ = ZoneInfo(os.environ.get("WEATHER_TZ", "America/Bogota"))

# OpenWeatherMap condition code -> emoji
ICONS = {
    "01d": "☀️", "01n": "🌙", "02d": "🌤️", "02n": "☁️",
    "03d": "⛅", "03n": "☁️", "04d": "☁️", "04n": "☁️",
    "09d": "🌧️", "09n": "🌧️", "10d": "🌦️", "10n": "🌧️",
    "11d": "⛈️", "11n": "⛈️", "13d": "❄️", "13n": "❄️",
    "50d": "🌫️", "50n": "🌫️",
}


def fetch() -> dict:
    if not API_KEY:
        sys.exit("OPENWEATHER_API_KEY is not set — add it as a repository secret.")

    params = {"appid": API_KEY, "units": "metric"}
    if LAT and LON:                 # preferido: coordenadas, sin ambigüedad
        params |= {"lat": LAT, "lon": LON}
    elif CITY:                      # alternativa: nombre de ciudad
        params["q"] = CITY
    else:
        sys.exit("Set WEATHER_LAT + WEATHER_LON (preferred) or WEATHER_CITY.")

    url = "https://api.openweathermap.org/data/2.5/weather?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=20) as resp:
        return json.load(resp)


def local(ts: int, offset_seconds: int) -> str:
    """Format a unix timestamp in the city's own timezone."""
    tz = timezone(timedelta(seconds=offset_seconds))
    return datetime.fromtimestamp(ts, tz).strftime("%H:%M")


def render(data: dict) -> str:
    w = data["weather"][0]
    main = data["main"]
    icon = ICONS.get(w["icon"], "🌡️")
    offset = data.get("timezone", 0)
    updated = datetime.now(TZ).strftime("%A, %d %b %Y at %H:%M")

    return (
        f"| {icon} Condition | 🌡️ Temp | 🤔 Feels like | 💧 Humidity | 💨 Wind | 🌅 Sunrise | 🌇 Sunset |\n"
        f"| :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"
        f"| {w['description'].title()} | {main['temp']:.0f}°C | {main['feels_like']:.0f}°C | "
        f"{main['humidity']}% | {data['wind']['speed']:.1f} m/s | "
        f"{local(data['sys']['sunrise'], offset)} | {local(data['sys']['sunset'], offset)} |\n"
        f"\n<sub>📍 {LABEL or data.get('name', '')} · last updated {updated} "
        f"(auto-refreshed every 6h by GitHub Actions)</sub>"
    )


def main() -> None:
    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        sys.exit(f"Could not find {START} / {END} markers in README.md")

    block = render(fetch())
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    README.write_text(f"{head}{START}\n{block}\n{END}{tail}", encoding="utf-8")
    print("README weather block updated.")


if __name__ == "__main__":
    main()
