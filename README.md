# Hermes Agent Bootstrap & Setup Blueprint

A turnkey blueprint to configure a freshly installed **Hermes Agent** with the full autonomous workflow:
- **Telegram Gateway & Groq Voice STT**
- **Dual-Account Google Workspace** (Primary Account for Calendar only, Secondary "Scout" Account for Gmail triage & sending)
- **Automated Silent Watchdogs** (Morning/Evening plan summaries, Calendar RSVP alerts, Scout mailbox triage)
- **Custom Skills & Utilities** (`feasibility-check`, `fix_epub`)

---

## How to Use (For the Human)

1. Deploy Hermes on your server/VPS following the official docs (`curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash`).
2. Start Hermes (`hermes`) and paste this prompt to your new agent:

```text
Please clone https://github.com/ICsharp1/hermes-agent-bootstrap.git into ~/hermes-agent-bootstrap, read BOOTSTRAP.md in that directory, and follow its step-by-step instructions to configure yourself. Ask me for API keys or OAuth permissions only when you reach the step that requires them.
```

3. Your agent will read `BOOTSTRAP.md` and execute the entire setup autonomously, only pausing to ask you for your Telegram bot token, Groq API key, and Google OAuth approval links.
