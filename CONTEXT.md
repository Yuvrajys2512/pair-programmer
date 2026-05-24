# Pair Programmer — Master Context File

> Read this file at the start of any session. It gives you the full picture
> without having to grep the codebase or re-read every .md file.
> Last updated: 2026-05-25.

---

## What This Project Is

A multi-agent code review system where three LLM agents debate a code file and
produce a structured verdict. The core UX loop:

1. **The Critic** opens with a structured JSON review — bugs, security holes,
   edge cases, performance traps, design issues, style problems.
2. **The Advocate** streams a prose rebuttal — defending intent, conceding real
   issues, pushing back on inflated severity.
3. They alternate for N rounds (mode-controlled).
4. **The Judge** reads the full debate transcript and returns a scored JSON
   verdict with winner, action items, strengths, and win lists.
5. **The Fixer** (optional) rewrites the code from the Judge's action items
   and shows a unified diff with per-item approval.

There is also a web UI (React + Vite), a FastAPI backend with SSE streaming,
and SQLite persistence for review history. The pipeline is orchestrated through
LangGraph. Custom personas can be layered on top of modes.

---

## Current Status — ALL 9 Phases Complete

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Critic — structured JSON review | Done |
| 2 | Debate loop — Critic + Advocate, N rounds | Done |
| 3 | Judge — scored verdict with action items | Done |
| 4 | Review modes (roast / standard / deep) | Done |
| 5 | Fixer — rewrites code from verdict | Done |
| 6 | LangGraph migration — full state graph | Done |
| 7 | Web UI — React frontend + FastAPI SSE | Done |
| 8 | SQLite persistence + review history | Done |
| 9 | Custom personas — composable identity overlays | Done |

The original roadmap is fully implemented. Open work is captured in
`future_work.md` as a prioritized tier list (see below).

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| LLM provider | Groq (free tier, `llama-3.3-70b-versatile`) |
| Orchestration | LangGraph (`langgraph>=0.2.0`) |
| CLI rendering | Rich |
| Data validation | Pydantic v2 |
| Backend API | FastAPI + SSE (`uvicorn`) |
| Frontend | React + TypeScript + Vite |
| Database | SQLite via SQLAlchemy 2.0 |
| Prompt storage | Markdown files |
| Config | `python-dotenv` |

Dependencies in `requirements.txt`:
```
groq>=0.13.0
python-dotenv>=1.0.0
pydantic>=2.5.0
rich>=13.7.0
langgraph>=0.2.0
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.0
```

Frontend dependencies: standard React 18 + TypeScript + Vite stack in
`frontend/package.json`.

---

## Project Structure

```
pair-programmer/
├── main.py                        # CLI entry point + Rich terminal renderers
├── requirements.txt
├── pairprog.db                    # SQLite DB (created at runtime, gitignored)
├── .env                           # GROQ_API_KEY + GROQ_MODEL (gitignored)
│
├── agents/
│   ├── critic.py                  # review() → CriticReview; rebut_stream() → chunks
│   ├── advocate.py                # rebut_stream() → chunks
│   ├── judge.py                   # synthesize(state) → Verdict
│   ├── fixer.py                   # fix(code, verdict, language) → FixerResult
│   └── prompts/
│       ├── critic_system.md       # Critic base personality + JSON schema
│       ├── advocate_system.md     # Advocate base personality
│       ├── judge_system.md        # Judge base personality + JSON schema
│       ├── fixer_system.md        # Fixer base personality + JSON schema
│       ├── modes/
│       │   ├── roast.md           # CRITIC / ADVOCATE / JUDGE sections
│       │   └── deep.md            # CRITIC / ADVOCATE / JUDGE sections
│       └── personas/
│           ├── faang_interviewer.md
│           ├── mentor.md
│           ├── staff_engineer.md
│           └── security_auditor.md
│
├── core/
│   ├── llm.py                     # Groq client wrapper (JSON + streaming)
│   ├── models.py                  # Pydantic schemas (all data contracts)
│   ├── modes.py                   # ReviewMode enum + mode overlay loader
│   ├── debate.py                  # Hand-rolled debate loop (non-graph path)
│   ├── graph.py                   # LangGraph pipeline (PipelineState TypedDict)
│   ├── transcript.py              # Prompt builders for each agent turn
│   ├── text.py                    # number_lines() helper
│   ├── listener.py                # DebateListener protocol + _NullListener
│   └── personas.py                # Persona registry + overlay applier
│
├── web/
│   ├── app.py                     # FastAPI app (routes + SSE endpoint)
│   ├── db.py                      # SQLAlchemy engine + init_db()
│   ├── storage.py                 # ORM models (Review, DebateMessageRow, etc.)
│   ├── persist.py                 # create_review / get_review / list_reviews
│   ├── api_models.py              # Pydantic request/response models for HTTP
│   └── sse.py                     # stream_pipeline() async generator
│
├── frontend/
│   └── src/
│       ├── App.tsx                # Root component
│       ├── api.ts                 # HTTP client to backend
│       ├── types.ts               # TypeScript types mirroring backend schemas
│       └── components/
│           ├── CodeEditor.tsx     # Code input (textarea, not Monaco)
│           ├── ModeSelector.tsx   # Roast / Standard / Deep picker
│           ├── PersonaSelector.tsx
│           ├── DebatePanel.tsx    # SSE consumer; live streaming chat view
│           ├── VerdictCard.tsx    # Renders the Judge's verdict
│           ├── DiffView.tsx       # Before/after diff display
│           └── HistoryView.tsx    # Past reviews list
│
└── examples/
    └── buggy_code.py              # Test fixture with intentional issues
```

---

## Architecture — How It All Fits Together

### Four-layer mental model

```
CLI / Web layer
  main.py (terminal)   web/app.py (HTTP)
        │                    │
        └────────┬───────────┘
                 ▼
  Orchestration layer
    core/debate.py  (hand-rolled)
    core/graph.py   (LangGraph — preferred path)
                 │
                 ▼
  Agent layer
    agents/critic.py   agents/advocate.py
    agents/judge.py    agents/fixer.py
                 │
                 ▼
  Prompt + Schema layer
    agents/prompts/*.md   core/models.py
```

### Prompt layering (mode + persona)

```
base prompt (critic_system.md)
  + mode overlay  (modes/roast.md → ## CRITIC section)
  + persona overlay (personas/mentor.md → ## CRITIC section)
```

Mode overlay is appended first, then persona. Persona has final say on
identity/perspective conflicts. Mode still controls tone and length.

### LangGraph pipeline graph

```
START
  └─► critic_initial (structured JSON review)
        └─► advocate_turn
              ├─► (round < max) ──► critic_turn ──► advocate_turn (loop)
              ├─► (round == max, verdict) ──► judge_node
              │                                  ├─► (fixer) ──► fixer_node ──► END
              │                                  └─► END
              └─► (round == max, no verdict) ──► END
```

State is a `PipelineState` TypedDict with append-only `transcript` via
`operator.add`. The same `DebateListener` protocol that drives the CLI
terminal renderer is injected into graph nodes for live streaming.

### Two run paths in `main.py`

1. **`--full-graph`** → `run_pipeline()` in `core/graph.py` — LangGraph end-to-end,
   no interactive confirmation, all fixes applied automatically.
2. **Default** → `run_debate()` in `core/debate.py` (hand-rolled loop), then
   `judge_synthesize()`, then `run_fixer()` with per-item Y/N confirmation.

The hand-rolled path exists to preserve the interactive fixer approval UX.

---

## Key Data Models (`core/models.py`)

```python
ReviewItem       # One Critic finding: category, severity, line_number, issue, suggestion
CriticReview     # summary + list[ReviewItem]
DebateMessage    # agent, round_number, content, is_initial_review
DebateState      # code, language, transcript, max_rounds, mode, persona
ActionItem       # priority, description, affected_lines
Verdict          # summary, score, critic_wins, advocate_wins, strengths, action_items, winner, winner_reasoning
ChangeEntry      # action_item_index, description
FixerResult      # fixed_code, changelog, changes_made
```

Category enum: BUG | SECURITY | EDGE_CASE | PERF | DESIGN | STYLE
Severity enum:  LOW | MEDIUM | HIGH | CRITICAL

---

## Modes

| Mode | Rounds | Tone | Focus |
|------|--------|------|-------|
| roast | 2 | Comedy roast, brutal+funny, 60-120 words/turn | Most embarrassing issues |
| standard | 3 | Professional (default) | Balanced, no overlay |
| deep | 5 | Senior-engineer architectural, 300-500 words/turn | SOLID, testability, scale |

Mode overlays live in `agents/prompts/modes/<name>.md` with `## CRITIC`,
`## ADVOCATE`, `## JUDGE` sections. `core/modes.py` parses them and appends
only the relevant section per agent. STANDARD has no overlay file.

---

## Personas

Four built-in personas in `agents/prompts/personas/`:
- `faang_interviewer` — evaluates like a FAANG bar-raiser
- `mentor` — patient, educational, growth-focused
- `staff_engineer` — systems-thinking, long-term ownership lens
- `security_auditor` — threat-model first, OWASP-aware

Usage: `python main.py file.py --persona mentor --verdict`

New personas: drop a `.md` file with `# Name`, description paragraph, then
`## CRITIC` / `## ADVOCATE` / `## JUDGE` sections into `agents/prompts/personas/`.

---

## Web Layer

**Backend:** FastAPI with SSE streaming.

Endpoints:
- `GET /api/health`
- `GET /api/personas`
- `POST /api/reviews/stream` — accepts `ReviewRequest`, returns SSE stream
- `GET /api/reviews` — paginated history list
- `GET /api/reviews/{id}` — full review detail

Database (SQLite at `pairprog.db`): tables for `reviews`, `debate_messages`,
`verdicts`, `fixes`. SQLAlchemy ORM in `web/storage.py`. Additive column
migrations handled manually in `web/db.py`.

**Frontend:** React + TypeScript + Vite, dev server on port 5173.
CORS is configured for `localhost:5173` / `127.0.0.1:5173`.

Components:
- `CodeEditor` — textarea (not Monaco, plain textarea for now)
- `ModeSelector` + `PersonaSelector` — dropdowns
- `DebatePanel` — SSE consumer, live streaming chat bubbles
- `VerdictCard` — renders Judge output
- `DiffView` — before/after diff
- `HistoryView` — lists past reviews from `/api/reviews`

---

## How to Run

**CLI:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env: GROQ_API_KEY=... and GROQ_MODEL=llama-3.3-70b-versatile

python main.py examples/buggy_code.py --verdict
python main.py examples/buggy_code.py --mode roast --verdict
python main.py examples/buggy_code.py --mode deep --rounds 3 --verdict --fix
python main.py examples/buggy_code.py --full-graph
python main.py examples/buggy_code.py --persona mentor --verdict
python main.py --graph-diagram
python main.py --list-personas
```

**Web (both servers needed):**
```powershell
# Terminal 1 — backend
uvicorn web.app:app --reload

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

---

## Debugging Guide

| Symptom | Where to look |
|---------|--------------|
| Terminal output looks wrong | `main.py` renderers |
| Turn order wrong | `core/debate.py` or `core/graph.py` |
| Agent sees wrong context | `core/transcript.py` |
| JSON parsing fails | `core/models.py` + agent system prompt |
| Tone / reasoning bad | Agent prompt or mode overlay `.md` |
| API calls fail | `.env` + `core/llm.py` |
| Web route broken | `web/app.py` |
| DB schema issue | `web/db.py` + `web/storage.py` |
| Persona not found | Check `agents/prompts/personas/` + slug spelling |

---

## What's Good

1. **Prompt quality** — All four agent prompts are detailed, opinionated, and
   have specific rules that prevent common LLM failure modes (blanket defense,
   hallucinated issues, documentation-as-fix, meta-praise openers, etc.).
2. **Pydantic validation on all LLM outputs** — Critic and Judge both use JSON
   mode + Pydantic parsing. Errors surface clearly.
3. **Prompt overlay architecture** — Modes and personas compose cleanly without
   duplicating entire system prompts.
4. **Full transcript in every turn** — Agents reference earlier points; the
   debate feels real, not like isolated one-shot calls.
5. **LangGraph integration** — Proper state graph with conditional routing.
   Append-only transcript prevents state mutation bugs.
6. **Streaming everywhere** — Both CLI (Rich) and web (SSE) stream tokens live.
   The live debate is the core UX differentiator.
7. **Clean separation of concerns** — CLI / Web / Orchestration / Agent /
   Prompt+Schema are distinct layers with clear responsibilities.
8. **Interactive Fixer** — Per-item Y/N approval in CLI mode. Re-runs the
   Fixer with only approved items if partially approved.
9. **SQLite persistence** — Full review history including transcript, verdict,
   and fixed code stored.
10. **Fixer is scope-constrained by prompt** — "Fix only what the action item
    describes. If you notice an unrelated bug, leave it." Prevents drift.

---

## What's Not Good / Gaps

1. **Zero tests** — No pytest, no unit tests, no integration tests. The
   non-LLM bits (`core/modes`, `core/transcript`, `core/text`, `core/personas`,
   `core/graph` routing) are all testable without a Groq API key. This is
   the biggest engineering maturity gap.
2. **No README screenshots or GIF** — The repo has no visual content. A
   recruiter clicking the GitHub link sees walls of text. The single highest-
   leverage improvement per `future_work.md`.
3. **Not deployed** — No live URL. Everything lives locally. Deployment to
   Fly.io or Railway would turn this from "code on GitHub" into "try it."
4. **All modes look identical in the web UI** — The roadmap calls for roast =
   dark + flames, deep = academic theme. Currently all modes share the same
   CSS. Estimated ~30 minutes of work.
5. **No shareable review URLs** — `/r/<review-id>` permalinks. DB already
   stores everything; just missing the route + frontend handler.
6. **No score-trend chart** — History view shows past reviews but no "your
   code is getting better over time" visualization.
7. **No export-to-markdown** — One button to copy the verdict as a markdown
   report to paste into a PR. Real utility, zero backend work.
8. **No GitHub Actions CI** — No type-check or lint badge in README.
9. **`core/personas.py` duplicates `_parse_sections()`** from `core/modes.py`
   — minor code smell, noted in the source comment. Low priority.
10. **CodeEditor is a plain textarea** — Not Monaco/CodeMirror. No syntax
    highlighting in the input panel. The roadmap called for Monaco.
11. **`PROJECT_OVERVIEW.md` is stale** — Still says "Phases 1-4 done, Phase 5+
    not built yet." Doesn't reflect Phase 5-9 completion.
12. **`frontend/README.md` is just Vite boilerplate** — Not project-specific.

---

## Prioritized Next Work (from `future_work.md`)

### Tier 1 — Do these first (force multipliers)
1. **README with screenshots + GIF** — Record a GIF of the live debate
   streaming. Embed the LangGraph Mermaid diagram (`python main.py
   --graph-diagram`). Add a "how to run" block. This is the single highest-
   leverage improvement.
2. **Deploy** — Fly.io (Docker-friendly, free tier) or Railway ($5/mo).
   One URL for backend + frontend.

### Tier 2 — High signal, low effort
3. Shareable review URLs (`/r/<review-id>`)
4. Score-trend chart in history modal
5. Export verdict as markdown (clipboard button)
6. Mode-specific visual flair (roast: dark + flames, deep: academic)

### Tier 3 — Engineering maturity
7. GitHub Actions CI (Python type-check + frontend lint)
8. Tests for `core/modes`, `core/text`, `core/transcript`, `core/personas`,
   `core/graph` routing

### Tier 4 — Feature extensions (pick one)
9. Git/PR integration — review a GitHub PR diff, not a whole file
10. Custom personas via the web UI (save to DB)
11. Debate replay at 2x speed

---

## Key Design Decisions (why things are the way they are)

- **Groq, not OpenAI/Anthropic** — Free tier, fast inference. Model is
  `llama-3.3-70b-versatile`. Config lives in `.env` as `GROQ_MODEL` so
  switching models requires no code changes.
- **JSON mode for Critic + Judge, streaming prose for Advocate** — Structured
  agents need machine-readable output. The Advocate's job is argumentative
  prose; streaming it makes the UX feel live.
- **Overlay prompts, not full rewrites per mode** — Base personality is stable;
  tone and depth are overlaid. Adding a new mode is a new `.md` file + enum
  entry, not a rewrite of three full prompts.
- **Full transcript in every debate turn** — Each agent sees the entire
  debate history, not just the last message. Enables callbacks and prevents
  repeated points.
- **Hand-rolled loop preserved alongside LangGraph** — `core/debate.py` still
  exists because the interactive per-item fixer approval UX requires control
  flow that doesn't fit naturally inside a compiled LangGraph graph.
- **Fixer is scope-constrained** — It only touches lines referenced by the
  Judge's action items. Prevents it from becoming an unsolicited refactoring
  agent.
- **Personas are applied after modes** — Persona has the final say on identity.
  Mode still controls tone and word count. The two concerns are independent.

---

## Example File for Testing

`examples/buggy_code.py` contains intentional issues:
- SQL injection (string concatenation in a query)
- Mutable default argument
- Mutation during iteration
- Division by zero on empty input
- Hardcoded secret-looking API key
- `eval()` on file contents
- Bare `except:` that swallows all errors

Run any mode against it to sanity-check agent behavior without writing new code.

---

## How to Add Things

### New review mode
1. Add enum value to `ReviewMode` in `core/modes.py`
2. Add default round count to `MAX_ROUNDS`
3. Create `agents/prompts/modes/<name>.md` with `## CRITIC`, `## ADVOCATE`,
   `## JUDGE` sections
4. Done — `main.py` picks it up via `choices=[m.value for m in ReviewMode]`

### New persona
1. Create `agents/prompts/personas/<slug>.md` with:
   - `# Display Name` heading
   - Description paragraph
   - `## CRITIC` and/or `## ADVOCATE` and/or `## JUDGE` sections
2. Done — `core/personas.py` discovers it by globbing the directory

### New agent (hypothetical)
- Add `agents/<name>.py`, `agents/prompts/<name>_system.md`
- Add a new node in `core/graph.py`
- Wire routing logic and edge to/from the new node
- Add rendering in `main.py` and `web/sse.py`
