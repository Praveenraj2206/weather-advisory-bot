import requests


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def geocode_location(city: str):
    """
    Convert a city name into latitude, longitude, and a resolved location name.
    Returns (latitude, longitude, resolved_name), or (None, None, None).
    """
    try:
        response = requests.get(
            GEOCODING_URL,
            params={
                "name": city,
                "count": 1,
                "language": "en",
                "format": "json",
            },
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        if not results:
            return None, None, None

        place = results[0]

        latitude = place.get("latitude")
        longitude = place.get("longitude")

        name_parts = [
            place.get("name"),
            place.get("admin1"),
            place.get("country"),
        ]
        resolved_name = ", ".join(
            dict.fromkeys(part for part in name_parts if part)
        )

        if latitude is None or longitude is None:
            return None, None, None

        return latitude, longitude, resolved_name

    except requests.RequestException as exc:
        print(f"Geocoding request failed: {exc}")
        return None, None, None
    except (ValueError, KeyError, TypeError) as exc:
        print(f"Could not process geocoding response: {exc}")
        return None, None, None


def fetch_weather(latitude: float, longitude: float):
    """
    Fetch current weather conditions from Open-Meteo.
    Returns a weather dictionary, or None if the request fails.
    """
    try:
        response = requests.get(
            FORECAST_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,"
                    "weather_code,"
                    "wind_speed_10m,"
                    "precipitation,"
                    "precipitation_probability,"
                    "uv_index"
                ),
                "timezone": "auto",
            },
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()
        current = data.get("current")

        if not isinstance(current, dict):
            print("Weather response did not contain current conditions.")
            return None

        required_fields = [
            "temperature_2m",
            "wind_speed_10m",
        ]

        if any(current.get(field) is None for field in required_fields):
            print("Weather response is missing essential fields.")
            return None

        return {
            "temperature_2m": current.get("temperature_2m"),
            "weather_code": current.get("weather_code"),
            "wind_speed_10m": current.get("wind_speed_10m"),
            "precipitation": current.get("precipitation"),
            "precipitation_probability": current.get(
                "precipitation_probability"
            ),
            "uv_index": current.get("uv_index"),
            "time": current.get("time"),
            "timezone": data.get("timezone"),
        }

    except requests.RequestException as exc:
        print(f"Weather request failed: {exc}")
        return None
    except (ValueError, KeyError, TypeError) as exc:
        print(f"Could not process weather response: {exc}")
        return None