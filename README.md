# 🎟️ Prize Bond Checker

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Automatically check your **Pakistani prize bonds** against official draw results from [allprizebond.pk](https://allprizebond.pk).

Works as a normal CLI tool, a **local family dashboard**, and an optional **daily alert** (Telegram, WhatsApp, or email). **Optional AI** (Ollama, Gemini, or GPT) adds smart summaries and natural-language commands — but everything still runs fine without AI.

No manual searching through thousands of numbers — add your bonds once, run one command after each draw, and see instantly if you won.

---

## Why this exists

If you own prize bonds, checking results after every draw is tedious:

- Each Rs. 200 draw has **2,400 winning numbers**
- Results are spread across 1st, 2nd, and 3rd prize sections
- Manually comparing your list is slow and error-prone

This tool does it in seconds.

---

## Features

- Checks **1st, 2nd, and 3rd** prize tiers (not just the table)
- Supports all common denominations: `100`, `200`, `750`, `1500`, `7500`, `15000`, `25000`, `40000`
- **Multi-denomination portfolio** — keep mixed bonds (and family owners) in one file
- **`--latest`** / **`--all`** — auto-check the newest published draw for one or every denomination
- **Voice add** — say the six digits on the dashboard (or `add --say`) and they are stored
- **MCP server** — Cursor / other agents can add bonds, check draws, and read history locally
- **Win history** — every check is stored in `history.sqlite` on your machine
- **Alerts** — Telegram, WhatsApp (Twilio), email, or a webhook after a new draw
- **Daily auto-check** — Windows Task Scheduler (or cron) so you do not have to remember
- **Optional AI** — Ollama (local/free), Gemini, or OpenAI for summaries and `--ask`
- **Works without AI** — if no provider is available, built-in summaries still work
- Exact 6-digit bond matching (no false positives)
- Privacy-first: your bond numbers stay in a local file that is **never committed to git**

---

## Not a programmer?

1. Install [Python 3.10+](https://www.python.org/downloads/) and tick **Add Python to PATH**
2. In this folder: `pip install -r requirements.txt` then `pip install -e .`
3. Copy `bonds.example.txt` to `bonds.txt` and add your numbers
4. Double-click **`start-dashboard.bat`**
5. Click **Speak a number** and read the six digits (Chrome or Edge)

The dashboard opens in your browser at `http://127.0.0.1:8765`. It is only reachable on this computer.

---

## Quick start (CLI)

### 1. Clone or download

```bash
git clone https://github.com/Irsalistic/prize-bond-checker.git
cd prize-bond-checker
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
pip install -e .
```

### 3. Add your bonds

```bash
copy bonds.example.txt bonds.txt
```

Edit `bonds.txt` — one bond number per line, or group by denomination:

```text
[200]
477670
436083

[750:parents]
123456
```

> **Important:** `bonds.txt` is in `.gitignore`. Never upload your real bond numbers to GitHub.

### 4. Run after a draw

```bash
# Manual date
python check_prize_bonds.py -d 2026-03-16 -b 200

# Auto latest draw
python check_prize_bonds.py --latest -b 200

# Every denomination in your portfolio
python check_prize_bonds.py --all --latest

# With a friendly summary (optional AI)
python check_prize_bonds.py --latest -b 200 --summary
```

Or using the installed command:

```bash
prize-bond-checker --all --latest --summary
prize-bond-checker web --open
prize-bond-checker history
```

---

## Family dashboard

```bash
python check_prize_bonds.py web --open
```

From the page you can:

- Check the latest draw for every denomination you hold
- **Speak a number** — Chrome/Edge listens, then adds the bond and reads it back
- Add / remove bonds by typing (with an optional owner name)
- See win ledger and check history
- Send a test alert if Telegram or WhatsApp is configured

Say: “four seven seven six seven zero” or “oh two two six six seven for parents”. Urdu digit words work too (`char`, `saat`, `sifar`).

```bash
python check_prize_bonds.py add --say "four seven seven six seven zero for parents"
python check_prize_bonds.py add 477670 -b 200 --owner parents
```

---

## MCP for Cursor and other agents

The same local actions are exposed as MCP tools, so an agent can add a spoken number, check the latest draw, and read wins without uploading your bonds.

```bash
pip install -e ".[mcp]"
```

This repo already includes `.cursor/mcp.json`. After installing the extra, reload MCP in Cursor. Tools:

| Tool | What it does |
|------|----------------|
| `add_bond` | Save one 6-digit number |
| `add_bonds_from_speech` | Parse English/Urdu digits and save |
| `list_bonds` | Show the local portfolio |
| `remove_bond` | Delete a number |
| `check_latest_draws` | Match bonds against the newest results |
| `get_history` / `get_wins` | Read the local ledger |

Resources: `prizebonds://portfolio`, `prizebonds://history`.

```bash
python -m prize_bond_checker.mcp_server
```

---

## Alerts after each draw

Copy `.env.example` to `.env` and fill in **one** channel.

### Telegram (easiest)

1. In Telegram, talk to [@BotFather](https://t.me/BotFather) and create a bot
2. Copy the token into `TELEGRAM_BOT_TOKEN`
3. Message your new bot, then open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` and copy your `chat.id` into `TELEGRAM_CHAT_ID`

```bash
python check_prize_bonds.py notify-test
python check_prize_bonds.py --all --latest --notify --skip-checked
```

`--skip-checked` means a daily run stays quiet unless a **new** draw is published.

### WhatsApp

Uses the official [Twilio WhatsApp API](https://www.twilio.com/docs/whatsapp). Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `WHATSAPP_TO` in `.env`.

### Daily auto-check on Windows

```bash
python check_prize_bonds.py schedule --install
```

That creates a Task Scheduler job which runs every day at 20:00, checks any new draws, and pings you if alerts are configured.

Remove it with:

```bash
python check_prize_bonds.py schedule --remove
```

---

## AI setup (optional)

The tool works **without any AI**. AI is only used for `--summary` and `--ask`.

### Option 1: Ollama (free, local — recommended)

1. Install [Ollama](https://ollama.com/)
2. Pull a model: `ollama pull llama3.2`
3. Run Ollama, then:

```bash
python check_prize_bonds.py --latest -b 200 --summary --ai-provider ollama
```

### Option 2: Google Gemini (free tier)

```bash
set GEMINI_API_KEY=your_key_here
python check_prize_bonds.py --latest -b 200 --summary --ai-provider gemini
```

### Option 3: OpenAI / GPT

```bash
set OPENAI_API_KEY=your_key_here
python check_prize_bonds.py --latest -b 200 --summary --ai-provider openai
```

### Auto-detect (default)

```bash
python check_prize_bonds.py --latest -b 200 --summary
```

Tries **Ollama → Gemini → OpenAI** in order. If none are available, prints a built-in summary instead.

---

## Usage

```bash
# Check latest Rs. 200 draw
python check_prize_bonds.py --latest -b 200

# Check every denomination you hold
python check_prize_bonds.py --all --latest --notify --skip-checked

# Natural language (AI helps parse; basic rules work without AI too)
python check_prize_bonds.py --ask "check my 200 bonds for the latest draw"

# Long flags
python check_prize_bonds.py --date 2026-03-16 --denomination 200

# Short flags
python check_prize_bonds.py -d 2026-03-16 -b 200

# Quick positional form
python check_prize_bonds.py 200 2026-03-16

# Show 1st and 2nd prize numbers for the draw
python check_prize_bonds.py -d 2026-03-16 -b 200 --show-winners

# Disable AI completely
python check_prize_bonds.py --latest -b 200 --summary --ai-provider none

# Custom bond file location
python check_prize_bonds.py -d 2026-03-16 -b 200 -f D:\my-bonds.txt

# Local dashboard
python check_prize_bonds.py web --open

# Print stored wins and past checks
python check_prize_bonds.py history
```

---

## Example output

```text
Latest draw found: 2026-06-15
Checking 31 bond(s) against Rs. 200 draw on 2026-06-15

Source: https://allprizebond.pk/draw/200/2026-06-15
Draw info: Draw #106 · Karachi
Prize slots parsed: 1st=1 winner(s), 2nd=5 winner(s), 3rd=2394 winner(s)

No matches found.

--- Summary ---
Checked 31 bond(s) against Rs. 200 draw on 2026-06-15 · Draw #106 · Karachi. No matches found this time.

(AI not available — using built-in summary)
```

With Ollama running:

```text
--- Summary ---
I checked all 31 of your Rs. 200 bonds against Draw #106 in Karachi (15 June 2026).
Unfortunately none matched this time — better luck on the next draw!

(AI provider: ollama (llama3.2))
```

---

## Understanding the output

| Line | Meaning |
|------|---------|
| `Prize slots parsed: 1st=1, 2nd=5, 3rd=2394` | How many winners exist in each tier — **same count every Rs. 200 draw** |
| `No matches found.` | Script worked; none of your bonds won |
| `You won!` | At least one of your bonds matched |

The **winning numbers themselves** change every draw. Always verify a win through official National Savings channels before claiming.

---

## Windows .exe (optional)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build-exe.ps1
```

Put `bonds.txt` next to `dist\prize-bond-checker.exe`, then:

```text
prize-bond-checker.exe web --open
```

---

## Project structure

```text
prize-bond-checker/
├── src/prize_bond_checker/
│   ├── cli.py          # Command-line interface
│   ├── scraper.py      # Fetch & parse draw pages
│   ├── latest.py       # Find latest draw date
│   ├── service.py      # Shared check pipeline
│   ├── portfolio.py    # Multi-denomination bond list
│   ├── history.py      # Local win ledger
│   ├── notify.py       # Telegram / WhatsApp / email
│   ├── scheduler.py    # Daily Task Scheduler / cron
│   ├── voice.py        # Spoken English/Urdu digit parser
│   ├── actions.py      # Shared add/list helpers
│   ├── mcp_server.py   # MCP tools for Cursor and other agents
│   ├── web/            # Local family dashboard
│   ├── ai/             # Optional AI providers & summaries
│   ├── checker.py      # Match bonds against results
│   ├── bonds.py        # Load bond list from file
│   ├── constants.py    # Denominations & prize info
│   └── models.py       # Data classes
├── tests/              # Unit tests with HTML fixtures
├── start-dashboard.bat
├── bonds.example.txt   # Template for your bond list
├── check_prize_bonds.py
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Development

```bash
pip install -r requirements-dev.txt
pip install -e .
pytest
```

---

## Author

Built by [Irsalistic](https://github.com/Irsalistic)

---

## Disclaimer

This project is **not affiliated** with National Savings Pakistan or allprizebond.pk. It reads publicly available draw results for personal convenience. Always verify wins through official channels before claiming prizes.

---

## License

MIT — see [LICENSE](LICENSE).
