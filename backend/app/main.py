from __future__ import annotations

import hashlib
import hmac
import html
import json
import os
import re
import secrets
import sqlite3
import urllib.parse
import uuid
from collections import OrderedDict
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field, field_validator

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
RATE_LIMIT_BUCKETS: OrderedDict[str, list[datetime]] = OrderedDict()
RATE_LIMIT_BUCKET_LIMIT = 10_000
RATE_LIMIT_LOCK = Lock()
ADMIN_COOKIE_NAME = "hermex_admin"
GOOGLE_COOKIE_NAME = "hermex_google"
OAUTH_STATE_COOKIE_NAME = "hermex_oauth_state"
DEFAULT_ADMIN_PASSWORD = "hermes-admin"
DEFAULT_ADMIN_SESSION_SECRET = "hermex-local-admin-session"
DEFAULT_GOOGLE_SESSION_SECRET = "hermex-local-google-session"
UNSAFE_SECRET_VALUES = {
    "",
    DEFAULT_ADMIN_SESSION_SECRET,
    DEFAULT_GOOGLE_SESSION_SECRET,
    "change_this_admin_session_secret",
    "change_this_google_session_secret",
}
UNSAFE_ADMIN_PASSWORD_VALUES = {
    "",
    DEFAULT_ADMIN_PASSWORD,
    "change_this_password",
    "change_this_admin_password",
}
UNSAFE_ADMIN_USERNAME_VALUES = {"", "admin", "change_this_admin_username"}

DEFAULT_SYSTEM_PROMPT = """
Anda adalah Hermes, analis kepribadian dan mentor reflektif.
Gunakan data kelahiran, pola internal yang dihitung sistem, dan jawaban pengguna
sebagai bahan refleksi. Data internal tidak perlu disebutkan kepada pengguna.
Gunakan bahasa: {language}.

Aturan:
- Jangan gunakan istilah astrologi, zodiak, planet, rumah, aspek, atau natal chart.
- Jangan menyatakan hasil sebagai diagnosis atau kepastian mutlak.
- Hubungkan interpretasi dengan pola internal dan jawaban yang tersedia.
- Jangan mengarang data yang tidak ada di payload.
- Return JSON valid saja dengan field:
  preview_summary, highlights, identity_keywords, username_suggestions, full_analysis, confidence, caveat.
- Urutkan field persis seperti daftar di atas dan jangan bungkus JSON dengan markdown.
- highlights harus tepat 3 string singkat.
- identity_keywords harus tepat 3 object {"word": "satu kata", "icon": "satu emoji"}.
- username_suggestions harus tepat 3 username lowercase yang boleh diedit pengguna.
- full_analysis harus object dengan field: core_identity, emotional_needs,
  social_approach, thinking_and_communication, relationships_and_values,
  drive_and_boundaries, inner_tensions, dominant_patterns, growth_focus.
- Setiap field full_analysis harus berupa paragraf Bahasa Indonesia minimal 50 kata.
- Buat hangat, spesifik, praktis, dan mudah dipindai.
- preview_summary harus 3-5 kalimat dengan panjang sekitar 80-140 kata.
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

    @field_validator("birth_time")
    @classmethod
    def validate_birth_time(cls, value: str | None) -> str | None:
        if value is None:
            return None
        hour, minute = map(int, value.split(":"))
        if hour > 23 or minute > 59:
            raise ValueError("birth_time must use a valid 24-hour HH:MM value")
        return value


class ValidationInput(BaseModel):
    profile_id: str
    claim_token: str = Field(min_length=16, max_length=160)
    answers: dict[str, Any] = Field(default_factory=dict)


class QuestionnaireQuestionInput(BaseModel):
    profile_id: str = Field(max_length=80)
    claim_token: str = Field(min_length=16, max_length=160)
    index: int = Field(ge=0, le=49)


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
    max_tokens: int | None = Field(default=None, ge=128, le=8000)
    requests_per_minute: int | None = Field(default=None, ge=1, le=300)
    requests_per_day: int | None = Field(default=None, ge=1, le=10000)


class LLMModelSyncInput(BaseModel):
    base_url: str | None = Field(default=None, max_length=300)
    api_key: str | None = Field(default=None, max_length=500)


class EntitlementInput(BaseModel):
    subject_type: str = Field(default="user_sub", pattern="^(user_sub|email)$")
    subject_id: str = Field(min_length=3, max_length=180)
    plan: str = Field(default="supporter", max_length=40)
    status: str = Field(default="active", pattern="^(active|trialing|past_due|canceled|expired)$")
    requests_per_minute: int | None = Field(default=None, ge=1, le=300)
    requests_per_day: int | None = Field(default=None, ge=1, le=10000)
    max_tokens: int | None = Field(default=None, ge=128, le=8000)
    source: str = Field(default="manual", max_length=80)
    external_id: str | None = Field(default=None, max_length=180)
    current_period_end: str | None = Field(default=None, max_length=80)


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
    claim_token: str | None = Field(default=None, min_length=16, max_length=160)
    display_name: str | None = Field(default=None, max_length=80)
    bio: str | None = Field(default=None, max_length=240)


class OwnerProfileSettingsInput(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-z0-9_]+$")
    is_public: bool = True


class ProfileClaimInput(BaseModel):
    profile_id: str = Field(max_length=80)
    claim_token: str = Field(min_length=16, max_length=160)


class UserHistorySyncInput(BaseModel):
    profile_ids: list[str] = Field(default_factory=list, max_length=50)
    profile_claims: list[ProfileClaimInput] = Field(default_factory=list, max_length=50)


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
                avatar_url TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        public_profile_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(public_profiles)").fetchall()
        }
        if "avatar_url" not in public_profile_columns:
            conn.execute("ALTER TABLE public_profiles ADD COLUMN avatar_url TEXT")
        if "is_public" not in public_profile_columns:
            conn.execute("ALTER TABLE public_profiles ADD COLUMN is_public INTEGER NOT NULL DEFAULT 1")
        feedback_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(feedback)").fetchall()
        }
        if "user_sub" not in feedback_columns:
            conn.execute("ALTER TABLE feedback ADD COLUMN user_sub TEXT")
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
            CREATE TABLE IF NOT EXISTS entitlements (
                subject_type TEXT NOT NULL,
                subject_id TEXT NOT NULL,
                plan TEXT NOT NULL,
                status TEXT NOT NULL,
                limits_json TEXT NOT NULL DEFAULT '{}',
                source TEXT NOT NULL,
                external_id TEXT,
                current_period_end TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (subject_type, subject_id)
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
        retired_slugs = (
            "setahun-di-langit-agustus-2025-juli-2026",
            "desember-2025-batas-bukti-review",
            "bulan-sebagai-ritme-harian",
            "merkurius-dan-cuaca-komunikasi",
            "saturnus-dan-struktur-sosial",
        )
        conn.executemany("DELETE FROM sky_posts WHERE slug = ?", ((slug,) for slug in retired_slugs))
        for post in default_sky_posts():
            existing_post = conn.execute("SELECT summary, body FROM sky_posts WHERE slug = ?", (post["slug"],)).fetchone()
            if not existing_post:
                seed_time = now_iso()
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
    password = os.getenv("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
    session_secret = os.getenv("ADMIN_SESSION_SECRET", DEFAULT_ADMIN_SESSION_SECRET)
    unsafe_password = password in UNSAFE_ADMIN_PASSWORD_VALUES or password.lower().startswith("change_this")
    unsafe_secret = session_secret in UNSAFE_SECRET_VALUES or session_secret.lower().startswith("change_this")
    if not is_local_public_app_url() and (unsafe_password or unsafe_secret):
        return False
    valid_user = secrets.compare_digest(username_value, username)
    valid_password = secrets.compare_digest(password_value, password)
    return valid_user and valid_password


def validate_hosted_admin_configuration() -> None:
    if is_local_public_app_url():
        return
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
    secret = os.getenv("ADMIN_SESSION_SECRET", DEFAULT_ADMIN_SESSION_SECRET)
    unsafe_username = username in UNSAFE_ADMIN_USERNAME_VALUES or username.lower().startswith("change_this")
    unsafe_password = password in UNSAFE_ADMIN_PASSWORD_VALUES or password.lower().startswith("change_this")
    unsafe_secret = secret in UNSAFE_SECRET_VALUES or secret.lower().startswith("change_this")
    if unsafe_username or unsafe_password or unsafe_secret:
        raise RuntimeError("Hosted admin requires unique ADMIN_USERNAME, ADMIN_PASSWORD, and ADMIN_SESSION_SECRET values")


def admin_session_secret() -> str:
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
    secret = os.getenv("ADMIN_SESSION_SECRET", DEFAULT_ADMIN_SESSION_SECRET)
    return f"{username}:{password}:{secret}"


def public_app_url() -> str:
    return os.getenv("PUBLIC_APP_URL", "http://127.0.0.1:5666").strip().rstrip("/")


def is_local_hostname(hostname: str | None) -> bool:
    return (hostname or "").strip("[]").lower() in {"127.0.0.1", "localhost", "::1"}


def is_local_public_app_url() -> bool:
    parsed = urllib.parse.urlparse(public_app_url())
    return parsed.scheme == "http" and is_local_hostname(parsed.hostname)


def request_hostname(request: Request) -> str | None:
    host = request.headers.get("host") or request.url.hostname or ""
    if os.getenv("TRUST_PROXY_HEADERS", "").lower() in {"1", "true", "yes", "on"}:
        host = request.headers.get("x-forwarded-host") or host
    return host.split(",", 1)[0].split(":", 1)[0].strip() or None


def request_scheme(request: Request) -> str:
    scheme = request.url.scheme
    if os.getenv("TRUST_PROXY_HEADERS", "").lower() in {"1", "true", "yes", "on"}:
        scheme = request.headers.get("x-forwarded-proto", scheme).split(",", 1)[0].strip().lower()
    return scheme


def is_local_request(request: Request) -> bool:
    return request_scheme(request) == "http" and is_local_hostname(request_hostname(request))


def hosted_context(request: Request | None = None) -> bool:
    if request is not None:
        return not is_local_request(request)
    return not is_local_public_app_url()


def secure_cookie(request: Request | None = None) -> bool:
    if request is not None:
        scheme = request_scheme(request)
        if scheme == "https":
            return True
        if is_local_request(request):
            return False
    return public_app_url().startswith("https://")


def session_max_age(env_key: str, default_seconds: int) -> int:
    try:
        return max(60, int(os.getenv(env_key, str(default_seconds))))
    except ValueError:
        return default_seconds


def signed_session_token(payload: dict[str, Any], secret: str) -> str:
    body = json.dumps(payload, separators=(",", ":"))
    signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def verify_signed_session_token(token: str | None, secret: str, max_age: int) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None
    body, signature = token.rsplit(".", 1)
    expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    if not secrets.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    try:
        issued_at = int(payload.get("iat", 0))
    except (TypeError, ValueError):
        return None
    now = int(datetime.now(timezone.utc).timestamp())
    if issued_at <= 0 or issued_at > now + 60 or now - issued_at > max_age:
        return None
    return payload


def admin_session_token() -> str:
    return signed_session_token(
        {"role": "admin", "iat": int(datetime.now(timezone.utc).timestamp())},
        admin_session_secret(),
    )


def google_session_secret(request: Request | None = None, raise_on_invalid: bool = False) -> str:
    explicit_secret = os.getenv("GOOGLE_SESSION_SECRET", "").strip()
    fallback_secret = os.getenv("ADMIN_SESSION_SECRET", DEFAULT_GOOGLE_SESSION_SECRET).strip()
    secret = explicit_secret or fallback_secret
    unsafe_secret = not explicit_secret or secret in UNSAFE_SECRET_VALUES or secret.lower().startswith("change_this")
    if hosted_context(request) and unsafe_secret:
        if raise_on_invalid:
            raise HTTPException(
                status_code=503,
                detail="GOOGLE_SESSION_SECRET must be configured with a non-default value for hosted deployments",
            )
        return ""
    return secret


def google_oauth_config(request: Request | None = None) -> dict[str, str]:
    return {
        "client_id": os.getenv("GOOGLE_CLIENT_ID", "").strip(),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", "").strip(),
        "redirect_uri": os.getenv(
            "GOOGLE_REDIRECT_URI",
            "http://127.0.0.1:5666/api/v1/auth/google/callback",
        ).strip(),
        "session_secret": google_session_secret(request),
    }


def google_session_token(user: dict[str, Any], request: Request | None = None) -> str:
    return signed_session_token(
        {
            "sub": user.get("sub"),
            "email": user.get("email"),
            "name": user.get("name"),
            "picture": user.get("picture"),
            "iat": int(datetime.now(timezone.utc).timestamp()),
        },
        google_session_secret(request, raise_on_invalid=True),
    )


def read_google_session(request: Request) -> dict[str, Any] | None:
    secret = google_session_secret(request)
    if not secret:
        return None
    return verify_signed_session_token(
        request.cookies.get(GOOGLE_COOKIE_NAME),
        secret,
        session_max_age("GOOGLE_SESSION_MAX_AGE_SECONDS", 60 * 60 * 24 * 30),
    )


def require_google_user(request: Request) -> dict[str, Any]:
    user = read_google_session(request)
    if not user or not (user.get("sub") or user.get("email")):
        raise HTTPException(status_code=401, detail="Google login required")
    return user


def viewer_owns_profile(profile_id: str, request: Request) -> bool:
    user = read_google_session(request)
    user_sub = str((user or {}).get("sub") or (user or {}).get("email") or "")
    if not user_sub:
        return False
    with db() as conn:
        return bool(
            conn.execute(
                "SELECT 1 FROM user_profiles WHERE user_sub = ? AND profile_id = ?",
                (user_sub, profile_id),
            ).fetchone()
        )


def require_linked_profile_owner(profile_id: str, request: Request) -> dict[str, Any]:
    user = require_google_user(request)
    if not viewer_owns_profile(profile_id, request):
        raise HTTPException(status_code=403, detail="This profile is not linked to the signed-in account")
    return user


def require_profile_owner(profile_id: str, request: Request) -> dict[str, Any] | None:
    if os.getenv("SELF_HOSTED_FULL_ACCESS", "").lower() in {"1", "true", "yes", "on"}:
        return read_google_session(request)
    return require_linked_profile_owner(profile_id, request)


def is_admin_request(request: Request) -> bool:
    session = verify_signed_session_token(
        request.cookies.get(ADMIN_COOKIE_NAME),
        admin_session_secret(),
        session_max_age("ADMIN_SESSION_MAX_AGE_SECONDS", 60 * 60 * 8),
    )
    if session and session.get("role") == "admin":
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
    <html lang="id">
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
          <p>Masuk buat cek aktivitas dan atur Hermex.</p>
          {f'<p class="error">{html.escape(error)}</p>' if error else ''}
          <label>Username<input name="username" autocomplete="username" /></label>
          <label>Password<input name="password" type="password" autocomplete="current-password" /></label>
          <button type="submit">Masuk</button>
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
        "max_tokens": setting_int("llm_max_tokens", "LLM_MAX_TOKENS", "8000"),
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


def masked_secret_label(value: str) -> str:
    """Return a display-only hint without exposing the stored secret."""
    secret = value.strip()
    if not secret:
        return "Belum disetel"
    if len(secret) <= 6:
        return f"{secret[:1]}{'•' * 6}{secret[-1:]}"
    return f"{secret[:3]}{'•' * 8}{secret[-3:]}"


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def normalize_limit_value(value: Any, minimum: int, maximum: int, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return min(maximum, max(minimum, parsed))


def plan_default_limits(plan: str) -> dict[str, int]:
    config = get_llm_config()
    base_limits = {
        "requests_per_minute": normalize_limit_value(config["requests_per_minute"], 1, 300, 6),
        "requests_per_day": normalize_limit_value(config["requests_per_day"], 1, 10000, 40),
        "max_tokens": normalize_limit_value(config["max_tokens"], 128, 8000, 8000),
    }
    normalized_plan = plan.lower().strip()
    if normalized_plan in {"supporter", "paid", "pro", "plus"}:
        return {
            "requests_per_minute": env_int("SUPPORTER_REQUESTS_PER_MINUTE", 60),
            "requests_per_day": env_int("SUPPORTER_REQUESTS_PER_DAY", 1000),
            "max_tokens": env_int("SUPPORTER_MAX_TOKENS", 8000),
        }
    if normalized_plan == "self_hosted":
        return {
            "requests_per_minute": env_int("SELF_HOSTED_REQUESTS_PER_MINUTE", 300),
            "requests_per_day": env_int("SELF_HOSTED_REQUESTS_PER_DAY", 10000),
            "max_tokens": env_int("SELF_HOSTED_MAX_TOKENS", 8000),
        }
    return base_limits


def merge_entitlement_limits(plan: str, limits_json: str | None = None) -> dict[str, int]:
    limits = plan_default_limits(plan)
    try:
        custom_limits = json.loads(limits_json or "{}")
    except json.JSONDecodeError:
        custom_limits = {}
    for key, minimum, maximum in (
        ("requests_per_minute", 1, 300),
        ("requests_per_day", 1, 10000),
        ("max_tokens", 128, 8000),
    ):
        if key in custom_limits:
            limits[key] = normalize_limit_value(custom_limits[key], minimum, maximum, limits[key])
        else:
            limits[key] = normalize_limit_value(limits[key], minimum, maximum, limits[key])
    return limits


def parse_period_end(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc) - timedelta(seconds=1)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def entitlement_row_is_active(row: sqlite3.Row | dict[str, Any] | None) -> bool:
    if not row:
        return False
    if row["status"] not in {"active", "trialing"}:
        return False
    period_end = parse_period_end(row["current_period_end"])
    return period_end is None or period_end > datetime.now(timezone.utc)


def entitlement_payload(
    plan: str,
    status: str,
    limits: dict[str, int],
    subject_key: str,
    authenticated: bool,
    source: str = "default",
    current_period_end: str | None = None,
) -> dict[str, Any]:
    return {
        "plan": plan,
        "status": status,
        "limits": limits,
        "subject_key": subject_key,
        "authenticated": authenticated,
        "source": source,
        "current_period_end": current_period_end,
    }


def public_entitlement_payload(entitlement: dict[str, Any]) -> dict[str, Any]:
    return {
        "plan": entitlement["plan"],
        "status": entitlement["status"],
        "limits": entitlement["limits"],
        "authenticated": entitlement["authenticated"],
        "source": entitlement["source"],
        "current_period_end": entitlement.get("current_period_end"),
    }


def current_entitlement(request: Request) -> dict[str, Any]:
    user = read_google_session(request)
    authenticated = bool(user)
    subject_key = f"client:{rate_limit_client_key(request)}"
    if user and user.get("sub"):
        subject_key = f"user_sub:{user['sub']}"
    elif user and user.get("email"):
        subject_key = f"email:{user['email']}"

    if os.getenv("SELF_HOSTED_FULL_ACCESS", "").lower() in {"1", "true", "yes", "on"}:
        return entitlement_payload(
            "self_hosted",
            "active",
            merge_entitlement_limits("self_hosted"),
            subject_key,
            authenticated,
            "self_hosted",
        )

    lookup_keys: list[tuple[str, str]] = []
    if user and user.get("sub"):
        lookup_keys.append(("user_sub", str(user["sub"])))
    if user and user.get("email"):
        lookup_keys.append(("email", str(user["email"]).lower()))

    with db() as conn:
        for subject_type, subject_id in lookup_keys:
            row = conn.execute(
                """
                SELECT * FROM entitlements
                WHERE subject_type = ? AND subject_id = ?
                """,
                (subject_type, subject_id),
            ).fetchone()
            if entitlement_row_is_active(row):
                return entitlement_payload(
                    row["plan"],
                    row["status"],
                    merge_entitlement_limits(row["plan"], row["limits_json"]),
                    f"{subject_type}:{subject_id}",
                    authenticated,
                    row["source"],
                    row["current_period_end"],
                )

    plan = "free" if authenticated else "guest"
    return entitlement_payload(plan, "active", merge_entitlement_limits(plan), subject_key, authenticated)


def save_entitlement(payload: EntitlementInput) -> dict[str, Any]:
    now = now_iso()
    subject_id = payload.subject_id.lower() if payload.subject_type == "email" else payload.subject_id
    custom_limits = {
        key: value
        for key, value in {
            "requests_per_minute": payload.requests_per_minute,
            "requests_per_day": payload.requests_per_day,
            "max_tokens": payload.max_tokens,
        }.items()
        if value is not None
    }
    limits_json = json.dumps(custom_limits, separators=(",", ":"))
    with db() as conn:
        conn.execute(
            """
            INSERT INTO entitlements (
                subject_type, subject_id, plan, status, limits_json, source,
                external_id, current_period_end, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(subject_type, subject_id) DO UPDATE SET
                plan = excluded.plan,
                status = excluded.status,
                limits_json = excluded.limits_json,
                source = excluded.source,
                external_id = excluded.external_id,
                current_period_end = excluded.current_period_end,
                updated_at = excluded.updated_at
            """,
            (
                payload.subject_type,
                subject_id,
                payload.plan.strip().lower() or "supporter",
                payload.status,
                limits_json,
                payload.source,
                payload.external_id,
                payload.current_period_end,
                now,
                now,
            ),
        )
    return {
        "subject_type": payload.subject_type,
        "subject_id": subject_id,
        "plan": payload.plan.strip().lower() or "supporter",
        "status": payload.status,
        "limits": merge_entitlement_limits(payload.plan, limits_json),
        "source": payload.source,
        "current_period_end": payload.current_period_end,
    }


def require_entitlement_secret(request: Request) -> bool:
    secret = os.getenv("ENTITLEMENT_WEBHOOK_SECRET", "").strip()
    if not secret:
        raise HTTPException(status_code=404, detail="Internal entitlement endpoint is disabled")
    provided = request.headers.get("x-hermex-entitlement-secret", "")
    if not secrets.compare_digest(provided, secret):
        raise HTTPException(status_code=401, detail="Invalid entitlement secret")
    return True


def rate_limit_client_key(request: Request) -> str:
    client_host = request.client.host if request.client else "unknown"
    if os.getenv("TRUST_PROXY_HEADERS", "").lower() in {"1", "true", "yes", "on"}:
        forwarded_for = request.headers.get("x-forwarded-for", "")
        trusted_host = forwarded_for.split(",", 1)[0].strip() if forwarded_for else ""
        if trusted_host:
            client_host = trusted_host
    user_agent = request.headers.get("user-agent", "unknown")[:120]
    return hashlib.sha256(f"{client_host}:{user_agent}".encode()).hexdigest()[:24]


def _cleanup_rate_limit_bucket(events: list[datetime], now: datetime) -> list[datetime]:
    cutoff = now - timedelta(days=1)
    return [event_time for event_time in events if event_time > cutoff]


def _rate_limit_bucket(key: str, now: datetime) -> list[datetime]:
    if len(RATE_LIMIT_BUCKETS) >= RATE_LIMIT_BUCKET_LIMIT and key not in RATE_LIMIT_BUCKETS:
        RATE_LIMIT_BUCKETS.popitem(last=False)
    events = _cleanup_rate_limit_bucket(RATE_LIMIT_BUCKETS.get(key, []), now)
    RATE_LIMIT_BUCKETS[key] = events
    RATE_LIMIT_BUCKETS.move_to_end(key)
    return events


def enforce_ai_rate_limit(request: Request, profile_id: str | None = None) -> dict[str, Any]:
    entitlement = current_entitlement(request)
    request.state.hermex_entitlement = entitlement
    minute_limit = max(1, int(entitlement["limits"]["requests_per_minute"]))
    day_limit = max(1, int(entitlement["limits"]["requests_per_day"]))
    now = datetime.now(timezone.utc)
    key = f"ai:{entitlement['subject_key']}"
    with RATE_LIMIT_LOCK:
        events = _rate_limit_bucket(key, now)
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
    return entitlement


def enforce_public_write_rate_limit(
    request: Request,
    action: str,
    minute_limit: int | None = None,
    day_limit: int | None = None,
) -> None:
    minute_limit = minute_limit or env_int("PUBLIC_WRITE_REQUESTS_PER_MINUTE", 20)
    day_limit = day_limit or env_int("PUBLIC_WRITE_REQUESTS_PER_DAY", 200)
    now = datetime.now(timezone.utc)
    key = f"write:{action}:{rate_limit_client_key(request)}"
    with RATE_LIMIT_LOCK:
        events = _rate_limit_bucket(key, now)
        minute_events = [event_time for event_time in events if now - event_time < timedelta(minutes=1)]
        if len(minute_events) >= minute_limit:
            raise HTTPException(
                status_code=429,
                detail=f"Write request limit reached: max {minute_limit} request(s) per minute.",
            )
        if len(events) >= day_limit:
            raise HTTPException(
                status_code=429,
                detail=f"Write request limit reached: max {day_limit} request(s) per day.",
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
    hh, mm = (payload.birth_time or "00:00").split(":")
    local_hour = int(hh) + int(mm) / 60
    try:
        tzinfo = ZoneInfo(payload.timezone or "UTC")
    except ZoneInfoNotFoundError:
        tzinfo = timezone.utc
    local_dt = datetime.combine(payload.birth_date, time(int(hh), int(mm)), tzinfo=tzinfo)
    utc_dt = local_dt.astimezone(timezone.utc)
    utc_hour = utc_dt.hour + utc_dt.minute / 60 + utc_dt.second / 3600
    return utc_dt.date(), utc_hour, local_hour


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

    ascendant = round((float(planets.get("sun", {}).get("longitude", 0)) + local_hour * 15) % 360, 3)
    house_system = "equal_house_estimate"
    house_cusps = None
    midheaven = None
    if swe and payload.latitude is not None and payload.longitude is not None:
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
            "precision": "reduced_assumed_midnight" if payload.birth_time is None else "time_based_estimate",
        },
        "aspects": build_aspects(planets),
        "location": {
            "birth_place": payload.birth_place,
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "timezone": payload.timezone,
            "effective_birth_time": payload.birth_time or "00:00",
            "birth_time_assumed": payload.birth_time is None,
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


SIGN_RULERS = {
    "Aries": "mars",
    "Taurus": "venus",
    "Gemini": "mercury",
    "Cancer": "moon",
    "Leo": "sun",
    "Virgo": "mercury",
    "Libra": "venus",
    "Scorpio": "mars",
    "Sagittarius": "jupiter",
    "Capricorn": "saturn",
    "Aquarius": "saturn",
    "Pisces": "jupiter",
    }


def circular_distance(left: float, right: float) -> float:
    distance = abs(left - right) % 360
    return min(distance, 360 - distance)


def aspects_to_point(planets: dict[str, dict[str, Any]], point: float | None) -> list[dict[str, Any]]:
    if point is None:
        return []
    major = {"conjunction": 0, "sextile": 60, "square": 90, "trine": 120, "opposition": 180}
    matches = []
    for name, planet in planets.items():
        distance = circular_distance(float(planet["longitude"]), point)
        for aspect_name, angle in major.items():
            orb = abs(distance - angle)
            if orb <= 6:
                matches.append({"planet": name, "type": aspect_name, "orb": round(orb, 2)})
                break
    return sorted(matches, key=lambda item: item["orb"])


def derive_personality_signals(chart: dict[str, Any]) -> dict[str, Any]:
    planets = chart["planets"]
    houses = chart["houses"]
    planet_houses = houses.get("planet_houses") or {}
    ascendant = houses.get("ascendant")
    ascendant_sign = (houses.get("ascendant_zodiac") or {}).get("zodiac_sign")
    ruler_name = SIGN_RULERS.get(ascendant_sign or "", "sun")

    angles = {
        "ascendant": ascendant,
        "descendant": None if ascendant is None else (ascendant + 180) % 360,
        "midheaven": houses.get("midheaven"),
        "imum_coeli": None if houses.get("midheaven") is None else (houses["midheaven"] + 180) % 360,
    }
    angular_planets = []
    for name, planet in planets.items():
        nearest = min(
            (
                (angle_name, circular_distance(float(planet["longitude"]), float(angle)))
                for angle_name, angle in angles.items()
                if angle is not None
            ),
            key=lambda item: item[1],
            default=None,
        )
        if nearest and nearest[1] <= 8:
            angular_planets.append({"planet": name, "angle": nearest[0], "orb": round(nearest[1], 2)})

    house_counts: dict[str, int] = {}
    for house in planet_houses.values():
        if house is not None:
            house_counts[str(house)] = house_counts.get(str(house), 0) + 1
    dominant_houses = sorted(house_counts.items(), key=lambda item: (-item[1], int(item[0])))[:3]

    element_counts = {element: 0 for element in ("fire", "earth", "air", "water")}
    modality_counts = {modality: 0 for modality in ("cardinal", "fixed", "mutable")}
    for planet in planets.values():
        element_counts[planet["element"]] += 1
        modality_counts[planet["modality"]] += 1

    planet_scores = {name: 0 for name in planets}
    for aspect in chart.get("aspects") or []:
        planet_scores[aspect["left"]] += 1
        planet_scores[aspect["right"]] += 1
    for item in angular_planets:
        planet_scores[item["planet"]] += 2
    dominant_planet = max(planet_scores, key=planet_scores.get) if planet_scores else None

    return {
        "sun": {"position": planets.get("sun"), "house": planet_houses.get("sun")},
        "moon": {"position": planets.get("moon"), "house": planet_houses.get("moon")},
        "ascendant": {
            "position": houses.get("ascendant_zodiac"),
            "aspects": aspects_to_point(planets, ascendant),
        },
        "chart_ruler": {
            "planet": ruler_name,
            "position": planets.get(ruler_name),
            "house": planet_houses.get(ruler_name),
            "aspects": [
                aspect
                for aspect in chart.get("aspects") or []
                if ruler_name in {aspect["left"], aspect["right"]}
            ],
        },
        "mercury": {"position": planets.get("mercury"), "house": planet_houses.get("mercury")},
        "venus": {"position": planets.get("venus"), "house": planet_houses.get("venus")},
        "mars": {"position": planets.get("mars"), "house": planet_houses.get("mars")},
        "major_aspects": chart.get("aspects") or [],
        "angular_and_dominant_houses": {
            "angular_planets": angular_planets,
            "dominant_houses": [{"house": int(house), "count": count} for house, count in dominant_houses],
        },
        "overall_pattern": {
            "elements": element_counts,
            "modalities": modality_counts,
            "dominant_element": max(element_counts, key=element_counts.get),
            "dominant_modality": max(modality_counts, key=modality_counts.get),
            "dominant_planet": dominant_planet,
        },
    }


QUESTIONNAIRE_COUNT = 10
QUESTIONNAIRE_WORD_MIN = 8
QUESTIONNAIRE_WORD_MAX = 20


def build_questionnaire(signals: dict[str, Any]) -> dict[str, Any]:
    overall = signals["overall_pattern"]
    element = overall["dominant_element"]
    modality = overall["dominant_modality"]
    has_tension = any(
        item.get("type") in {"square", "opposition"}
        for item in signals.get("major_aspects") or []
    )
    element_focus = {
        "fire": "berani mencoba pengalaman baru",
        "earth": "membuat rencana jadi sesuatu yang bisa dijalankan",
        "air": "bertukar pikiran dan melihat sudut pandang baru",
        "water": "memahami perasaan dan suasana yang tak terucap",
    }
    modality_focus = {
        "cardinal": "memulai dulu saat arahnya belum jelas",
        "fixed": "bertahan sampai urusannya benar-benar selesai",
        "mutable": "mengubah cara saat keadaan berubah",
    }
    house_focus = {
        1: "membawa diri dan memulai sesuatu",
        2: "rasa aman, nilai diri, dan uang",
        3: "belajar, berbicara, dan lingkungan dekat",
        4: "keluarga dan ruang pribadi",
        5: "kreativitas dan cara mengekspresikan diri",
        6: "rutinitas, pekerjaan, dan merawat diri",
        7: "hubungan dekat dan kerja sama",
        8: "kepercayaan dan perubahan besar",
        9: "keyakinan dan pencarian makna",
        10: "tanggung jawab dan pencapaian",
        11: "pertemanan dan tujuan bersama",
        12: "merenung, pulih, dan menyendiri",
    }

    def position_element(key: str) -> str:
        position = (signals.get(key) or {}).get("position") or {}
        return str(position.get("element") or element)

    def position_modality(key: str) -> str:
        position = (signals.get(key) or {}).get("position") or {}
        return str(position.get("modality") or modality)

    def position_house(key: str) -> str:
        house = int((signals.get(key) or {}).get("house") or 1)
        return house_focus[house]

    ruler = signals.get("chart_ruler") or {}
    ruler_position = ruler.get("position") or {}
    visible_focus = signals.get("angular_and_dominant_houses") or {}
    dominant_houses = visible_focus.get("dominant_houses") or []
    dominant_house = int(dominant_houses[0]["house"]) if dominant_houses else 1
    prompts = [
        f"Aku paling menjadi diri sendiri saat {element_focus[position_element('sun')]} lewat {position_house('sun')}.",
        f"Aku merasa aman saat {element_focus[position_element('moon')]} lewat {position_house('moon')}.",
        f"Di situasi baru, aku cenderung {modality_focus[position_modality('ascendant')]}.",
        f"Aku biasanya {modality_focus[str(ruler_position.get('modality') or modality)]} dalam {house_focus[int(ruler.get('house') or 1)]}.",
        f"Aku lebih mudah paham saat {element_focus[position_element('mercury')]} lewat {position_house('mercury')}.",
        f"Aku membangun kedekatan dengan {element_focus[position_element('venus')]} lewat {position_house('venus')}.",
        f"Saat mengejar tujuan, aku {modality_focus[position_modality('mars')]} dalam {position_house('mars')}.",
        (
            "Dorongan dalam diriku sering bertabrakan sebelum aku yakin memilih."
            if has_tension
            else "Pikiran, perasaan, dan tindakanku biasanya sejalan saat aku memilih."
        ),
        (
            f"Aku gampang terlihat saat sibuk dengan {house_focus[dominant_house]}."
            if visible_focus.get("angular_planets")
            else f"Perhatianku sering kembali ke {house_focus[dominant_house]}, walau kesibukanku berubah."
        ),
        f"Aku berkembang dengan {element_focus[element]} sambil {modality_focus[modality]}.",
    ]
    questions = [
        {"id": f"q_{index:02d}", "prompt": prompt}
        for index, prompt in enumerate(prompts, start=1)
    ]
    return {
        "scale": {
            "min": 1,
            "max": 5,
            "labels": {"1": "Sangat tidak sesuai", "5": "Sangat sesuai"},
        },
        "questions": questions,
    }


QUESTIONNAIRE_FORBIDDEN_TERMS = (
    "astrologi",
    "zodiak",
    "planet",
    "rumah",
    "aspek",
    "chart",
    "natal",
    "horoskop",
    "transit",
    "kosmik",
    "ascendant",
    "matahari",
    "bulan",
    "merkurius",
    "venus",
    "mars",
    "jupiter",
    "saturnus",
    "uranus",
    "neptunus",
    "pluto",
    "aries",
    "taurus",
    "gemini",
    "cancer",
    "leo",
    "virgo",
    "libra",
    "scorpio",
    "sagittarius",
    "capricorn",
    "aquarius",
    "pisces",
)


def questionnaire_is_safe(questionnaire: dict[str, Any]) -> bool:
    questions = questionnaire.get("questions") or []
    if len(questions) != QUESTIONNAIRE_COUNT:
        return False
    prompts = [str(item.get("prompt") or "").strip() for item in questions]
    public_text = " ".join(prompts).lower()
    return (
        all(QUESTIONNAIRE_WORD_MIN <= len(prompt.split()) <= QUESTIONNAIRE_WORD_MAX for prompt in prompts)
        and all(re.search(r"\baku\b", prompt.lower()) and not re.search(r"\bsaya\b", prompt.lower()) for prompt in prompts)
        and not any(term in public_text for term in QUESTIONNAIRE_FORBIDDEN_TERMS)
    )


async def generate_questionnaire(signals: dict[str, Any]) -> dict[str, Any]:
    fallback = build_questionnaire(signals)
    config = get_llm_config()
    if config["provider"] == "local_fallback" or not config["base_url"] or not config["api_key"]:
        return fallback

    request_payload = {
        "model": config["model"],
        "messages": [
            {
                "role": "system",
                "content": (
                    "Buat tepat 10 pernyataan refleksi kepribadian berbahasa Indonesia untuk dinilai 1-5. "
                    f"Setiap pernyataan harus {QUESTIONNAIRE_WORD_MIN}-{QUESTIONNAIRE_WORD_MAX} kata dan harus spesifik pada internal_signals yang diberikan. "
                    "Gunakan kata ganti 'aku', bahasa sehari-hari, satu gagasan per pernyataan, dan kalimat yang ringkas. "
                    "Bahas berurutan: identitas, kebutuhan emosi, cara hadir, arah tindakan, cara berpikir, "
                    "relasi dan nilai, ketegasan dan batas, ketegangan batin, fokus hidup, lalu temperamen umum. "
                    "Jangan sebut astrologi, zodiak, planet, rumah, aspek, chart, natal, horoskop, transit, atau kosmik. "
                    "Kembalikan JSON valid saja: {\"questions\":[\"...\"]}."
                ),
            },
            {"role": "user", "content": json.dumps({"internal_signals": signals}, sort_keys=True)},
        ],
        "temperature": config["temperature"],
        "max_tokens": min(1200, max(500, config["max_tokens"])),
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{config['base_url']}/chat/completions",
                headers={"Authorization": f"Bearer {config['api_key']}", "Content-Type": "application/json"},
                json=request_payload,
            )
        response.raise_for_status()
        content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        if content.startswith("```"):
            content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        prompts = json.loads(content).get("questions") or []
        questionnaire = {
            "scale": fallback["scale"],
            "questions": [
                {"id": f"q_{index:02d}", "prompt": str(prompt).strip()}
                for index, prompt in enumerate(prompts, start=1)
            ],
        }
    except (httpx.HTTPError, KeyError, TypeError, AttributeError, json.JSONDecodeError):
        return fallback
    return questionnaire if questionnaire_is_safe(questionnaire) else fallback


def questionnaire_question_view(profile: dict[str, Any], index: int) -> dict[str, Any]:
    questionnaire = profile.get("questionnaire") or {}
    questions = questionnaire.get("questions") or []
    if index >= len(questions):
        raise HTTPException(status_code=404, detail="Question not found")
    question = questions[index]
    return {
        "profile_id": profile["profile_id"],
        "questionnaire": {
            "count": len(questions),
            "scale": questionnaire.get("scale", {}),
            "current_question": {"id": question["id"], "prompt": question["prompt"], "index": index},
        },
    }


def validate_questionnaire_answers(profile: dict[str, Any], answers: dict[str, Any]) -> dict[str, int]:
    questions = profile.get("questionnaire", {}).get("questions") or []
    expected_ids = {question["id"] for question in questions}
    if not expected_ids:
        return {}
    if set(answers) != expected_ids:
        raise HTTPException(status_code=422, detail="Every questionnaire item must be answered exactly once")
    normalized: dict[str, int] = {}
    for question_id, value in answers.items():
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
            raise HTTPException(status_code=422, detail=f"Answer {question_id} must be an integer from 1 to 5")
        normalized[question_id] = value
    return normalized


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


def interpretation_is_public(request_payload_json: str | None) -> bool:
    if not request_payload_json or request_payload_json == "{}":
        return True
    try:
        request_payload = json.loads(request_payload_json)
        messages = request_payload.get("messages", [])
        user_message = next((item for item in reversed(messages) if item.get("role") == "user"), {})
        prompt_payload = json.loads(user_message.get("content") or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    return not prompt_payload.get("detail_question")


def latest_interpretation(profile_id: str, public_only: bool = False) -> dict[str, Any] | None:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT id, provider, model, request_payload_json, response_json, created_at
            FROM interpretations
            WHERE profile_id = ?
            ORDER BY created_at DESC
            """,
            (profile_id,),
        ).fetchall()
    selected_row = None
    for row in rows:
        if not public_only or interpretation_is_public(row["request_payload_json"]):
            selected_row = row
            break
    if not selected_row:
        return None
    profile = load_profile(profile_id)
    response = normalize_personality_response(json.loads(selected_row["response_json"]), profile)
    return {
        "interpretation_id": selected_row["id"],
        "provider": selected_row["provider"],
        "model": selected_row["model"],
        "interpretation": response,
        "created_at": selected_row["created_at"],
    }


def public_profile_payload(row: sqlite3.Row, viewer_is_owner: bool = False) -> dict[str, Any]:
    profile = public_profile_view(load_profile(row["profile_id"]))
    latest = latest_interpretation(row["profile_id"], public_only=True)
    payload = {
        "username": row["username"],
        "display_name": row["display_name"] or profile.get("display_name"),
        "bio": row["bio"],
        "avatar_url": row["avatar_url"],
        "is_public": bool(row["is_public"]),
        "viewer_is_owner": viewer_is_owner,
        "profile": profile,
        "latest_interpretation": latest,
        "public_url": f"{public_app_url()}/{row['username']}",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    if viewer_is_owner:
        payload["profile_id"] = row["profile_id"]
    return payload


def public_profile_view(profile: dict[str, Any]) -> dict[str, Any]:
    traits = profile.get("traits", {})
    chart = profile.get("chart", {})
    houses = chart.get("houses", {}).get("planet_houses", {})
    planets = chart.get("planets", {})
    public_planets = []
    for name, planet in planets.items():
        if not isinstance(planet, dict):
            continue
        public_planets.append(
            {
                "name": name,
                "zodiac_sign": planet.get("zodiac_sign"),
                "degree_in_sign": planet.get("degree_in_sign"),
                "longitude": planet.get("longitude"),
                "element": planet.get("element"),
                "modality": planet.get("modality"),
                "house": houses.get(name),
            }
        )
    house_data = chart.get("houses") or {}
    signals = profile.get("personality_signals") or {}
    return {
        "display_name": profile.get("display_name"),
        "traits": {
            "dominant_element": traits.get("dominant_element"),
            "confidence": traits.get("confidence"),
            "interests": list(traits.get("interests") or [])[:5],
            "talents": list(traits.get("talents") or [])[:5],
            "career_themes": list(traits.get("career_themes") or [])[:5],
        },
        "chart_highlights": {
            "planets": public_planets,
            "aspects": chart.get("aspects") or [],
            "aspects_count": len(chart.get("aspects") or []),
            "house_system": house_data.get("house_system"),
            "house_cusps": house_data.get("cusps") or [],
            "angles": {
                "ascendant": house_data.get("ascendant_zodiac"),
                "midheaven": house_data.get("midheaven_zodiac"),
            },
            "chart_ruler": signals.get("chart_ruler"),
            "angular_and_dominant_houses": signals.get("angular_and_dominant_houses"),
            "overall_pattern": signals.get("overall_pattern"),
        },
    }


def default_sky_posts() -> list[dict[str, str]]:
    articles = [
        ("agustus-2025-ai-uranus-dan-gelembung", "Agustus 2025: Ketika Gelembung AI Mulai Dipertanyakan", """## Peristiwa yang terjadi
Pada 19 Agustus, NASA mengumumkan penemuan satelit kecil baru yang mengorbit Uranus melalui pengamatan James Webb Space Telescope. Dua hari kemudian, laporan tentang studi MIT ramai diberitakan karena menyimpulkan sebagian besar proyek AI generatif perusahaan yang diteliti belum menunjukkan dampak terukur pada laba-rugi. Keduanya adalah kejadian berbeda: satu penemuan astronomi, satu evaluasi ekonomi teknologi.

## Kaitannya dengan langit
Berita AI itu muncul dekat konjungsi Saturnus–Neptunus dan oposisi Mars. Saturnus dibaca sebagai pengujian realitas, Neptunus sebagai gambaran ekspektasi atau gelembung, dan Mars sebagai tekanan yang “menusuk” optimisme. Penemuan satelit Uranus terasa lebih literal: Uranus baru memasuki Gemini, tanda yang berkaitan dengan informasi dan penemuan.

Hubungan tersebut merupakan interpretasi retrospektif, bukan bukti planet menyebabkan laporan MIT atau penemuan NASA. Fakta peristiwanya dapat diperiksa pada arsip NASA 19 Agustus 2025 dan laporan media mengenai studi MIT. Lapisan astrologis hanya menjelaskan mengapa pembicara menilai simbol dan waktu kejadiannya menarik setelah berita muncul.

## Sumber
Review astrologis: segmen berita September Astrology Forecast 2025, The Astrology Podcast. Verifikasi fakta: NASA Science, “New Moon Discovered Orbiting Uranus Using NASA’s Webb Telescope”; MIT Project NANDA dan laporan Axios 21 Agustus 2025."""),
        ("september-2025-kimmel-dan-siklus-24-tahun", "September 2025: Penangguhan Jimmy Kimmel dan Pengulangan 24 Tahun", """## Peristiwa yang terjadi
ABC menghentikan sementara Jimmy Kimmel Live pada 17 September 2025 setelah komentar Kimmel mengenai pembunuhan Charlie Kirk memicu tekanan dari afiliasi jaringan dan pejabat komunikasi federal. Program itu kembali mengudara beberapa hari kemudian. Peristiwa tersebut menjadi perdebatan nasional tentang kebebasan berbicara, tekanan pemerintah, dan batas tanggung jawab penyiaran.

## Kaitannya dengan langit
Tanggalnya punya kemiripan dengan kasus Bill Maher. Maher juga terkena sanksi ABC pada 17 September 2001 setelah komentarnya mengenai serangan 11 September, lalu posisinya kelak digantikan Kimmel. Jarak tepat 24 tahun dibaca sebagai dua putaran Jupiter yang masing-masing sekitar dua belas tahun, dipadukan dengan pola delapan tahunan Venus. Uranus yang sedang berhenti di Gemini menjadi simbol gangguan pada media, komunikasi, dan kebebasan berbicara.

Ini bukan klaim bahwa siklus planet menangguhkan sebuah acara televisi. Keputusan ABC, tekanan afiliasi, pernyataan regulator, dan respons publik tetap merupakan proses manusia yang terdokumentasi. Astrologi di sini adalah cara pembicara membaca pengulangan waktu setelah kedua peristiwa diketahui, bukan alat untuk menggantikan sebab sosial dan politik yang dapat diuji.

## Sumber
Review astrologis: segmen berita October Astrology Forecast 2025. Verifikasi fakta: Reuters, ABC News, serta pengumuman jaringan pada 17–23 September 2025."""),
        ("oktober-2025-pencurian-louvre", "Oktober 2025: Tujuh Menit Pencurian di Louvre", """## Peristiwa yang terjadi
Pada 19 Oktober 2025 sekitar pukul 09.30, sekelompok pencuri memasuki Galerie d’Apollon di Museum Louvre menggunakan tangga angkut, memecahkan etalase, lalu membawa kabur perhiasan bersejarah kerajaan Prancis. Interpol dan otoritas museum kemudian mengonfirmasi barang curian serta memasukkannya ke basis data karya seni curian. Aksi berlangsung cepat di tengah jam kunjungan museum.

## Kaitannya dengan langit
Pencurian itu terjadi saat konjungsi Merkurius–Mars di Scorpio mendekati puncaknya. Merkurius diasosiasikan dengan mobilitas, taktik, dan pencurian; Mars dengan pembobolan serta tindakan agresif; sementara Scorpio menambah tema sesuatu yang tersembunyi dan bernilai. Konfigurasi tersebut juga berada dekat horizon timur pada waktu kejadian.

Korelasi simbolis ini tidak menjelaskan kegagalan keamanan, pilihan pelaku, atau mekanisme pencurian. Penyelidikan kriminal tetap bergantung pada rekaman, saksi, bukti forensik, dan kerja kepolisian. Kaitan langitnya dibaca sesudah fakta diketahui, tanpa mengubah interpretasi menjadi penyebab.

## Sumber
Review astrologis: segmen berita November Astrology Forecast 2025. Verifikasi fakta: pernyataan resmi Musée du Louvre, basis data Interpol, dan laporan AP pada 19–20 Oktober 2025."""),
        ("november-2025-cloudflare-dan-merkurius", "November 2025: Ketika Gangguan Cloudflare Menjalar ke Mana-mana", """## Peristiwa yang terjadi
Pada 18 November 2025, gangguan pada infrastruktur Cloudflare membuat banyak layanan daring tidak dapat diakses atau bekerja tidak stabil. Dampaknya terasa luas karena Cloudflare berada di antara pengguna dan banyak situs sebagai penyedia jaringan, keamanan, dan penyaring lalu lintas. Insiden itu muncul pada bulan yang juga dipenuhi pembatalan penerbangan di Amerika Serikat dan gangguan logistik lain.

## Kaitannya dengan langit
Gangguan tersebut terjadi pada periode Merkurius retrograde yang beroposisi dengan Uranus. Merkurius mewakili pertukaran data, perjalanan, serta jaringan penghubung; Uranus digunakan untuk perubahan mendadak dan kerusakan yang menyebar secara tak terduga. Oposisi keduanya dibaca sebagai gambaran sistem komunikasi yang terganggu dari dua sisi, setelah gangguannya tercatat.

Penyebab teknis Cloudflare tetap harus dibaca dari laporan insiden perusahaan, bukan dari konfigurasi planet. Perangkat lunak, kapasitas jaringan, proses operasional, dan respons teknisi adalah penjelasan kausal yang sebenarnya. Astrologi hanya menjadi lapisan tentang waktu dan simbol, sehingga laporan kejadian tetap perlu dipisahkan dari interpretasinya.

## Sumber
Review astrologis: segmen berita December Astrology Forecast 2025. Verifikasi fakta: laporan insiden Cloudflare 18 November 2025 dan pemberitaan teknologi pada hari yang sama."""),
        ("januari-2026-minneapolis-mars-pluto", "Januari 2026: Kekerasan di Minneapolis dan Mars–Pluto", """## Peristiwa yang terjadi
Operasi imigrasi federal di Minneapolis memicu protes besar setelah dua warga sipil ditembak mati dalam insiden terpisah pada Januari 2026. Renee Nicole Good meninggal pada 7 Januari, sedangkan Alex Pretti meninggal pada 24 Januari. Kedua kasus menjadi pusat perdebatan tentang penggunaan kekuatan, kewenangan agen federal, dan akuntabilitas operasi penegakan imigrasi.

## Kaitannya dengan langit
Kematian pertama berdekatan dengan pertemuan Venus–Mars, lalu kematian kedua terjadi saat Mars mendekati Pluto di Aquarius. Mars diasosiasikan dengan tindakan bersenjata dan konflik, Pluto dengan konsentrasi kuasa, serta Aquarius dengan kelompok dan gerakan kolektif. Protes yang membesar sesudah insiden dibaca sebagai bagian dari pola simbolik itu.

Interpretasi tersebut bukan penjelasan hukum maupun forensik. Keputusan petugas, kebijakan operasi, rekaman video, investigasi, dan proses peradilan adalah sumber untuk memahami mengapa kejadian berlangsung. Peta langit hanya memberi bingkai waktu setelah peristiwa terjadi. Memisahkan dua lapisan ini penting agar refleksi astrologis tidak mengaburkan korban, tanggung jawab institusional, atau bukti yang bisa diuji.

## Sumber
Review astrologis: segmen berita February Astrology Forecast 2026. Verifikasi fakta: laporan media dan pernyataan otoritas Minneapolis pada Januari 2026."""),
        ("februari-2026-super-bowl-bad-bunny", "Februari 2026: Bad Bunny, Super Bowl, dan Identitas Puerto Riko", """## Peristiwa yang terjadi
Bad Bunny membawakan pertunjukan paruh waktu Super Bowl pada 8 Februari 2026 dengan penampilan berbahasa Spanyol yang menonjolkan budaya Puerto Riko. Panggung olahraga terbesar di Amerika Serikat itu berubah menjadi momen budaya: musik, bahasa, identitas kepulauan, serta hubungan Puerto Riko dengan Amerika menjadi bagian dari percakapan publik.

## Kaitannya dengan langit
Momen tersebut berdekatan dengan pertemuan Saturnus–Neptunus dan siklus historis hubungan politik Puerto Riko–Amerika Serikat yang berulang dekat konfigurasi dua planet itu. Saturnus dibaca sebagai struktur negara dan batas kelembagaan; Neptunus sebagai identitas kolektif, budaya, serta batas yang menjadi kabur. Penampilan Bad Bunny menjadi manifestasi budaya yang terlihat, bukan keputusan politik formal.

Kehadiran musisi, pilihan bahasa, desain pertunjukan, dan penerimaan publik mempunyai sebab produksi dan sosial yang konkret. Planet tidak memilih daftar lagu atau membuat kebijakan penyiaran. Kaitan astrologis adalah pembacaan pola sejarah setelah acara berlangsung. Nilainya, jika ada, berada pada pertanyaan reflektif tentang identitas dan struktur—bukan pada klaim bahwa satu konfigurasi kosmik menghasilkan satu pertunjukan.

## Sumber
Review astrologis: segmen berita March Astrology Forecast 2026. Verifikasi fakta: dokumentasi resmi Super Bowl dan laporan pertunjukan 8 Februari 2026."""),
        ("maret-2026-sora-ditutup", "Maret 2026: OpenAI Menutup Sora", """## Peristiwa yang terjadi
Pada 24 Maret 2026, OpenAI mengumumkan penghentian aplikasi video AI Sora. Aplikasi dan pengalaman web ditutup pada 26 April, sementara penghentian API dijadwalkan kemudian. Keputusan itu datang setelah Sora sempat viral, memicu perdebatan tentang deepfake, hak atas kemiripan wajah, biaya komputasi, dan hubungan industri kreatif dengan video generatif.

## Kaitannya dengan langit
Pengumuman itu muncul dekat pertemuan Matahari–Saturnus dan perubahan arah Merkurius setelah fase retrograde bersama Mars di Pisces. Saturnus menjadi simbol penghentian, batas, dan evaluasi kelayakan; Merkurius untuk produk komunikasi; Neptunus dan Pisces untuk citra sintetis yang menyulitkan pembedaan nyata dan rekaan. Hubungan ini dibaca setelah keputusan perusahaan diumumkan.

Alasan bisnis Sora tetap berada pada strategi OpenAI, penggunaan produk, biaya, risiko, dan prioritas pengembangan model. Konfigurasi planet tidak menggantikan analisis produk atau pernyataan perusahaan. Artikel ini mempertahankan interpretasi astrologis sebagai komentar budaya atas waktunya, sambil menempatkan pengumuman resmi sebagai fakta utama yang dapat diperiksa.

## Sumber
Review astrologis: segmen berita April Astrology Forecast 2026. Verifikasi fakta: OpenAI Help Center, pengumuman OpenAI 24 Maret, serta laporan AP dan The Guardian."""),
        ("april-2026-percobaan-serangan-dan-uranus", "April 2026: Serangan di Washington dan Ingres Uranus", """## Peristiwa yang terjadi
Pada 25 April 2026, sebuah insiden keamanan terjadi ketika Donald Trump menghadiri rangkaian acara White House Correspondents’ Dinner di Washington. Peristiwa itu segera ditangani sebagai percobaan serangan terhadap presiden dan menjadi berita utama. Fakta detailnya harus mengikuti pembaruan aparat keamanan dan hasil penyelidikan, bukan spekulasi yang beredar pada jam-jam pertama.

## Kaitannya dengan langit
Insiden tersebut terjadi pada hari Uranus memasuki Gemini. Posisi Bulan juga membentuk sudut tegang terhadap Uranus dan menyentuh titik penting pada peta kelahiran Trump. Uranus dipakai sebagai simbol kejutan mendadak, sedangkan Gemini dikaitkan dengan acara media, informasi, dan ruang publik yang dipenuhi komunikasi.

Korelasi waktu tidak menetapkan sebab. Pengamanan, tindakan pelaku, respons aparat, dan konteks politik adalah rangkaian nyata yang perlu diteliti melalui bukti. Bahkan dalam kerangka astrologi, kaitannya dibaca secara retrospektif. Artikel ini karena itu tidak memperluas interpretasi menjadi tuduhan, prediksi lanjutan, atau kepastian tentang motif.

## Sumber
Review astrologis: segmen berita May Astrology Forecast 2026. Verifikasi fakta: laporan aparat federal dan media arus utama mengenai insiden 25 April 2026."""),
        ("mei-2026-ledakan-pabrik-kembang-api", "Mei 2026: Ledakan Pabrik Kembang Api dan Mars–Jupiter", """## Peristiwa yang terjadi
Pada 4 Mei 2026, ledakan besar terjadi di sebuah pabrik kembang api di China dan menyebabkan puluhan korban meninggal serta luka-luka. Peristiwa ini merupakan kecelakaan industri yang harus dipahami melalui standar keselamatan, penyimpanan bahan peledak, pengawasan, dan hasil penyelidikan lokal—bukan melalui simbol astrologis.

## Kaitannya dengan langit
Waktu kejadian sekitar pukul 16.43 lokal menempatkan Mars dan Jupiter dekat sudut utama peta ketika keduanya membentuk square. Mars dibaca sebagai simbol api, ledakan, dan cedera; Jupiter sebagai pembesar skala. Karena lokasi tersebut memang memproduksi kembang api, gambarnya terasa sangat literal setelah peristiwa diketahui.

Kesan simbolis tidak boleh mengurangi kebutuhan akan investigasi material. Jumlah bahan, prosedur kerja, kepatuhan bangunan, pelatihan pekerja, dan respons darurat adalah faktor yang dapat menjelaskan skala bencana. Astrologi di sini hanya merekam cara pembicara membaca kesamaan bahasa simbol dan waktu, tanpa menyatakan planet menyalakan ledakan atau menentukan jumlah korban.

## Sumber
Review astrologis: segmen berita June Astrology Forecast 2026. Fakta perlu dirujuk silang dengan laporan pemerintah setempat dan kantor berita mengenai ledakan 4 Mei 2026."""),
        ("juni-2026-gempa-venezuela", "Juni 2026: Gempa Ganda Venezuela", """## Peristiwa yang terjadi
Pada 24 Juni 2026, dua gempa kuat bermagnitudo 7,2 dan 7,5 mengguncang wilayah utara-tengah Venezuela dalam selang waktu singkat. Laporan kemanusiaan menggambarkan kerusakan luas, korban jiwa, pengungsian, dan tekanan pada layanan kesehatan. Angka korban terus berubah selama operasi pencarian, sehingga artikel ini tidak mengunci satu angka awal sebagai hasil akhir.

## Kaitannya dengan langit
Gempa ganda itu berdekatan dengan Mars yang mendekati Uranus di Gemini. Konfigurasinya juga dibandingkan dengan Mars–Uranus pada peta pendirian Venezuela, sebuah teknik yang disebut recurrence transit. Mars digunakan sebagai simbol pelepasan energi mendadak, sedangkan Uranus mewakili guncangan dan perubahan tiba-tiba.

Gempa bumi mempunyai sebab geologis: pergerakan sesar, akumulasi tegangan, kedalaman, dan kondisi tanah. Astrologi tidak memprediksi lokasi atau menggantikan seismologi. Korelasi waktunya dibaca setelah kejadian. Informasi keselamatan dan dampak harus mengikuti lembaga geologi serta organisasi kemanusiaan, bukan penafsiran planet.

## Sumber
Review astrologis: segmen berita July Astrology Forecast 2026. Verifikasi fakta: UNFPA, UNICEF, UNHCR, laporan AP, dan laporan teknis gempa Venezuela 24 Juni 2026."""),
        ("juli-2026-lindsey-graham", "Juli 2026: Wafatnya Lindsey Graham dan Recurrence Transit", """## Peristiwa yang terjadi
Senator Amerika Serikat Lindsey Graham meninggal mendadak pada 11 Juli 2026 dalam usia 71 tahun. Temuan awal yang diberitakan menyebut robekan aorta sebagai kemungkinan penyebab. Pemakaman dan penghormatan publik kemudian menghadirkan pejabat Amerika serta tokoh internasional, mencerminkan panjangnya karier Graham dalam politik luar negeri dan pertahanan.

## Kaitannya dengan langit
Graham lahir dengan konjungsi Mars–Uranus dan meninggal beberapa hari setelah konfigurasi yang sama kembali terjadi di langit. Pola ini disebut recurrence transit: susunan planet kelahiran muncul kembali saat peristiwa penting terjadi. Mars dan Uranus digunakan sebagai bahasa simbol untuk kejadian yang mendadak, bukan diagnosis medis.

Penyebab kematian harus mengikuti pemeriksaan medis, riwayat kesehatan, dan pernyataan keluarga atau pejabat. Recurrence transit tidak membuktikan mekanisme biologis dan tidak dapat digunakan untuk menyimpulkan risiko pada orang lain dengan susunan serupa. Hubungan waktunya dibaca setelah kematian diumumkan, sambil mempertahankan batas antara fakta medis dan interpretasi astrologis.

## Sumber
Review astrologis: segmen berita August Astrology Forecast 2026. Verifikasi fakta: laporan AP 28 Juli 2026 dan keterangan awal mengenai kematian Lindsey Graham."""),
    ]
    return [
        {
            "slug": slug,
            "title": title,
            "tag": title.split(":", 1)[0],
            "summary": body.splitlines()[1][:180].rstrip() + "…",
            "body": body.split("\n\n## Sumber", 1)[0],
        }
        for slug, title, body in articles
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
    value: Any = content.strip()
    for _ in range(3):
        if not isinstance(value, str):
            break
        text = value.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines and lines[-1].strip() == "```" else lines[1:]).strip()
        candidates = [text]
        if "{" in text and "}" in text:
            candidates.append(text[text.find("{") : text.rfind("}") + 1])
        for candidate in candidates:
            try:
                value = json.loads(candidate)
                break
            except json.JSONDecodeError:
                continue
        else:
            recovered = recover_personality_json(text)
            if recovered:
                return normalize_llm_response(recovered)
            return normalize_llm_response({"summary": text or "LLM returned no message content.", **({"raw": raw} if raw else {})})
    return normalize_llm_response(value if isinstance(value, dict) else {"summary": value})


def recover_personality_json(text: str) -> dict[str, Any]:
    """Recover complete fields from a provider response truncated mid-JSON."""
    decoder = json.JSONDecoder()

    def value_for(key: str) -> Any:
        marker = f'"{key}"'
        start = text.find(marker)
        if start < 0:
            return None
        start = text.find(":", start + len(marker))
        if start < 0:
            return None
        try:
            return decoder.raw_decode(text[start + 1 :].lstrip())[0]
        except json.JSONDecodeError:
            return None

    recovered = {
        key: value_for(key)
        for key in ("preview_summary", "highlights", "identity_keywords", "username_suggestions", "confidence", "caveat")
    }
    sections = {
        key: value_for(key)
        for key in (
            "core_identity",
            "emotional_needs",
            "social_approach",
            "thinking_and_communication",
            "relationships_and_values",
            "drive_and_boundaries",
            "inner_tensions",
            "dominant_patterns",
            "growth_focus",
        )
    }
    recovered["full_analysis"] = {key: value for key, value in sections.items() if isinstance(value, str)}
    return {key: value for key, value in recovered.items() if value not in (None, {}, [])}


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


def local_personality_response(profile: dict[str, Any], language: str) -> dict[str, Any]:
    traits = profile["traits"]
    dominant = traits["dominant_element"]
    labels = {
        "fire": ("inisiatif", "keberanian kreatif", "penggerak"),
        "earth": ("ketekunan", "cara berpikir praktis", "pembangun"),
        "air": ("rasa ingin tahu", "komunikasi", "penjelajahide"),
        "water": ("kepekaan", "refleksi", "pengamat"),
    }
    strength, style, identity = labels.get(dominant, labels["air"])
    caveat = profile.get("precision", {}).get("caveat")
    if language == "en":
        preview = (
            f"You tend to lead with {strength}, supported by a {style} approach when reading people and situations. "
            "You usually make progress by noticing patterns first, then turning them into a direction that feels meaningful. "
            "This can make you thoughtful and adaptable, although competing needs may slow a decision when expectations are unclear. "
            "Your strongest growth comes from naming your priorities early, checking what you genuinely need, and setting clear boundaries before taking on something new."
        )
        highlights = ["Learns from patterns", "Values meaningful progress", "Benefits from clear boundaries"]
        identity_keywords = [
            {"word": "Curious", "icon": "✦"},
            {"word": "Clear", "icon": "◉"},
            {"word": "Growing", "icon": "↗"},
        ]
    else:
        preview = (
            f"Kamu cenderung bergerak dengan {strength}, ditopang oleh {style} saat membaca orang dan situasi. "
            "Biasanya kamu menangkap pola terlebih dahulu, lalu mengubahnya menjadi arah yang terasa bermakna dan masuk akal untuk dijalani. "
            "Cara ini membuatmu peka sekaligus lentur, meski beberapa kebutuhan yang datang bersamaan dapat membuat keputusan terasa lebih lambat ketika ekspektasi belum jelas. "
            "Perkembangan terbesarmu muncul saat kamu menyebut prioritas sejak awal, memeriksa kebutuhan diri dengan jujur, dan menetapkan batas sebelum menerima tanggung jawab baru."
        )
        highlights = ["Cepat membaca pola", "Mengutamakan kemajuan yang bermakna", "Berkembang dengan batas yang jelas"]
        identity_keywords = [
            {"word": "Peka", "icon": "✦"},
            {"word": "Jernih", "icon": "◉"},
            {"word": "Tumbuh", "icon": "↗"},
        ]
    full_analysis = {
        "core_identity": preview,
        "emotional_needs": (
            "Kamu membutuhkan ruang yang cukup untuk mengenali perasaan sebelum merespons. Emosi biasanya menjadi lebih mudah dipahami "
            "ketika kamu tidak dipaksa segera memberi jawaban dan dapat menamai apa yang sedang terjadi dengan jujur. Dukungan terbaik "
            "datang dari suasana yang tenang, orang yang konsisten, serta kebiasaan sederhana untuk berhenti sejenak sebelum mengambil keputusan penting."
        ),
        "social_approach": (
            "Kamu cenderung mengamati suasana terlebih dahulu lalu menyesuaikan cara hadir. Kepekaan ini membantu kamu membaca kebutuhan "
            "kelompok tanpa harus selalu menjadi pusat perhatian. Namun, terlalu lama menimbang respons orang lain dapat membuat keinginanmu "
            "sendiri kurang terlihat. Hubungan sosial terasa lebih ringan saat kamu menyampaikan posisi sejak awal, tetap ramah, dan tidak mengorbankan batas pribadi."
        ),
        "thinking_and_communication": (
            "Kamu berkembang saat dapat mengolah pola lalu menjelaskannya dengan bahasamu sendiri. Pikiranmu bekerja baik ketika informasi "
            "dapat disusun menjadi urutan yang jelas, dibandingkan, kemudian diuji lewat percakapan. Saat banyak hal datang bersamaan, catatan "
            "singkat dan pertanyaan yang spesifik membantumu menjaga fokus. Orang lain lebih mudah mengikuti gagasanmu ketika kesimpulan disertai contoh yang konkret."
        ),
        "relationships_and_values": (
            "Kedekatan terasa sehat ketika nilai pribadi dan kebutuhan bersama sama-sama punya tempat. Kamu menghargai hubungan yang tumbuh "
            "melalui perhatian konsisten, percakapan terbuka, dan tindakan yang dapat dipercaya. Ada kecenderungan memberi banyak ruang kepada "
            "orang lain, sehingga penting untuk menyebut kebutuhanmu tanpa menunggu mereka menebak. Kejelasan kecil sejak awal mencegah kecewa yang menumpuk diam-diam."
        ),
        "drive_and_boundaries": (
            "Langkahmu paling kuat ketika tujuan dan batas dibuat jelas sejak awal. Kamu dapat bekerja tekun selama memahami alasan di balik "
            "sebuah tanggung jawab dan melihat kemajuan yang nyata. Dorongan untuk membantu kadang membuat beban bertambah tanpa disadari. "
            "Sebelum menyanggupi hal baru, periksa waktu, tenaga, dan prioritas agar ketegasanmu tetap hangat tanpa berubah menjadi kelelahan."
        ),
        "inner_tensions": (
            "Keinginan bergerak cepat kadang perlu diseimbangkan dengan kebutuhan memastikan arah. Satu bagian dirimu ingin segera mencoba, "
            "sementara bagian lain mencari kepastian agar risiko tetap terkendali. Tarik-menarik ini bukan kelemahan; ia dapat menjadi sistem "
            "pemeriksaan yang berguna. Tetapkan batas waktu untuk menimbang, pilih langkah kecil yang bisa diuji, lalu evaluasi berdasarkan hasil nyata."
        ),
        "dominant_patterns": (
            f"Tema {strength} dan {style} muncul berulang dalam cara kamu mengambil keputusan. Kamu biasanya mengumpulkan petunjuk, mencari "
            "hubungan di antaranya, lalu memilih arah yang terasa masuk akal sekaligus selaras dengan nilai pribadi. Pola ini membuatmu kuat "
            "dalam situasi yang membutuhkan pemahaman menyeluruh. Tantangannya adalah berhenti mencari satu petunjuk tambahan ketika informasi yang tersedia sebenarnya sudah cukup."
        ),
        "growth_focus": (
            "Fokus pertumbuhanmu adalah membangun kebiasaan mengecek kebutuhan diri sebelum menyetujui tuntutan baru. Mulailah dengan "
            "menanyakan apa yang benar-benar penting, sumber daya apa yang tersedia, dan batas mana yang tidak boleh dilewati. Latihan kecil "
            "namun rutin akan lebih efektif daripada perubahan besar sesaat. Catat keputusan penting, tinjau hasilnya, lalu perbaiki cara memilih tanpa menghakimi diri."
        ),
    }
    return {
        "preview_summary": preview,
        "highlights": highlights,
        "identity_keywords": identity_keywords,
        "username_suggestions": [f"{identity}tenang", f"{identity}bertumbuh", f"{identity}jernih"],
        "full_analysis": full_analysis,
        "confidence": traits["confidence"],
        "caveat": caveat,
    }


def normalize_username_suggestions(value: Any, profile: dict[str, Any]) -> list[str]:
    candidates = value if isinstance(value, list) else []
    normalized = []
    for item in candidates:
        username = "".join(
            char
            for char in str(item).lower().replace(" ", "_")
            if char in "abcdefghijklmnopqrstuvwxyz0123456789_"
        )
        if 3 <= len(username) <= 32 and username not in normalized:
            normalized.append(username)
    return normalized[:3]


def normalize_identity_keywords(value: Any, profile: dict[str, Any]) -> list[dict[str, str]]:
    candidates = value if isinstance(value, list) else []
    normalized: list[dict[str, str]] = []
    for item in candidates:
        word = item.get("word") if isinstance(item, dict) else item
        icon = item.get("icon") if isinstance(item, dict) else None
        word = str(word or "").strip().split()[0][:20] if str(word or "").strip() else ""
        icon = str(icon or "").strip()[:4]
        if word and not any(entry["word"].lower() == word.lower() for entry in normalized):
            normalized.append({"word": word, "icon": icon or "✦"})
        if len(normalized) == 3:
            return normalized
    return normalized


def normalize_personality_response(response: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    fallback = local_personality_response(profile, "id")
    for key in ("preview_summary", "summary"):
        embedded = response.get(key)
        if not isinstance(embedded, str):
            continue
        parsed = parse_llm_content(embedded)
        if any(name in parsed for name in ("preview_summary", "full_analysis", "username_suggestions", "identity_keywords")):
            response = {**response, **parsed}
            break
    full_analysis = response.get("full_analysis")
    if not isinstance(full_analysis, dict):
        full_analysis = {}
    highlights = response.get("highlights")
    if not isinstance(highlights, list):
        highlights = []
    normalized_highlights = [stringify_response_item(item) for item in highlights]
    preview_summary = str(response.get("preview_summary") or response.get("summary") or fallback["preview_summary"]).strip()
    if preview_summary.startswith("{") and '"preview_summary"' in preview_summary:
        preview_summary = preview_summary.split('"preview_summary"', 1)[1].split(":", 1)[-1].lstrip()
        if preview_summary.startswith('"'):
            preview_summary = preview_summary[1:]
        preview_summary = preview_summary.split('",', 1)[0].rstrip('"} \n').replace('\\"', '"').replace("\\n", " ")
    return {
        "preview_summary": preview_summary or fallback["preview_summary"],
        "highlights": normalized_highlights[:3],
        "identity_keywords": normalize_identity_keywords(response.get("identity_keywords"), profile),
        "username_suggestions": normalize_username_suggestions(response.get("username_suggestions"), profile),
        "full_analysis": {
            key: str(full_analysis[key]).strip()
            for key in fallback["full_analysis"]
            if len(str(full_analysis.get(key) or "").split()) >= 50
        },
        "confidence": response.get("confidence") or profile["traits"]["confidence"],
        "caveat": profile.get("precision", {}).get("caveat") or response.get("caveat"),
    }


def guest_interpretation_view(response: dict[str, Any]) -> dict[str, Any]:
    return {
        "preview_summary": response.get("preview_summary") or response.get("summary", ""),
        "highlights": list(response.get("highlights") or response.get("strengths") or [])[:3],
        "identity_keywords": list(response.get("identity_keywords") or [])[:3],
        "username_suggestions": list(response.get("username_suggestions") or [])[:3],
        "confidence": response.get("confidence"),
        "caveat": response.get("caveat"),
    }


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


async def call_llm(
    profile: dict[str, Any],
    language: str = "id",
    question: str | None = None,
    max_tokens_override: int | None = None,
) -> dict[str, Any]:
    config = get_llm_config()
    provider = config["provider"]
    base_url = config["base_url"]
    api_key = config["api_key"]
    model = config["model"]
    temperature = config["temperature"]
    max_tokens = normalize_limit_value(max_tokens_override, 128, 8000, config["max_tokens"])

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
        "internal_birth_pattern": profile["chart"],
        "personality_signals": profile.get("personality_signals", {}),
        "traits": profile["traits"],
        "questionnaire": profile.get("questionnaire", {}),
        "validation": profile.get("validation", {}),
        "detail_question": question,
    }
    language_name = "Indonesian" if language == "id" else "English"
    system_prompt_template = get_setting(
        "llm_system_prompt",
        os.getenv("LLM_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
    )
    system_prompt = system_prompt_template.replace("{language}", language_name)
    if "preview_summary" not in system_prompt or "identity_keywords" not in system_prompt:
        system_prompt = f"{system_prompt}\n\n{DEFAULT_SYSTEM_PROMPT.replace('{language}', language_name)}"
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

    if provider == "local_fallback":
        return {
            "provider": "local_fallback",
            "model": "local-template",
            "prompt_hash": prompt_hash,
            "request_payload": request_payload,
            "response": local_personality_response(profile, language),
        }
    if not base_url or not api_key:
        raise HTTPException(status_code=503, detail="Layanan AI belum dikonfigurasi. Coba lagi setelah pengaturan diperbarui.")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=request_payload,
            )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Layanan AI sedang tidak tersedia. Coba lagi sebentar.") from exc

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
                "response": normalize_personality_response(parse_llm_content(streamed_content), profile),
            }
        raise HTTPException(status_code=502, detail="Layanan AI mengirim respons yang tidak dapat dibaca. Coba lagi sebentar.")

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    parsed = normalize_personality_response(parse_llm_content(content, raw=data), profile)
    return {
        "provider": provider,
        "model": model,
        "prompt_hash": prompt_hash,
        "request_payload": request_payload,
        "response": parsed,
    }


app = FastAPI(title="Hermex API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5666,http://127.0.0.1:5666",
    ).split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    validate_hosted_admin_configuration()
    init_db()


@app.get("/api/v1/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "hermex-api", "database": str(DB_PATH)}


@app.get("/api/v1/auth/google/start")
def google_auth_start(request: Request) -> RedirectResponse:
    google_session_secret(request, raise_on_invalid=True)
    config = google_oauth_config(request)
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
        OAUTH_STATE_COOKIE_NAME,
        state,
        httponly=True,
        samesite="lax",
        secure=secure_cookie(request),
        path="/",
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
    expected_state = request.cookies.get(OAUTH_STATE_COOKIE_NAME)
    if not code or not state or not expected_state or not secrets.compare_digest(state, expected_state):
        return RedirectResponse(f"{app_url}/?auth=google_state_error", status_code=303)

    google_session_secret(request, raise_on_invalid=True)
    config = google_oauth_config(request)
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
    response.delete_cookie(OAUTH_STATE_COOKIE_NAME, path="/")
    response.set_cookie(
        GOOGLE_COOKIE_NAME,
        google_session_token(user, request),
        httponly=True,
        samesite="lax",
        secure=secure_cookie(request),
        path="/",
        max_age=session_max_age("GOOGLE_SESSION_MAX_AGE_SECONDS", 60 * 60 * 24 * 30),
    )
    return response


@app.get("/api/v1/auth/me")
def auth_me(request: Request) -> dict[str, Any]:
    user = read_google_session(request)
    return {"authenticated": bool(user), "user": user}


@app.get("/api/v1/entitlement")
def get_entitlement(request: Request) -> dict[str, Any]:
    return public_entitlement_payload(current_entitlement(request))


@app.get("/api/v1/auth/logout")
def auth_logout() -> RedirectResponse:
    response = RedirectResponse(public_app_url(), status_code=303)
    response.delete_cookie(GOOGLE_COOKIE_NAME, path="/")
    return response


@app.post("/api/v1/user/history/sync")
def sync_user_history(payload: UserHistorySyncInput, request: Request) -> dict[str, Any]:
    user = require_google_user(request)
    user_sub = str(user.get("sub") or user.get("email"))
    profile_claims = list({claim.profile_id: claim for claim in payload.profile_claims if claim.profile_id}.values())
    linked_count = 0
    with db() as conn:
        for claim in profile_claims:
            row = conn.execute("SELECT profile_json FROM profiles WHERE id = ?", (claim.profile_id,)).fetchone()
            if not row:
                continue
            try:
                profile_json = json.loads(row["profile_json"])
            except json.JSONDecodeError:
                continue
            expected_token = str(profile_json.get("claim_token") or "")
            if not expected_token or not secrets.compare_digest(expected_token, claim.claim_token):
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO user_profiles (user_sub, profile_id, linked_at)
                VALUES (?, ?, ?)
                """,
                (user_sub, claim.profile_id, now_iso()),
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
            SELECT p.profile_json, up.linked_at, pp.username AS public_username, pp.is_public
            FROM user_profiles up
            JOIN profiles p ON p.id = up.profile_id
            LEFT JOIN public_profiles pp ON pp.profile_id = up.profile_id
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
                "public_username": row["public_username"],
                "is_public": bool(row["is_public"]) if row["is_public"] is not None else None,
            }
        )
    return {"history": history}


@app.delete("/api/v1/user/history/{profile_id}")
def delete_user_history(profile_id: str, request: Request) -> dict[str, Any]:
    user = require_google_user(request)
    user_sub = str(user.get("sub") or user.get("email"))
    with db() as conn:
        owned = conn.execute(
            "SELECT 1 FROM user_profiles WHERE user_sub = ? AND profile_id = ?",
            (user_sub, profile_id),
        ).fetchone()
        if not owned:
            raise HTTPException(status_code=403, detail="Profile is not linked to this account")
        conn.execute("DELETE FROM feedback WHERE profile_id = ?", (profile_id,))
        conn.execute("DELETE FROM interpretations WHERE profile_id = ?", (profile_id,))
        conn.execute("DELETE FROM public_profiles WHERE profile_id = ?", (profile_id,))
        conn.execute(
            "DELETE FROM user_profiles WHERE profile_id = ?",
            (profile_id,),
        )
        conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
    return {"status": "ok"}


@app.post("/api/v1/birth/analyze")
async def analyze_birth(payload: BirthProfileInput, request: Request) -> dict[str, Any]:
    enforce_public_write_rate_limit(request, "birth_analyze")
    profile_id = str(uuid.uuid4())
    time_unknown = payload.birth_time is None
    chart = compute_chart(payload)
    traits = build_trait_profile(chart, time_unknown)
    signals = derive_personality_signals(chart)
    questionnaire = await generate_questionnaire(signals)
    precision = {
        "level": "reduced" if time_unknown else "standard",
        "assumed_birth_time": "00:00" if time_unknown else None,
        "caveat": (
            "Jam lahir tidak diisi, jadi perhitungan memakai asumsi 00:00. Tambahkan jam yang lebih tepat agar hasil lebih akurat."
            if time_unknown
            else None
        ),
    }
    profile = {
        "profile_id": profile_id,
        "claim_token": secrets.token_urlsafe(32),
        "display_name": payload.display_name,
        "birth_date": payload.birth_date.isoformat(),
        "birth_time": payload.birth_time,
        "birth_place": payload.birth_place,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "timezone": payload.timezone or "manual-or-utc-pending",
        "time_unknown": time_unknown,
        "precision": precision,
        "chart": chart,
        "traits": traits,
        "personality_signals": signals,
        "questionnaire": questionnaire,
        "needs_validation": True,
        "validation_questions": [
            {"id": question["id"], "label": question["prompt"], "type": "rating", "min": 1, "max": 5}
            for question in questionnaire["questions"]
        ],
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
    response = questionnaire_question_view(profile, 0)
    response.update(
        {
            "claim_token": profile["claim_token"],
            "precision": precision,
            "needs_validation": True,
        }
    )
    return response


@app.post("/api/v1/birth/question")
def get_questionnaire_question(payload: QuestionnaireQuestionInput, request: Request) -> dict[str, Any]:
    enforce_public_write_rate_limit(request, "birth_question", minute_limit=120, day_limit=1000)
    profile = load_profile(payload.profile_id)
    expected_token = str(profile.get("claim_token") or "")
    if not expected_token or not secrets.compare_digest(payload.claim_token, expected_token):
        raise HTTPException(status_code=403, detail="Invalid profile claim token")
    return questionnaire_question_view(profile, payload.index)


@app.post("/api/v1/birth/validate")
def validate_birth(payload: ValidationInput, request: Request) -> dict[str, Any]:
    enforce_public_write_rate_limit(request, "birth_validate")
    profile = load_profile(payload.profile_id)
    expected_token = str(profile.get("claim_token") or "")
    if not expected_token or not secrets.compare_digest(payload.claim_token, expected_token):
        raise HTTPException(status_code=403, detail="Invalid profile claim token")
    answers = validate_questionnaire_answers(profile, payload.answers)
    score_boost = 0.16 if answers else 0
    base_score = float(profile["traits"]["confidence"]["score"])
    new_score = min(base_score + score_boost, 0.88)
    profile["traits"]["confidence"] = {"score": round(new_score, 2), "label": "high" if new_score >= 0.7 else "medium"}
    profile["validation"] = {"answers": answers, "resolved_at": now_iso()}
    profile["needs_validation"] = False
    save_profile(profile)
    return {
        "profile_id": profile["profile_id"],
        "confidence": profile["traits"]["confidence"],
        "ready_for_interpretation": True,
        "precision": profile.get("precision"),
    }


@app.get("/api/v1/profiles/{profile_id}")
def get_profile(profile_id: str, request: Request) -> dict[str, Any]:
    profile = load_profile(profile_id)
    require_profile_owner(profile_id, request)
    return {key: value for key, value in profile.items() if key != "claim_token"}


@app.post("/api/v1/public-profiles")
def create_public_profile(payload: PublicProfileInput, request: Request) -> dict[str, Any]:
    enforce_public_write_rate_limit(request, "public_profile", minute_limit=8, day_limit=60)
    profile = load_profile(payload.profile_id)
    username = payload.username.strip().lower()
    email = payload.email.strip().lower()
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise HTTPException(status_code=422, detail="Valid email is required")
    user = read_google_session(request)
    user_sub = str((user or {}).get("sub") or "")
    expected_claim_token = str(profile.get("claim_token") or "")
    has_valid_claim = bool(
        payload.claim_token
        and expected_claim_token
        and secrets.compare_digest(payload.claim_token, expected_claim_token)
    )

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
            ).fetchone() if user_sub else None
            if not owner_row and not has_valid_claim:
                raise HTTPException(status_code=403, detail="Profile claim token or Google-linked ownership is required")
            conn.execute(
                """
                UPDATE public_profiles
                SET username = ?, email = ?, display_name = ?, bio = ?, avatar_url = COALESCE(?, avatar_url), updated_at = ?
                WHERE profile_id = ?
                """,
                (
                    username,
                    email,
                    payload.display_name or profile.get("display_name"),
                    payload.bio,
                    (user or {}).get("picture"),
                    updated_at,
                    payload.profile_id,
                ),
            )
        else:
            owner_row = conn.execute(
                "SELECT 1 FROM user_profiles WHERE user_sub = ? AND profile_id = ?",
                (user_sub, payload.profile_id),
            ).fetchone() if user_sub else None
            if not owner_row and not has_valid_claim:
                raise HTTPException(status_code=403, detail="Profile claim token or Google-linked ownership is required")
            conn.execute(
                """
                INSERT INTO public_profiles (username, profile_id, email, display_name, bio, avatar_url, created_at, updated_at, is_public)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    username,
                    payload.profile_id,
                    email,
                    payload.display_name or profile.get("display_name"),
                    payload.bio,
                    (user or {}).get("picture"),
                    updated_at,
                    updated_at,
                ),
            )
            if user_sub:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO user_profiles (user_sub, profile_id, linked_at)
                    VALUES (?, ?, ?)
                    """,
                    (user_sub, payload.profile_id, updated_at),
                )
        row = conn.execute(
            "SELECT * FROM public_profiles WHERE username = ?",
            (username,),
        ).fetchone()
    return {
        "status": "ok",
        "public_profile": public_profile_payload(row, viewer_owns_profile(payload.profile_id, request)),
    }


@app.get("/api/v1/user/profile-settings/{profile_id}")
def get_owner_profile_settings(profile_id: str, request: Request) -> dict[str, Any]:
    require_linked_profile_owner(profile_id, request)
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM public_profiles WHERE profile_id = ?",
            (profile_id,),
        ).fetchone()
    return {
        "profile_id": profile_id,
        "username": row["username"] if row else None,
        "is_public": bool(row["is_public"]) if row else False,
        "public_url": f"{public_app_url()}/{row['username']}" if row else None,
    }


@app.patch("/api/v1/user/profile-settings/{profile_id}")
def update_owner_profile_settings(
    profile_id: str,
    payload: OwnerProfileSettingsInput,
    request: Request,
) -> dict[str, Any]:
    require_linked_profile_owner(profile_id, request)
    username = payload.username.strip().lower()
    with db() as conn:
        row = conn.execute(
            "SELECT username FROM public_profiles WHERE profile_id = ?",
            (profile_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Public profile has not been created")
        taken = conn.execute(
            "SELECT profile_id FROM public_profiles WHERE username = ? AND profile_id != ?",
            (username, profile_id),
        ).fetchone()
        if taken:
            raise HTTPException(status_code=409, detail="Username already taken")
        conn.execute(
            "UPDATE public_profiles SET username = ?, is_public = ?, updated_at = ? WHERE profile_id = ?",
            (username, int(payload.is_public), now_iso(), profile_id),
        )
    return {
        "status": "ok",
        "profile_id": profile_id,
        "username": username,
        "is_public": payload.is_public,
        "public_url": f"{public_app_url()}/{username}",
    }


@app.get("/api/v1/public-profiles")
def list_public_profiles(limit: int = 24) -> dict[str, Any]:
    limit = max(1, min(limit, 50))
    with db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM public_profiles
            WHERE is_public = 1
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return {"profiles": [public_profile_payload(row) for row in rows]}


@app.get("/api/v1/public-profiles/{username}")
def get_public_profile(username: str, request: Request) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM public_profiles WHERE username = ?",
            (username.strip().lower(),),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Public profile not found")
    owner = viewer_owns_profile(row["profile_id"], request)
    if not row["is_public"] and not owner:
        raise HTTPException(status_code=403, detail="Profil ini private")
    return public_profile_payload(row, owner)


@app.get("/api/v1/sky-news")
def sky_news() -> dict[str, Any]:
    posts = sky_news_rows()
    return {"updated_at": now_iso(), "disclaimer": "Catatan reflektif, bukan ramalan deterministik.", "posts": posts}


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
    if profile.get("questionnaire") and not profile.get("validation"):
        raise HTTPException(status_code=409, detail="Complete the questionnaire before requesting an interpretation")
    entitlement = enforce_ai_rate_limit(request, profile["profile_id"])
    llm_result = await call_llm(
        profile,
        language=payload.language,
        max_tokens_override=entitlement["limits"]["max_tokens"],
    )
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
    preview = guest_interpretation_view(llm_result["response"])
    return {
        "profile_id": profile["profile_id"],
        "interpretation_id": interpretation_id,
        "provider": llm_result["provider"],
        "model": llm_result["model"],
        "interpretation": preview,
        "confidence": profile["traits"]["confidence"],
        "requires_google_login": os.getenv("SELF_HOSTED_FULL_ACCESS", "").lower() not in {"1", "true", "yes", "on"},
    }


@app.get("/api/v1/interpretations/{interpretation_id}/full")
def full_interpretation(interpretation_id: str, request: Request) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute(
            """
            SELECT id, profile_id, provider, model, response_json, created_at
            FROM interpretations
            WHERE id = ?
            """,
            (interpretation_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Interpretation not found")
    require_profile_owner(row["profile_id"], request)
    profile = load_profile(row["profile_id"])
    response = normalize_personality_response(json.loads(row["response_json"]), profile)
    return {
        "profile_id": row["profile_id"],
        "interpretation_id": row["id"],
        "provider": row["provider"],
        "model": row["model"],
        "interpretation": response,
        "chart": profile.get("chart"),
        "precision": profile.get("precision"),
        "created_at": row["created_at"],
    }


@app.post("/api/v1/interpretation/ask")
async def ask_interpretation_detail(payload: DetailedQuestionInput, request: Request) -> dict[str, Any]:
    profile = load_profile(payload.profile_id)
    require_profile_owner(profile["profile_id"], request)
    entitlement = enforce_ai_rate_limit(request, profile["profile_id"])
    llm_result = await call_llm(
        profile,
        language=payload.language,
        question=payload.question,
        max_tokens_override=entitlement["limits"]["max_tokens"],
    )
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
def submit_feedback(payload: FeedbackInput, request: Request) -> dict[str, Any]:
    enforce_public_write_rate_limit(request, "feedback", minute_limit=10, day_limit=100)
    user_sub = None
    if payload.source == "accuracy":
        if not payload.profile_id:
            raise HTTPException(status_code=422, detail="profile_id is required for accuracy feedback")
        user = require_linked_profile_owner(payload.profile_id, request)
        user_sub = str((user or {}).get("sub") or (user or {}).get("email") or "")
        if payload.interpretation_id:
            with db() as conn:
                matches_profile = conn.execute(
                    "SELECT 1 FROM interpretations WHERE id = ? AND profile_id = ?",
                    (payload.interpretation_id, payload.profile_id),
                ).fetchone()
            if not matches_profile:
                raise HTTPException(status_code=422, detail="interpretation_id does not belong to profile_id")
    feedback_id = str(uuid.uuid4())
    with db() as conn:
        conn.execute(
            """
            INSERT INTO feedback (id, profile_id, interpretation_id, rating, message, source, user_sub, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                feedback_id,
                payload.profile_id,
                payload.interpretation_id,
                payload.rating,
                payload.message,
                payload.source,
                user_sub,
                now_iso(),
            ),
        )
    return {"status": "ok", "feedback_id": feedback_id}


@app.get("/api/v1/user/profiles/{profile_id}/feedback/accuracy")
def get_accuracy_feedback(profile_id: str, request: Request) -> dict[str, Any]:
    require_linked_profile_owner(profile_id, request)
    with db() as conn:
        row = conn.execute(
            """
            SELECT id, interpretation_id, rating, message, created_at
            FROM feedback
            WHERE profile_id = ? AND source = 'accuracy'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (profile_id,),
        ).fetchone()
    return {"feedback": dict(row) if row else None}


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
    response = RedirectResponse("/admin/dashboard/overview", status_code=303)
    response.set_cookie(
        ADMIN_COOKIE_NAME,
        admin_session_token(),
        httponly=True,
        samesite="lax",
        secure=secure_cookie(request),
        path="/",
        max_age=session_max_age("ADMIN_SESSION_MAX_AGE_SECONDS", 60 * 60 * 8),
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


@app.get("/api/v1/admin/entitlements")
def list_admin_entitlements(_admin: bool = Depends(require_admin)) -> dict[str, Any]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM entitlements
            ORDER BY updated_at DESC
            LIMIT 100
            """
        ).fetchall()
    return {
        "entitlements": [
            {
                "subject_type": row["subject_type"],
                "subject_id": row["subject_id"],
                "plan": row["plan"],
                "status": row["status"],
                "limits": merge_entitlement_limits(row["plan"], row["limits_json"]),
                "source": row["source"],
                "external_id": row["external_id"],
                "current_period_end": row["current_period_end"],
                "active": entitlement_row_is_active(row),
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]
    }


@app.post("/api/v1/admin/entitlements")
def upsert_admin_entitlement(payload: EntitlementInput, _admin: bool = Depends(require_admin)) -> dict[str, Any]:
    return {"status": "ok", "entitlement": save_entitlement(payload)}


@app.post("/api/v1/internal/entitlement")
def upsert_internal_entitlement(payload: EntitlementInput, request: Request) -> dict[str, Any]:
    require_entitlement_secret(request)
    return {"status": "ok", "entitlement": save_entitlement(payload)}


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
        return RedirectResponse("/admin/dashboard/news/edit", status_code=303)
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
    return RedirectResponse("/admin/dashboard/news", status_code=303)


@app.post("/admin/sky-news/delete")
async def admin_sky_news_delete_form(request: Request) -> RedirectResponse:
    require_admin(request)
    form = await request.form()
    post_id = str(form.get("id") or "").strip()
    if post_id:
        with db() as conn:
            conn.execute("DELETE FROM sky_posts WHERE id = ?", (post_id,))
    return RedirectResponse("/admin/dashboard/news", status_code=303)


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
        return RedirectResponse("/admin/dashboard/calendar/edit", status_code=303)
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
    return RedirectResponse("/admin/dashboard/calendar", status_code=303)


@app.post("/admin/sky-calendar/delete")
async def admin_sky_calendar_delete_form(request: Request) -> RedirectResponse:
    require_admin(request)
    form = await request.form()
    event_id = str(form.get("id") or "").strip()
    if event_id:
        with db() as conn:
            conn.execute("DELETE FROM astrology_calendar WHERE id = ?", (event_id,))
    return RedirectResponse("/admin/dashboard/calendar", status_code=303)


def json_script_payload(value: Any) -> str:
    return (
        json.dumps(value, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("'", "\\u0027")
    )


ADMIN_DASHBOARD_CSS = """
:root { color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, sans-serif; color: #2f2938; background: #f5f2ea; }
* { box-sizing: border-box; }
body { margin: 0; min-height: 100vh; }
a { color: inherit; }
.admin-app { min-height: 100vh; display: grid; grid-template-columns: 232px minmax(0, 1fr); }
.sidebar { position: sticky; top: 0; height: 100vh; padding: 24px 16px; background: #30273d; color: #fffdf7; display: flex; flex-direction: column; }
.brand { display: flex; align-items: center; gap: 10px; margin: 0 8px 28px; font-weight: 900; text-decoration: none; }
.brand-mark { width: 34px; height: 34px; display: grid; place-items: center; border-radius: 11px; background: #f5bd6b; color: #30273d; }
.side-nav { display: grid; gap: 5px; }
.side-nav a { padding: 10px 12px; border-radius: 11px; color: #d9d1e2; font-weight: 700; text-decoration: none; }
.side-nav a:hover, .side-nav a.active { color: #30273d; background: #fffdf7; }
.sidebar small { margin-top: auto; padding: 12px; color: #aaa0b4; }
.workspace { min-width: 0; }
.topbar { min-height: 70px; padding: 14px clamp(18px, 4vw, 44px); border-bottom: 1px solid #ddd8cf; background: rgba(255,253,247,.9); display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.topbar strong { font-size: .9rem; }
.topbar a { color: #635b6f; font-size: .9rem; text-decoration: none; }
.content { width: min(1120px, 100%); padding: 36px clamp(18px, 4vw, 44px) 60px; }
.page-head { display: flex; justify-content: space-between; align-items: end; gap: 18px; margin-bottom: 26px; }
.eyebrow { margin: 0 0 6px; color: #6759db; font-size: .72rem; font-weight: 900; letter-spacing: .12em; text-transform: uppercase; }
h1 { margin: 0; font-size: clamp(2rem, 5vw, 3.5rem); letter-spacing: -.055em; line-height: .95; }
h2 { margin: 0; letter-spacing: -.03em; }
.muted { color: #736b7c; }
.button { display: inline-flex; justify-content: center; align-items: center; gap: 7px; min-height: 40px; border: 0; border-radius: 10px; padding: 9px 14px; background: #5f54dc; color: white; font: inherit; font-weight: 800; text-decoration: none; cursor: pointer; }
.button.secondary { border: 1px solid #d7d1c8; background: #fffdf7; color: #30273d; }
.button.danger { background: #fff0ea; color: #a44327; }
.stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 26px; }
.stat, .panel { border: 1px solid #ded9d1; border-radius: 16px; background: #fffdf7; box-shadow: 0 8px 28px rgba(48,39,61,.05); }
.stat { padding: 18px; }
.stat span { color: #736b7c; font-size: .84rem; }
.stat strong { display: block; margin-top: 7px; font-size: 1.9rem; letter-spacing: -.04em; }
.panel { margin-bottom: 16px; overflow: hidden; }
.panel-pad { padding: 20px; }
.panel-head { padding: 17px 20px; border-bottom: 1px solid #e5e0d8; display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 13px 16px; border-bottom: 1px solid #ebe7df; text-align: left; vertical-align: top; }
th { color: #736b7c; font-size: .74rem; text-transform: uppercase; letter-spacing: .06em; }
tr:last-child td { border-bottom: 0; }
.actions { display: flex; justify-content: flex-end; gap: 7px; }
.actions .button { min-height: 34px; padding: 6px 10px; font-size: .82rem; }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
label { display: grid; gap: 7px; color: #453d4d; font-size: .86rem; font-weight: 800; }
label.wide { grid-column: 1 / -1; }
input, select, textarea { width: 100%; border: 1px solid #d8d2ca; border-radius: 11px; padding: 11px 12px; background: white; color: #30273d; font: inherit; }
textarea { min-height: 150px; resize: vertical; line-height: 1.5; }
.form-actions { display: flex; gap: 10px; margin-top: 18px; }
.config-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); margin: 0; }
.config-list div { padding: 16px 20px; border-bottom: 1px solid #ebe7df; }
.config-list div:nth-child(odd) { border-right: 1px solid #ebe7df; }
.config-list dt { margin-bottom: 5px; color: #736b7c; font-size: .75rem; font-weight: 800; text-transform: uppercase; letter-spacing: .05em; }
.config-list dd { margin: 0; overflow-wrap: anywhere; font-weight: 750; }
.config-view-actions { display: flex; gap: 10px; padding: 18px 20px; }
.feedback { padding: 18px 20px; }
.feedback + .feedback { border-top: 1px solid #e5e0d8; }
.feedback-head { display: flex; justify-content: space-between; gap: 12px; }
.stars { color: #d98c27; letter-spacing: .08em; }
details.config { border-bottom: 1px solid #e5e0d8; }
details.config:last-child { border-bottom: 0; }
details.config > summary { padding: 18px 20px; cursor: pointer; font-weight: 900; list-style-position: inside; }
details.config > div { padding: 0 20px 20px; }
pre { max-height: 360px; overflow: auto; white-space: pre-wrap; font: .78rem/1.5 ui-monospace, SFMono-Regular, Menlo, monospace; }
.toolbar { display: flex; gap: 10px; margin-bottom: 16px; }
.toolbar input { flex: 1; }
.mobile-nav { display: none; }
@media (max-width: 800px) {
  .admin-app { display: block; }
  .sidebar { position: static; height: auto; padding: 14px 18px; flex-direction: row; align-items: center; }
  .brand { margin: 0; }
  .side-nav, .sidebar small { display: none; }
  .mobile-nav { display: block; margin-left: auto; width: auto; }
  .stats, .form-grid { grid-template-columns: 1fr; }
  .config-list { grid-template-columns: 1fr; }
  .config-list div:nth-child(odd) { border-right: 0; }
  label.wide { grid-column: auto; }
  .page-head, .feedback-head { align-items: start; flex-direction: column; }
  .topbar { display: none; }
}
"""


ADMIN_DASHBOARD_NAV = (
    ("overview", "Ringkasan"),
    ("feedback", "Feedback"),
    ("news", "Berita Langit"),
    ("calendar", "Kalender"),
    ("activity", "Aktivitas"),
    ("settings", "Pengaturan"),
)


def admin_dashboard_shell(section: str, title: str, subtitle: str, content: str, script: str = "") -> str:
    active_section = section.split("/", 1)[0]
    nav = "".join(
        f'<a class="{"active" if key == active_section else ""}" href="/admin/dashboard/{key}">{label}</a>'
        for key, label in ADMIN_DASHBOARD_NAV
    )
    mobile_options = "".join(
        f'<option value="{key}" {"selected" if key == active_section else ""}>{label}</option>'
        for key, label in ADMIN_DASHBOARD_NAV
    )
    return f"""
    <!doctype html>
    <html lang="id">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>{html.escape(title)} · Hermex Admin</title>
        <style>{ADMIN_DASHBOARD_CSS}</style>
      </head>
      <body>
        <div class="admin-app">
          <aside class="sidebar">
            <a class="brand" href="/admin/dashboard/overview"><span class="brand-mark">✦</span> Hermex Admin</a>
            <nav class="side-nav" aria-label="Navigasi admin">{nav}</nav>
            <select class="mobile-nav" aria-label="Buka halaman admin" onchange="location.href='/admin/dashboard/'+this.value">{mobile_options}</select>
            <small>Panel internal Hermex</small>
          </aside>
          <div class="workspace">
            <header class="topbar"><strong>hermex.fun / admin</strong><a href="/">Lihat situs ↗</a></header>
            <main class="content">
              <header class="page-head">
                <div><p class="eyebrow">Dashboard</p><h1>{html.escape(title)}</h1><p class="muted">{html.escape(subtitle)}</p></div>
              </header>
              {content}
            </main>
          </div>
        </div>
        {script}
      </body>
    </html>
    """


def admin_activity_cards(guests: list[dict[str, Any]]) -> str:
    cards = []
    for guest in guests:
        latest = guest.get("latest_interpretation")
        prompt = json.dumps(latest["request_payload"], indent=2, ensure_ascii=False) if latest else "Belum ada prompt AI."
        response = json.dumps(latest["response"], indent=2, ensure_ascii=False) if latest else "Belum ada respons AI."
        cards.append(
            f"""
            <article class="panel activity-card" data-search="{html.escape(' '.join(str(value or '') for value in (guest.get('display_name'), guest.get('birth_place'), latest.get('provider') if latest else '', latest.get('model') if latest else '')))}">
              <div class="panel-head"><div><strong>{html.escape(guest.get('display_name') or 'Tamu')}</strong><div class="muted">{html.escape(guest.get('birth_place') or '-')} · {html.escape(guest.get('created_at') or '')}</div></div><span>{html.escape(guest.get('birth_date') or '')}</span></div>
              <div class="panel-pad"><details><summary>Data permintaan AI</summary><pre>{html.escape(prompt)}</pre></details><details><summary>Respons terakhir</summary><pre>{html.escape(response)}</pre></details></div>
            </article>
            """
        )
    return "".join(cards) or '<div class="panel panel-pad">Belum ada aktivitas.</div>'


@app.get("/admin/dashboard", include_in_schema=False)
def admin_dashboard_redirect(request: Request) -> RedirectResponse:
    if not is_admin_request(request):
        return RedirectResponse("/admin/login", status_code=303)
    return RedirectResponse("/admin/dashboard/overview", status_code=303)


@app.get("/admin/dashboard/{section:path}", response_class=HTMLResponse, include_in_schema=False)
def admin_dashboard_page(request: Request, section: str, id: str = "", limit: int = 50, mode: str = "view") -> str:
    if not is_admin_request(request):
        return login_page()

    allowed = {"overview", "feedback", "news", "news/edit", "calendar", "calendar/edit", "activity", "settings"}
    if section not in allowed:
        raise HTTPException(status_code=404, detail="Admin page not found")

    if section == "overview":
        guests = guest_history(limit=min(max(limit, 1), 50), _admin=True)["guests"]
        feedback_rows = admin_feedback_history()
        average_rating = round(sum(row["rating"] for row in feedback_rows) / len(feedback_rows), 1) if feedback_rows else 0
        config = public_llm_config()
        recent = "".join(
            f'<tr><td>{html.escape(item.get("display_name") or "Tamu")}</td><td>{html.escape(item.get("birth_place") or "-")}</td><td>{html.escape(item.get("created_at") or "")}</td></tr>'
            for item in guests[:6]
        ) or '<tr><td colspan="3">Belum ada aktivitas.</td></tr>'
        content = f"""
        <section class="stats">
          <article class="stat"><span>Analisis terbaru</span><strong>{len(guests)}</strong></article>
          <article class="stat"><span>Feedback</span><strong>{len(feedback_rows)}</strong></article>
          <article class="stat"><span>Rating rata-rata</span><strong>{average_rating or '-'}</strong></article>
          <article class="stat"><span>Model aktif</span><strong>{html.escape(config['model'])}</strong></article>
        </section>
        <section class="panel"><div class="panel-head"><h2>Aktivitas terbaru</h2><a class="button secondary" href="/admin/dashboard/activity">Lihat semua</a></div><div class="table-wrap"><table><thead><tr><th>Nama</th><th>Lokasi lahir</th><th>Waktu</th></tr></thead><tbody>{recent}</tbody></table></div></section>
        """
        return admin_dashboard_shell(section, "Ringkasan", "Angka penting dan aktivitas terbaru.", content)

    if section == "feedback":
        rows = admin_feedback_history()
        cards = "".join(
            f'<article class="feedback"><div class="feedback-head"><div><strong>{html.escape(row.get("display_name") or "Tamu")}</strong><div class="muted">{html.escape(row.get("birth_place") or "-")} · {html.escape(row.get("created_at") or "")}</div></div><span class="stars">{"★" * int(row["rating"])}{"☆" * (5 - int(row["rating"]))}</span></div><p>{html.escape(row.get("message") or "Tanpa catatan tambahan.")}</p></article>'
            for row in rows
        ) or '<div class="panel-pad">Belum ada feedback.</div>'
        return admin_dashboard_shell(section, "Feedback", "Ulasan akurasi dari pengguna.", f'<section class="panel">{cards}</section>')

    if section == "news":
        rows = sky_news_rows()
        table_rows = "".join(
            f'<tr><td><strong>{html.escape(row.get("title") or "")}</strong><div class="muted">/{html.escape(row.get("slug") or "")}</div></td><td>{html.escape(row.get("tag") or "-")}</td><td>{html.escape(row.get("updated_at") or "")}</td><td><div class="actions"><a class="button secondary" href="/admin/dashboard/news/edit?id={urllib.parse.quote(row.get("id") or "")}">Edit</a><form method="post" action="/admin/sky-news/delete" onsubmit="return confirm(\'Hapus artikel ini?\')"><input type="hidden" name="id" value="{html.escape(row.get("id") or "")}"/><button class="button danger" type="submit">Hapus</button></form></div></td></tr>'
            for row in rows
        ) or '<tr><td colspan="4">Belum ada artikel.</td></tr>'
        content = f'<section class="panel"><div class="panel-head"><h2>Semua artikel</h2><a class="button" href="/admin/dashboard/news/edit">+ Artikel baru</a></div><div class="table-wrap"><table><thead><tr><th>Artikel</th><th>Tag</th><th>Diperbarui</th><th></th></tr></thead><tbody>{table_rows}</tbody></table></div></section>'
        return admin_dashboard_shell(section, "Berita Langit", "Kelola daftar artikel tanpa form panjang di halaman ini.", content)

    if section == "news/edit":
        item = next((row for row in sky_news_rows() if row.get("id") == id), {})
        content = f"""
        <section class="panel panel-pad"><form method="post" action="/admin/sky-news/save">
          <input type="hidden" name="id" value="{html.escape(item.get('id') or '')}" />
          <div class="form-grid">
            <label>Slug<input name="slug" required value="{html.escape(item.get('slug') or '')}" placeholder="judul-artikel" /></label>
            <label>Tag<input name="tag" value="{html.escape(item.get('tag') or '')}" placeholder="Mars–Jupiter" /></label>
            <label class="wide">Judul<input name="title" required value="{html.escape(item.get('title') or '')}" /></label>
            <label class="wide">Ringkasan<textarea name="summary" required>{html.escape(item.get('summary') or '')}</textarea></label>
            <label class="wide">Isi artikel<textarea name="body" required style="min-height:360px">{html.escape(item.get('body') or '')}</textarea></label>
          </div><div class="form-actions"><button class="button" type="submit">Simpan artikel</button><a class="button secondary" href="/admin/dashboard/news">Batal</a></div>
        </form></section>
        """
        return admin_dashboard_shell("news", "Edit artikel" if item else "Artikel baru", "Satu halaman khusus untuk satu artikel.", content)

    if section == "calendar":
        rows = astrology_calendar_rows()
        table_rows = "".join(
            f'<tr><td>{html.escape(row.get("event_date") or "")}</td><td><strong>{html.escape(row.get("title") or "")}</strong><div class="muted">{html.escape(row.get("summary") or "")}</div></td><td>{html.escape(row.get("tag") or "-")}</td><td><div class="actions"><a class="button secondary" href="/admin/dashboard/calendar/edit?id={urllib.parse.quote(row.get("id") or "")}">Edit</a><form method="post" action="/admin/sky-calendar/delete" onsubmit="return confirm(\'Hapus agenda ini?\')"><input type="hidden" name="id" value="{html.escape(row.get("id") or "")}"/><button class="button danger" type="submit">Hapus</button></form></div></td></tr>'
            for row in rows
        ) or '<tr><td colspan="4">Belum ada agenda.</td></tr>'
        content = f'<section class="panel"><div class="panel-head"><h2>Semua agenda</h2><a class="button" href="/admin/dashboard/calendar/edit">+ Agenda baru</a></div><div class="table-wrap"><table><thead><tr><th>Tanggal</th><th>Agenda</th><th>Tag</th><th></th></tr></thead><tbody>{table_rows}</tbody></table></div></section>'
        return admin_dashboard_shell(section, "Kalender Langit", "Atur agenda bulanan dari halaman terpisah.", content)

    if section == "calendar/edit":
        item = next((row for row in astrology_calendar_rows() if row.get("id") == id), {})
        content = f"""
        <section class="panel panel-pad"><form method="post" action="/admin/sky-calendar/save">
          <input type="hidden" name="id" value="{html.escape(item.get('id') or '')}" />
          <div class="form-grid">
            <label>Tanggal<input name="event_date" type="date" required value="{html.escape(item.get('event_date') or '')}" /></label>
            <label>Tag<input name="tag" required value="{html.escape(item.get('tag') or '')}" /></label>
            <label class="wide">Judul<input name="title" required value="{html.escape(item.get('title') or '')}" /></label>
            <label class="wide">Ringkasan<textarea name="summary" required>{html.escape(item.get('summary') or '')}</textarea></label>
          </div><div class="form-actions"><button class="button" type="submit">Simpan agenda</button><a class="button secondary" href="/admin/dashboard/calendar">Batal</a></div>
        </form></section>
        """
        return admin_dashboard_shell("calendar", "Edit agenda" if item else "Agenda baru", "Satu halaman khusus untuk satu agenda.", content)

    if section == "activity":
        guests = guest_history(limit=min(max(limit, 1), 200), _admin=True)["guests"]
        payload = json_script_payload(guests)
        content = f'<div class="toolbar"><input id="activity-search" placeholder="Cari nama, lokasi, provider, atau model"/><button class="button secondary" id="export-guests" type="button">Unduh JSON</button></div>{admin_activity_cards(guests)}'
        script = f"""<script id="guest-data" type="application/json">{payload}</script><script>
        document.getElementById('activity-search').addEventListener('input', (event) => {{ const query = event.target.value.toLowerCase(); document.querySelectorAll('.activity-card').forEach((card) => card.hidden = !card.dataset.search.toLowerCase().includes(query)); }});
        document.getElementById('export-guests').addEventListener('click', () => {{ const blob = new Blob([JSON.stringify(JSON.parse(document.getElementById('guest-data').textContent), null, 2)], {{type:'application/json'}}); const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href=url; link.download=`hermex-activity-${{new Date().toISOString().slice(0,10)}}.json`; link.click(); URL.revokeObjectURL(url); }});
        </script>"""
        return admin_dashboard_shell(section, "Aktivitas", "Riwayat analisis dan keluaran AI.", content, script)

    private_config = get_llm_config()
    config = public_llm_config(private_config)
    current_prompt = get_setting("llm_system_prompt", os.getenv("LLM_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT))
    if mode != "edit":
        values = (
            ("Provider", "OpenAI-compatible" if config["provider"] == "openai_compat" else "Local fallback"),
            ("Base URL", config["base_url"] or "Belum disetel"),
            ("API key", masked_secret_label(private_config["api_key"])),
            ("Model", config["model"]),
            ("Temperature", str(config["temperature"])),
            ("Token maksimum", str(config["max_tokens"])),
            ("Permintaan / menit", str(config["requests_per_minute"])),
            ("Permintaan / hari", str(config["requests_per_day"])),
        )
        config_rows = "".join(
            f"<div><dt>{html.escape(label)}</dt><dd>{html.escape(value)}</dd></div>"
            for label, value in values
        )
        content = f"""
        <section class="panel">
          <div class="panel-head"><h2>Koneksi model</h2><span class="muted">Mode lihat</span></div>
          <dl class="config-list">{config_rows}</dl>
          <div class="config-view-actions"><a class="button" href="/admin/dashboard/settings?mode=edit">Edit pengaturan</a></div>
        </section>
        <section class="panel">
          <div class="panel-head"><h2>Prompt sistem</h2><span class="muted">Instruksi analisis AI</span></div>
          <div class="panel-pad"><pre>{html.escape(current_prompt)}</pre></div>
        </section>
        """
        return admin_dashboard_shell(section, "Pengaturan", "Lihat konfigurasi aktif. Masuk mode edit hanya saat perlu mengubahnya.", content)

    provider_options = "".join(
        f'<option value="{key}" {"selected" if config["provider"] == key else ""}>{label}</option>'
        for key, label in (("openai_compat", "OpenAI-compatible"), ("local_fallback", "Local fallback"))
    )
    content = f"""
    <section class="panel">
      <div class="panel-head"><h2>Edit koneksi model</h2><span class="muted">API key tersimpan tidak pernah ditampilkan</span></div><div class="panel-pad">
        <div class="form-grid">
          <label>Provider<select id="provider">{provider_options}</select></label><label>Base URL<input id="base-url" value="{html.escape(config['base_url'])}" /></label>
          <label>API key<input id="api-key" type="password" value="" autocomplete="new-password" placeholder="{'Kosongkan untuk mempertahankan API key' if config['has_api_key'] else 'Tempel API key'}" /></label>
          <label>Model<input id="model" value="{html.escape(config['model'])}" /></label>
          <label>Temperature<input id="temperature" type="number" min="0" max="2" step="0.1" value="{config['temperature']}" /></label>
          <label>Token maksimum<input id="max-tokens" type="number" min="128" max="8000" value="{config['max_tokens']}" /></label>
          <label>Permintaan / menit<input id="rpm" type="number" min="1" max="300" value="{config['requests_per_minute']}" /></label>
          <label>Permintaan / hari<input id="rpd" type="number" min="1" max="10000" value="{config['requests_per_day']}" /></label>
        </div><div class="form-actions"><button class="button" id="save-provider" type="button">Simpan koneksi</button><button class="button secondary" id="sync-models" type="button">Cek model</button><a class="button secondary" href="/admin/dashboard/settings">Batal</a><span id="provider-status"></span></div>
      </div>
    </section>
    <section class="panel">
      <div class="panel-head"><h2>Edit prompt sistem</h2><span class="muted">Instruksi analisis AI</span></div>
      <div class="panel-pad"><label>Prompt<textarea id="prompt" style="min-height:360px">{html.escape(current_prompt)}</textarea></label><div class="form-actions"><button class="button" id="save-prompt" type="button">Simpan prompt</button><span id="prompt-status"></span></div></div>
    </section>
    """
    script = """<script>
    const value = (id) => document.getElementById(id).value;
    document.getElementById('save-provider').addEventListener('click', async () => {
      const status = document.getElementById('provider-status'); status.textContent = 'Menyimpan…';
      const response = await fetch('/api/v1/admin/llm-config', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({provider:value('provider'), base_url:value('base-url'), api_key:value('api-key'), model:value('model'), temperature:Number(value('temperature')), max_tokens:Number(value('max-tokens')), requests_per_minute:Number(value('rpm')), requests_per_day:Number(value('rpd'))})});
      status.textContent = response.ok ? 'Tersimpan' : await response.text(); if (response.ok) location.href='/admin/dashboard/settings';
    });
    document.getElementById('sync-models').addEventListener('click', async () => {
      const status = document.getElementById('provider-status'); status.textContent = 'Memeriksa…';
      const response = await fetch('/api/v1/admin/llm-models', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({base_url:value('base-url'), api_key:value('api-key')})});
      if (!response.ok) { status.textContent=await response.text(); return; } const data=await response.json(); status.textContent=`${(data.models||[]).length} model tersedia`;
    });
    document.getElementById('save-prompt').addEventListener('click', async () => {
      const status=document.getElementById('prompt-status'); status.textContent='Menyimpan…'; const response=await fetch('/api/v1/admin/prompt',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:value('prompt')})}); status.textContent=response.ok?'Tersimpan':await response.text();
    });
    </script>"""
    return admin_dashboard_shell(section, "Edit pengaturan", "Ubah hanya nilai yang diperlukan. API key kosong berarti tetap memakai key tersimpan.", content, script)


@app.get("/api/v1/roadmap/{profile_id}")
def roadmap(profile_id: str) -> dict[str, Any]:
    profile = load_profile(profile_id)
    return {"profile_id": profile_id, "roadmap": profile["roadmap_preview"], "progress_percentage": 0}
