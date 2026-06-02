import pytest
from weather import WeatherData, WeatherAnalytics


def make_weather(temp, humidity=50, wind=10, city="TestCity"):
    return WeatherData(city, temp, temp-2, humidity, wind, "Clear")


def test_temp_conversion():
    w = make_weather(0)
    assert w.temp_f == 32.0

def test_temp_conversion_100():
    w = make_weather(100)
    assert w.temp_f == 212.0

def test_comfort_comfortable():
    w = make_weather(22, humidity=50)
    assert "Comfortable" in w.comfort_score()

def test_comfort_hot():
    w = make_weather(38, humidity=80)
    assert "Hot" in w.comfort_score()

def test_comfort_cold():
    w = make_weather(-5)
    assert "Cold" in w.comfort_score() or "Freezing" in w.comfort_score()

def test_wind_chill_none_when_warm():
    w = make_weather(20)
    assert w.wind_chill() is None

def test_wind_chill_calculated():
    w = make_weather(-5, wind=30)
    assert w.wind_chill() is not None

def test_overdue_no_deadline():
    w = make_weather(20)
    assert w.is_overdue() == False

def test_analytics_trend_rising():
    records = [make_weather(t) for t in [10, 12, 15, 18, 22]]
    a = WeatherAnalytics(records)
    assert "Rising" in a.temperature_trend()

def test_analytics_trend_falling():
    records = [make_weather(t) for t in [30, 25, 20, 15, 10]]
    a = WeatherAnalytics(records)
    assert "Falling" in a.temperature_trend()

def test_stats_summary():
    records = [make_weather(t) for t in [10, 20, 30]]
    a = WeatherAnalytics(records)
    stats = a.stats_summary()
    assert stats["temp_avg"] == 20.0
    assert stats["temp_max"] == 30
    assert stats["temp_min"] == 10

def test_anomaly_detection():
    records = [make_weather(t) for t in [20, 21, 20, 19, 60]]
    a = WeatherAnalytics(records)
    alerts = a.detect_anomalies()
    assert len(alerts) > 0
