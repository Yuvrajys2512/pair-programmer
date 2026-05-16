# Pair Programmer

Two AI agents argue about your code so you don't have to argue with yourself.

A multi-agent code review system where **The Critic** and **The Advocate** debate your code across multiple rounds, and **The Judge** synthesizes the debate into a structured, actionable verdict. Three review modes let you dial the intensity from a comedy roast to a senior-engineer architectural review.

See `pair-programmer-roadmap.md` for the full vision and phase plan.

---

## Current status — Phase 4 complete

| Phase | Status |
|---|---|
| 1. Foundation — The Critic | done |
| 2. Debate loop — Critic + Advocate, N rounds | done |
| 3. The Judge — structured verdict | done |
| 4. Review modes — Roast / Standard / Deep | done |
| 5. The Fixer — rewrites the code | next |

---

## Setup

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure your API key
copy .env.example .env
# Then edit .env and paste your Groq API key (free: https://console.groq.com/keys)
```

---

## Usage

### Full debate with verdict (the main experience)

```powershell
python main.py examples/buggy_code.py --verdict
```

The Critic opens with a structured review. The Advocate rebuts. They go back and forth for the mode's round count. The Judge then reads the full transcript and returns a scored verdict with prioritized action items.

### Modes

```powershell
# Roast — 2 rounds, comedy-roast tone, short and brutal
python main.py examples/buggy_code.py --mode roast --verdict

# Standard — 3 rounds, professional, the default
python main.py examples/buggy_code.py --mode standard --verdict

# Deep — 5 rounds, senior-engineer architectural review
python main.py examples/buggy_code.py --mode deep --verdict
```

The same code run through all three modes should feel like three different reviewers.

### Other flags

```powershell
# Just the Critic, one-shot structured review (Phase 1 behaviour)
python main.py examples/buggy_code.py --solo

# Override the round count for any mode
python main.py examples/buggy_code.py --mode deep --rounds 3 --verdict

# Print the source file before reviewing
python main.py examples/buggy_code.py --show-code --verdict
```

---

## How modes work

Each mode is a **prompt overlay** applied on top of the base agent prompts — not a separate prompt per mode. The base prompts (`agents/prompts/*_system.md`) define each agent's core identity. Mode files in `agents/prompts/modes/` add tone, depth, and output-length overrides for the Critic, Advocate, and Judge.

`STANDARD` has no overlay — the base prompts are the standard experience. `ROAST` and `DEEP` ship overlay files; new modes can be added by dropping a new markdown file with `## CRITIC`, `## ADVOCATE`, `## JUDGE` sections into `agents/prompts/modes/` and adding the enum entry.

---

## Project structure

```
pair-programmer/
├── agents/
│   ├── critic.py              # The Critic agent (structured review + rebuttals)
│   ├── advocate.py            # The Advocate (streamed prose rebuttals)
│   ├── judge.py               # The Judge (structured verdict)
│   └── prompts/
│       ├── critic_system.md   # Base Critic personality
│       ├── advocate_system.md # Base Advocate personality
│       ├── judge_system.md    # Base Judge personality
│       └── modes/
│           ├── roast.md       # Roast-mode overlays
│           └── deep.md        # Deep-review overlays
├── core/
│   ├── llm.py                 # Groq client wrapper (JSON + streaming)
│   ├── models.py              # Pydantic: ReviewItem, DebateState, Verdict, ...
│   ├── modes.py               # ReviewMode enum + overlay loader
│   ├── debate.py              # Orchestrator: runs the N-round debate
│   ├── text.py                # Line-numbering helper
│   └── transcript.py          # Builds the user-prompt views for each agent
├── examples/
│   └── buggy_code.py          # Sample code with intentional issues
├── main.py                    # CLI entry point + Rich terminal renderers
├── requirements.txt
└── .env                       # Your API key (gitignored)
```
