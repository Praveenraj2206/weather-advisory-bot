import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

CURRENT = "temperature_2m,wind_speed_10m,wind_gusts_10m,precipitation,weather_code"
HOURLY = (
    "temperature_2m,wind_speed_10m,wind_gusts_10m,precipitation,"
    "precipitation_probability,uv_index,weather_code"
)


def geocode_location(city: str):
    """Return (latitude, longitude, resolved_name), or (None, None, None)."""
    try:
        response = requests.get(
            GEOCODING_URL,
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=10,
        )
        response.raise_for_status()
        results = response.json().get("results") or []
        if not results:
            return None, None, None

        place = results[0]
        latitude, longitude = place.get("latitude"), place.get("longitude")
        if latitude is None or longitude is None:
            return None, None, None

        parts = [place.get("name"), place.get("admin1"), place.get("country")]
        resolved_name = ", ".join(dict.fromkeys(p for p in parts if p))
        return latitude, longitude, resolved_name

    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        print(f"Geocoding failed: {exc}")
        return None, None, None


def fetch_weather(latitude: float, longitude: float, target_hour: int | None = None):
    """Fetch weather for now (target_hour=None) or for an hour of today (local time).

    Returns a dict using the field names the SOPs use, or None on any failure.
    precipitation_probability and uv_index are hourly-only in Open-Meteo, so
    they are always read from the matching hourly slot.
    """
    try:
        response = requests.get(
            FORECAST_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": CURRENT,
                "hourly": HOURLY,
                "forecast_days": 1,
                "timezone": "auto",
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        current = data.get("current") or {}
        hourly = data.get("hourly") or {}
        now = current.get("time")
        times = hourly.get("time") or []
        if not now or not times:
            return None

        prefix = now[:13] if target_hour is None else f"{now[:10]}T{target_hour:02d}"
        index = next((i for i, t in enumerate(times) if t.startswith(prefix)), None)
        if index is None:
            return None

        def hourly_value(name):
            values = hourly.get(name) or []
            return values[index] if index < len(values) else None

        def pick(current_name, hourly_name):
            return current.get(current_name) if target_hour is None else hourly_value(hourly_name)

        weather = {
            "temperature": pick("temperature_2m", "temperature_2m"),
            "wind_speed": pick("wind_speed_10m", "wind_speed_10m"),
            "wind_gusts": pick("wind_gusts_10m", "wind_gusts_10m"),
            "precipitation": pick("precipitation", "precipitation"),
            "weather_code": pick("weather_code", "weather_code"),
            "precipitation_probability": hourly_value("precipitation_probability"),
            "uv_index": hourly_value("uv_index"),
            "time": times[index],
            "timezone": data.get("timezone"),
        }

        if weather["temperature"] is None or weather["wind_speed"] is None:
            return None
        return weather

    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        print(f"Weather request failed: {exc}")
        return None