import os
import asyncio
import copy
import json
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from app import main


class PersonalityFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        main.RATE_LIMIT_BUCKETS.clear()
        self.birth = main.BirthProfileInput(
            birth_date=date(1997, 6, 19),
            birth_place="Jakarta, Indonesia",
            latitude=-6.2,
            longitude=106.816666,
            timezone="Asia/Jakarta",
        )

    def test_missing_time_uses_midnight_and_builds_safe_questionnaire(self) -> None:
        chart = main.compute_chart(self.birth)
        signals = main.derive_personality_signals(chart)
        questionnaire = main.build_questionnaire(signals)

        self.assertEqual(chart["location"]["effective_birth_time"], "00:00")
        self.assertTrue(chart["location"]["birth_time_assumed"])
        self.assertEqual(chart["houses"]["precision"], "reduced_assumed_midnight")
        self.assertEqual(
            set(signals),
            {
                "sun",
                "moon",
                "ascendant",
                "chart_ruler",
                "mercury",
                "venus",
                "mars",
                "major_aspects",
                "angular_and_dominant_houses",
                "overall_pattern",
            },
        )
        self.assertEqual(len(questionnaire["questions"]), 10)
        self.assertTrue(
            all(
                main.QUESTIONNAIRE_WORD_MIN
                <= len(item["prompt"].split())
                <= main.QUESTIONNAIRE_WORD_MAX
                for item in questionnaire["questions"]
            )
        )
        public_text = " ".join(item["prompt"].lower() for item in questionnaire["questions"])
        self.assertNotIn("saya", public_text)
        self.assertTrue(all("aku" in item["prompt"].lower() for item in questionnaire["questions"]))
        for forbidden in ("astrologi", "zodiak", "planet", "rumah", "aspek", "chart", "kosmik"):
            self.assertNotIn(forbidden, public_text)

        profile = {"questionnaire": questionnaire}
        answers = {item["id"]: 3 for item in questionnaire["questions"]}
        self.assertEqual(main.validate_questionnaire_answers(profile, answers), answers)
        answers["q_01"] = 6
        with self.assertRaises(HTTPException):
            main.validate_questionnaire_answers(profile, answers)

    def test_questionnaire_changes_with_internal_personality_signals(self) -> None:
        signals = main.derive_personality_signals(main.compute_chart(self.birth))
        changed = copy.deepcopy(signals)
        changed["sun"]["position"]["element"] = "water"
        changed["moon"]["position"]["element"] = "earth"
        changed["ascendant"]["position"]["modality"] = "cardinal"
        changed["angular_and_dominant_houses"]["dominant_houses"] = [{"house": 4, "count": 4}]
        changed["overall_pattern"]["dominant_element"] = "fire"
        changed["overall_pattern"]["dominant_modality"] = "fixed"

        original = main.build_questionnaire(signals)
        personalized = main.build_questionnaire(changed)

        self.assertNotEqual(
            [item["prompt"] for item in original["questions"]],
            [item["prompt"] for item in personalized["questions"]],
        )
        self.assertTrue(main.questionnaire_is_safe(original))
        self.assertTrue(main.questionnaire_is_safe(personalized))

    def test_questionnaire_pronouns_match_whole_words(self) -> None:
        questionnaire = main.build_questionnaire(main.derive_personality_signals(main.compute_chart(self.birth)))
        questionnaire["questions"][0]["prompt"] = "Aku menjaga orang yang aku sayang ketika keadaan sulit."
        self.assertTrue(main.questionnaire_is_safe(questionnaire))

        questionnaire["questions"][0]["prompt"] = "Saya menjaga orang yang saya sayang ketika keadaan sulit."
        self.assertFalse(main.questionnaire_is_safe(questionnaire))

    def test_guest_preview_does_not_include_full_analysis(self) -> None:
        response = {
            "preview_summary": "Ringkas",
            "highlights": ["A", "B", "C"],
            "username_suggestions": ["satu", "dua", "tiga"],
            "full_analysis": {"core_identity": "private"},
        }
        preview = main.guest_interpretation_view(response)
        self.assertNotIn("full_analysis", preview)
        self.assertNotIn("private", str(preview))

    def test_admin_settings_never_render_full_api_key(self) -> None:
        secret = "sk-live-super-private-987654"
        config = {
            "provider": "openai_compat",
            "base_url": "https://llm.example/v1",
            "api_key": secret,
            "model": "test-model",
            "temperature": 0.4,
            "max_tokens": 700,
            "requests_per_minute": 6,
            "requests_per_day": 40,
        }
        request = Request({"type": "http", "method": "GET", "path": "/admin/dashboard/settings", "headers": []})
        with (
            patch.object(main, "is_admin_request", return_value=True),
            patch.object(main, "get_llm_config", return_value=config),
            patch.object(main, "get_setting", return_value="Prompt aman untuk pengujian."),
        ):
            view = main.admin_dashboard_page(request, "settings")
            edit = main.admin_dashboard_page(request, "settings", mode="edit")

        self.assertNotIn(secret, view)
        self.assertNotIn(secret, edit)
        self.assertIn(main.masked_secret_label(secret), view)
        self.assertNotIn('id="api-key"', view)
        self.assertIn('id="api-key" type="password" value=""', edit)

    def test_personality_response_unwraps_double_encoded_json_and_expands_sections(self) -> None:
        chart = main.compute_chart(self.birth)
        profile = {
            "profile_id": "profile-test",
            "traits": main.build_trait_profile(chart, time_unknown=True),
            "precision": {"caveat": "Jam lahir diasumsikan pukul 00.00."},
        }
        provider_payload = {
            "preview_summary": "Kamu teliti, hangat, dan mampu melihat hubungan antargagasan sebelum menentukan langkah.",
            "highlights": ["Teliti", "Hangat", "Terarah"],
            "username_suggestions": ["pembacajernih", "langkahtenang", "arahbaru"],
            "full_analysis": {"emotional_needs": "Kamu perlu waktu untuk memahami perasaan."},
        }
        wrapped = "```json\n" + json.dumps(json.dumps(provider_payload)) + "\n```"

        parsed = main.parse_llm_content(wrapped)
        normalized = main.normalize_personality_response(parsed, profile)

        self.assertEqual(normalized["preview_summary"], provider_payload["preview_summary"])
        self.assertNotIn("preview_summary", normalized["preview_summary"])
        self.assertTrue(
            all(len(paragraph.split()) >= 50 for paragraph in normalized["full_analysis"].values())
        )

    def test_identity_keywords_do_not_invent_missing_model_output(self) -> None:
        chart = main.compute_chart(self.birth)
        profile = {
            "profile_id": "profile-test",
            "traits": main.build_trait_profile(chart, time_unknown=True),
            "precision": {"caveat": None},
        }
        normalized = main.normalize_personality_response(
            {
                "identity_keywords": [
                    {"word": "Sangat Peka", "icon": "✨"},
                    {"word": "Jernih", "icon": "👁️"},
                ]
            },
            profile,
        )
        self.assertEqual(len(normalized["identity_keywords"]), 2)
        self.assertTrue(all(len(item["word"].split()) == 1 for item in normalized["identity_keywords"]))
        self.assertTrue(all(item["icon"] for item in normalized["identity_keywords"]))

    def test_truncated_json_recovers_complete_personality_fields(self) -> None:
        truncated = """{
          \"preview_summary\": \"Ringkasan yang dibuat model.\",
          \"highlights\": [\"Adaptif\", \"Teliti\", \"Mandiri\"],
          \"identity_keywords\": [{\"word\": \"Adaptif\", \"icon\": \"↗\"}],
          \"full_analysis\": {\"core_identity\": \"Bagian lengkap.\", \"emotional_needs\": \"terpotong
        """

        recovered = main.parse_llm_content(truncated)

        self.assertEqual(recovered["highlights"], ["Adaptif", "Teliti", "Mandiri"])
        self.assertEqual(recovered["identity_keywords"][0]["word"], "Adaptif")
        self.assertEqual(recovered["full_analysis"], {"core_identity": "Bagian lengkap."})

    def test_local_full_analysis_has_at_least_fifty_words_per_section(self) -> None:
        chart = main.compute_chart(self.birth)
        profile = {
            "traits": main.build_trait_profile(chart, time_unknown=True),
            "precision": {"caveat": "Jam lahir diasumsikan pukul 00.00."},
        }
        analysis = main.local_personality_response(profile, "id")["full_analysis"]
        self.assertTrue(all(len(paragraph.split()) >= 50 for paragraph in analysis.values()))

    def test_truncated_json_preview_is_shown_as_plain_text(self) -> None:
        chart = main.compute_chart(self.birth)
        profile = {
            "traits": main.build_trait_profile(chart, time_unknown=True),
            "precision": {"caveat": None},
        }
        normalized = main.normalize_personality_response(
            {"preview_summary": '{\n  "preview_summary": "Kamu teliti dan hangat saat membaca situasi'},
            profile,
        )
        self.assertEqual(normalized["preview_summary"], "Kamu teliti dan hangat saat membaca situasi")

    def test_questionnaire_generation_falls_back_without_provider(self) -> None:
        signals = main.derive_personality_signals(main.compute_chart(self.birth))
        with patch.dict(os.environ, {"LLM_PROVIDER": "local_fallback"}):
            questionnaire = asyncio.run(main.generate_questionnaire(signals))
        self.assertEqual(questionnaire, main.build_questionnaire(signals))
        self.assertTrue(main.questionnaire_is_safe(questionnaire))

    def test_questionnaire_generation_uses_configured_ai(self) -> None:
        prompts = [
            f"Aku melihat kebiasaan pribadiku lewat pernyataan reflektif nomor {index}."
            for index in range(1, 11)
        ]
        content = json.dumps({"questions": prompts})

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict:
                return {"choices": [{"message": {"content": content}}]}

        class FakeClient:
            def __init__(self, **_kwargs) -> None:
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args) -> None:
                return None

            async def post(self, *_args, **_kwargs) -> FakeResponse:
                return FakeResponse()

        signals = main.derive_personality_signals(main.compute_chart(self.birth))
        config = {
            "provider": "openai_compat",
            "base_url": "https://llm.example/v1",
            "api_key": "secret",
            "model": "test-model",
            "temperature": 0.2,
            "max_tokens": 700,
        }
        with patch.object(main, "get_llm_config", return_value=config), patch.object(main.httpx, "AsyncClient", FakeClient):
            questionnaire = asyncio.run(main.generate_questionnaire(signals))
        self.assertEqual([item["prompt"] for item in questionnaire["questions"]], prompts)

    def test_configured_llm_failure_never_returns_a_template(self) -> None:
        chart = main.compute_chart(self.birth)
        profile = {
            "profile_id": "profile-test",
            "birth_date": "1997-06-19",
            "chart": chart,
            "traits": main.build_trait_profile(chart, time_unknown=True),
            "questionnaire": {},
            "validation": {},
        }

        class FailingClient:
            def __init__(self, **_kwargs) -> None:
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args) -> None:
                return None

            async def post(self, *_args, **_kwargs):
                raise main.httpx.ConnectError("offline")

        config = {
            "provider": "openai_compat", "base_url": "https://llm.example/v1", "api_key": "secret",
            "model": "test-model", "temperature": 0.2, "max_tokens": 8000,
        }
        with patch.object(main, "get_llm_config", return_value=config), patch.object(main.httpx, "AsyncClient", FailingClient):
            with self.assertRaises(HTTPException) as error:
                asyncio.run(main.call_llm(profile))
        self.assertEqual(error.exception.status_code, 503)

    def test_hosted_admin_rejects_documented_defaults(self) -> None:
        with patch.dict(os.environ, {"ADMIN_USERNAME": "admin", "ADMIN_PASSWORD": "hermes-admin", "ADMIN_SESSION_SECRET": "hermex-local-admin-session"}):
            with patch.object(main, "is_local_public_app_url", return_value=False):
                with self.assertRaises(RuntimeError):
                    main.validate_hosted_admin_configuration()

    def test_seeded_article_is_not_overwritten_after_an_admin_edit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "articles.db"
            with patch.object(main, "DB_PATH", db_path):
                main.init_db()
                with main.db() as conn:
                    slug = main.default_sky_posts()[0]["slug"]
                    conn.execute("UPDATE sky_posts SET body = ? WHERE slug = ?", ("Catatan admin\n\n## Sumber\nTetap simpan ini.", slug))
                main.init_db()
                with main.db() as conn:
                    body = conn.execute("SELECT body FROM sky_posts WHERE slug = ?", (slug,)).fetchone()["body"]
            self.assertIn("Tetap simpan ini.", body)

    def test_current_sky_archive_is_seeded_by_default(self) -> None:
        expected = {
            "agustus-2025-ai-uranus-dan-gelembung",
            "september-2025-kimmel-dan-siklus-24-tahun",
            "oktober-2025-pencurian-louvre",
            "november-2025-cloudflare-dan-merkurius",
            "januari-2026-minneapolis-mars-pluto",
            "februari-2026-super-bowl-bad-bunny",
            "maret-2026-sora-ditutup",
            "april-2026-percobaan-serangan-dan-uranus",
            "mei-2026-ledakan-pabrik-kembang-api",
            "juni-2026-gempa-venezuela",
            "juli-2026-lindsey-graham",
        }
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "sky.db"
            with patch.object(main, "DB_PATH", db_path):
                main.init_db()
                with main.db() as conn:
                    seeded = {row[0] for row in conn.execute("SELECT slug FROM sky_posts")}
        self.assertTrue(expected.issubset(seeded))
        self.assertEqual(set(post["slug"] for post in main.default_sky_posts()), expected)

    def test_profile_owner_is_enforced_outside_self_hosted_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "test.db"
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "CREATE TABLE user_profiles (user_sub TEXT, profile_id TEXT, linked_at TEXT)"
                )
                conn.execute(
                    "INSERT INTO user_profiles VALUES ('google-1', 'profile-1', 'now')"
                )
            request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
            with (
                patch.object(main, "DB_PATH", db_path),
                patch.object(main, "read_google_session", return_value={"sub": "google-1"}),
                patch.dict(os.environ, {"SELF_HOSTED_FULL_ACCESS": "false"}),
            ):
                main.require_profile_owner("profile-1", request)
                with self.assertRaises(HTTPException) as error:
                    main.require_profile_owner("profile-2", request)
                self.assertEqual(error.exception.status_code, 403)

    def test_guest_api_returns_preview_only_and_full_route_is_gated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "api.db"
            with (
                patch.object(main, "DB_PATH", db_path),
                patch.dict(
                    os.environ,
                    {"LLM_PROVIDER": "local_fallback", "SELF_HOSTED_FULL_ACCESS": "false"},
                ),
                TestClient(main.app) as client,
            ):
                analyzed = client.post(
                    "/api/v1/birth/analyze",
                    json={
                        "birth_date": "1997-06-19",
                        "birth_place": "Jakarta, Indonesia",
                        "latitude": -6.2,
                        "longitude": 106.816666,
                        "timezone": "Asia/Jakarta",
                    },
                ).json()
                for private_key in ("chart", "personality_signals", "traits", "validation_questions"):
                    self.assertNotIn(private_key, analyzed)
                self.assertNotIn("questions", analyzed["questionnaire"])

                answers = {}
                current = analyzed["questionnaire"]["current_question"]
                answers[current["id"]] = 3
                for index in range(1, analyzed["questionnaire"]["count"]):
                    question_response = client.post(
                        "/api/v1/birth/question",
                        json={
                            "profile_id": analyzed["profile_id"],
                            "claim_token": analyzed["claim_token"],
                            "index": index,
                        },
                    )
                    self.assertEqual(question_response.status_code, 200)
                    question_payload = question_response.json()["questionnaire"]
                    self.assertNotIn("questions", question_payload)
                    self.assertEqual(question_payload["current_question"]["index"], index)
                    answers[question_payload["current_question"]["id"]] = 3
                public_text = " ".join(
                    client.post(
                        "/api/v1/birth/question",
                        json={
                            "profile_id": analyzed["profile_id"],
                            "claim_token": analyzed["claim_token"],
                            "index": index,
                        },
                    ).json()["questionnaire"]["current_question"]["prompt"].lower()
                    for index in range(analyzed["questionnaire"]["count"])
                )
                for forbidden in main.QUESTIONNAIRE_FORBIDDEN_TERMS:
                    self.assertNotIn(forbidden, public_text)

                invalid_question = client.post(
                    "/api/v1/birth/question",
                    json={"profile_id": analyzed["profile_id"], "claim_token": "x" * 20, "index": 1},
                )
                self.assertEqual(invalid_question.status_code, 403)
                invalid_validation = client.post(
                    "/api/v1/birth/validate",
                    json={"profile_id": analyzed["profile_id"], "claim_token": "x" * 20, "answers": answers},
                )
                self.assertEqual(invalid_validation.status_code, 403)
                validated = client.post(
                    "/api/v1/birth/validate",
                    json={
                        "profile_id": analyzed["profile_id"],
                        "claim_token": analyzed["claim_token"],
                        "answers": answers,
                    },
                )
                self.assertEqual(validated.status_code, 200)
                interpreted = client.post(
                    "/api/v1/interpretation",
                    json={"profile_id": analyzed["profile_id"], "language": "id"},
                )
                self.assertEqual(interpreted.status_code, 200)
                payload = interpreted.json()
                self.assertNotIn("full_analysis", payload["interpretation"])
                self.assertGreaterEqual(len(payload["interpretation"]["preview_summary"].split()), 60)

                full_path = f"/api/v1/interpretations/{payload['interpretation_id']}/full"
                self.assertEqual(client.get(full_path).status_code, 401)
                with patch.object(main, "read_google_session", return_value={"sub": "google-owner"}):
                    with main.db() as conn:
                        conn.execute(
                            "INSERT INTO user_profiles VALUES (?, ?, ?)",
                            ("google-owner", analyzed["profile_id"], "now"),
                        )
                    owner_full = client.get(full_path)
                    self.assertEqual(owner_full.status_code, 200)
                    self.assertIn("full_analysis", owner_full.json()["interpretation"])
                with patch.object(main, "read_google_session", return_value={"sub": "google-other"}):
                    self.assertEqual(client.get(full_path).status_code, 403)
                with patch.dict(os.environ, {"SELF_HOSTED_FULL_ACCESS": "true"}):
                    full = client.get(full_path)
                self.assertEqual(full.status_code, 200)
                self.assertIn("full_analysis", full.json()["interpretation"])
                self.assertIn("chart", full.json())

    def test_owner_settings_visibility_slug_and_accuracy_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "owner.db"
            profile = {
                "profile_id": "profile-owner",
                "display_name": "Owner",
                "traits": {
                    "dominant_element": "air",
                    "confidence": {"score": 0.7, "label": "high"},
                    "interests": [],
                    "talents": [],
                    "career_themes": [],
                },
                "chart": {"planets": {}, "houses": {"planet_houses": {}}, "aspects": []},
                "created_at": "2026-08-01T00:00:00+00:00",
            }
            with patch.object(main, "DB_PATH", db_path):
                main.init_db()
                with main.db() as conn:
                    conn.execute(
                        "INSERT INTO profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            "profile-owner", "Owner", "1997-06-19", None, "Jakarta", None,
                            None, "Asia/Jakarta", 1, json.dumps(profile), profile["created_at"],
                        ),
                    )
                    conn.execute(
                        "INSERT INTO user_profiles VALUES (?, ?, ?)",
                        ("google-owner", "profile-owner", profile["created_at"]),
                    )
                    conn.execute(
                        """
                        INSERT INTO public_profiles
                        (username, profile_id, email, display_name, bio, avatar_url, created_at, updated_at, is_public)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                        """,
                        (
                            "ownerlama", "profile-owner", "owner@example.com", "Owner", None,
                            "https://example.com/avatar.jpg", profile["created_at"], profile["created_at"],
                        ),
                    )
                with TestClient(main.app) as client:
                    with patch.object(main, "read_google_session", return_value=None):
                        private = client.get("/api/v1/public-profiles/ownerlama")
                        self.assertEqual(private.status_code, 403)
                        self.assertEqual(private.json()["detail"], "Profil ini private")
                        self.assertEqual(client.get("/api/v1/public-profiles").json()["profiles"], [])
                        rejected = client.post(
                            "/api/v1/feedback",
                            json={"profile_id": "profile-owner", "rating": 5, "source": "accuracy"},
                        )
                        self.assertEqual(rejected.status_code, 401)

                    user = {"sub": "google-owner", "email": "owner@example.com"}
                    with patch.object(main, "read_google_session", return_value=user):
                        hidden = client.get("/api/v1/public-profiles/ownerlama")
                        self.assertTrue(hidden.json()["viewer_is_owner"])
                        self.assertEqual(hidden.json()["avatar_url"], "https://example.com/avatar.jpg")
                        changed = client.patch(
                            "/api/v1/user/profile-settings/profile-owner",
                            json={"username": "ownerbaru", "is_public": True},
                        )
                        self.assertEqual(changed.status_code, 200)
                        self.assertTrue(changed.json()["public_url"].endswith("/ownerbaru"))
                        self.assertNotIn("/@", changed.json()["public_url"])
                        submitted = client.post(
                            "/api/v1/feedback",
                            json={
                                "profile_id": "profile-owner",
                                "rating": 5,
                                "message": "Akurat",
                                "source": "accuracy",
                            },
                        )
                        self.assertEqual(submitted.status_code, 200)
                        saved = client.get("/api/v1/user/profiles/profile-owner/feedback/accuracy")
                        self.assertEqual(saved.json()["feedback"]["rating"], 5)
                        history = client.get("/api/v1/user/history").json()["history"]
                        self.assertEqual(history[0]["public_username"], "ownerbaru")

                    with patch.object(main, "read_google_session", return_value=None):
                        public = client.get("/api/v1/public-profiles/ownerbaru")
                        self.assertEqual(public.status_code, 200)
                        self.assertFalse(public.json()["viewer_is_owner"])

    def test_new_public_profile_defaults_to_public(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "public-default.db"
            with patch.object(main, "DB_PATH", db_path):
                main.init_db()
                with main.db() as conn:
                    conn.execute(
                        "INSERT INTO profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        ("profile-public", "Owner", "1997-06-19", None, "Jakarta", None, None, "Asia/Jakarta", 1, "{}", "now"),
                    )
                    conn.execute("INSERT INTO user_profiles VALUES (?, ?, ?)", ("google-owner", "profile-public", "now"))
                with TestClient(main.app) as client, patch.object(main, "read_google_session", return_value={"sub": "google-owner"}):
                    created = client.post(
                        "/api/v1/public-profiles",
                        json={"profile_id": "profile-public", "username": "pemilikpublik", "email": "owner@example.com"},
                    )
                self.assertEqual(created.status_code, 200)
                self.assertTrue(created.json()["public_profile"]["is_public"])

    def test_delete_history_removes_owned_profile_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "delete.db"
            with patch.object(main, "DB_PATH", db_path):
                main.init_db()
                with main.db() as conn:
                    conn.execute(
                        "INSERT INTO profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        ("profile-delete", "Owner", "1997-06-19", None, "Jakarta", None, None, "Asia/Jakarta", 1, "{}", "now"),
                    )
                    conn.execute("INSERT INTO user_profiles VALUES (?, ?, ?)", ("google-owner", "profile-delete", "now"))
                    conn.execute(
                        "INSERT INTO public_profiles (username, profile_id, email, created_at, updated_at, is_public) VALUES (?, ?, ?, ?, ?, ?)",
                        ("hapusdata", "profile-delete", "owner@example.com", "now", "now", 1),
                    )
                    conn.execute(
                        "INSERT INTO interpretations VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        ("interpretation-delete", "profile-delete", "local_fallback", "local", "hash", "{}", "{}", "now"),
                    )
                with TestClient(main.app) as client, patch.object(main, "read_google_session", return_value={"sub": "google-owner"}):
                    self.assertEqual(client.delete("/api/v1/user/history/profile-delete").status_code, 200)
                with main.db() as conn:
                    self.assertFalse(conn.execute("SELECT 1 FROM profiles WHERE id = 'profile-delete'").fetchone())
                    self.assertFalse(conn.execute("SELECT 1 FROM public_profiles WHERE profile_id = 'profile-delete'").fetchone())
                    self.assertFalse(conn.execute("SELECT 1 FROM interpretations WHERE profile_id = 'profile-delete'").fetchone())


if __name__ == "__main__":
    unittest.main()
