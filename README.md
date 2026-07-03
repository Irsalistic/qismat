# 🎟️ Prize Bond Checker

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Automatically check your **Pakistani prize bonds** against official draw results from [allprizebond.pk](https://allprizebond.pk).

Works as a normal CLI tool. **Optional AI** (Ollama, Gemini, or GPT) adds smart summaries and natural-language commands — but everything still runs fine without AI.

No manual searching through thousands of numbers — just add your bonds once, run one command after each draw, and see instantly if you won.

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
- **`--latest`** — auto-check the newest published draw (no date needed)
- **Optional AI** — Ollama (local/free), Gemini, or OpenAI for summaries and `--ask` commands
- **Works without AI** — if no provider is available, built-in summaries still work
- Exact 6-digit bond matching (no false positives)
- Simple bond list file — one number per line
- Clear CLI output with optional top-prize display
- Privacy-first: your bond numbers stay in a local file that is **never committed to git**

---

## Quick start

### 1. Clone or download

```bash
git clone https://github.com/Irsalistic/prize-bond-checker.git
cd prize-bond-checker
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Or install as a package:

```bash
pip install -e .
```

### 3. Add your bonds

**Option A — one by one** (`bonds.txt`):

```bash
copy bonds.example.txt bonds.txt
```

Edit `bonds.txt` — one bond number per line.

**Option B — bulk import (recommended for hundreds or thousands):**

Export your bonds from Excel as `.csv` or `.xlsx`, then:

```bash
python check_prize_bonds.py --import my_bonds.csv
python check_prize_bonds.py --import my_bonds.xlsx
```

Bonds can be separated by **commas, spaces, or new lines** — the tool finds every 6-digit number automatically.

For Excel import: `pip install openpyxl` (or `pip install -r requirements-excel.txt`)

Replace all bonds instead of merging:

```bash
python check_prize_bonds.py --import my_bonds.csv --replace
```

> **Important:** `bonds.txt` is in `.gitignore`. Never upload your real bond numbers to GitHub.

### 4. Run after a draw

```bash
# Manual date
python check_prize_bonds.py -d 2026-03-16 -b 200

# Auto latest draw (recommended)
python check_prize_bonds.py --latest -b 200

# With AI summary (optional)
python check_prize_bonds.py --latest -b 200 --summary
```

Or using the installed command:

```bash
prize-bond-checker --latest -b 200 --summary
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

Copy `.env.example` to `.env` for persistent settings (optional).

---

## Usage

```bash
# Check latest Rs. 200 draw
python check_prize_bonds.py --latest -b 200

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

The **winning numbers themselves** change every draw. Only the **structure** (1 + 5 + 2394 for Rs. 200) stays the same.

---

## Project structure

```text
prize-bond-checker/
├── src/prize_bond_checker/
│   ├── cli.py          # Command-line interface
│   ├── scraper.py      # Fetch & parse draw pages
│   ├── latest.py       # Find latest draw date
│   ├── ai/             # Optional AI providers & summaries
│   ├── checker.py      # Match bonds against results
│   ├── bonds.py        # Load bond list from file
│   ├── constants.py    # Denominations & prize info
│   └── models.py       # Data classes
├── tests/              # Unit tests with HTML fixtures
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
