"""
Email delivery module for Mafia Game Manager.

Handles Gmail SMTP connection, secure email formatting (HTML + text fallback),
and error handling.

STRICT PRIVACY / SECURITY ENFORCEMENT:
- Under NO circumstance should role data be included in server logs, print statements,
  or general error messages.
- If an email send fails, log only the recipient email address and the exception type/message.
"""

import smtplib
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import List, Optional, Tuple

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_TIMEOUT = 15  # seconds

# Descriptions strictly following user requirements
ROLE_DESCRIPTIONS = {
    "Mafia": (
        "Secretly eliminates one player each night with your fellow Mafia members.\n"
        "During the day, blend in with the citizens and avoid suspicion at all costs."
    ),
    "Doctor": (
        "Each night, choose one player to save from elimination.\n"
        "You may protect yourself or another player, but choose wisely!"
    ),
    "Detective": (
        "Each night, investigate one player to learn if they are Mafia.\n"
        "Use your information carefully during day discussions without exposing your identity."
    ),
    "Citizen": (
        "You have no special night powers.\n"
        "Work with your fellow citizens to find and eliminate the Mafia through discussion and voting."
    ),
}

ROLE_COLORS = {
    "Mafia": "#dc2626",      # Crimson red
    "Doctor": "#16a34a",     # Emerald green
    "Detective": "#2563eb",  # Royal blue
    "Citizen": "#d97706",    # Amber gold
}


def create_role_email(
    sender_email: str,
    recipient_name: str,
    recipient_email: str,
    role: str,
    fellow_mafia: Optional[List[str]] = None,
) -> MIMEMultipart:
    """
    Construct a multipart MIME email (HTML + Plaintext fallback).
    Contains:
    - Subject: "Your Mafia Game Role"
    - Greeting with player's name
    - The role in large text
    - 2-3 line description of what that role does
    - If Mafia and fellow_mafia provided: lists other Mafia members' names
    - Footer: "Keep your role secret!"
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your Mafia Game Role"
    msg["From"] = formataddr(("Mafia Game Manager", sender_email))
    msg["To"] = formataddr((recipient_name, recipient_email))

    description = ROLE_DESCRIPTIONS.get(role, "")

    # Mafia-specific knowledge section
    mafia_text_extra = ""
    mafia_html_extra = ""

    if role == "Mafia" and fellow_mafia is not None:
        if fellow_mafia:
            names_str = ", ".join(fellow_mafia)
            mafia_text_extra = f"\nFellow Mafia member(s): {names_str}\n"
            mafia_html_extra = f"""
            <div style="margin-top: 14px; padding: 12px 16px; border: 1px solid #e2e8f0; border-radius: 8px; text-align: left;">
                <p style="margin: 0; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: #64748b;">
                    Fellow Mafia Member(s)
                </p>
                <p style="margin: 4px 0 0 0; font-size: 14px; color: #0f172a; font-weight: 600;">
                    {names_str}
                </p>
            </div>
            """
        else:
            mafia_text_extra = "\nYou are the only Mafia member in this game.\n"
            mafia_html_extra = """
            <div style="margin-top: 14px; padding: 12px 16px; border: 1px solid #e2e8f0; border-radius: 8px; text-align: left;">
                <p style="margin: 0; font-size: 13px; color: #64748b; font-style: italic;">
                    You are the only Mafia member in this game.
                </p>
            </div>
            """

    # Plain text version
    text_content = f"""Hello {recipient_name},

YOUR SECRET ROLE: {role.upper()}

{description}
{mafia_text_extra}
---------------------------------
Keep your role secret!
Do not show or disclose your role to anyone.
---------------------------------
"""

    # HTML version (Privacy-optimized: No bright background colors, compact text size to prevent shoulder-surfing)
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Mafia Game Role</title>
</head>
<body style="margin: 0; padding: 24px; background-color: #0f172a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #334155;">
    <div style="max-width: 520px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);">
        
        <!-- Header banner -->
        <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 20px; text-align: center; border-bottom: 2px solid #334155;">
            <h1 style="margin: 0; font-size: 18px; letter-spacing: 2px; text-transform: uppercase; color: #f8fafc; font-weight: 700;">
                Mafia Game
            </h1>
            <p style="margin: 4px 0 0 0; font-size: 12px; color: #94a3b8; letter-spacing: 0.5px;">
                CONFIDENTIAL ROLE ASSIGNMENT
            </p>
        </div>

        <!-- Main Body -->
        <div style="padding: 24px 20px; text-align: left;">
            <p style="margin: 0 0 16px 0; font-size: 15px; color: #475569;">
                Hello <strong style="color: #0f172a;">{recipient_name}</strong>,
            </p>

            <!-- Discreet Role Section (No background color, normal compact text size to prevent nearby peeking) -->
            <div style="margin: 0 0 16px 0; padding: 12px 14px; border: 1px solid #e2e8f0; border-radius: 8px; text-align: left;">
                <span style="font-size: 12px; text-transform: uppercase; letter-spacing: 0.8px; color: #64748b; font-weight: 600; display: block; margin-bottom: 4px;">
                    Your Assigned Role
                </span>
                <span style="font-size: 16px; font-weight: 700; color: #0f172a; letter-spacing: 0.5px;">
                    {role}
                </span>
            </div>

            <!-- Role Description Card -->
            <div style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px; text-align: left; margin-bottom: 12px;">
                <p style="margin: 0; font-size: 13px; line-height: 1.6; color: #334155; white-space: pre-line;">
                    {description}
                </p>
            </div>

            {mafia_html_extra}

            <!-- Warning Notice -->
            <div style="margin-top: 20px; padding: 10px 14px; border: 1px solid #e2e8f0; border-radius: 6px; text-align: left;">
                <p style="margin: 0; font-size: 12px; font-weight: 600; color: #475569;">
                    &#129323; Keep your role secret!
                </p>
                <p style="margin: 2px 0 0 0; font-size: 11px; color: #64748b;">
                    Do not show your screen or disclose this email to anyone.
                </p>
            </div>
        </div>

        <!-- Footer -->
        <div style="background-color: #f1f5f9; padding: 14px; text-align: center; border-top: 1px solid #e2e8f0;">
            <p style="margin: 0; font-size: 11px; color: #94a3b8;">
                Generated by Mafia Game Manager &bull; Offline Party Game
            </p>
        </div>

    </div>
</body>
</html>
"""

    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))
    return msg


def create_smtp_session(gmail_address: str, app_password: str) -> smtplib.SMTP:
    """
    Establish an authenticated TLS connection to smtp.gmail.com.
    Raises clear, informative exceptions on failure.
    """
    clean_address = (gmail_address or "").strip()
    clean_password = (app_password or "").replace(" ", "").strip()

    if not clean_address or not clean_password:
        raise ValueError("GMAIL_ADDRESS or GMAIL_APP_PASSWORD is not set in .env")

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(clean_address, clean_password)
        return server
    except smtplib.SMTPAuthenticationError as e:
        raise ConnectionError(
            "Gmail authentication failed. Verify that GMAIL_ADDRESS is correct and you are using "
            "a 16-character Google App Password (not your normal Google account password). "
            "Ensure 2-Step Verification is enabled on your Google account."
        ) from e
    except socket.gaierror as e:
        raise ConnectionError(
            "Network error: Unable to resolve 'smtp.gmail.com'. Please check your internet connection."
        ) from e
    except (socket.timeout, TimeoutError) as e:
        raise ConnectionError(
            "Connection timed out while contacting smtp.gmail.com. Please check your firewall or internet."
        ) from e
    except Exception as e:
        raise ConnectionError(f"SMTP error: {str(e)}") from e


def test_smtp_connection(gmail_address: str, app_password: str) -> Tuple[bool, str]:
    """
    Test Gmail SMTP credentials and connectivity.
    Returns (success: bool, message: str).
    """
    try:
        server = create_smtp_session(gmail_address, app_password)
        server.quit()
        return True, "SMTP connection and credentials verified successfully."
    except Exception as e:
        return False, str(e)
