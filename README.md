# Pair Programmer

Two AI agents argue about your code so you don't have to argue with yourself.

A multi-agent code review system where **The Critic** and **The Advocate** debate your code, and **The Judge** synthesizes the debate into actionable feedback.

See `pair-programmer-roadmap.md` for the full vision and phase plan.

---

## Phase 1 — The Critic (current)

A single agent that takes a code file and prints a structured review.

### Setup

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

### Run

```powershell
python main.py examples/buggy_code.py
```

You'll see a structured critique of the sample code printed to the terminal.

---

## Project Structure

```
pair-programmer/
├── agents/
│   ├── critic.py              # The Critic agent
│   └── prompts/
│       └── critic_system.md   # The Critic's personality
├── core/
│   ├── llm.py                 # Groq client wrapper
│   └── models.py              # Pydantic review schema
├── examples/
│   └── buggy_code.py          # Sample code with intentional issues
├── main.py                    # CLI entry point
├── requirements.txt
└── .env                       # Your API key (gitignored)
```
