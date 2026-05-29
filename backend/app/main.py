from __future__ import annotations

import hashlib
import hmac
import html
import json
import os
import secrets
import sqlite3
import urllib.parse
import uuid
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field

try:
    import swisseph as swe
except Exception:  # pragma: no cover - optional runtime fallback
    swe = None

load_dotenv()

DATABASE_URL = os.getenv("SQLITE_URL", "sqlite:///./hermex.db")
DB_PATH = Path(DATABASE_URL.replace("sqlite:///", "", 1))
if not DB_PATH.is_absolute():
    DB_PATH = Path.cwd() / DB_PATH

security = HTTPBasic()
RATE_LIMIT_BUCKETS: dict[str, list[datetime]] = {}

DEFAULT_SYSTEM_PROMPT = """
Anda adalah Hermes, seorang ahli astrologi modern dan mentor reflektif.
Analisis natal chart yang diberikan secara hati-hati berdasarkan posisi planet,
zodiac sign, house estimate, aspect, lokasi, timezone, dan konteks profil.
Gunakan bahasa: {language}.

Aturan:
- Jangan menyatakan astrologi sebagai kepastian mutlak.
- Jelaskan sebagai refleksi pengembangan diri dan arah eksplorasi karier.
- Hubungkan interpretasi dengan data chart yang tersedia.
- Jangan mengarang data chart yang tidak ada di payload.
- Return JSON valid saja dengan field:
  summary, strengths, weaknesses, love, interests, talents, careers,
  five_year_roadmap, development_plan, confidence.
- strengths, weaknesses, interests, talents, careers, love harus array string.
- five_year_roadmap harus array object dengan year, theme, focus.
- Untuk five_year_roadmap, gunakan 5 tahun terakhir yang sudah lewat, mundur dari tahun sekarang, bukan 5 tahun ke depan.
- Isi setiap focus 1-2 kalimat yang cukup informatif.
- development_plan boleh array object dengan horizon, focus, confidence.
- Buat ringkas, praktis, dan mudah discan di kartu UI.
""".strip()

ZODIAC_SIGNS = [
    ("Aries", "fire", "cardinal"),
    ("Taurus", "earth", "fixed"),
    ("Gemini", "air", "mutable"),
    ("Cancer", "water", "cardinal"),
    ("Leo", "fire", "fixed"),
    ("Virgo", "earth", "mutable"),
    ("Libra", "air", "cardinal"),
    ("Scorpio", "water", "fixed"),
    ("Sagittarius", "fire", "mutable"),
    ("Capricorn", "earth", "cardinal"),
    ("Aquarius", "air", "fixed"),
    ("Pisces", "water", "mutable"),
]


class BirthProfileInput(BaseModel):
    display_name: str | None = Field(default=None, max_length=80)
    birth_date: date
    birth_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    birth_place: str = Field(min_length=2, max_length=160)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = Field(default=None, max_length=80)


class ValidationInput(BaseModel):
    profile_id: str
    answers: dict[str, Any] = Field(default_factory=dict)


class InterpretationInput(BaseModel):
    profile_id: str
    language: str = Field(default="id", pattern="^(id|en)$")


class DetailedQuestionInput(BaseModel):
    profile_id: str
    language: str = Field(default="id", pattern="^(id|en)$")
    question: str = Field(min_length=4, max_length=700)


class LLMConfigInput(BaseModel):
    provider: str = Field(default="openai_compat", max_length=80)
    base_url: str | None = Field(default=None, max_length=300)
    api_key: str | None = Field(default=None, max_length=500)
    model: str | None = Field(default=None, max_length=160)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=128, le=4000)
    requests_per_minute: int | None = Field(default=None, ge=1, le=300)
    requests_per_day: int | None = Field(default=None, ge=1, le=10000)


class LLMModelSyncInput(BaseModel):
    base_url: str | None = Field(default=None, max_length=300)
    api_key: str | None = Field(default=None, max_length=500)


class FeedbackInput(BaseModel):
    profile_id: str | None = Field(default=None, max_length=80)
    interpretation_id: str | None = Field(default=None, max_length=80)
    rating: int = Field(ge=1, le=5)
    message: str | None = Field(default=None, max_length=1200)
    source: str = Field(default="web", max_length=40)


class PublicProfileInput(BaseModel):
    profile_id: str = Field(max_length=80)
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-z0-9_]+$")
    email: str = Field(min_length=5, max_length=160)
    display_name: str | None = Field(default=None, max_length=80)
    bio: str | None = Field(default=None, max_length=240)


class UserHistorySyncInput(BaseModel):
    profile_ids: list[str] = Field(default_factory=list, max_length=50)


class SkyPostInput(BaseModel):
    id: str | None = Field(default=None, max_length=80)
    slug: str = Field(min_length=3, max_length=120, pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=3, max_length=180)
    tag: str = Field(min_length=2, max_length=80)
    summary: str = Field(min_length=8, max_length=600)
    body: str = Field(min_length=8, max_length=2400)


class SkyPostDeleteInput(BaseModel):
    id: str = Field(max_length=80)


class AstrologyCalendarInput(BaseModel):
    id: str | None = Field(default=None, max_length=80)
    event_date: date
    title: str = Field(min_length=3, max_length=180)
    tag: str = Field(min_length=2, max_length=80)
    summary: str = Field(min_length=8, max_length=600)


class AstrologyCalendarDeleteInput(BaseModel):
    id: str = Field(max_length=80)


class QuestStartInput(BaseModel):
    profile_id: str
    quest_slug: str


class QuestCompleteInput(BaseModel):
    quest_id: str
    result_payload: dict[str, Any] = Field(default_factory=dict)


@contextmanager
def db() -> Any:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY,
                display_name TEXT,
                birth_date TEXT NOT NULL,
                birth_time TEXT,
                birth_place TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                timezone TEXT,
                time_unknown INTEGER NOT NULL,
                profile_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS interpretations (
                id TEXT PRIMARY KEY,
                profile_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_hash TEXT NOT NULL,
                request_payload_json TEXT NOT NULL DEFAULT '{}',
                response_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(interpretations)").fetchall()
        }
        if "request_payload_json" not in columns:
            conn.execute("ALTER TABLE interpretations ADD COLUMN request_payload_json TEXT NOT NULL DEFAULT '{}'")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_quests (
                id TEXT PRIMARY KEY,
                profile_id TEXT NOT NULL,
                quest_slug TEXT NOT NULL,
                status TEXT NOT NULL,
                score INTEGER NOT NULL DEFAULT 0,
                result_json TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                profile_id TEXT,
                interpretation_id TEXT,
                rating INTEGER NOT NULL,
                message TEXT,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS public_profiles (
                username TEXT PRIMARY KEY,
                profile_id TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                display_name TEXT,
                bio TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_sub TEXT NOT NULL,
                profile_id TEXT NOT NULL,
                linked_at TEXT NOT NULL,
                PRIMARY KEY (user_sub, profile_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sky_posts (
                id TEXT PRIMARY KEY,
                slug TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                tag TEXT NOT NULL,
                summary TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS astrology_calendar (
                id TEXT PRIMARY KEY,
                event_date TEXT NOT NULL,
                title TEXT NOT NULL,
                tag TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        if conn.execute("SELECT COUNT(*) AS count FROM astrology_calendar").fetchone()["count"] == 0:
            seed_time = now_iso()
            for event in default_astrology_calendar():
                conn.execute(
                    """
                    INSERT INTO astrology_calendar (id, event_date, title, tag, summary, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        event["event_date"],
                        event["title"],
                        event["tag"],
                        event["summary"],
                        seed_time,
                        seed_time,
                    ),
                )
        if conn.execute("SELECT COUNT(*) AS count FROM sky_posts").fetchone()["count"] == 0:
            seed_time = now_iso()
            for post in default_sky_posts():
                conn.execute(
                    """
                    INSERT INTO sky_posts (id, slug, title, tag, summary, body, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        post["slug"],
                        post["title"],
                        post["tag"],
                        post["summary"],
                        post["body"],
                        seed_time,
                        seed_time,
                    ),
                )


def verify_admin_credentials(username_value: str, password_value: str) -> bool:
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "hermes-admin")
    valid_user = secrets.compare_digest(username_value, username)
    valid_password = secrets.compare_digest(password_value, password)
    return valid_user and valid_password


def admin_session_token() -> str:
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "hermes-admin")
    secret = os.getenv("ADMIN_SESSION_SECRET", "hermex-local-admin-session")
    return hashlib.sha256(f"{username}:{password}:{secret}".encode()).hexdigest()


def public_app_url() -> str:
    return os.getenv("PUBLIC_APP_URL", "http://127.0.0.1:18173").strip().rstrip("/")


def google_oauth_config() -> dict[str, str]:
    return {
        "client_id": os.getenv("GOOGLE_CLIENT_ID", "").strip(),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", "").strip(),
        "redirect_uri": os.getenv(
            "GOOGLE_REDIRECT_URI",
            "http://127.0.0.1:18080/api/v1/auth/google/callback",
        ).strip(),
        "session_secret": os.getenv(
            "GOOGLE_SESSION_SECRET",
            os.getenv("ADMIN_SESSION_SECRET", "hermex-local-google-session"),
        ).strip(),
    }


def google_session_token(user: dict[str, Any]) -> str:
    config = google_oauth_config()
    payload = json.dumps(
        {
            "sub": user.get("sub"),
            "email": user.get("email"),
            "name": user.get("name"),
            "picture": user.get("picture"),
            "iat": int(datetime.now(timezone.utc).timestamp()),
        },
        separators=(",", ":"),
    )
    signature = hmac.new(config["session_secret"].encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def read_google_session(request: Request) -> dict[str, Any] | None:
    token = request.cookies.get("hermex_google")
    if not token or "." not in token:
        return None
    payload, signature = token.rsplit(".", 1)
    expected = hmac.new(
        google_oauth_config()["session_secret"].encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    if not secrets.compare_digest(signature, expected):
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def require_google_user(request: Request) -> dict[str, Any]:
    user = read_google_session(request)
    if not user or not (user.get("sub") or user.get("email")):
        raise HTTPException(status_code=401, detail="Google login required")
    return user


def is_admin_request(request: Request) -> bool:
    cookie = request.cookies.get("hermex_admin")
    if cookie and secrets.compare_digest(cookie, admin_session_token()):
        return True

    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("basic "):
        try:
            import base64

            raw = base64.b64decode(authorization.split(" ", 1)[1]).decode()
            username_value, password_value = raw.split(":", 1)
            return verify_admin_credentials(username_value, password_value)
        except Exception:
            return False
    return False


def require_admin(request: Request) -> bool:
    if is_admin_request(request):
        return True
    raise HTTPException(status_code=401, detail="Not authenticated", headers={"WWW-Authenticate": "Basic"})


def login_page(error: str = "") -> str:
    return f"""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Hermex Admin Login</title>
        <style>
          body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; background: linear-gradient(135deg,#fff8df,#dff5ed); color: #2f2437; font-family: Avenir Next, system-ui, sans-serif; }}
          form {{ width: min(420px, calc(100vw - 32px)); border-radius: 28px; background: #fffdf7; padding: 28px; box-shadow: 0 24px 70px rgba(47,36,55,.14); }}
          h1 {{ margin: 0 0 8px; letter-spacing: -.04em; }}
          p {{ color: #765f7a; }}
          label {{ display: grid; gap: 8px; margin: 14px 0; font-weight: 800; }}
          input {{ border: 1px solid rgba(47,36,55,.18); border-radius: 16px; padding: 13px 14px; font: inherit; }}
          button {{ width: 100%; border: 0; border-radius: 999px; padding: 14px 16px; background: #2f2437; color: #fff8df; font-weight: 900; cursor: pointer; }}
          .error {{ color: #b3264c; font-weight: 800; }}
        </style>
      </head>
      <body>
        <form method="post" action="/admin/login">
          <h1>Hermex Admin</h1>
          <p>Masuk untuk melihat guest history dan mengatur prompt Hermes.</p>
          {f'<p class="error">{html.escape(error)}</p>' if error else ''}
          <label>Username<input name="username" autocomplete="username" /></label>
          <label>Password<input name="password" type="password" autocomplete="current-password" /></label>
          <button type="submit">Login</button>
        </form>
      </body>
    </html>
    """


def require_basic_admin(credentials: HTTPBasicCredentials = Depends(security)) -> bool:
    if not verify_admin_credentials(credentials.username, credentials.password):
        raise HTTPException(
            status_code=401,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True


def get_setting(key: str, default: str) -> str:
    with db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with db() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (key, value, now_iso()),
        )


def setting_float(key: str, env_key: str, default: str) -> float:
    try:
        return float(get_setting(key, os.getenv(env_key, default)))
    except ValueError:
        return float(default)


def setting_int(key: str, env_key: str, default: str) -> int:
    try:
        return int(get_setting(key, os.getenv(env_key, default)))
    except ValueError:
        return int(default)


def get_llm_config() -> dict[str, Any]:
    return {
        "provider": get_setting("llm_provider", os.getenv("LLM_PROVIDER", "openai_compat")).strip() or "openai_compat",
        "base_url": get_setting("llm_base_url", os.getenv("LLM_BASE_URL", "")).strip().rstrip("/"),
        "api_key": get_setting("llm_api_key", os.getenv("LLM_API_KEY", "")).strip(),
        "model": get_setting("llm_model", os.getenv("LLM_MODEL", "gpt-4o-mini")).strip() or "gpt-4o-mini",
        "temperature": setting_float("llm_temperature", "LLM_TEMPERATURE", "0.4"),
        "max_tokens": setting_int("llm_max_tokens", "LLM_MAX_TOKENS", "700"),
        "requests_per_minute": setting_int("llm_requests_per_minute", "LLM_REQUESTS_PER_MINUTE", "6"),
        "requests_per_day": setting_int("llm_requests_per_day", "LLM_REQUESTS_PER_DAY", "40"),
    }


def public_llm_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or get_llm_config()
    return {
        "provider": config["provider"],
        "base_url": config["base_url"],
        "model": config["model"],
        "temperature": config["temperature"],
        "max_tokens": config["max_tokens"],
        "requests_per_minute": config["requests_per_minute"],
        "requests_per_day": config["requests_per_day"],
        "has_api_key": bool(config["api_key"]),
    }


def rate_limit_client_key(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    client_host = forwarded_for.split(",", 1)[0].strip() if forwarded_for else ""
    if not client_host:
        client_host = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")[:120]
    return hashlib.sha256(f"{client_host}:{user_agent}".encode()).hexdigest()[:24]


def enforce_ai_rate_limit(request: Request, profile_id: str | None = None) -> None:
    config = get_llm_config()
    minute_limit = max(1, int(config["requests_per_minute"]))
    day_limit = max(1, int(config["requests_per_day"]))
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=1)
    for bucket_key, bucket_events in list(RATE_LIMIT_BUCKETS.items()):
        bucket_events[:] = [event_time for event_time in bucket_events if event_time > stale_cutoff]
        if not bucket_events:
            RATE_LIMIT_BUCKETS.pop(bucket_key, None)
    key = f"ai:{rate_limit_client_key(request)}"
    events = RATE_LIMIT_BUCKETS.setdefault(key, [])
    events[:] = [event_time for event_time in events if now - event_time < timedelta(days=1)]
    minute_events = [event_time for event_time in events if now - event_time < timedelta(minutes=1)]
    if len(minute_events) >= minute_limit:
        raise HTTPException(
            status_code=429,
            detail=f"AI request limit reached: max {minute_limit} request(s) per minute.",
        )
    if len(events) >= day_limit:
        raise HTTPException(
            status_code=429,
            detail=f"AI request limit reached: max {day_limit} request(s) per day.",
        )
    events.append(now)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def chart_seed(payload: BirthProfileInput) -> int:
    raw = (
        f"{payload.birth_date}:{payload.birth_time}:{payload.birth_place}:"
        f"{payload.latitude}:{payload.longitude}:{payload.timezone}"
    ).encode()
    return int(hashlib.sha256(raw).hexdigest()[:8], 16)


def utc_birth_context(payload: BirthProfileInput) -> tuple[date, float, float]:
    local_hour = 12.0
    if payload.birth_time:
        hh, mm = payload.birth_time.split(":")
        local_hour = int(hh) + int(mm) / 60
        try:
            tzinfo = ZoneInfo(payload.timezone or "UTC")
        except ZoneInfoNotFoundError:
            tzinfo = timezone.utc
        local_dt = datetime.combine(payload.birth_date, time(int(hh), int(mm)), tzinfo=tzinfo)
        utc_dt = local_dt.astimezone(timezone.utc)
        utc_hour = utc_dt.hour + utc_dt.minute / 60 + utc_dt.second / 3600
        return utc_dt.date(), utc_hour, local_hour
    return payload.birth_date, 12.0, local_hour


def compute_chart(payload: BirthProfileInput) -> dict[str, Any]:
    utc_date, utc_hour, local_hour = utc_birth_context(payload)

    planets = {}
    if swe:
        jd = swe.julday(utc_date.year, utc_date.month, utc_date.day, utc_hour)
        planet_ids = {
            "sun": swe.SUN,
            "moon": swe.MOON,
            "mercury": swe.MERCURY,
            "venus": swe.VENUS,
            "mars": swe.MARS,
            "jupiter": swe.JUPITER,
            "saturn": swe.SATURN,
            "uranus": swe.URANUS,
            "neptune": swe.NEPTUNE,
            "pluto": swe.PLUTO,
        }
        optional_planets = {
            "true_node": getattr(swe, "TRUE_NODE", None),
            "chiron": getattr(swe, "CHIRON", None),
            "lilith": getattr(swe, "MEAN_APOG", None),
        }
        planet_ids.update({name: planet_id for name, planet_id in optional_planets.items() if planet_id is not None})
        for name, planet_id in planet_ids.items():
            try:
                result, _flags = swe.calc_ut(jd, planet_id)
            except Exception:
                continue
            planets[name] = {"longitude": round(float(result[0]) % 360, 3)}
    else:
        seed = chart_seed(payload)
        location_offset = ((payload.longitude or 0) * 0.37 + (payload.latitude or 0) * 0.19) % 360
        for idx, name in enumerate(["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto", "true_node", "chiron", "lilith"]):
            planets[name] = {"longitude": round(((seed / (idx + 3)) + idx * 37 + location_offset) % 360, 3)}

    for planet in planets.values():
        planet.update(zodiac_position(planet["longitude"]))

    ascendant = None if payload.birth_time is None else round((planets["sun"]["longitude"] + local_hour * 15) % 360, 3)
    house_system = "equal_house_estimate"
    house_cusps = None
    midheaven = None
    if swe and payload.birth_time is not None and payload.latitude is not None and payload.longitude is not None:
        try:
            jd = swe.julday(utc_date.year, utc_date.month, utc_date.day, utc_hour)
            cusps, ascmc = swe.houses_ex(jd, payload.latitude, payload.longitude, b"P")
            house_cusps = [round(float(cusp) % 360, 3) for cusp in cusps]
            ascendant = round(float(ascmc[0]) % 360, 3)
            midheaven = round(float(ascmc[1]) % 360, 3)
            house_system = "placidus"
        except Exception:
            house_cusps = None
    planet_houses = (
        planet_houses_from_cusps(planets, house_cusps)
        if house_cusps
        else estimate_planet_houses(planets, ascendant)
    )

    return {
        "planets": planets,
        "houses": {
            "ascendant": ascendant,
            "ascendant_zodiac": None if ascendant is None else zodiac_position(ascendant),
            "midheaven": midheaven,
            "midheaven_zodiac": None if midheaven is None else zodiac_position(midheaven),
            "house_system": house_system,
            "cusps": house_cusps,
            "planet_houses": planet_houses,
            "precision": "reduced_without_birth_time" if payload.birth_time is None else "time_based_estimate",
        },
        "aspects": build_aspects(planets),
        "location": {
            "birth_place": payload.birth_place,
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "timezone": payload.timezone,
            "utc_date": utc_date.isoformat(),
            "utc_decimal_hour": round(utc_hour, 4),
        },
    }


def build_aspects(planets: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    major = {"conjunction": 0, "sextile": 60, "square": 90, "trine": 120, "opposition": 180}
    names = list(planets)
    aspects: list[dict[str, Any]] = []
    for left_index, left in enumerate(names):
        for right in names[left_index + 1 :]:
            diff = abs(planets[left]["longitude"] - planets[right]["longitude"])
            diff = min(diff, 360 - diff)
            for aspect_name, angle in major.items():
                orb = abs(diff - angle)
                if orb <= 6:
                    aspects.append({"left": left, "right": right, "type": aspect_name, "orb": round(orb, 2)})
    return aspects[:16]


def zodiac_position(longitude: float) -> dict[str, Any]:
    sign_index = int(longitude // 30) % 12
    sign, element, modality = ZODIAC_SIGNS[sign_index]
    degree = longitude % 30
    return {
        "zodiac_sign": sign,
        "degree_in_sign": round(degree, 2),
        "element": element,
        "modality": modality,
    }


def estimate_planet_houses(planets: dict[str, dict[str, Any]], ascendant: float | None) -> dict[str, int | None]:
    if ascendant is None:
        return {name: None for name in planets}
    houses: dict[str, int | None] = {}
    for name, planet in planets.items():
        relative = (planet["longitude"] - ascendant) % 360
        houses[name] = int(relative // 30) + 1
    return houses


def planet_houses_from_cusps(planets: dict[str, dict[str, Any]], cusps: list[float] | None) -> dict[str, int | None]:
    if not cusps or len(cusps) < 12:
        return {name: None for name in planets}
    houses: dict[str, int | None] = {}
    for name, planet in planets.items():
        longitude = planet["longitude"] % 360
        matched_house: int | None = None
        for index, cusp in enumerate(cusps[:12]):
            next_cusp = cusps[(index + 1) % 12]
            span = (next_cusp - cusp) % 360
            relative = (longitude - cusp) % 360
            if relative < span:
                matched_house = index + 1
                break
        houses[name] = matched_house
    return houses


def sign_element(longitude: float) -> str:
    return ZODIAC_SIGNS[int(longitude // 30) % 12][1]


def build_trait_profile(chart: dict[str, Any], time_unknown: bool) -> dict[str, Any]:
    element_scores = {"fire": 0, "earth": 0, "air": 0, "water": 0}
    for planet in chart["planets"].values():
        element_scores[sign_element(planet["longitude"])] += 1

    ranked = sorted(element_scores.items(), key=lambda item: item[1], reverse=True)
    dominant = ranked[0][0]
    trait_map = {
        "fire": ["initiative", "creative courage", "visible leadership"],
        "earth": ["craft discipline", "systems thinking", "practical execution"],
        "air": ["communication", "analysis", "learning agility"],
        "water": ["empathy", "pattern sensing", "reflective guidance"],
    }
    career_map = {
        "fire": ["founder/operator", "creative producer", "community lead"],
        "earth": ["product builder", "operations analyst", "technical craftsperson"],
        "air": ["researcher", "educator", "developer advocate"],
        "water": ["coach", "story strategist", "care-oriented designer"],
    }
    confidence = 0.72 if not time_unknown else 0.52
    return {
        "dominant_element": dominant,
        "element_scores": element_scores,
        "interests": trait_map[dominant],
        "talents": trait_map[dominant][:2],
        "career_themes": career_map[dominant],
        "confidence": {"score": confidence, "label": "medium" if time_unknown else "high"},
        "ethics_note": "Reflective guidance only; not deterministic prediction.",
    }


def validation_questions(payload: BirthProfileInput) -> list[dict[str, Any]]:
    questions = []
    if payload.birth_time is None:
        questions.append(
            {
                "id": "birth_time_certainty",
                "label": "How certain are you about your birth time?",
                "type": "choice",
                "choices": ["unknown", "approximate", "known_later"],
            }
        )
    questions.append(
        {
            "id": "current_pull",
            "label": "Which work style feels most energizing right now?",
            "type": "choice",
            "choices": ["building", "teaching", "organizing", "supporting"],
        }
    )
    return questions


def roadmap_for(profile: dict[str, Any]) -> list[dict[str, Any]]:
    themes = profile["traits"]["career_themes"]
    return [
        {"horizon": "30 days", "focus": f"Explore {themes[0]} through one small public project.", "confidence": "medium"},
        {"horizon": "60 days", "focus": f"Validate {themes[1]} with feedback from 3 trusted people.", "confidence": "medium"},
        {"horizon": "90 days", "focus": f"Package learnings into a portfolio path around {themes[2]}.", "confidence": "medium"},
    ]


def load_profile(profile_id: str) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute("SELECT profile_json FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    return json.loads(row["profile_json"])


def save_profile(profile: dict[str, Any]) -> None:
    with db() as conn:
        conn.execute(
            """
            UPDATE profiles
            SET profile_json = ?
            WHERE id = ?
            """,
            (json.dumps(profile), profile["profile_id"]),
        )


def latest_interpretation(profile_id: str) -> dict[str, Any] | None:
    with db() as conn:
        row = conn.execute(
            """
            SELECT id, provider, model, response_json, created_at
            FROM interpretations
            WHERE profile_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (profile_id,),
        ).fetchone()
    if not row:
        return None
    return {
        "interpretation_id": row["id"],
        "provider": row["provider"],
        "model": row["model"],
        "interpretation": json.loads(row["response_json"]),
        "created_at": row["created_at"],
    }


def public_profile_payload(row: sqlite3.Row) -> dict[str, Any]:
    profile = load_profile(row["profile_id"])
    return {
        "username": row["username"],
        "display_name": row["display_name"] or profile.get("display_name"),
        "bio": row["bio"],
        "profile": profile,
        "latest_interpretation": latest_interpretation(row["profile_id"]),
        "public_url": f"{public_app_url()}/@{row['username']}",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def default_sky_posts() -> list[dict[str, str]]:
    return [
        {
            "slug": "bulan-sebagai-ritme-harian",
            "title": "Bulan sebagai ritme harian",
            "tag": "Moon",
            "summary": "Bulan sering dipakai sebagai bahasa simbolik untuk membaca ritme emosi, kebutuhan aman, dan kapan kita perlu jeda.",
            "body": "Di Hermex, berita langit tidak dibaca sebagai sebab pasti peristiwa bumi. Ia dipakai sebagai lensa refleksi: ketika ritme terasa cepat, kita bisa bertanya apa yang perlu dirapikan, dilepas, atau dirawat.",
        },
        {
            "slug": "merkurius-dan-cuaca-komunikasi",
            "title": "Merkurius dan cuaca komunikasi",
            "tag": "Mercury",
            "summary": "Merkurius melambangkan cara berpikir, bahasa, belajar, dan transaksi ide antar orang.",
            "body": "Saat tema Merkurius sedang terasa kuat, hubungan antara langit dan bumi bisa dibaca sebagai ajakan memperjelas pesan: menulis lebih ringkas, memeriksa asumsi, dan membuat keputusan dengan informasi yang cukup.",
        },
        {
            "slug": "saturnus-dan-struktur-sosial",
            "title": "Saturnus dan struktur sosial",
            "tag": "Saturn",
            "summary": "Saturnus sering dikaitkan dengan batas, struktur, tanggung jawab, dan proses menjadi dewasa.",
            "body": "Dalam peristiwa sehari-hari, simbol Saturnus membantu membaca mengapa sistem, aturan, dan komitmen terasa penting. Bukan untuk menakut-nakuti, tapi untuk melihat area hidup yang minta fondasi lebih sehat.",
        },
    ]


def default_astrology_calendar() -> list[dict[str, str]]:
    today = date.today()
    return [
        {
            "event_date": today.isoformat(),
            "title": "Moon check-in",
            "tag": "Moon",
            "summary": "Momen refleksi ringan untuk membaca kebutuhan emosi dan ritme harian.",
        },
        {
            "event_date": (today + timedelta(days=7)).isoformat(),
            "title": "Mercury note day",
            "tag": "Mercury",
            "summary": "Hari simbolik untuk merapikan pesan, catatan, dan cara mengambil keputusan.",
        },
    ]


def sky_news_rows() -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT id, slug, title, tag, summary, body, created_at, updated_at
            FROM sky_posts
            ORDER BY updated_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def astrology_calendar_rows() -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT id, event_date, title, tag, summary, created_at, updated_at
            FROM astrology_calendar
            ORDER BY event_date ASC, updated_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def parse_llm_content(content: str, raw: dict[str, Any] | None = None) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```json"):
        text = text.removeprefix("```json").removesuffix("```").strip()
    elif text.startswith("```"):
        text = text.removeprefix("```").removesuffix("```").strip()

    try:
        parsed = json.loads(text)
        return normalize_llm_response(parsed if isinstance(parsed, dict) else {"summary": parsed})
    except json.JSONDecodeError:
        return normalize_llm_response({"summary": text or "LLM returned no message content.", **({"raw": raw} if raw else {})})


def stringify_response_item(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, (int, float, bool)):
        return str(item)
    if isinstance(item, dict):
        for key in ("title", "name", "role", "career", "path", "label", "focus", "description", "summary"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value
        values = [str(value) for value in item.values() if isinstance(value, (str, int, float))]
        if values:
            return " - ".join(values[:3])
    return json.dumps(item, ensure_ascii=False)


def normalize_llm_response(response: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(response)
    for key in ("strengths", "weaknesses", "love", "interests", "talents", "careers"):
        value = normalized.get(key)
        if isinstance(value, list):
            normalized[key] = [stringify_response_item(item) for item in value]
        elif value:
            normalized[key] = [stringify_response_item(value)]
    return normalized


def parse_sse_chat_content(text: str) -> str:
    chunks: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line.removeprefix("data:").strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            continue
        choice = (event.get("choices") or [{}])[0]
        delta = choice.get("delta") or {}
        message = choice.get("message") or {}
        content = delta.get("content") or message.get("content") or ""
        if content:
            chunks.append(content)
    return "".join(chunks).strip()


async def call_llm(profile: dict[str, Any], language: str = "id", question: str | None = None) -> dict[str, Any]:
    config = get_llm_config()
    provider = config["provider"]
    base_url = config["base_url"]
    api_key = config["api_key"]
    model = config["model"]
    temperature = config["temperature"]
    max_tokens = config["max_tokens"]

    prompt_payload = {
        "profile_id": profile["profile_id"],
        "language": language,
        "current_year": datetime.now(timezone.utc).year,
        "birth_context": {
            "birth_date": profile.get("birth_date"),
            "birth_time": profile.get("birth_time"),
            "birth_place": profile.get("birth_place"),
            "latitude": profile.get("latitude"),
            "longitude": profile.get("longitude"),
            "timezone": profile.get("timezone"),
        },
        "astrology_chart": profile["chart"],
        "traits": profile["traits"],
        "roadmap_preview": profile["roadmap_preview"],
        "validation": profile.get("validation", {}),
        "detail_question": question,
    }
    language_name = "Indonesian" if language == "id" else "English"
    system_prompt_template = get_setting(
        "llm_system_prompt",
        os.getenv("LLM_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
    )
    system_prompt = system_prompt_template.replace("{language}", language_name)
    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {"role": "user", "content": json.dumps(prompt_payload, sort_keys=True)},
    ]
    prompt_hash = hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()
    request_payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    if provider == "local_fallback" or not base_url or not api_key:
        return {
            "provider": "local_fallback",
            "model": "local-template",
            "prompt_hash": prompt_hash,
            "request_payload": request_payload,
            "response": {
                "summary": (
                    "Hermex membuat roadmap reflektif lokal karena kredensial LLM belum dikonfigurasi."
                    if language == "id"
                    else "Hermex generated a local reflective roadmap because no LLM credentials were configured."
                ),
                "strengths": profile["traits"]["talents"],
                "development_plan": profile["roadmap_preview"],
                "careers": profile["traits"]["career_themes"],
                "confidence": profile["traits"]["confidence"],
            },
        }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=request_payload,
            )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return {
            "provider": f"{provider}_error",
            "model": model,
            "prompt_hash": prompt_hash,
            "request_payload": request_payload,
            "response": {
                "summary": (
                    "Provider LLM belum bisa dijangkau, jadi Hermex mengembalikan interpretasi lokal yang aman."
                    if language == "id"
                    else "The configured LLM provider could not be reached, so Hermex returned a safe local interpretation."
                ),
                "error": exc.__class__.__name__,
                "strengths": profile["traits"]["talents"],
                "development_plan": profile["roadmap_preview"],
                "careers": profile["traits"]["career_themes"],
                "confidence": profile["traits"]["confidence"],
            },
        }

    try:
        data = response.json()
    except json.JSONDecodeError:
        text = response.text.strip()
        streamed_content = parse_sse_chat_content(text)
        if streamed_content:
            return {
                "provider": provider,
                "model": model,
                "prompt_hash": prompt_hash,
                "request_payload": request_payload,
                "response": parse_llm_content(streamed_content),
            }
        return {
            "provider": f"{provider}_non_json",
            "model": model,
            "prompt_hash": prompt_hash,
            "request_payload": request_payload,
            "response": {
                "summary": text[:1200] or (
                    "Provider LLM mengembalikan respons non-JSON kosong."
                    if language == "id"
                    else "The configured LLM provider returned an empty non-JSON response."
                ),
                "strengths": profile["traits"]["talents"],
                "development_plan": profile["roadmap_preview"],
                "careers": profile["traits"]["career_themes"],
                "confidence": profile["traits"]["confidence"],
            },
        }

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    parsed = parse_llm_content(content, raw=data)
    return {
        "provider": provider,
        "model": model,
        "prompt_hash": prompt_hash,
        "request_payload": request_payload,
        "response": parsed,
    }


app = FastAPI(title="Hermex API", version="0.1.0-alpha")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:18173,http://127.0.0.1:18173",
    ).split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/v1/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "hermex-api", "database": str(DB_PATH)}


@app.get("/api/v1/auth/google/start")
def google_auth_start() -> RedirectResponse:
    config = google_oauth_config()
    if not config["client_id"] or not config["client_secret"]:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")
    state = secrets.token_urlsafe(24)
    query = urllib.parse.urlencode(
        {
            "client_id": config["client_id"],
            "redirect_uri": config["redirect_uri"],
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "select_account",
        }
    )
    response = RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{query}", status_code=302)
    response.set_cookie(
        "hermex_oauth_state",
        state,
        httponly=True,
        samesite="lax",
        secure=public_app_url().startswith("https://"),
        max_age=600,
    )
    return response


@app.get("/api/v1/auth/google/callback")
async def google_auth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    app_url = public_app_url()
    if error:
        return RedirectResponse(f"{app_url}/?auth=google_error", status_code=303)
    expected_state = request.cookies.get("hermex_oauth_state")
    if not code or not state or not expected_state or not secrets.compare_digest(state, expected_state):
        return RedirectResponse(f"{app_url}/?auth=google_state_error", status_code=303)

    config = google_oauth_config()
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": config["client_id"],
                    "client_secret": config["client_secret"],
                    "redirect_uri": config["redirect_uri"],
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            user_response = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            user_response.raise_for_status()
            user = user_response.json()
    except (httpx.HTTPError, KeyError, json.JSONDecodeError):
        return RedirectResponse(f"{app_url}/?auth=google_exchange_error", status_code=303)

    response = RedirectResponse(f"{app_url}/?auth=google_connected", status_code=303)
    response.delete_cookie("hermex_oauth_state")
    response.set_cookie(
        "hermex_google",
        google_session_token(user),
        httponly=True,
        samesite="lax",
        secure=app_url.startswith("https://"),
        max_age=60 * 60 * 24 * 30,
    )
    return response


@app.get("/api/v1/auth/me")
def auth_me(request: Request) -> dict[str, Any]:
    user = read_google_session(request)
    return {"authenticated": bool(user), "user": user}


@app.get("/api/v1/auth/logout")
def auth_logout() -> RedirectResponse:
    response = RedirectResponse(public_app_url(), status_code=303)
    response.delete_cookie("hermex_google")
    return response


@app.post("/api/v1/user/history/sync")
def sync_user_history(payload: UserHistorySyncInput, request: Request) -> dict[str, Any]:
    user = require_google_user(request)
    user_sub = str(user.get("sub") or user.get("email"))
    profile_ids = list(dict.fromkeys([profile_id for profile_id in payload.profile_ids if profile_id]))
    linked_count = 0
    with db() as conn:
        for profile_id in profile_ids:
            exists = conn.execute("SELECT 1 FROM profiles WHERE id = ?", (profile_id,)).fetchone()
            if not exists:
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO user_profiles (user_sub, profile_id, linked_at)
                VALUES (?, ?, ?)
                """,
                (user_sub, profile_id, now_iso()),
            )
            linked_count += 1
    return {"status": "ok", "linked": linked_count}


@app.get("/api/v1/user/history")
def get_user_history(request: Request) -> dict[str, Any]:
    user = require_google_user(request)
    user_sub = str(user.get("sub") or user.get("email"))
    with db() as conn:
        rows = conn.execute(
            """
            SELECT p.profile_json, up.linked_at
            FROM user_profiles up
            JOIN profiles p ON p.id = up.profile_id
            WHERE up.user_sub = ?
            ORDER BY up.linked_at DESC
            """,
            (user_sub,),
        ).fetchall()
    history = []
    for row in rows:
        profile = json.loads(row["profile_json"])
        history.append(
            {
                "profile_id": profile["profile_id"],
                "display_name": profile.get("display_name"),
                "birth_place": profile.get("birth_place"),
                "created_at": profile.get("created_at"),
                "dominant": profile.get("traits", {}).get("dominant_element", "-"),
                "profile": profile,
                "interpretation": latest_interpretation(profile["profile_id"]),
                "linked_at": row["linked_at"],
            }
        )
    return {"history": history}


@app.delete("/api/v1/user/history/{profile_id}")
def delete_user_history(profile_id: str, request: Request) -> dict[str, Any]:
    user = require_google_user(request)
    user_sub = str(user.get("sub") or user.get("email"))
    with db() as conn:
        conn.execute(
            "DELETE FROM user_profiles WHERE user_sub = ? AND profile_id = ?",
            (user_sub, profile_id),
        )
    return {"status": "ok"}


@app.post("/api/v1/birth/analyze")
def analyze_birth(payload: BirthProfileInput) -> dict[str, Any]:
    profile_id = str(uuid.uuid4())
    time_unknown = payload.birth_time is None
    chart = compute_chart(payload)
    traits = build_trait_profile(chart, time_unknown)
    profile = {
        "profile_id": profile_id,
        "display_name": payload.display_name,
        "birth_date": payload.birth_date.isoformat(),
        "birth_time": payload.birth_time,
        "birth_place": payload.birth_place,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "timezone": payload.timezone or "manual-or-utc-pending",
        "time_unknown": time_unknown,
        "chart": chart,
        "traits": traits,
        "needs_validation": time_unknown,
        "validation_questions": validation_questions(payload),
        "roadmap_preview": [],
        "created_at": now_iso(),
    }
    profile["roadmap_preview"] = roadmap_for(profile)
    with db() as conn:
        conn.execute(
            """
            INSERT INTO profiles (
                id, display_name, birth_date, birth_time, birth_place, latitude, longitude,
                timezone, time_unknown, profile_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile_id,
                payload.display_name,
                payload.birth_date.isoformat(),
                payload.birth_time,
                payload.birth_place,
                payload.latitude,
                payload.longitude,
                profile["timezone"],
                int(time_unknown),
                json.dumps(profile),
                profile["created_at"],
            ),
        )
    return profile


@app.post("/api/v1/birth/validate")
def validate_birth(payload: ValidationInput) -> dict[str, Any]:
    profile = load_profile(payload.profile_id)
    score_boost = 0.16 if payload.answers else 0
    base_score = float(profile["traits"]["confidence"]["score"])
    new_score = min(base_score + score_boost, 0.88)
    profile["traits"]["confidence"] = {"score": round(new_score, 2), "label": "high" if new_score >= 0.7 else "medium"}
    profile["validation"] = {"answers": payload.answers, "resolved_at": now_iso()}
    profile["needs_validation"] = False
    save_profile(profile)
    return {
        "profile_id": profile["profile_id"],
        "confidence": profile["traits"]["confidence"],
        "ready_for_interpretation": True,
        "traits": profile["traits"],
    }


@app.get("/api/v1/profiles/{profile_id}")
def get_profile(profile_id: str) -> dict[str, Any]:
    return load_profile(profile_id)


@app.post("/api/v1/public-profiles")
def create_public_profile(payload: PublicProfileInput, request: Request) -> dict[str, Any]:
    profile = load_profile(payload.profile_id)
    username = payload.username.strip().lower()
    email = payload.email.strip().lower()
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise HTTPException(status_code=422, detail="Valid email is required")
    user = read_google_session(request)
    user_sub = str((user or {}).get("sub") or "")

    with db() as conn:
        existing_username = conn.execute(
            "SELECT profile_id FROM public_profiles WHERE username = ?",
            (username,),
        ).fetchone()
        if existing_username and existing_username["profile_id"] != payload.profile_id:
            raise HTTPException(status_code=409, detail="Username already taken")

        existing_profile = conn.execute(
            "SELECT username FROM public_profiles WHERE profile_id = ?",
            (payload.profile_id,),
        ).fetchone()
        if existing_profile and existing_profile["username"] != username:
            username_taken = conn.execute(
                "SELECT 1 FROM public_profiles WHERE username = ?",
                (username,),
            ).fetchone()
            if username_taken:
                raise HTTPException(status_code=409, detail="Username already taken")

        updated_at = now_iso()
        if existing_profile:
            owner_row = conn.execute(
                "SELECT 1 FROM user_profiles WHERE user_sub = ? AND profile_id = ?",
                (user_sub, payload.profile_id),
            ).fetchone()
            if not user_sub or not owner_row:
                raise HTTPException(status_code=403, detail="Login required to update this public profile")
            conn.execute(
                """
                UPDATE public_profiles
                SET username = ?, email = ?, display_name = ?, bio = ?, updated_at = ?
                WHERE profile_id = ?
                """,
                (
                    username,
                    email,
                    payload.display_name or profile.get("display_name"),
                    payload.bio,
                    updated_at,
                    payload.profile_id,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO public_profiles (username, profile_id, email, display_name, bio, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    payload.profile_id,
                    email,
                    payload.display_name or profile.get("display_name"),
                    payload.bio,
                    updated_at,
                    updated_at,
                ),
            )
        row = conn.execute(
            "SELECT * FROM public_profiles WHERE username = ?",
            (username,),
        ).fetchone()
    return {"status": "ok", "public_profile": public_profile_payload(row)}


@app.get("/api/v1/public-profiles")
def list_public_profiles(limit: int = 24) -> dict[str, Any]:
    limit = max(1, min(limit, 50))
    with db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM public_profiles
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return {"profiles": [public_profile_payload(row) for row in rows]}


@app.get("/api/v1/public-profiles/{username}")
def get_public_profile(username: str) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM public_profiles WHERE username = ?",
            (username.strip().lower(),),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Public profile not found")
    return public_profile_payload(row)


@app.get("/api/v1/sky-news")
def sky_news() -> dict[str, Any]:
    posts = sky_news_rows()
    return {"updated_at": now_iso(), "disclaimer": "Editorial astrology for reflection, not deterministic prediction.", "posts": posts}


@app.get("/api/v1/sky-calendar")
def sky_calendar() -> dict[str, Any]:
    return {"updated_at": now_iso(), "events": astrology_calendar_rows()}


@app.post("/api/v1/admin/sky-news")
def admin_save_sky_news(payload: SkyPostInput, request: Request) -> dict[str, Any]:
    require_admin(request)
    post_id = payload.id or str(uuid.uuid4())
    updated_at = now_iso()
    with db() as conn:
        if payload.id:
            conn.execute(
                """
                UPDATE sky_posts
                SET slug = ?, title = ?, tag = ?, summary = ?, body = ?, updated_at = ?
                WHERE id = ?
                """,
                (payload.slug, payload.title, payload.tag, payload.summary, payload.body, updated_at, payload.id),
            )
        else:
            conn.execute(
                """
                INSERT INTO sky_posts (id, slug, title, tag, summary, body, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (post_id, payload.slug, payload.title, payload.tag, payload.summary, payload.body, updated_at, updated_at),
            )
    return {"status": "ok", "post_id": post_id}


@app.post("/api/v1/admin/sky-news/delete")
def admin_delete_sky_news(payload: SkyPostDeleteInput, request: Request) -> dict[str, Any]:
    require_admin(request)
    with db() as conn:
        conn.execute("DELETE FROM sky_posts WHERE id = ?", (payload.id,))
    return {"status": "ok"}


@app.post("/api/v1/admin/sky-calendar")
def admin_save_sky_calendar(payload: AstrologyCalendarInput, request: Request) -> dict[str, Any]:
    require_admin(request)
    event_id = payload.id or str(uuid.uuid4())
    updated_at = now_iso()
    with db() as conn:
        if payload.id:
            conn.execute(
                """
                UPDATE astrology_calendar
                SET event_date = ?, title = ?, tag = ?, summary = ?, updated_at = ?
                WHERE id = ?
                """,
                (payload.event_date.isoformat(), payload.title, payload.tag, payload.summary, updated_at, payload.id),
            )
        else:
            conn.execute(
                """
                INSERT INTO astrology_calendar (id, event_date, title, tag, summary, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, payload.event_date.isoformat(), payload.title, payload.tag, payload.summary, updated_at, updated_at),
            )
    return {"status": "ok", "event_id": event_id}


@app.post("/api/v1/admin/sky-calendar/delete")
def admin_delete_sky_calendar(payload: AstrologyCalendarDeleteInput, request: Request) -> dict[str, Any]:
    require_admin(request)
    with db() as conn:
        conn.execute("DELETE FROM astrology_calendar WHERE id = ?", (payload.id,))
    return {"status": "ok"}


@app.post("/api/v1/interpretation")
async def interpretation(payload: InterpretationInput, request: Request) -> dict[str, Any]:
    profile = load_profile(payload.profile_id)
    enforce_ai_rate_limit(request, profile["profile_id"])
    llm_result = await call_llm(profile, language=payload.language)
    interpretation_id = str(uuid.uuid4())
    with db() as conn:
        conn.execute(
            """
            INSERT INTO interpretations (id, profile_id, provider, model, prompt_hash, request_payload_json, response_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                interpretation_id,
                profile["profile_id"],
                llm_result["provider"],
                llm_result["model"],
                llm_result["prompt_hash"],
                json.dumps(llm_result["request_payload"]),
                json.dumps(llm_result["response"]),
                now_iso(),
            ),
        )
    return {
        "profile_id": profile["profile_id"],
        "interpretation_id": interpretation_id,
        "provider": llm_result["provider"],
        "model": llm_result["model"],
        "interpretation": llm_result["response"],
        "confidence": profile["traits"]["confidence"],
    }


@app.post("/api/v1/interpretation/ask")
async def ask_interpretation_detail(payload: DetailedQuestionInput, request: Request) -> dict[str, Any]:
    profile = load_profile(payload.profile_id)
    enforce_ai_rate_limit(request, profile["profile_id"])
    llm_result = await call_llm(profile, language=payload.language, question=payload.question)
    interpretation_id = str(uuid.uuid4())
    with db() as conn:
        conn.execute(
            """
            INSERT INTO interpretations (id, profile_id, provider, model, prompt_hash, request_payload_json, response_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                interpretation_id,
                profile["profile_id"],
                llm_result["provider"],
                llm_result["model"],
                llm_result["prompt_hash"],
                json.dumps(llm_result["request_payload"]),
                json.dumps(llm_result["response"]),
                now_iso(),
            ),
        )
    return {
        "profile_id": profile["profile_id"],
        "interpretation_id": interpretation_id,
        "provider": llm_result["provider"],
        "model": llm_result["model"],
        "question": payload.question,
        "interpretation": llm_result["response"],
        "confidence": profile["traits"]["confidence"],
    }


@app.post("/api/v1/feedback")
def submit_feedback(payload: FeedbackInput) -> dict[str, Any]:
    feedback_id = str(uuid.uuid4())
    with db() as conn:
        conn.execute(
            """
            INSERT INTO feedback (id, profile_id, interpretation_id, rating, message, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                feedback_id,
                payload.profile_id,
                payload.interpretation_id,
                payload.rating,
                payload.message,
                payload.source,
                now_iso(),
            ),
        )
    return {"status": "ok", "feedback_id": feedback_id}


@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_form() -> str:
    return login_page()


@app.post("/admin/login")
async def admin_login(request: Request):
    body = (await request.body()).decode()
    form = urllib.parse.parse_qs(body)
    username_value = form.get("username", [""])[0]
    password_value = form.get("password", [""])[0]
    if not verify_admin_credentials(username_value, password_value):
        return HTMLResponse(login_page("Username atau password salah."), status_code=401)
    response = RedirectResponse("/admin/dashboard", status_code=303)
    response.set_cookie(
        "hermex_admin",
        admin_session_token(),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 8,
    )
    return response


@app.get("/api/v1/admin/guest-history")
def guest_history(limit: int = 50, _admin: bool = Depends(require_admin)) -> dict[str, Any]:
    limit = min(max(limit, 1), 200)
    with db() as conn:
        rows = conn.execute(
            """
            SELECT
                p.id,
                p.display_name,
                p.birth_date,
                p.birth_time,
                p.birth_place,
                p.latitude,
                p.longitude,
                p.timezone,
                p.profile_json,
                p.created_at,
                i.provider,
                i.model,
                i.prompt_hash,
                i.request_payload_json,
                i.response_json,
                i.created_at AS interpreted_at
            FROM profiles p
            LEFT JOIN interpretations i ON i.id = (
                SELECT id
                FROM interpretations latest
                WHERE latest.profile_id = p.id
                ORDER BY latest.created_at DESC
                LIMIT 1
            )
            ORDER BY p.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    guests = []
    for row in rows:
        profile = json.loads(row["profile_json"])
        guests.append(
            {
                "profile_id": row["id"],
                "display_name": row["display_name"],
                "birth_date": row["birth_date"],
                "birth_time": row["birth_time"],
                "birth_place": row["birth_place"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "timezone": row["timezone"],
                "traits": profile.get("traits"),
                "roadmap_preview": profile.get("roadmap_preview"),
                "created_at": row["created_at"],
                "latest_interpretation": None
                if row["response_json"] is None
                else {
                    "provider": row["provider"],
                    "model": row["model"],
                    "prompt_hash": row["prompt_hash"],
                    "request_payload": json.loads(row["request_payload_json"] or "{}"),
                    "response": json.loads(row["response_json"]),
                    "created_at": row["interpreted_at"],
                },
            }
        )
    return {"guests": guests}


def admin_feedback_history(limit: int = 80) -> list[dict[str, Any]]:
    limit = min(max(limit, 1), 200)
    with db() as conn:
        rows = conn.execute(
            """
            SELECT
                f.id,
                f.profile_id,
                f.interpretation_id,
                f.rating,
                f.message,
                f.source,
                f.created_at,
                p.display_name,
                p.birth_place
            FROM feedback f
            LEFT JOIN profiles p ON p.id = f.profile_id
            ORDER BY f.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/v1/admin/prompt")
async def update_admin_prompt(request: Request, _admin: bool = Depends(require_admin)) -> dict[str, Any]:
    body = await request.json()
    prompt = str(body.get("prompt", "")).strip()
    if len(prompt) < 80:
        raise HTTPException(status_code=400, detail="Prompt is too short")
    set_setting("llm_system_prompt", prompt)
    return {"status": "ok", "prompt": prompt}


@app.post("/api/v1/admin/llm-config")
async def update_admin_llm_config(payload: LLMConfigInput, _admin: bool = Depends(require_admin)) -> dict[str, Any]:
    provider = payload.provider.strip() or "openai_compat"
    if provider not in {"openai_compat", "local_fallback"}:
        raise HTTPException(status_code=400, detail="Unsupported provider")

    set_setting("llm_provider", provider)
    set_setting("llm_base_url", (payload.base_url or "").strip().rstrip("/"))
    if payload.api_key is not None and payload.api_key.strip():
        set_setting("llm_api_key", payload.api_key.strip())
    set_setting("llm_model", (payload.model or "gpt-4o-mini").strip())
    if payload.temperature is not None:
        set_setting("llm_temperature", str(payload.temperature))
    if payload.max_tokens is not None:
        set_setting("llm_max_tokens", str(payload.max_tokens))
    if payload.requests_per_minute is not None:
        set_setting("llm_requests_per_minute", str(payload.requests_per_minute))
    if payload.requests_per_day is not None:
        set_setting("llm_requests_per_day", str(payload.requests_per_day))
    return {"status": "ok", "config": public_llm_config()}


@app.post("/api/v1/admin/llm-models")
async def sync_admin_llm_models(payload: LLMModelSyncInput, _admin: bool = Depends(require_admin)) -> dict[str, Any]:
    config = get_llm_config()
    base_url = (payload.base_url or config["base_url"]).strip().rstrip("/")
    api_key = (payload.api_key or config["api_key"]).strip()
    if not base_url:
        raise HTTPException(status_code=400, detail="Base URL is required")

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail=f"Could not sync models: {exc.__class__.__name__}") from exc

    raw_models = data.get("data", []) if isinstance(data, dict) else data if isinstance(data, list) else []
    model_ids = []
    for item in raw_models:
        model_id = item.get("id") if isinstance(item, dict) else item
        if model_id and str(model_id).strip():
            model_ids.append(str(model_id).strip())
    models = sorted(set(model_ids))
    return {"models": models}


@app.post("/admin/sky-news/save")
async def admin_sky_news_save_form(request: Request) -> RedirectResponse:
    require_admin(request)
    form = await request.form()
    post_id = str(form.get("id") or "").strip()
    updated_at = now_iso()
    raw_slug = str(form.get("slug") or "").strip().lower().replace(" ", "-")
    slug = "".join(char for char in raw_slug if char.isalnum() or char == "-").strip("-")
    values = (
        slug,
        str(form.get("title") or "").strip(),
        str(form.get("tag") or "").strip(),
        str(form.get("summary") or "").strip(),
        str(form.get("body") or "").strip(),
    )
    if not values[0] or not values[1] or not values[3] or not values[4]:
        return RedirectResponse("/admin/dashboard#sky-news", status_code=303)
    with db() as conn:
        if post_id:
            conn.execute(
                """
                UPDATE sky_posts
                SET slug = ?, title = ?, tag = ?, summary = ?, body = ?, updated_at = ?
                WHERE id = ?
                """,
                (*values, updated_at, post_id),
            )
        else:
            conn.execute(
                """
                INSERT INTO sky_posts (id, slug, title, tag, summary, body, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), *values, updated_at, updated_at),
            )
    return RedirectResponse("/admin/dashboard#sky-news", status_code=303)


@app.post("/admin/sky-news/delete")
async def admin_sky_news_delete_form(request: Request) -> RedirectResponse:
    require_admin(request)
    form = await request.form()
    post_id = str(form.get("id") or "").strip()
    if post_id:
        with db() as conn:
            conn.execute("DELETE FROM sky_posts WHERE id = ?", (post_id,))
    return RedirectResponse("/admin/dashboard#sky-news", status_code=303)


@app.post("/admin/sky-calendar/save")
async def admin_sky_calendar_save_form(request: Request) -> RedirectResponse:
    require_admin(request)
    form = await request.form()
    event_id = str(form.get("id") or "").strip()
    updated_at = now_iso()
    values = (
        str(form.get("event_date") or "").strip(),
        str(form.get("title") or "").strip(),
        str(form.get("tag") or "").strip(),
        str(form.get("summary") or "").strip(),
    )
    if not all(values):
        return RedirectResponse("/admin/dashboard#sky-news", status_code=303)
    with db() as conn:
        if event_id:
            conn.execute(
                """
                UPDATE astrology_calendar
                SET event_date = ?, title = ?, tag = ?, summary = ?, updated_at = ?
                WHERE id = ?
                """,
                (*values, updated_at, event_id),
            )
        else:
            conn.execute(
                """
                INSERT INTO astrology_calendar (id, event_date, title, tag, summary, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), *values, updated_at, updated_at),
            )
    return RedirectResponse("/admin/dashboard#sky-news", status_code=303)


@app.post("/admin/sky-calendar/delete")
async def admin_sky_calendar_delete_form(request: Request) -> RedirectResponse:
    require_admin(request)
    form = await request.form()
    event_id = str(form.get("id") or "").strip()
    if event_id:
        with db() as conn:
            conn.execute("DELETE FROM astrology_calendar WHERE id = ?", (event_id,))
    return RedirectResponse("/admin/dashboard#sky-news", status_code=303)


def json_script_payload(value: Any) -> str:
    return (
        json.dumps(value, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("'", "\\u0027")
    )


@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, limit: int = 50) -> str:
    if not is_admin_request(request):
        return login_page()
    data = guest_history(limit=limit, _admin=True)
    current_prompt = get_setting("llm_system_prompt", os.getenv("LLM_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT))
    llm_config = public_llm_config()
    llm_config_json = json_script_payload(llm_config)
    guest_payload_json = json_script_payload(data["guests"])
    provider_options = {
        "openai_compat": "OpenAI-compatible endpoint",
        "local_fallback": "Local fallback only",
    }
    provider_select = "".join(
        f'<option value="{html.escape(value)}" {"selected" if llm_config["provider"] == value else ""}>{html.escape(label)}</option>'
        for value, label in provider_options.items()
    )
    feedback_rows = admin_feedback_history()
    sky_rows = sky_news_rows()
    calendar_rows = astrology_calendar_rows()
    average_rating = round(sum(row["rating"] for row in feedback_rows) / len(feedback_rows), 2) if feedback_rows else 0
    cards = []
    for guest in data["guests"]:
        latest = guest.get("latest_interpretation")
        prompt = json.dumps(latest["request_payload"], indent=2) if latest else "No AI prompt yet."
        response = json.dumps(latest["response"], indent=2) if latest else "No AI response yet."
        cards.append(
            f"""
            <article class="guest-card">
              <div class="guest-head">
                <div>
                  <p class="eyebrow">{html.escape(guest["created_at"])}</p>
                  <h2>{html.escape(guest["display_name"] or "Anonymous guest")}</h2>
                </div>
                <span>{html.escape(guest["birth_place"])}</span>
              </div>
              <dl>
                <div><dt>Birth</dt><dd>{html.escape(guest["birth_date"])} {html.escape(guest["birth_time"] or "")}</dd></div>
                <div><dt>Coordinates</dt><dd>{guest["latitude"]}, {guest["longitude"]}</dd></div>
                <div><dt>Timezone</dt><dd>{html.escape(guest["timezone"] or "-")}</dd></div>
                <div><dt>Dominant</dt><dd>{html.escape((guest.get("traits") or {}).get("dominant_element", "-"))}</dd></div>
              </dl>
              <details>
                <summary>Prompt sent to AI</summary>
                <pre>{html.escape(prompt)}</pre>
              </details>
              <details>
                <summary>Latest AI response</summary>
                <pre>{html.escape(response)}</pre>
              </details>
            </article>
            """
        )
    sky_cards = []
    for post in sky_rows:
        sky_cards.append(
            f"""
            <article class="guest-card">
              <div class="guest-head">
                <div>
                  <time>{html.escape(post.get("updated_at") or "")}</time>
                  <h2>{html.escape(post.get("title") or "")}</h2>
                </div>
                <span class="pill">{html.escape(post.get("tag") or "")}</span>
              </div>
              <form method="post" action="/admin/sky-news/save" class="stack-form">
                <input type="hidden" name="id" value="{html.escape(post.get("id") or "")}" />
                <label>Slug<input name="slug" value="{html.escape(post.get("slug") or "")}" /></label>
                <label>Title<input name="title" value="{html.escape(post.get("title") or "")}" /></label>
                <label>Tag<input name="tag" value="{html.escape(post.get("tag") or "")}" /></label>
                <label>Summary<textarea name="summary">{html.escape(post.get("summary") or "")}</textarea></label>
                <label>Body<textarea name="body">{html.escape(post.get("body") or "")}</textarea></label>
                <button type="submit">Save post</button>
              </form>
              <form method="post" action="/admin/sky-news/delete">
                <input type="hidden" name="id" value="{html.escape(post.get("id") or "")}" />
                <button class="danger" type="submit">Delete post</button>
              </form>
            </article>
            """
        )

    calendar_cards = []
    for event in calendar_rows:
        calendar_cards.append(
            f"""
            <article class="guest-card">
              <div class="guest-head">
                <div>
                  <time>{html.escape(event.get("event_date") or "")}</time>
                  <h2>{html.escape(event.get("title") or "")}</h2>
                </div>
                <span class="pill">{html.escape(event.get("tag") or "")}</span>
              </div>
              <form method="post" action="/admin/sky-calendar/save" class="stack-form">
                <input type="hidden" name="id" value="{html.escape(event.get("id") or "")}" />
                <label>Date<input name="event_date" type="date" value="{html.escape(event.get("event_date") or "")}" /></label>
                <label>Title<input name="title" value="{html.escape(event.get("title") or "")}" /></label>
                <label>Tag<input name="tag" value="{html.escape(event.get("tag") or "")}" /></label>
                <label>Summary<textarea name="summary">{html.escape(event.get("summary") or "")}</textarea></label>
                <button type="submit">Save event</button>
              </form>
              <form method="post" action="/admin/sky-calendar/delete">
                <input type="hidden" name="id" value="{html.escape(event.get("id") or "")}" />
                <button class="danger" type="submit">Delete event</button>
              </form>
            </article>
            """
        )

    feedback_cards = []
    for item in feedback_rows:
        stars = "★" * int(item["rating"]) + "☆" * (5 - int(item["rating"]))
        feedback_cards.append(
            f"""
            <article class="guest-card feedback-card">
              <div class="guest-head">
                <div>
                  <p class="eyebrow">{html.escape(item["created_at"])}</p>
                  <h2>{html.escape(item.get("display_name") or "Anonymous guest")}</h2>
                </div>
                <span>{html.escape(stars)}</span>
              </div>
              <p>{html.escape(item.get("message") or "No written feedback.")}</p>
              <small>{html.escape(item.get("birth_place") or "-")} · {html.escape(item.get("source") or "web")}</small>
            </article>
            """
        )

    return f"""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Hermex Guest Dashboard</title>
        <style>
          body {{
            margin: 0;
            color: #2f2437;
            background: #f8f3e7;
            font-family: Avenir Next, Inter, ui-sans-serif, system-ui, sans-serif;
          }}
          main {{ width: min(1120px, calc(100vw - 32px)); margin: 0 auto; padding: 32px 0; }}
          header {{ display: flex; justify-content: space-between; gap: 16px; align-items: end; margin-bottom: 20px; }}
          h1 {{ margin: 0; font-size: clamp(2rem, 5vw, 4rem); letter-spacing: -.06em; line-height: .9; }}
          .eyebrow {{ margin: 0 0 6px; color: #8e6b45; font-size: .75rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }}
          .guest-card {{ border: 1px solid rgba(47,36,55,.12); border-radius: 24px; background: #fffdf7; padding: 20px; box-shadow: 0 18px 50px rgba(47,36,55,.08); margin-bottom: 16px; }}
          .prompt-editor, .provider-editor {{ border: 1px solid rgba(47,36,55,.12); border-radius: 24px; background: #fffdf7; padding: 20px; box-shadow: 0 18px 50px rgba(47,36,55,.08); margin-bottom: 16px; }}
          textarea {{ width: 100%; min-height: 220px; border: 1px solid rgba(47,36,55,.16); border-radius: 16px; padding: 14px; font: 13px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace; }}
          input, select {{ width: 100%; box-sizing: border-box; border: 1px solid rgba(47,36,55,.16); border-radius: 14px; padding: 12px; background: #fffdf7; color: #2f2437; font: inherit; }}
          label {{ display: grid; gap: 7px; font-weight: 800; }}
          button {{ border: 0; border-radius: 999px; margin-top: 10px; padding: 10px 16px; background: #2f2437; color: #fff8df; font-weight: 800; cursor: pointer; }}
          code {{ border-radius: 6px; background: #f8f3e7; padding: 2px 6px; }}
          #saveStatus, #providerStatus {{ margin-left: 10px; font-weight: 800; color: #5f7f60; }}
          .control-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
          .inline-actions {{ display: flex; gap: 10px; align-items: end; }}
          .inline-actions label {{ flex: 1; }}
          .inline-actions button {{ width: auto; white-space: nowrap; }}
          .hint {{ color: #806d83; font-size: .88rem; }}
          .admin-menu {{ display: flex; gap: 10px; flex-wrap: wrap; margin: 0 0 16px; }}
          .admin-menu button {{ width: auto; margin: 0; background: #fffdf7; color: #2f2437; border: 1px solid rgba(47,36,55,.12); }}
          .admin-menu button.active {{ background: #2f2437; color: #fff8df; }}
          .dashboard-panel {{ display: none; }}
          .dashboard-panel.active {{ display: block; }}
          .overview-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }}
          .stat-card {{ border-radius: 20px; background: #fffdf7; padding: 18px; border: 1px solid rgba(47,36,55,.12); box-shadow: 0 14px 40px rgba(47,36,55,.07); }}
          .stat-card strong {{ display: block; font-size: 2rem; letter-spacing: -.04em; }}
          .admin-toolbar {{ display: flex; gap: 10px; align-items: center; margin-bottom: 14px; }}
          .admin-toolbar input {{ flex: 1; }}
          .admin-toolbar button {{ margin: 0; white-space: nowrap; }}
          .feedback-card p {{ font-size: 1rem; line-height: 1.55; }}
          .stack-form {{ display: grid; gap: 12px; margin-top: 12px; }}
          .stack-form label {{ display: grid; gap: 6px; font-weight: 900; }}
          .stack-form input, .stack-form textarea {{ width: 100%; border: 1px solid rgba(47,36,55,.16); border-radius: 16px; padding: 12px; background: rgba(255,255,255,.62); color: #20385e; font: inherit; box-sizing: border-box; }}
          .stack-form textarea {{ min-height: 92px; resize: vertical; }}
          .danger {{ margin-top: 10px; background: #f09d73; color: #2f2437; }}
          .guest-head {{ display: flex; justify-content: space-between; gap: 14px; align-items: start; }}
          h2 {{ margin: 0; }}
          .guest-head span {{ border-radius: 999px; background: #e6f5ef; padding: 8px 12px; font-weight: 800; }}
          dl {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }}
          dt {{ color: #806d83; font-size: .74rem; font-weight: 800; text-transform: uppercase; }}
          dd {{ margin: 4px 0 0; font-weight: 700; }}
          details {{ margin-top: 10px; border-radius: 16px; background: #f8f3e7; padding: 12px; }}
          summary {{ cursor: pointer; font-weight: 900; }}
          pre {{ white-space: pre-wrap; overflow: auto; font-size: .82rem; line-height: 1.45; }}
          @media (max-width: 760px) {{ header, .guest-head, .inline-actions {{ display: block; }} dl, .control-grid, .overview-grid {{ grid-template-columns: 1fr; }} }}
        </style>
      </head>
      <body>
        <main>
          <header>
            <div>
              <p class="eyebrow">Local backend dashboard</p>
              <h1>Hermex guest history</h1>
            </div>
            <p>{len(data["guests"])} guest records</p>
          </header>
          <nav class="admin-menu" aria-label="Admin menu">
            <button class="active" data-target="overview" type="button">Overview</button>
            <button data-target="provider" type="button">Provider</button>
            <button data-target="prompt" type="button">Setting prompt</button>
            <button data-target="feedback" type="button">Feedback</button>
            <button data-target="sky-news" type="button">Berita Langit</button>
            <button data-target="logs" type="button">Log</button>
          </nav>
          <section class="dashboard-panel active" data-panel="overview">
            <div class="overview-grid">
              <article class="stat-card"><span>Guest records</span><strong>{len(data["guests"])}</strong></article>
              <article class="stat-card"><span>Feedback</span><strong>{len(feedback_rows)}</strong></article>
              <article class="stat-card"><span>Average rating</span><strong>{average_rating}</strong></article>
              <article class="stat-card"><span>AI provider</span><strong>{html.escape(llm_config["provider"])}</strong></article>
              <article class="stat-card"><span>AI / minute</span><strong>{llm_config["requests_per_minute"]}</strong></article>
              <article class="stat-card"><span>AI / day</span><strong>{llm_config["requests_per_day"]}</strong></article>
            </div>
          </section>
          <section class="dashboard-panel" data-panel="prompt">
          <div class="prompt-editor">
            <p class="eyebrow">Hermes AI prompt</p>
            <h2>Editable system prompt</h2>
            <p>Use <code>{{language}}</code> where the active UI language should be inserted.</p>
            <textarea id="prompt">{html.escape(current_prompt)}</textarea>
            <button id="savePrompt">Save prompt</button>
            <span id="saveStatus"></span>
          </div>
          </section>
          <section class="dashboard-panel" data-panel="provider">
          <div class="provider-editor">
            <p class="eyebrow">Hermes AI provider</p>
            <h2>Provider, endpoint, API key, and model</h2>
            <p class="hint">Use an OpenAI-compatible endpoint. API keys are saved only in local SQLite settings and are never printed back here.</p>
            <div class="control-grid">
              <label>Provider
                <select id="provider">{provider_select}</select>
              </label>
              <label>Base URL
                <input id="baseUrl" value="{html.escape(llm_config["base_url"])}" placeholder="https://api.openai.com/v1" />
              </label>
              <label>API key
                <input id="apiKey" type="password" placeholder="{'Saved key active - leave blank to keep it' if llm_config["has_api_key"] else 'Paste API key'}" />
              </label>
              <label>Temperature
                <input id="temperature" type="number" min="0" max="2" step="0.1" value="{llm_config["temperature"]}" />
              </label>
              <label>Max tokens
                <input id="maxTokens" type="number" min="128" max="4000" step="1" value="{llm_config["max_tokens"]}" />
              </label>
              <label>Requests / minute
                <input id="requestsPerMinute" type="number" min="1" max="300" step="1" value="{llm_config["requests_per_minute"]}" />
              </label>
              <label>Requests / day
                <input id="requestsPerDay" type="number" min="1" max="10000" step="1" value="{llm_config["requests_per_day"]}" />
              </label>
            </div>
            <div class="inline-actions">
              <label>Model
                <select id="modelSelect"><option value="{html.escape(llm_config["model"])}">{html.escape(llm_config["model"])}</option></select>
              </label>
              <button id="syncModels" type="button">Sync models</button>
            </div>
            <button id="saveProvider">Save AI provider</button>
            <span id="providerStatus"></span>
          </div>
          </section>
          <section class="dashboard-panel" data-panel="sky-news">
            <article class="guest-card">
              <h2>Add Astrology Calendar event</h2>
              <form method="post" action="/admin/sky-calendar/save" class="stack-form">
                <label>Date<input name="event_date" type="date" /></label>
                <label>Title<input name="title" placeholder="Venus enters Cancer" /></label>
                <label>Tag<input name="tag" placeholder="Transit" /></label>
                <label>Summary<textarea name="summary" placeholder="Dampak reflektif singkat untuk pembaca."></textarea></label>
                <button type="submit">Add calendar event</button>
              </form>
            </article>
            <h2>Astrology Calendar</h2>
            {''.join(calendar_cards) or '<p>No astrology calendar events yet.</p>'}
            <article class="guest-card">
              <h2>Add Berita Langit post</h2>
              <form method="post" action="/admin/sky-news/save" class="stack-form">
                <label>Slug<input name="slug" placeholder="merkurius-dan-komunikasi" /></label>
                <label>Title<input name="title" placeholder="Merkurius dan cuaca komunikasi" /></label>
                <label>Tag<input name="tag" placeholder="Mercury" /></label>
                <label>Summary<textarea name="summary" placeholder="Ringkasan pendek untuk kartu blog."></textarea></label>
                <label>Body<textarea name="body" placeholder="Isi artikel sederhana."></textarea></label>
                <button type="submit">Add post</button>
              </form>
            </article>
            {''.join(sky_cards) or '<p>No sky posts yet.</p>'}
          </section>

          <section class="dashboard-panel" data-panel="feedback">
            {''.join(feedback_cards) or '<p>No feedback yet.</p>'}
          </section>
          <section class="dashboard-panel" data-panel="logs">
            <div class="admin-toolbar">
              <input id="logSearch" placeholder="Search guest, city, provider, model..." />
              <button id="exportGuests" type="button">Export JSON</button>
            </div>
            {''.join(cards) or '<p>No guests yet.</p>'}
          </section>
        </main>
        <script>
          document.querySelectorAll('.admin-menu button').forEach((button) => {{
            button.addEventListener('click', () => {{
              document.querySelectorAll('.admin-menu button').forEach((item) => item.classList.remove('active'));
              document.querySelectorAll('.dashboard-panel').forEach((panel) => panel.classList.remove('active'));
              button.classList.add('active');
              document.querySelector(`[data-panel="${{button.dataset.target}}"]`).classList.add('active');
            }});
          }});

          const initialConfig = {llm_config_json};
          const provider = document.getElementById('provider');
          const baseUrl = document.getElementById('baseUrl');
          const apiKey = document.getElementById('apiKey');
          const modelSelect = document.getElementById('modelSelect');
          const temperature = document.getElementById('temperature');
          const maxTokens = document.getElementById('maxTokens');
          const requestsPerMinute = document.getElementById('requestsPerMinute');
          const requestsPerDay = document.getElementById('requestsPerDay');
          const providerStatus = document.getElementById('providerStatus');
          const guestPayload = {guest_payload_json};

          function setModels(models, selected) {{
            const unique = Array.from(new Set([selected, ...models].filter(Boolean)));
            modelSelect.innerHTML = unique.map((model) => `<option value="${{model}}">${{model}}</option>`).join('');
            modelSelect.value = selected || unique[0] || '';
          }}
          setModels([], initialConfig.model);

          document.getElementById('syncModels').addEventListener('click', async () => {{
            providerStatus.textContent = 'Syncing models...';
            const response = await fetch('/api/v1/admin/llm-models', {{
              method: 'POST',
              headers: {{ 'Content-Type': 'application/json' }},
              body: JSON.stringify({{ base_url: baseUrl.value, api_key: apiKey.value }})
            }});
            if (!response.ok) {{
              providerStatus.textContent = await response.text();
              return;
            }}
            const data = await response.json();
            setModels(data.models || [], modelSelect.value);
            providerStatus.textContent = `Synced ${{(data.models || []).length}} models`;
          }});

          document.getElementById('saveProvider').addEventListener('click', async () => {{
            providerStatus.textContent = 'Saving provider...';
            const response = await fetch('/api/v1/admin/llm-config', {{
              method: 'POST',
              headers: {{ 'Content-Type': 'application/json' }},
              body: JSON.stringify({{
                provider: provider.value,
                base_url: baseUrl.value,
                api_key: apiKey.value,
                model: modelSelect.value,
                temperature: Number(temperature.value),
                max_tokens: Number(maxTokens.value),
                requests_per_minute: Number(requestsPerMinute.value),
                requests_per_day: Number(requestsPerDay.value)
              }})
            }});
            providerStatus.textContent = response.ok ? 'Provider saved' : await response.text();
            if (response.ok) apiKey.value = '';
          }});

          document.getElementById('savePrompt').addEventListener('click', async () => {{
            const prompt = document.getElementById('prompt').value;
            const status = document.getElementById('saveStatus');
            status.textContent = 'Saving...';
            const response = await fetch('/api/v1/admin/prompt', {{
              method: 'POST',
              headers: {{ 'Content-Type': 'application/json' }},
              body: JSON.stringify({{ prompt }})
            }});
            status.textContent = response.ok ? 'Saved' : await response.text();
          }});

          document.getElementById('logSearch')?.addEventListener('input', (event) => {{
            const query = event.target.value.toLowerCase();
            document.querySelectorAll('[data-panel="logs"] .guest-card').forEach((card) => {{
              card.style.display = card.textContent.toLowerCase().includes(query) ? '' : 'none';
            }});
          }});

          document.getElementById('exportGuests')?.addEventListener('click', () => {{
            const blob = new Blob([JSON.stringify(guestPayload, null, 2)], {{ type: 'application/json' }});
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `hermex-guests-${{new Date().toISOString().slice(0, 10)}}.json`;
            link.click();
            URL.revokeObjectURL(url);
          }});
        </script>
      </body>
    </html>
    """


@app.post("/api/v1/quests/start")
def start_quest(payload: QuestStartInput) -> dict[str, Any]:
    load_profile(payload.profile_id)
    quest_id = str(uuid.uuid4())
    quest = {
        "quest_id": quest_id,
        "profile_id": payload.profile_id,
        "quest_slug": payload.quest_slug,
        "status": "started",
        "score": 0,
    }
    with db() as conn:
        conn.execute(
            """
            INSERT INTO user_quests (id, profile_id, quest_slug, status, score, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (quest_id, payload.profile_id, payload.quest_slug, "started", 0, now_iso()),
        )
    return quest


@app.post("/api/v1/quests/complete")
def complete_quest(payload: QuestCompleteInput) -> dict[str, Any]:
    score = min(100, max(10, len(json.dumps(payload.result_payload)) // 3))
    with db() as conn:
        row = conn.execute("SELECT profile_id, quest_slug FROM user_quests WHERE id = ?", (payload.quest_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Quest not found")
        conn.execute(
            """
            UPDATE user_quests
            SET status = ?, score = ?, result_json = ?, completed_at = ?
            WHERE id = ?
            """,
            ("completed", score, json.dumps(payload.result_payload), now_iso(), payload.quest_id),
        )
    return {
        "quest_id": payload.quest_id,
        "status": "completed",
        "reward": {"score": score, "badge": "first-reflection"},
        "next_suggestion": "Start the 30-day roadmap experiment.",
    }


@app.get("/api/v1/roadmap/{profile_id}")
def roadmap(profile_id: str) -> dict[str, Any]:
    profile = load_profile(profile_id)
    return {"profile_id": profile_id, "roadmap": profile["roadmap_preview"], "progress_percentage": 0}
