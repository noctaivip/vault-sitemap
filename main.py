
from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

WAQI_TOKEN = os.getenv("WAQI_TOKEN", "").strip()
OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY", "").strip()

app = FastAPI(title="AirGuard Uzbekistan API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


async def fetch_json(url: str) -> dict[str, Any]:
    timeout = httpx.Timeout(15.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "airguard-uzbekistan-api",
        "waqi_configured": bool(WAQI_TOKEN),
        "openweather_configured": bool(OPENWEATHER_KEY),
    }


@app.get("/api/realtime/summary")
async def realtime_summary(
    city: str = Query("tashkent", min_length=1, max_length=100)
) -> dict[str, Any]:
    if not WAQI_TOKEN or not OPENWEATHER_KEY:
        raise HTTPException(
            status_code=500,
            detail="Server tokens are not configured. Set WAQI_TOKEN and OPENWEATHER_KEY in environment.",
        )

    waqi_url = f"https://api.waqi.info/feed/{city}/?token={WAQI_TOKEN}"
    weather_url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?q={city}&appid={OPENWEATHER_KEY}&units=metric&lang=ru"
    )

    try:
        waqi_data = await fetch_json(waqi_url)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"WAQI request failed: {exc}") from exc

    try:
        weather_data = await fetch_json(weather_url)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenWeather request failed: {exc}") from exc

    if waqi_data.get("status") != "ok" or "data" not in waqi_data:
        raise HTTPException(status_code=502, detail="WAQI returned unusable payload.")
    if "main" not in weather_data:
        raise HTTPException(status_code=502, detail="OpenWeather returned unusable payload.")

    d = waqi_data["data"]
    iaqi = d.get("iaqi", {})
    aqi = int(d.get("aqi") or 0)
    pm25 = int((iaqi.get("pm25") or {}).get("v") or max(10, round(aqi * 0.45)))
    co2 = int((iaqi.get("co2") or {}).get("v") or (650 + round(aqi * 0.7)))

    wind = round(float((weather_data.get("wind") or {}).get("speed") or 0), 1)
    temp_c = round(float((weather_data.get("main") or {}).get("temp") or 0), 1)
    humidity = int((weather_data.get("main") or {}).get("humidity") or 0)
    weather_desc = ((weather_data.get("weather") or [{}])[0]).get("description") or "без описания"

    return {
        "city": {
            "query": city,
            "display_name": (d.get("city") or {}).get("name") or city.title(),
            "geo": (d.get("city") or {}).get("geo"),
        },
        "air": {
            "aqi": aqi,
            "pm25": pm25,
            "co2": co2,
            "time": (d.get("time") or {}).get("s"),
            "idx": d.get("idx"),
        },
        "weather": {
            "temperature_c": temp_c,
            "humidity": humidity,
            "wind_mps": wind,
            "description": weather_desc,
        },
        "source": {
            "waqi": True,
            "openweather": True,
        },
    }


@app.get("/")
async def root() -> FileResponse:
    index = os.path.join(FRONTEND_DIR, "index.html")
    return FileResponse(index)
