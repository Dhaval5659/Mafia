# 🕵️‍♂️ Mafia Game Manager

A clean, responsive web application designed for offline Mafia game hosts/moderators. The app manages player rosters and secretly emails role assignments to players via Gmail SMTP.

The game itself is played offline, so the app handles only player roster management and secret role delivery.

---

## 🔒 Strict Host Privacy Guarantee

As the game host/moderator, **you cannot see any player's role**:
- **No host view, no toggle, no admin screen, and no API endpoint** reveals player roles.
- Roles are generated dynamically in **server memory only** using Python's cryptographically secure `secrets` library (`random.SystemRandom`).
- **Never saved to disk**: Neither SQLite nor JSON files ever store roles or game histories.
- **Never written to logs**: Server console logs and error messages only record recipient emails and delivery statuses—never roles.
- **In-memory retry only**: Role assignments stay in memory strictly during an active game session to allow retrying failed emails. Clicking **"New Game"** or stopping the server wipes role memory completely.

---

## 📁 Project Architecture

```
Mafia/
├── app.py                 # Flask server, in-memory game state, and REST API
├── database.py            # SQLite storage for persistent player roster (Names, Emails, ON/OFF)
├── mailer.py              # Gmail SMTP integration, HTML/plain-text email templates & error handling
├── requirements.txt       # Python dependencies (Flask, python-dotenv)
├── .env.example           # Environment template for Gmail credentials
├── .env                   # Your local secrets (git-ignored, never committed)
├── templates/
│   └── index.html         # Responsive, framework-free dashboard UI & modals
├── static/
│   ├── css/
│   │   └── style.css      # Modern dark noir Mafia theme, badges, switches & animations
│   └── js/
│       └── app.js         # Client-side reactivity, live count summaries, and modals
├── test_mafia.py          # Automated test suite (13 unit & API privacy tests)
└── README.md              # Documentation, setup guide, and verification checklist
```

---

## 🚀 Step-by-Step Setup Guide

### 1. Generate a Gmail App Password
Google requires an **App Password** (a 16-character code) for third-party SMTP access. Your standard Google account password will **not** work.

1. Go to your **Google Account**: [https://myaccount.google.com](https://myaccount.google.com).
2. On the left navigation panel, click **Security**.
3. Under **"How you sign in to Google"**, ensure **2-Step Verification** is turned **ON** (Google requires 2FA to create app passwords).
4. In the search bar at the top of Google Account, search for **"App passwords"** (or visit [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)).
5. In the **"App name"** field, type `Mafia App` and click **Create**.
6. Google will display a **16-character code** (e.g. `abcd efgh ijkl mnop`).
7. Copy this code (spaces do not matter, the app automatically strips them).

---

### 2. Configure Your `.env` File
1. In the project folder (`d:\Movya\Mafia`), create a copy of `.env.example` named `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Open `.env` in any text editor and fill in your Gmail address and the 16-character App Password:
   ```ini
   GMAIL_ADDRESS=yourname@gmail.com
   GMAIL_APP_PASSWORD=abcdefghijklmnop

   PORT=5000
   DEBUG=False
   ```

---

### 3. Install Requirements
Ensure Python 3.9+ is installed, then install dependencies:
```powershell
pip install -r requirements.txt
```

---

### 4. Run the Application
Start the Flask local server:
```powershell
python app.py
```
Open your web browser and navigate to:
```
http://localhost:5000
```

---

## 🎮 How to Use the Dashboard

1. **Add Players**:
   - Enter player name and valid email address.
   - Duplicate emails (case-insensitive) are automatically blocked.
   - Saved players remain stored in SQLite (`mafia.db`) for all future games.

2. **Select Players for the Game**:
   - Use the **"In Game" ON/OFF switch** on the right side of each player's row.
   - Toggle **ON** to include the player in the current game.
   - Toggle **OFF** to skip the player (e.g., if absent) without deleting them.
   - Use **"Select All"** or **"Deselect All"** for quick bulk actions.

3. **Configure Role Settings**:
   - **Number of Mafia**: Set freely (1 or 2). Minimum 1.
   - **Doctor**: Always included (1).
   - **Detective**: Toggle ON to include 1 Detective, or OFF to exclude.
   - **Citizens**: Calculated automatically from remaining active players.
   - **"Mafia know each other"**: If checked and 2 Mafia are chosen, both Mafia members receive an email listing the other Mafia player's name. (You, the host, still never see this).
   - **Live Summary**: Shows **counts only** (e.g., `8 players: 2 Mafia, 1 Doctor, 1 Detective, 4 Citizens`).

4. **Assign Roles & Send Emails**:
   - Click **"Assign Roles & Send Emails"**.
   - A confirmation dialog displays the active player count and role breakdown.
   - Once confirmed, the app shuffles roles using `secrets.SystemRandom`, generates confidential HTML emails, and dispatches them sequentially via Gmail SMTP with no delay.
   - The delivery modal displays **Player Name, Email, and Delivery Status (`✓ Sent` or `✗ Failed`)** with error details if any fail. It **never displays roles**.
   - If any email fails (e.g., recipient address error or brief network hiccup), click **"Retry Failed Emails Only"**.

5. **Discussion Timer (Day Phase Stopwatch)**:
   - Built-in timer with a default of **100 seconds** (`01:40`).
   - Host can customize the duration freely using the seconds input (e.g. 90s, 120s) or click one of the quick preset buttons (`60s`, `100s`, `120s`, `180s`).
   - Controls: **Start / Pause**, **Reset**, and quick adjusters (**+30s**, **+60s**, **-10s**).
   - Dynamic progress bar changes from green to warning amber (under 30s) and critical pulsing red (under 10s).
   - Sound alert: plays a 3-note chime when time runs out (uses Web Audio API, completely offline, can be muted with 🔊/🔇).
   - **Focus / Fullscreen View**: Click `⛶` or the header timer button to display a giant countdown clock for everyone to see (supports Spacebar to pause/resume and R to reset).

6. **Start a New Game**:
   - Click **"New Game"** in the top navbar.
   - Confirms and wipes the role assignment from server memory.
   - Keeps your saved player roster in SQLite intact for the next game.

---

## 🧪 5-Player Verification Checklist

Before hosting a real game, run through this 5-minute verification:

- [ ] **Step 1: Check SMTP Status**
  - Launch `python app.py` and open `http://localhost:5000`.
  - The status pill in the top-right navbar should show a green dot: `SMTP Ready (you***@gmail.com)`.

- [ ] **Step 2: Add 5 Test Players**
  - Add 5 test entries (you can use your own email with Gmail sub-addressing, e.g. `yourname+test1@gmail.com`, `yourname+test2@gmail.com`, etc., which all arrive in your Gmail inbox).
  - Verify that attempting to add an existing email displays an alert: `A player with email '...' already exists`.

- [ ] **Step 3: Test Validation Guards**
  - Toggle 2 players OFF so only 3 remain active.
  - Notice that the **"Assign Roles & Send Emails"** button is disabled and a warning banner appears: `At least 4 active players are required (currently 3)`.
  - Toggle all 5 players ON.
  - Set Mafia count to 2, keep Doctor (1), and Detective ON (1).
  - Check the live summary badge: `5 Players: 2 Mafia | 1 Doctor | 1 Detective | 1 Citizen`.

- [ ] **Step 4: Dispatch Role Emails**
  - Click **"Assign Roles & Send Emails"**.
  - Review the confirmation modal, then click **"Yes, Shuffle & Send Now"**.
  - Watch the delivery status modal show `✓ Sent` for each recipient.
  - Check your terminal console: confirm it logs `INFO: Email delivered to ...` with **NO role names anywhere**.

- [ ] **Step 5: Verify Strict Privacy (Zero Leaks)**
  - **Terminal / Console**: Check that no role (`Mafia`, `Doctor`, `Detective`, `Citizen`) was printed.
  - **Network Tab (F12 Developer Tools)**: Inspect the `/api/game/assign-and-send` response payload. Confirm it returns only `player_id`, `name`, `email`, and `status`. No roles!
  - **Database Inspection**: Run the command:
    ```powershell
    python -c "import sqlite3; conn = sqlite3.connect('mafia.db'); print(conn.execute('PRAGMA table_info(players)').fetchall())"
    ```
    Confirm only columns are `id`, `name`, `email`, `in_game`, `created_at`.
  - **Inbox Inspection**: Open the 5 emails received in Gmail. Each email should state only that player's role, description, and "Keep your role secret!". The two Mafia emails should name each other.

- [ ] **Step 6: Run Automated Tests**
  - Run the full test suite in your terminal:
    ```powershell
    python -m unittest test_mafia.py -v
    ```
  - All 13 unit, security, and privacy tests should pass with `OK`.
