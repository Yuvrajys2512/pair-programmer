# Pair Programmer Project Overview

This file explains what has been built so far, how the pieces work together,
and where to look when you want to change or extend the project.

## What This Project Is

Pair Programmer is a Python CLI tool that reviews code using a small multi-agent
LLM system.

Instead of asking one model for a review, the app creates a debate:

1. The Critic reviews the code first and returns structured findings.
2. The Advocate responds, defending reasonable choices and challenging weak criticism.
3. The Critic and Advocate continue for several rounds.
4. The Judge can optionally read the full debate and produce a final verdict.

The main user experience is:

```powershell
python main.py examples/buggy_code.py --verdict
```

That command reviews `examples/buggy_code.py`, streams the debate in the
terminal, and then prints the Judge's verdict.

## Current Build Status

The project currently has Phases 1 through 4 implemented.

| Phase | Status | What exists |
|---|---:|---|
| Phase 1: Critic review | Done | One-shot structured review from the Critic |
| Phase 2: Debate loop | Done | Critic and Advocate debate for multiple rounds |
| Phase 3: Judge verdict | Done | Structured final verdict with score and action items |
| Phase 4: Review modes | Done | `roast`, `standard`, and `deep` modes |
| Phase 5: Fixer | Not built yet | Planned agent that rewrites code from the verdict |
| Phase 6+: LangGraph, UI, history | Not built yet | Planned future architecture and product layers |

The detailed future plan is in `pair-programmer-roadmap.md`.

## Tech Stack

The app is intentionally small and CLI-first.

| Area | Technology |
|---|---|
| Language | Python |
| CLI rendering | Rich |
| LLM provider | Groq |
| Config loading | python-dotenv |
| Data validation | Pydantic |
| Agent orchestration | Hand-written Python loop |
| Prompt storage | Markdown files |

Dependencies are listed in `requirements.txt`:

```text
groq
python-dotenv
pydantic
rich
```

## Project Structure

```text
.
|-- main.py
|-- README.md
|-- pair-programmer-roadmap.md
|-- PROJECT_OVERVIEW.md
|-- requirements.txt
|-- .env.example
|-- agents/
|   |-- critic.py
|   |-- advocate.py
|   |-- judge.py
|   |-- prompts/
|       |-- critic_system.md
|       |-- advocate_system.md
|       |-- judge_system.md
|       |-- modes/
|           |-- roast.md
|           |-- deep.md
|-- core/
|   |-- debate.py
|   |-- llm.py
|   |-- models.py
|   |-- modes.py
|   |-- text.py
|   |-- transcript.py
|-- examples/
|   |-- buggy_code.py
```

Generated or local-only folders such as `.venv/`, `__pycache__/`, `.git/`, and
`.claude/` are not part of the application logic.

## How To Run It

Set up the project:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Then edit `.env` and set:

```text
GROQ_API_KEY=your_actual_key
GROQ_MODEL=llama-3.3-70b-versatile
```

Run the main experience:

```powershell
python main.py examples/buggy_code.py --verdict
```

Run only the Critic, with no debate:

```powershell
python main.py examples/buggy_code.py --solo
```

Run a specific mode:

```powershell
python main.py examples/buggy_code.py --mode roast --verdict
python main.py examples/buggy_code.py --mode standard --verdict
python main.py examples/buggy_code.py --mode deep --verdict
```

Override the round count:

```powershell
python main.py examples/buggy_code.py --mode deep --rounds 3 --verdict
```

Show the source file before the review:

```powershell
python main.py examples/buggy_code.py --show-code --verdict
```

## Execution Flow

This is the current runtime path when you run:

```powershell
python main.py examples/buggy_code.py --verdict
```

1. `main.py` parses CLI arguments.
2. `main.py` reads the target code file.
3. `main.py` detects the language from the file extension.
4. `main.py` chooses the review mode.
5. `core.debate.run_debate()` creates a `DebateState`.
6. The Critic performs the initial structured JSON review.
7. The Advocate streams a prose rebuttal.
8. For each remaining round, the Critic and Advocate stream more prose turns.
9. The full transcript is stored in `DebateState.transcript`.
10. If `--verdict` is passed, the Judge reads the state and returns structured JSON.
11. `main.py` renders the debate and verdict in the terminal using Rich.

The high-level flow looks like this:

```text
source file
   |
   v
main.py
   |
   v
run_debate()
   |
   +--> Critic initial JSON review
   |
   +--> Advocate rebuttal
   |
   +--> Critic rebuttal
   |
   +--> Advocate rebuttal
   |
   v
DebateState transcript
   |
   v
Judge verdict, if --verdict is enabled
```

## Main Files And Responsibilities

### `main.py`

`main.py` is the CLI entry point and terminal renderer.

It handles:

- CLI flags such as `--mode`, `--rounds`, `--solo`, `--verdict`, and `--show-code`.
- File reading.
- Language detection from extensions like `.py`, `.js`, `.ts`, `.go`, and `.rs`.
- Calling either the solo Critic flow or the full debate flow.
- Rendering output using Rich panels, tables, syntax highlighting, and rules.

Important functions/classes:

- `detect_language(path)`: maps file extensions to syntax names.
- `render_item(item)`: renders one review issue.
- `render_review_panel(review)`: renders the Critic's structured review.
- `render_verdict(verdict)`: renders the Judge's structured verdict.
- `TerminalDebateListener`: receives streamed debate events and prints them.
- `main()`: wires the CLI together.

### `core/debate.py`

This file owns the debate orchestration.

It defines:

- `DebateListener`: a protocol for anything that wants to receive debate events.
- `_NullListener`: a no-op listener for non-interactive use.
- `_stream_turn(...)`: runs one streamed Critic or Advocate turn.
- `run_debate(...)`: runs the full debate and returns a `DebateState`.

The debate order is:

1. Round 1 Critic structured review.
2. Round 1 Advocate response.
3. Round 2 Critic response.
4. Round 2 Advocate response.
5. Continue until `max_rounds`.

The initial Critic review is JSON because it needs to fit the `CriticReview`
schema. Later debate turns are streamed prose.

### `core/llm.py`

This file is the Groq integration layer.

It handles:

- Loading `.env`.
- Reading `GROQ_API_KEY`.
- Reading `GROQ_MODEL`.
- Creating a singleton Groq client.
- Calling the model in JSON mode.
- Calling the model in streaming mode.

Important functions:

- `get_config()`: validates the API key and model config.
- `get_client()`: creates or reuses the Groq client.
- `complete_json(...)`: calls the model and requests JSON output.
- `complete_stream(...)`: streams model text chunks.

If the API key is missing or still set to the placeholder value, the app raises
a clear error telling you to configure `.env`.

### `core/models.py`

This file defines the structured data contracts with Pydantic.

Main models:

- `ReviewItem`: one issue found by the Critic.
- `CriticReview`: the Critic's opening structured review.
- `DebateMessage`: one message in the debate transcript.
- `DebateState`: the full state passed through the debate.
- `ActionItem`: one Judge-recommended fix.
- `Verdict`: the Judge's final structured result.

Important type aliases:

- `Category`: `BUG`, `SECURITY`, `EDGE_CASE`, `PERF`, `DESIGN`, `STYLE`.
- `Severity`: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
- `AgentName`: `CRITIC`, `ADVOCATE`.

The models are important because they make LLM output less loose. The Critic and
Judge must return JSON that can be parsed into these schemas.

### `core/modes.py`

This file defines review modes.

Modes:

- `roast`: 2 rounds, short, funny, brutal, but still technically grounded.
- `standard`: 3 rounds, professional default.
- `deep`: 5 rounds, more architectural and senior-engineer focused.

Important pieces:

- `ReviewMode`: enum of available modes.
- `MAX_ROUNDS`: default round count per mode.
- `_parse_sections(text)`: parses mode prompt files into agent-specific chunks.
- `load_addendum(mode, agent)`: loads the mode overlay for an agent.
- `apply_addendum(base_prompt, mode, agent)`: appends the overlay to a base prompt.

`standard` has no overlay. It uses the base prompts directly.

### `core/transcript.py`

This file builds the prompts sent to the agents during the debate.

It handles:

- Turning the Critic's JSON review into readable markdown.
- Formatting the full debate transcript.
- Building the user prompt for each Critic or Advocate turn.
- Building the user prompt for the Judge.

Important functions:

- `_render_initial_review(content)`: converts JSON review content into readable text.
- `_format_transcript(state)`: renders the transcript so far.
- `build_debate_user_prompt(state, role, round_number)`: builds a debate-turn prompt.
- `build_judge_user_prompt(state)`: builds the Judge prompt.

This file is what lets each agent see the original code and the full debate so
far, instead of responding only to the last message.

### `core/text.py`

This file currently has one helper:

- `number_lines(code)`: prefixes source code with line numbers.

Line numbering is important because the agents are instructed to cite specific
lines in findings, rebuttals, and action items.

### `agents/critic.py`

This file wraps the Critic agent.

It loads `agents/prompts/critic_system.md`, applies the selected mode overlay,
and calls the LLM.

Functions:

- `review(...)`: produces the initial structured JSON review.
- `rebut_stream(...)`: streams a prose debate response in later rounds.

The Critic's initial review uses `complete_json(...)` and is parsed into
`CriticReview`.

### `agents/advocate.py`

This file wraps the Advocate agent.

It loads `agents/prompts/advocate_system.md`, applies the selected mode overlay,
and streams a rebuttal using the current `DebateState`.

Function:

- `rebut_stream(...)`: streams the Advocate's prose response.

The Advocate does not return JSON. Its job is argumentative prose.

### `agents/judge.py`

This file wraps the Judge agent.

It loads `agents/prompts/judge_system.md`, applies the selected mode overlay,
and asks the LLM for a structured verdict.

Function:

- `synthesize(state)`: returns a parsed `Verdict`.

The Judge uses a lower temperature than the debate agents because the verdict
should be more stable and less performative.

## Prompt System

The agents are mostly defined by markdown prompt files.

### Base prompts

| Prompt | Purpose |
|---|---|
| `agents/prompts/critic_system.md` | Defines the Critic's strict review personality and JSON schema |
| `agents/prompts/advocate_system.md` | Defines the Advocate's pragmatic rebuttal personality |
| `agents/prompts/judge_system.md` | Defines the Judge's impartial verdict behavior and JSON schema |

### Mode overlays

| Overlay | Purpose |
|---|---|
| `agents/prompts/modes/roast.md` | Makes each agent sharper, shorter, and funnier |
| `agents/prompts/modes/deep.md` | Makes each agent more architectural and detailed |

Mode overlays are split into sections:

```markdown
## CRITIC
...

## ADVOCATE
...

## JUDGE
...
```

`core/modes.py` parses these sections and appends only the relevant section to
the relevant agent's base prompt.

## Data Flow Details

### Initial Critic review

Input:

- Source code.
- Detected language.
- Review mode.
- Critic system prompt.

Output:

- `CriticReview`.

Shape:

```json
{
  "summary": "Short summary",
  "items": [
    {
      "category": "BUG",
      "severity": "HIGH",
      "line_number": 12,
      "issue": "Concrete issue",
      "suggestion": "Concrete fix"
    }
  ]
}
```

### Debate turns

Input:

- Source code with line numbers.
- Full debate transcript so far.
- Current role: `CRITIC` or `ADVOCATE`.
- Current round number.
- Agent system prompt plus mode overlay.

Output:

- Streamed prose chunks.
- Final text stored in a `DebateMessage`.

### Judge verdict

Input:

- Source code with line numbers.
- Full debate transcript.
- Judge system prompt plus mode overlay.

Output:

- `Verdict`.

Shape:

```json
{
  "summary": "Overall assessment",
  "score": 6,
  "critic_wins": ["..."],
  "advocate_wins": ["..."],
  "strengths": ["..."],
  "action_items": [
    {
      "priority": "HIGH",
      "description": "Fix the SQL query by using parameters.",
      "affected_lines": [16, 17]
    }
  ],
  "winner": "CRITIC",
  "winner_reasoning": "The Critic proved the highest-risk issues."
}
```

## Example Code

`examples/buggy_code.py` is a test fixture with intentional issues.

It includes:

- SQL injection through string concatenation.
- A mutable default argument.
- Mutation while iterating a list.
- Division by zero on empty input.
- A hardcoded secret-looking API key.
- `eval()` on file contents.
- A bare `except` that hides errors.

This file is useful for testing whether the Critic, Advocate, Judge, and modes
are behaving as expected.

## How To Add A New Mode

1. Add a new enum value in `core/modes.py`.
2. Add its default round count to `MAX_ROUNDS`.
3. Create a new file in `agents/prompts/modes/`, for example:

```text
agents/prompts/modes/interview.md
```

4. Give the file these sections:

```markdown
# Interview Mode

## CRITIC
Instructions for the Critic.

## ADVOCATE
Instructions for the Advocate.

## JUDGE
Instructions for the Judge.
```

5. Run:

```powershell
python main.py examples/buggy_code.py --mode interview --verdict
```

You will also need to ensure `main.py` accepts the new enum value through the
existing `choices=[m.value for m in ReviewMode]` logic.

## How To Add A New Agent

The planned next agent is the Fixer.

A clean implementation would likely add:

```text
agents/fixer.py
agents/prompts/fixer_system.md
core/fixes.py
```

The likely flow would be:

1. Run the debate.
2. Run the Judge.
3. Pass the original code and `Verdict.action_items` to the Fixer.
4. Ask the Fixer to return fixed code plus explanations.
5. Generate a diff with Python's `difflib`.
6. Show the diff before applying or saving changes.

The important constraint from the roadmap: the Fixer should only fix issues
identified in the Judge's verdict. It should not perform random cleanup.

## Design Decisions Already Made

### Structured JSON for important outputs

The Critic's opening review and the Judge's verdict use JSON mode and Pydantic
validation. This keeps important output machine-readable.

### Streamed prose for debate turns

The Critic and Advocate stream later debate turns. This makes the CLI feel live
and gives the product its main personality.

### Prompt overlays instead of duplicate prompts

Modes do not duplicate entire system prompts. They append focused overlays on
top of the base agent prompts. This keeps the core identities consistent while
letting tone and depth change.

### Full transcript in every debate prompt

Each debate turn receives the full transcript so far. This allows agents to
refer back to earlier points and avoid acting like isolated one-shot calls.

### Hand-written orchestration for now

The debate loop is currently plain Python. LangGraph is planned later, after the
product behavior is proven.

## Known Limitations

- There are no automated tests yet.
- There is no web UI yet.
- There is no Fixer agent yet.
- Reviews require a configured Groq API key.
- The app reviews one file at a time.
- There is no persistence or review history.
- The current orchestration is linear and local, not a reusable graph.

## Good Next Steps

1. Add tests for `core.modes`, `core.text`, and `core.transcript`.
2. Add the Fixer agent and diff generation.
3. Add a small test suite around `examples/buggy_code.py` expectations.
4. Add LangGraph once the agent behavior feels stable.
5. Build a FastAPI backend and streaming UI.

## Quick Mental Model

Think of the project as four layers:

```text
CLI layer
  main.py renders and handles user commands

Orchestration layer
  core/debate.py decides who speaks when

Agent layer
  agents/*.py load prompts and call the LLM

Prompt and schema layer
  agents/prompts/*.md define behavior
  core/models.py defines valid structured output
```

When debugging behavior, use this rule:

- If the terminal output looks wrong, start in `main.py`.
- If turn order is wrong, start in `core/debate.py`.
- If an agent sees the wrong context, start in `core/transcript.py`.
- If JSON parsing fails, inspect `core/models.py` and the relevant system prompt.
- If tone or reasoning is bad, edit the relevant prompt or mode overlay.
- If API calls fail, inspect `.env` and `core/llm.py`.

