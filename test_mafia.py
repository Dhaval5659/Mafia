"""
Automated Test Suite for Mafia Game Manager.

Tests:
1. Database layer: SQLite schema, table creation, add, toggle, duplicate rejection, delete.
2. Strict Privacy Verification: Database NEVER contains any role columns.
3. Mailer unit tests: Role email structure, content, confidentiality, mafia knowledge.
4. Flask API endpoints:
   - Adding players, duplicate detection, input validation.
   - Toggling in_game status.
   - Live status checks.
   - Strict Privacy Verification: API responses NEVER contain 'role' in any key or value.
   - Validation rules: < 4 players, role overflow.
   - In-memory assignment and mock email delivery.
   - Retry failed emails.
   - New Game reset wiping memory while preserving database.
"""

import os
import unittest
import sqlite3
import json
import tempfile
from unittest.mock import patch, MagicMock

import database as db
import mailer
from app import app, active_game


class TestDatabaseLayer(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_file.close()
        self.db_path = self.temp_file.name
        db.init_db(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    def test_schema_has_no_role_columns(self):
        """CRITICAL PRIVACY TEST: Ensure the SQLite database schema has ZERO role columns."""
        with db.get_db_connection(self.db_path) as conn:
            columns = [row["name"] for row in conn.execute("PRAGMA table_info(players)").fetchall()]
            
            # Must contain only standard roster fields
            expected_fields = {"id", "name", "email", "in_game", "created_at"}
            self.assertEqual(set(columns), expected_fields)
            
            # Specifically assert no role-related keywords exist in table schema
            for col in columns:
                self.assertNotIn("role", col.lower())
                self.assertNotIn("secret", col.lower())
                self.assertNotIn("mafia", col.lower())

    def test_add_and_get_players(self):
        p1 = db.add_player("Alice", "alice@example.com", in_game=True, db_path=self.db_path)
        p2 = db.add_player("Bob", "bob@example.com", in_game=False, db_path=self.db_path)

        all_players = db.get_all_players(self.db_path)
        self.assertEqual(len(all_players), 2)

        active_players = db.get_active_players(self.db_path)
        self.assertEqual(len(active_players), 1)
        self.assertEqual(active_players[0]["name"], "Alice")

    def test_duplicate_email_blocked(self):
        db.add_player("Alice", "alice@example.com", in_game=True, db_path=self.db_path)
        # Exact duplicate
        with self.assertRaises(ValueError):
            db.add_player("Alice Two", "alice@example.com", in_game=True, db_path=self.db_path)
        # Case-insensitive duplicate
        with self.assertRaises(ValueError):
            db.add_player("Alice Cap", "ALICE@EXAMPLE.COM", in_game=True, db_path=self.db_path)

    def test_invalid_email_format_rejected(self):
        with self.assertRaises(ValueError):
            db.add_player("Invalid User", "notanemail", in_game=True, db_path=self.db_path)
        with self.assertRaises(ValueError):
            db.add_player("Invalid User", "missing@domain", in_game=True, db_path=self.db_path)

    def test_toggle_player_status(self):
        p = db.add_player("Charlie", "charlie@example.com", in_game=True, db_path=self.db_path)
        self.assertTrue(p["in_game"])

        db.toggle_player_status(p["id"], False, db_path=self.db_path)
        active = db.get_active_players(self.db_path)
        self.assertEqual(len(active), 0)

        db.toggle_player_status(p["id"], True, db_path=self.db_path)
        active = db.get_active_players(self.db_path)
        self.assertEqual(len(active), 1)

    def test_delete_player(self):
        p = db.add_player("David", "david@example.com", in_game=True, db_path=self.db_path)
        self.assertTrue(db.delete_player(p["id"], db_path=self.db_path))
        self.assertEqual(len(db.get_all_players(self.db_path)), 0)


class TestMailer(unittest.TestCase):
    def test_email_structure_and_confidentiality(self):
        """Verify the generated email contains correct text and confidentiality footer."""
        msg = mailer.create_role_email(
            sender_email="host@gmail.com",
            recipient_name="Alice",
            recipient_email="alice@example.com",
            role="Doctor"
        )
        self.assertEqual(msg["Subject"], "Your Mafia Game Role")
        self.assertIn("Alice", msg["To"])

        # Decode plain text part
        text_part = msg.get_payload(0).get_payload(decode=True).decode("utf-8")
        self.assertIn("Hello Alice", text_part)
        self.assertIn("YOUR SECRET ROLE: DOCTOR", text_part)
        self.assertIn("Keep your role secret!", text_part)
        self.assertIn("Each night, choose one player to save", text_part)

        # Decode HTML part
        html_part = msg.get_payload(1).get_payload(decode=True).decode("utf-8")
        self.assertIn("Doctor", html_part)
        self.assertIn("Keep your role secret!", html_part)

    def test_mafia_knowledge_inclusion(self):
        """When mafia know each other is enabled, fellow mafia members are listed."""
        msg = mailer.create_role_email(
            sender_email="host@gmail.com",
            recipient_name="Alice",
            recipient_email="alice@example.com",
            role="Mafia",
            fellow_mafia=["Bob", "Charlie"]
        )
        text_part = msg.get_payload(0).get_payload(decode=True).decode("utf-8")
        self.assertIn("Fellow Mafia member(s): Bob, Charlie", text_part)

        # When lone mafia
        msg_lone = mailer.create_role_email(
            sender_email="host@gmail.com",
            recipient_name="Alice",
            recipient_email="alice@example.com",
            role="Mafia",
            fellow_mafia=[]
        )
        text_lone = msg_lone.get_payload(0).get_payload(decode=True).decode("utf-8")
        self.assertIn("You are the only Mafia member in this game.", text_lone)


class TestFlaskAPIAndStrictPrivacy(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_file.close()
        self.db_path = self.temp_file.name
        os.environ["DATABASE_PATH"] = self.db_path
        db.init_db(self.db_path)

        active_game.clear()
        app.config["TESTING"] = True
        self.client = app.test_client()

        # Seed 5 players
        self.players = [
            db.add_player("Player 1", "p1@example.com", in_game=True, db_path=self.db_path),
            db.add_player("Player 2", "p2@example.com", in_game=True, db_path=self.db_path),
            db.add_player("Player 3", "p3@example.com", in_game=True, db_path=self.db_path),
            db.add_player("Player 4", "p4@example.com", in_game=True, db_path=self.db_path),
            db.add_player("Player 5", "p5@example.com", in_game=True, db_path=self.db_path),
        ]

    def tearDown(self):
        os.environ.pop("DATABASE_PATH", None)
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass
        active_game.clear()

    def test_minimum_players_validation(self):
        """Should reject assign-and-send if active players < 4."""
        # Deactivate 2 players, leaving only 3
        db.toggle_player_status(self.players[0]["id"], False, db_path=self.db_path)
        db.toggle_player_status(self.players[1]["id"], False, db_path=self.db_path)

        res = self.client.post("/api/game/assign-and-send", json={
            "mafia_count": 1,
            "detective_enabled": True
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Minimum 4 active players", data["error"])

    def test_special_roles_overflow_validation(self):
        """Should reject if special roles exceed active players."""
        # 4 players active, but request 3 Mafia + 1 Doctor + 1 Detective = 5 special roles
        res = self.client.post("/api/game/assign-and-send", json={
            "mafia_count": 4,  # 4 mafia + 1 doc + 1 det = 6 > 5 players
            "detective_enabled": True
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("exceed the number of active players", data["error"])

    @patch("mailer.create_smtp_session")
    @patch.dict(os.environ, {"GMAIL_ADDRESS": "test@gmail.com", "GMAIL_APP_PASSWORD": "secretpassword123"})
    def test_assign_and_send_strict_privacy(self, mock_smtp):
        """
        CRITICAL PRIVACY TEST:
        Role assignments must succeed, but the response and delivery results
        must contain NO role information.
        """
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        res = self.client.post("/api/game/assign-and-send", json={
            "mafia_count": 2,
            "detective_enabled": True,
            "mafia_know_each_other": True
        })

        data = res.get_json()
        self.assertEqual(res.status_code, 200, f"Failed with {data}")
        self.assertTrue(data["success"])
        self.assertEqual(data["summary"]["total"], 5)
        self.assertEqual(data["summary"]["sent"], 5)
        self.assertEqual(data["summary"]["failed"], 0)

        # STRICT PRIVACY ASSERTIONS:
        # Check every item in results to ensure NO role info is leaked
        for item in data["results"]:
            self.assertIn("player_id", item)
            self.assertIn("name", item)
            self.assertIn("email", item)
            self.assertIn("status", item)
            self.assertEqual(item["status"], "sent")
            # Must NOT contain 'role'
            self.assertNotIn("role", item)
            self.assertNotIn("secret_role", item)

        # Entire serialized response text must not contain any role names as assignments
        res_text = res.get_data(as_text=True)
        self.assertNotIn('"role"', res_text)
        self.assertNotIn('Mafia', res_text)
        self.assertNotIn('Doctor', res_text)
        self.assertNotIn('Detective', res_text)
        self.assertNotIn('Citizen', res_text)

        # Ensure SMTP send_message was called 5 times
        self.assertEqual(mock_server.send_message.call_count, 5)

        # Check /api/game/status also has NO roles
        status_res = self.client.get("/api/game/status")
        status_data = status_res.get_json()
        for item in status_data["results"]:
            self.assertNotIn("role", item)
        status_text = status_res.get_data(as_text=True)
        self.assertNotIn('"role"', status_text)

    @patch("mailer.create_smtp_session")
    @patch.dict(os.environ, {"GMAIL_ADDRESS": "test@gmail.com", "GMAIL_APP_PASSWORD": "secretpassword123"})
    def test_retry_failed_emails(self, mock_smtp):
        """Verify retrying failed emails operates in-memory without role leakage."""
        mock_server = MagicMock()
        # Fail the first send, succeed on the rest
        call_count = [0]
        def side_effect_send(msg):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Simulated network timeout")
            return None

        mock_server.send_message.side_effect = side_effect_send
        mock_smtp.return_value = mock_server

        # First run: 1 failure
        res = self.client.post("/api/game/assign-and-send", json={
            "mafia_count": 1,
            "detective_enabled": True
        })
        data = res.get_json()
        self.assertEqual(data["summary"]["failed"], 1)
        self.assertEqual(data["summary"]["sent"], 4)

        # Retry failed email
        mock_server.send_message.side_effect = None  # Succeed now
        retry_res = self.client.post("/api/game/retry-failed")
        retry_data = retry_res.get_json()

        self.assertTrue(retry_data["success"])
        self.assertEqual(retry_data["summary"]["sent"], 5)
        self.assertEqual(retry_data["summary"]["failed"], 0)

        # Check again: NO roles in retry response
        for item in retry_data["results"]:
            self.assertNotIn("role", item)

    def test_new_game_reset(self):
        """Verify 'New Game' wipes memory while preserving database players."""
        # Set active game
        active_game.has_active_game = True
        active_game._secret_assignments[1] = {"role": "Mafia"}
        active_game.delivery_status[1] = {"status": "sent"}

        res = self.client.post("/api/game/reset")
        self.assertEqual(res.status_code, 200)

        # In-memory assignment wiped
        self.assertFalse(active_game.has_active_game)
        self.assertEqual(len(active_game._secret_assignments), 0)
        self.assertEqual(len(active_game.delivery_status), 0)

        # SQLite database still has all 5 players
        self.assertEqual(len(db.get_all_players(self.db_path)), 5)


if __name__ == "__main__":
    unittest.main()
