"""
Mafia Game Manager - Flask Application
--------------------------------------
A local web application for offline Mafia game moderators/hosts.
Manages player rosters and secretly emails role assignments to players.

STRICT PRIVACY / SECURITY CONTRACT:
- The host must never see any player's role.
- No role data is EVER written to the database, JSON files, console output,
  server logs, or any API response / HTML.
- Role assignments are retained ONLY in server memory during an active game
  to allow retrying failed email deliveries.
- Resetting the game or restarting the server permanently wipes all role memory.
"""

import os
import secrets
import logging
from typing import Dict, List, Optional
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

import database as db
import mailer

# Load environment variables from .env
load_dotenv()

# Configure server logger strictly to avoid role leaks
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("mafia_app")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", secrets.token_hex(16))

# Initialize database on startup
db.init_db()


class InMemGameAssignment:
    """
    Manages secret role assignments in server memory ONLY.
    Under NO circumstance is this data exposed to the frontend,
    written to disk, or logged.
    """
    def __init__(self):
        self.has_active_game: bool = False
        # Dict[player_id, Dict]:
        # player_id -> {"name": str, "email": str, "role": str, "fellow_mafia": Optional[List[str]]}
        self._secret_assignments: Dict[int, Dict] = {}
        # Dict[player_id, Dict]:
        # player_id -> {"player_id": int, "name": str, "email": str, "status": "sent"|"failed", "error": str}
        # Notice: delivery_status contains ONLY identity and status, NEVER role.
        self.delivery_status: Dict[int, Dict] = {}

    def clear(self):
        """Wipe all role assignments and delivery tracking from memory."""
        self.has_active_game = False
        self._secret_assignments.clear()
        self.delivery_status.clear()

    def get_public_delivery_results(self) -> List[Dict]:
        """
        Return delivery status for all players in the active game.
        STRICT GUARANTEE: Never includes role data.
        """
        return list(self.delivery_status.values())

    def get_summary(self) -> Dict:
        """Return counts of sent and failed emails."""
        total = len(self.delivery_status)
        sent = sum(1 for item in self.delivery_status.values() if item.get("status") == "sent")
        failed = sum(1 for item in self.delivery_status.values() if item.get("status") == "failed")
        return {
            "total": total,
            "sent": sent,
            "failed": failed
        }


# Singleton active game state in server memory
active_game = InMemGameAssignment()


# --------------------------------------------------------------------------
# Frontend Route
# --------------------------------------------------------------------------

@app.route("/")
def index():
    """Render the single-page Mafia Game Manager dashboard."""
    return render_template("index.html")


# --------------------------------------------------------------------------
# Player Management API Endpoints
# --------------------------------------------------------------------------

@app.route("/api/players", methods=["GET"])
def api_get_players():
    """Return all saved players (names, emails, in_game status)."""
    players = db.get_all_players()
    return jsonify({"success": True, "players": players})


@app.route("/api/players", methods=["POST"])
def api_add_player():
    """
    Add a new player.
    Validates email format and rejects duplicate emails (case-insensitive).
    """
    data = request.get_json() or {}
    name = data.get("name")
    email = data.get("email")

    try:
        new_player = db.add_player(name, email, in_game=True)
        return jsonify({"success": True, "player": new_player}), 201
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error("Error adding player: %s", str(e))
        return jsonify({"success": False, "error": "Database error while adding player."}), 500


@app.route("/api/players/<int:player_id>/toggle", methods=["POST"])
def api_toggle_player(player_id: int):
    """Toggle a player's in_game status (ON = included, OFF = skipped)."""
    data = request.get_json() or {}
    in_game = bool(data.get("in_game", False))

    updated = db.toggle_player_status(player_id, in_game)
    if not updated:
        return jsonify({"success": False, "error": "Player not found."}), 404

    return jsonify({"success": True, "player_id": player_id, "in_game": in_game})


@app.route("/api/players/toggle-all", methods=["POST"])
def api_toggle_all_players():
    """Set in_game status for all players (Select All / Deselect All)."""
    data = request.get_json() or {}
    in_game = bool(data.get("in_game", True))

    affected = db.set_all_players_status(in_game)
    return jsonify({"success": True, "affected": affected, "in_game": in_game})


@app.route("/api/players/<int:player_id>", methods=["DELETE"])
def api_delete_player(player_id: int):
    """Delete a player by ID."""
    deleted = db.delete_player(player_id)
    if not deleted:
        return jsonify({"success": False, "error": "Player not found."}), 404

    return jsonify({"success": True, "message": "Player deleted."})


# --------------------------------------------------------------------------
# SMTP Status / Health Check Endpoint
# --------------------------------------------------------------------------

@app.route("/api/smtp/status", methods=["GET"])
def api_smtp_status():
    """
    Check if Gmail credentials exist in .env and verify connectivity.
    Does not reveal credentials to the client.
    """
    gmail_addr = os.getenv("GMAIL_ADDRESS", "").strip()
    app_pwd = os.getenv("GMAIL_APP_PASSWORD", "").strip()

    if not gmail_addr or not app_pwd:
        return jsonify({
            "configured": False,
            "sender_email": None,
            "connected": False,
            "message": "GMAIL_ADDRESS or GMAIL_APP_PASSWORD is not set in .env."
        })

    # Mask sender email for display (e.g. host***@gmail.com)
    parts = gmail_addr.split("@")
    masked_email = f"{parts[0][:3]}***@{parts[1]}" if len(parts) == 2 and len(parts[0]) >= 3 else gmail_addr

    # If the user passed ?test=1, run actual SMTP authentication test
    run_test = request.args.get("test") == "1"
    if run_test:
        success, msg = mailer.test_smtp_connection(gmail_addr, app_pwd)
        return jsonify({
            "configured": True,
            "sender_email": masked_email,
            "connected": success,
            "message": msg
        })

    return jsonify({
        "configured": True,
        "sender_email": masked_email,
        "connected": True,
        "message": "Gmail credentials configured in .env."
    })


# --------------------------------------------------------------------------
# Game Execution & Role Assignment Endpoints
# --------------------------------------------------------------------------

@app.route("/api/game/status", methods=["GET"])
def api_game_status():
    """
    Return current game delivery status without ANY role details.
    """
    return jsonify({
        "has_active_game": active_game.has_active_game,
        "results": active_game.get_public_delivery_results(),
        "summary": active_game.get_summary()
    })


@app.route("/api/game/assign-and-send", methods=["POST"])
def api_assign_and_send():
    """
    Assign secret roles to all active players and send out individual emails.

    Validation Rules:
    - Active players >= 4.
    - Special roles (Mafia + Doctor + Detective) <= active players.
    - Number of Mafia must be >= 1.
    - Gmail credentials configured.

    STRICT GUARANTEE:
    - Roles exist only in server memory.
    - Roles are NEVER returned in this response or logged.
    """
    data = request.get_json() or {}

    try:
        mafia_count = int(data.get("mafia_count", 1))
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Invalid mafia count."}), 400

    detective_enabled = bool(data.get("detective_enabled", True))
    mafia_know_each_other = bool(data.get("mafia_know_each_other", False))

    if mafia_count < 1:
        return jsonify({"success": False, "error": "Number of Mafia must be at least 1."}), 400

    # Retrieve only players with in_game == 1
    active_players = db.get_active_players()
    total_active = len(active_players)

    if total_active < 4:
        return jsonify({
            "success": False,
            "error": f"Minimum 4 active players required to start a game (currently {total_active})."
        }), 400

    doctor_count = 1
    detective_count = 1 if detective_enabled else 0
    special_roles_count = mafia_count + doctor_count + detective_count

    if special_roles_count > total_active:
        return jsonify({
            "success": False,
            "error": f"Special roles ({special_roles_count}) exceed the number of active players ({total_active})."
        }), 400

    citizen_count = total_active - special_roles_count

    # Verify SMTP credentials exist
    gmail_addr = os.getenv("GMAIL_ADDRESS", "").strip()
    app_pwd = os.getenv("GMAIL_APP_PASSWORD", "").strip()

    if not gmail_addr or not app_pwd:
        return jsonify({
            "success": False,
            "error": "GMAIL_ADDRESS and GMAIL_APP_PASSWORD must be configured in your .env file."
        }), 400

    # Build the role distribution list
    roles_pool: List[str] = (
        ["Mafia"] * mafia_count +
        ["Doctor"] * doctor_count +
        (["Detective"] * detective_count) +
        ["Citizen"] * citizen_count
    )

    # Cryptographically secure random shuffle
    crypto_rng = secrets.SystemRandom()
    crypto_rng.shuffle(roles_pool)

    # Initialize fresh in-memory game state
    active_game.clear()
    active_game.has_active_game = True

    # Identify fellow Mafia members if the setting is enabled
    mafia_member_names: List[str] = []
    if mafia_know_each_other and mafia_count > 1:
        for idx, player in enumerate(active_players):
            if roles_pool[idx] == "Mafia":
                mafia_member_names.append(player["name"])

    # Store assignments in server memory ONLY
    for idx, player in enumerate(active_players):
        assigned_role = roles_pool[idx]
        p_id = player["id"]

        fellows: Optional[List[str]] = None
        if assigned_role == "Mafia" and mafia_know_each_other:
            fellows = [name for name in mafia_member_names if name != player["name"]]

        active_game._secret_assignments[p_id] = {
            "name": player["name"],
            "email": player["email"],
            "role": assigned_role,
            "fellow_mafia": fellows
        }

    # Attempt to open SMTP connection and send emails
    smtp_server = None
    try:
        smtp_server = mailer.create_smtp_session(gmail_addr, app_pwd)
    except Exception as e:
        logger.error("Failed to connect to Gmail SMTP: %s", str(e))
        # Record all as failed due to connection error
        for p_id, item in active_game._secret_assignments.items():
            active_game.delivery_status[p_id] = {
                "player_id": p_id,
                "name": item["name"],
                "email": item["email"],
                "status": "failed",
                "error": str(e)
            }
        return jsonify({
            "success": True,
            "results": active_game.get_public_delivery_results(),
            "summary": active_game.get_summary(),
            "has_failed": True,
            "connection_error": str(e)
        })

    # Sequential delivery with NO delay
    for p_id, item in active_game._secret_assignments.items():
        try:
            msg = mailer.create_role_email(
                sender_email=gmail_addr,
                recipient_name=item["name"],
                recipient_email=item["email"],
                role=item["role"],
                fellow_mafia=item["fellow_mafia"]
            )
            smtp_server.send_message(msg)
            # Log recipient email ONLY - NEVER log the role!
            logger.info("Email delivered to %s", item["email"])

            active_game.delivery_status[p_id] = {
                "player_id": p_id,
                "name": item["name"],
                "email": item["email"],
                "status": "sent",
                "error": None
            }
        except Exception as e:
            logger.error("Failed sending email to %s: %s", item["email"], str(e))
            active_game.delivery_status[p_id] = {
                "player_id": p_id,
                "name": item["name"],
                "email": item["email"],
                "status": "failed",
                "error": str(e)
            }

    try:
        smtp_server.quit()
    except Exception:
        pass

    summary = active_game.get_summary()
    return jsonify({
        "success": True,
        "results": active_game.get_public_delivery_results(),
        "summary": summary,
        "has_failed": summary["failed"] > 0
    })


@app.route("/api/game/retry-failed", methods=["POST"])
def api_retry_failed():
    """
    Retry sending emails ONLY for players whose delivery previously failed.
    Uses the role assignment currently preserved in server memory.
    """
    if not active_game.has_active_game:
        return jsonify({"success": False, "error": "No active game found to retry."}), 400

    failed_player_ids = [
        p_id for p_id, item in active_game.delivery_status.items()
        if item.get("status") == "failed"
    ]

    if not failed_player_ids:
        return jsonify({
            "success": True,
            "message": "No failed emails to retry.",
            "results": active_game.get_public_delivery_results(),
            "summary": active_game.get_summary()
        })

    gmail_addr = os.getenv("GMAIL_ADDRESS", "").strip()
    app_pwd = os.getenv("GMAIL_APP_PASSWORD", "").strip()

    if not gmail_addr or not app_pwd:
        return jsonify({"success": False, "error": "Gmail credentials missing from .env."}), 400

    try:
        smtp_server = mailer.create_smtp_session(gmail_addr, app_pwd)
    except Exception as e:
        logger.error("Failed to connect to Gmail SMTP during retry: %s", str(e))
        for p_id in failed_player_ids:
            active_game.delivery_status[p_id]["error"] = str(e)
        return jsonify({
            "success": True,
            "results": active_game.get_public_delivery_results(),
            "summary": active_game.get_summary(),
            "has_failed": True,
            "connection_error": str(e)
        })

    for p_id in failed_player_ids:
        assignment = active_game._secret_assignments.get(p_id)
        if not assignment:
            continue

        try:
            msg = mailer.create_role_email(
                sender_email=gmail_addr,
                recipient_name=assignment["name"],
                recipient_email=assignment["email"],
                role=assignment["role"],
                fellow_mafia=assignment["fellow_mafia"]
            )
            smtp_server.send_message(msg)
            logger.info("Retry email delivered to %s", assignment["email"])

            active_game.delivery_status[p_id] = {
                "player_id": p_id,
                "name": assignment["name"],
                "email": assignment["email"],
                "status": "sent",
                "error": None
            }
        except Exception as e:
            logger.error("Retry failed for %s: %s", assignment["email"], str(e))
            active_game.delivery_status[p_id]["error"] = str(e)

    try:
        smtp_server.quit()
    except Exception:
        pass

    summary = active_game.get_summary()
    return jsonify({
        "success": True,
        "results": active_game.get_public_delivery_results(),
        "summary": summary,
        "has_failed": summary["failed"] > 0
    })


@app.route("/api/game/reset", methods=["POST"])
def api_reset_game():
    """
    'New Game' action:
    Wipes the active game role assignments and delivery tracking from memory.
    Keeps all saved players in the database intact.
    """
    active_game.clear()
    return jsonify({
        "success": True,
        "message": "Game reset successfully. Previous role assignment wiped from memory."
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug_mode = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
    print(f"==================================================")
    print(f"  Mafia Game Manager running at http://localhost:{port}")
    print(f"  Host will NEVER see roles in UI, DB, or logs.")
    print(f"==================================================")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
