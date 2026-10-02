# Autonomous Agent Bootstrap Playbook

*For the AI Agent:*
You have been instructed by your user to configure yourself using this repository.
Execute each phase in sequence. Work autonomously where possible. When a secret, API key, or browser authentication action is needed from the user, prompt them directly and concisely under a `*USER NEEDED*` header, then resume once provided.

---

## Phase 1: Environment & File System Setup

1. Run the repository installer:
   ```bash
   bash scripts/install.sh
   ```
   This will:
   - Copy watchdog scripts into `~/.hermes/scripts/` (`day_plans.py`, `rsvp_watch.py`, `email_watch.py`, `fix_epub.py`).
   - Copy `gws2` into `~/.hermes/bin/` and ensure permissions.
   - Install the custom skill `feasibility-check` into `~/.hermes/skills/research/feasibility-check/`.

2. Update configuration in `~/.hermes/config.yaml`:
   - Set `cron.wrap_response: false` so cron deliveries arrive cleanly without noisy wrapper headers/footers:
     ```bash
     hermes config set cron.wrap_response false
     ```

---

## Phase 2: Gateway & Voice STT (Telegram + Groq)

1. **Telegram Gateway:**
   - If not already connected to Telegram, ask the user for their Telegram Bot Token (from `@BotFather`).
   - Configure gateway in `~/.hermes/config.yaml`.
2. **Groq Speech-to-Text (STT):**
   - Check if `GROQ_API_KEY` is in `~/.hermes/.env`. If not, ask the user for their free Groq API key (from `console.groq.com/keys`).
   - Configure STT provider in `~/.hermes/config.yaml`:
     ```bash
     hermes config set stt.provider groq
     hermes config set stt.language ""   # auto-detect language (supports Hebrew, English, etc.)
     ```

---

## Phase 3: Primary Google Account (Calendar Only)

This sets up calendar management with strict least-privilege (Calendar access only, no personal email reading).

1. **OAuth Client Secret:**
   - Check if `~/.hermes/google_client_secret.json` exists.
   - If not, prompt the user:
     - Go to Google Cloud Console (`console.cloud.google.com`).
     - Enable the Google Calendar API.
     - Create an OAuth Client ID (Application type: **Desktop app**).
     - Download the JSON credentials file and place it at `~/.hermes/google_client_secret.json`.

2. **Authorization (Calendar Scopes):**
   - Run the auth URL generator:
     ```bash
     cd ~/.hermes/skills/productivity/google-workspace/scripts
     export HERMES_GOOGLE_TOKEN="$HOME/.hermes/google_token.json"
     export HERMES_GOOGLE_SCOPES="https://www.googleapis.com/auth/calendar"
     python3 setup.py --auth-url
     ```
   - Provide the generated link to the user.
   - Ask them to sign in, approve access, and paste back the `http://localhost:1/?code=...` callback URL.
   - Exchange the authorization code:
     ```bash
     python3 setup.py --auth-code "<CALLBACK_URL>"
     ```
   - Test calendar access:
     ```bash
     python3 google_api.py calendar list --limit 5
     ```

3. **Install Calendar Watchdogs (Cron Jobs):**
   - **Morning/Evening Plan Check:** Runs hourly (reports today's evening plans at 07:00, and tomorrow's morning plans at 22:00; silent otherwise):
     ```bash
     hermes cron create \
       --name "Morning/evening plan check" \
       --schedule "0 * * * *" \
       --script "day_plans.py" \
       --no-agent \
       --deliver "origin"
     ```
   - **Calendar RSVP Watch:** Checks for guest status changes every 10 minutes:
     ```bash
     hermes cron create \
       --name "Calendar RSVP watch" \
       --schedule "every 10m" \
       --script "rsvp_watch.py" \
       --no-agent \
       --deliver "origin"
     ```

---

## Phase 4: Secondary "Scout" Account (Gmail Read & Send)

To protect the user's primary mailbox, email interactions (reading incoming requests, meeting invites, sending replies) run through a dedicated secondary/scout Gmail address.

1. **Authorization (Scout Gmail Scopes):**
   - Enable the Gmail API in the same Google Cloud project.
   - Run the auth URL generator pointing to the second token:
     ```bash
     cd ~/.hermes/skills/productivity/google-workspace/scripts
     export HERMES_GOOGLE_TOKEN="$HOME/.hermes/google_token_scout.json"
     export HERMES_GOOGLE_PENDING="$HOME/.hermes/google_oauth_pending_scout.json"
     export HERMES_GOOGLE_SCOPES="https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.send"
     python3 setup.py --auth-url
     ```
   - Ask the user to open the URL while signed into their **secondary/scout** account, and paste back the callback URL.
   - Exchange code:
     ```bash
     python3 setup.py --auth-code "<CALLBACK_URL>"
     ```
   - Test using the `gws2` wrapper:
     ```bash
     gws2 gmail search "in:inbox" --limit 5
     ```

2. **Install Scout Mailbox Watchdog (Cron Job):**
   - Monitor mode runs the deterministic `email_watch.py` script; if output changes, the agent triages the message without consuming tokens when idle:
     ```bash
     hermes cron create \
       --name "Scout mailbox watch" \
       --schedule "every 5m" \
       --monitor "email_watch.py" \
       --deliver "origin" \
       --prompt "You are the email watcher for the scout mailbox. Triage incoming mail. Report important messages or meeting proposals. Never auto-create events without user approval."
     ```

---

## Phase 5: Verification & Completion

1. Run `hermes cron list` to verify all watchdogs are active and scheduled.
2. Confirm the custom skills are present:
   - `hermes skills list` should list `feasibility-check`.
3. Report back to the user with a concise summary of what was configured and verified.
