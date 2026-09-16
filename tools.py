"""
NOVA ke tools — yeh woh actual "kaam" hain jo NOVA kar sakta hai.
Naya tool add karna ho to: (1) yahan ek function likho, (2) tools.py ke
TOOLS dictionary mein register karo, (3) main.py ke system prompt mein
uska naam aur use bata do.
"""

import subprocess
import platform
import datetime
import urllib.request
import urllib.parse
import json


def get_time(_args=None):
    """Abhi ka time batata hai."""
    now = datetime.datetime.now()
    return f"Abhi time hai: {now.strftime('%I:%M %p')}"


def get_weather(args):
    """
    Open-Meteo (free, no API key chahiye) se weather laata hai.
    args = {"city": "Jaipur"}
    """
    city = args.get("city", "Jaipur")

    try:
        # Step 1: city ka lat/long nikalo (free geocoding API)
        geo_url = (
            "https://geocoding-api.open-meteo.com/v1/search"
            f"?name={urllib.parse.quote(city)}&count=1"
        )
        with urllib.request.urlopen(geo_url, timeout=10) as resp:
            geo_data = json.loads(resp.read())

        if not geo_data.get("results"):
            return f"'{city}' ka location nahi mila."

        lat = geo_data["results"][0]["latitude"]
        lon = geo_data["results"][0]["longitude"]

        # Step 2: us location ka weather nikalo
        weather_url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code"
        )
        with urllib.request.urlopen(weather_url, timeout=10) as resp:
            weather_data = json.loads(resp.read())

        temp = weather_data["current"]["temperature_2m"]
        return f"{city} mein abhi temperature hai {temp}°C"

    except Exception as e:
        return f"Weather nahi mil paaya: {e}"


def open_app(args):
    """
    App/program open karta hai.
    args = {"app_name": "chrome"}
    NOTE: yeh sirf tumhare apne computer ke liye hai, jahan yeh naam
    system mein install/available ho.
    """
    app_name = args.get("app_name", "").lower().strip()
    system = platform.system()

    try:
        if system == "Windows":
            subprocess.Popen(["start", app_name], shell=True)
        elif system == "Darwin":  # macOS
            subprocess.Popen(["open", "-a", app_name])
        else:  # Linux
            subprocess.Popen([app_name])
        return f"{app_name} khol raha hoon..."
    except Exception as e:
        return f"{app_name} open nahi kar paaya: {e}"


# Yeh dictionary main.py isse use karega tool ka naam se function dhoondne ke liye
TOOLS = {
    "get_time": get_time,
    "get_weather": get_weather,
    "open_app": open_app,
}
