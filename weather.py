import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from statistics import mean, median, stdev


API_KEY = "demo"
BASE_URL = "https://wttr.in"
CACHE_FILE = "weather_cache.json"
HISTORY_FILE = "weather_history.json"


class WeatherData:
    def __init__(self, city: str, temp_c: float, feels_like: float,
                 humidity: int, wind_kph: float, condition: str,
                 timestamp: str = None):
        self.city = city
        self.temp_c = temp_c
        self.temp_f = round(temp_c * 9/5 + 32, 1)
        self.feels_like = feels_like
        self.humidity = humidity
        self.wind_kph = wind_kph
        self.condition = condition
        self.timestamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M")

    def to_dict(self) -> dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, d: dict):
        obj = cls(d["city"], d["temp_c"], d["feels_like"],
                  d["humidity"], d["wind_kph"], d["condition"], d["timestamp"])
        return obj

    def heat_index(self) -> float:
        t = self.temp_f
        h = self.humidity
        hi = (-42.379 + 2.04901523*t + 10.14333127*h
              - 0.22475541*t*h - 0.00683783*t*t
              - 0.05481717*h*h + 0.00122874*t*t*h
              + 0.00085282*t*h*h - 0.00000199*t*t*h*h)
        return round((hi - 32) * 5/9, 1)

    def wind_chill(self) -> Optional[float]:
        if self.temp_c > 10 or self.wind_kph < 4.8:
            return None
        wc = (13.12 + 0.6215*self.temp_c
              - 11.37*(self.wind_kph**0.16)
              + 0.3965*self.temp_c*(self.wind_kph**0.16))
        return round(wc, 1)

    def comfort_score(self) -> str:
        if 18 <= self.temp_c <= 26 and self.humidity < 60:
            return "😊 Comfortable"
        elif self.temp_c > 35 or (self.temp_c > 30 and self.humidity > 70):
            return "🥵 Very Hot"
        elif self.temp_c < 0:
            return "🥶 Freezing"
        elif self.temp_c < 10:
            return "🧥 Cold"
        elif self.humidity > 80:
            return "💧 Humid"
        else:
            return "🌤️ Moderate"


class WeatherAnalytics:
    def __init__(self, records: List[WeatherData]):
        self.records = records

    def temperature_trend(self) -> str:
        if len(self.records) < 2:
            return "Not enough data"
        temps = [r.temp_c for r in self.records]
        first_half = mean(temps[:len(temps)//2])
        second_half = mean(temps[len(temps)//2:])
        diff = second_half - first_half
        if diff > 2:
            return f"📈 Rising (+{diff:.1f}°C)"
        elif diff < -2:
            return f"📉 Falling ({diff:.1f}°C)"
        else:
            return f"➡️ Stable ({diff:+.1f}°C)"

    def stats_summary(self) -> dict:
        if not self.records:
            return {}
        temps = [r.temp_c for r in self.records]
        humidities = [r.humidity for r in self.records]
        winds = [r.wind_kph for r in self.records]
        return {
            "temp_avg": round(mean(temps), 1),
            "temp_max": max(temps),
            "temp_min": min(temps),
            "temp_median": round(median(temps), 1),
            "temp_stdev": round(stdev(temps), 2) if len(temps) > 1 else 0,
            "humidity_avg": round(mean(humidities), 1),
            "wind_avg": round(mean(winds), 1),
        }

    def detect_anomalies(self) -> List[str]:
        alerts = []
        if len(self.records) < 3:
            return alerts
        temps = [r.temp_c for r in self.records]
        avg = mean(temps)
        sd = stdev(temps) if len(temps) > 1 else 0
        for r in self.records:
            if sd > 0 and abs(r.temp_c - avg) > 2 * sd:
                alerts.append(f"⚠️ Anomaly at {r.timestamp}: {r.temp_c}°C (avg={avg:.1f}°C)")
        for r in self.records:
            if r.temp_c > 40:
                alerts.append(f"🔥 Extreme heat at {r.timestamp}: {r.temp_c}°C")
            if r.temp_c < -10:
                alerts.append(f"❄️ Extreme cold at {r.timestamp}: {r.temp_c}°C")
            if r.wind_kph > 80:
                alerts.append(f"💨 Storm warning at {r.timestamp}: {r.wind_kph} km/h")
            if r.humidity > 90:
                alerts.append(f"💧 High humidity at {r.timestamp}: {r.humidity}%")
        return alerts

    def ascii_chart(self, width: int = 40) -> str:
        if not self.records:
            return "No data"
        temps = [r.temp_c for r in self.records]
        min_t, max_t = min(temps), max(temps)
        rng = max_t - min_t if max_t != min_t else 1
        lines = []
        lines.append(f"Temperature Chart ({min_t:.0f}°C - {max_t:.0f}°C)")
        lines.append("─" * width)
        for r in self.records[-10:]:
            bar_len = int((r.temp_c - min_t) / rng * (width - 15))
            bar = "█" * bar_len
            label = r.timestamp[-5:]
            lines.append(f"{label} |{bar} {r.temp_c:.1f}°C")
        lines.append("─" * width)
        return "\n".join(lines)


class WeatherCache:
    def __init__(self):
        self.cache = {}
        self.load()

    def load(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE) as f:
                    self.cache = json.load(f)
            except json.JSONDecodeError:
                self.cache = {}

    def save(self):
        with open(CACHE_FILE, "w") as f:
            json.dump(self.cache, f, indent=2)

    def get(self, city: str) -> Optional[dict]:
        entry = self.cache.get(city.lower())
        if not entry:
            return None
        cached_time = datetime.strptime(entry["timestamp"], "%Y-%m-%d %H:%M")
        if datetime.now() - cached_time < timedelta(minutes=10):
            return entry["data"]
        return None

    def set(self, city: str, data: dict):
        self.cache[city.lower()] = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "data": data
        }
        self.save()


def fetch_weather(city: str, cache: WeatherCache) -> Optional[WeatherData]:
    cached = cache.get(city)
    if cached:
        print("📦 Using cached data...")
        return WeatherData.from_dict(cached)
    try:
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        with urllib.request.urlopen(url, timeout=8) as resp:
            raw = json.loads(resp.read().decode())
        current = raw["current_condition"][0]
        data = WeatherData(
            city=city,
            temp_c=float(current["temp_C"]),
            feels_like=float(current["FeelsLikeC"]),
            humidity=int(current["humidity"]),
            wind_kph=float(current["windspeedKmph"]),
            condition=current["weatherDesc"][0]["value"]
        )
        cache.set(city, data.to_dict())
        return data
    except Exception as e:
        print(f"❌ Could not fetch weather: {e}")
        return None


def load_history() -> List[WeatherData]:
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE) as f:
            return [WeatherData.from_dict(d) for d in json.load(f)]
    except Exception:
        return []


def save_to_history(data: WeatherData):
    history = load_history()
    history.append(data)
    history = history[-100:]
    with open(HISTORY_FILE, "w") as f:
        json.dump([d.to_dict() for d in history], f, indent=2)


def display_weather(data: WeatherData):
    print(f"\n🌍 Weather in {data.city.title()}")
    print(f"{'─'*35}")
    print(f"🌡  Temperature : {data.temp_c}°C / {data.temp_f}°F")
    print(f"🤔 Feels Like  : {data.feels_like}°C")
    print(f"💧 Humidity    : {data.humidity}%")
    print(f"💨 Wind        : {data.wind_kph} km/h")
    print(f"☁️  Condition   : {data.condition}")
    print(f"🧠 Comfort     : {data.comfort_score()}")
    wc = data.wind_chill()
    if wc:
        print(f"🌬️  Wind Chill  : {wc}°C")
    if data.temp_c > 27:
        print(f"🔆 Heat Index  : {data.heat_index()}°C")
    print(f"{'─'*35}")


import urllib.parse


def main():
    cache = WeatherCache()
    print("⛅ Weather Analytics CLI")
    print("Type 'help' for commands.\n")

    while True:
        try:
            cmd = input("weather >> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if cmd == "quit":
            print("Goodbye! ☀")
            break

        elif cmd == "help":
            print("""
Commands:
  fetch   - Get current weather for a city
  history - View saved weather history
  analyze - Analyze trends from history
  chart   - Show ASCII temperature chart
  alerts  - Check for weather anomalies
  compare - Compare two cities
  quit    - Exit
""")

        elif cmd == "fetch":
            city = input("Enter city name: ").strip()
            if not city:
                print("❌ City name cannot be empty.")
                continue
            data = fetch_weather(city, cache)
            if data:
                display_weather(data)
                save_to_history(data)

        elif cmd == "history":
            history = load_history()
            if not history:
                print("No history yet. Use 'fetch' first.")
            else:
                print(f"\n📚 Last {min(10, len(history))} records:")
                for r in history[-10:]:
                    print(f"  [{r.timestamp}] {r.city.title()}: {r.temp_c}°C, {r.condition}")

        elif cmd == "analyze":
            history = load_history()
            if len(history) < 2:
                print("Need at least 2 records. Use 'fetch' more.")
                continue
            analytics = WeatherAnalytics(history)
            stats = analytics.stats_summary()
            print(f"\n📊 Analytics Summary:")
            print(f"  Avg Temp    : {stats['temp_avg']}°C")
            print(f"  Max Temp    : {stats['temp_max']}°C")
            print(f"  Min Temp    : {stats['temp_min']}°C")
            print(f"  Median Temp : {stats['temp_median']}°C")
            print(f"  Std Dev     : {stats['temp_stdev']}°C")
            print(f"  Avg Humidity: {stats['humidity_avg']}%")
            print(f"  Avg Wind    : {stats['wind_avg']} km/h")
            print(f"  Trend       : {analytics.temperature_trend()}")

        elif cmd == "chart":
            history = load_history()
            if not history:
                print("No history yet.")
            else:
                analytics = WeatherAnalytics(history)
                print(analytics.ascii_chart())

        elif cmd == "alerts":
            history = load_history()
            if not history:
                print("No history yet.")
            else:
                analytics = WeatherAnalytics(history)
                alerts = analytics.detect_anomalies()
                if alerts:
                    print("\n🚨 Alerts:")
                    for a in alerts:
                        print(f"  {a}")
                else:
                    print("✅ No anomalies detected.")

        elif cmd == "compare":
            city1 = input("First city: ").strip()
            city2 = input("Second city: ").strip()
            d1 = fetch_weather(city1, cache)
            d2 = fetch_weather(city2, cache)
            if d1 and d2:
                print(f"\n{'─'*45}")
                print(f"{'Metric':<15} {d1.city.title():<15} {d2.city.title():<15}")
                print(f"{'─'*45}")
                print(f"{'Temp (°C)':<15} {d1.temp_c:<15} {d2.temp_c:<15}")
                print(f"{'Feels Like':<15} {d1.feels_like:<15} {d2.feels_like:<15}")
                print(f"{'Humidity %':<15} {d1.humidity:<15} {d2.humidity:<15}")
                print(f"{'Wind km/h':<15} {d1.wind_kph:<15} {d2.wind_kph:<15}")
                print(f"{'Comfort':<15} {d1.comfort_score()}")
                print(f"{'':15} {d2.comfort_score()}")
                print(f"{'─'*45}")
        else:
            print("Unknown command. Type 'help'.")


if __name__ == "__main__":
    main()
