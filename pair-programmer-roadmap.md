# Pair Programmer — Implementation Roadmap

> Two AI agents argue about your code so you don't have to argue with yourself.

---

## Project Overview

A multi-agent code review system where two AI agents with opposing philosophies — **The Critic** and **The Advocate** — debate your code in real time. A **Judge** synthesizes the debate into actionable feedback. Users can dial the intensity from a casual roast to a deep architectural review.

### Agent Personalities

- **The Critic** — Assumes the code is guilty until proven innocent. Hunts for bugs, security holes, edge cases, bad patterns, and performance traps. Thinks every function is too long and every variable is named wrong.
- **The Advocate** — Defends the developer's intent. Argues for pragmatism, pushes back on over-engineering, and highlights what the code does *well*. Keeps the Critic honest.
- **The Judge** — Silent observer. Reads the full debate transcript, decides who made better points, and produces a final structured verdict with concrete action items.
- **The Fixer** (extension) — Takes the Judge's verdict and rewrites the code. Shows a clean diff of what changed and why.

---

## Phase 1: Foundation — Single Agent Review

**Goal:** Get one agent talking about code. Prove you can send code to an LLM and get structured feedback back.

**Verifiable Output:** A Python script that takes a code file as input and prints a structured review to the terminal.

### Steps

1. **Project setup**
   - Initialize repo, set up virtual environment, install dependencies (`langchain`, `langchain-anthropic` or `openai`, `python-dotenv`).
   - Create a clean folder structure:
     ```
     pair-programmer/
     ├── agents/
     │   ├── critic.py
     │   ├── advocate.py
     │   ├── judge.py
     │   └── prompts/
     │       ├── critic_system.md
     │       ├── advocate_system.md
     │       └── judge_system.md
     ├── core/
     │   ├── debate.py
     │   └── models.py
     ├── examples/
     │   └── sample_code.py
     ├── main.py
     ├── .env
     └── requirements.txt
     ```
   - Set up API keys in `.env`, confirm you can make a basic LLM call.

2. **Define the Critic's system prompt**
   - Write `critic_system.md` — this is where the personality lives. Be specific: what does the Critic look for? In what order? What tone does it use? What format should its output follow?
   - The prompt should instruct the agent to return structured output (use a consistent format — bullet points with categories like `[BUG]`, `[SECURITY]`, `[STYLE]`, `[PERF]`, `[EDGE_CASE]`).
   - Test the prompt directly in a playground first. Iterate until the tone and structure feel right.

3. **Build the Critic agent**
   - Create `critic.py` — a function/class that takes code as input, loads the system prompt, calls the LLM, and returns the structured review.
   - Use Pydantic models in `models.py` to define the review schema (e.g., `ReviewItem` with fields: `category`, `severity`, `line_number`, `issue`, `suggestion`).
   - Parse the LLM output into these models (start with structured output / JSON mode if your provider supports it, otherwise parse manually).

4. **Wire up the CLI entry point**
   - `main.py` reads a code file from a CLI argument, passes it to the Critic, prints the review.
   - Test with 3-4 different code samples (one clean, one buggy, one with security issues, one with style problems). Sanity check: does the Critic catch what you'd expect?

### Checkpoint

Run `python main.py examples/sample_code.py` and get a clean, structured, useful review printed to your terminal. If the Critic's feedback is generic or useless, fix the prompt before moving on.

---

## Phase 2: The Debate Loop — Two Agents Talking

**Goal:** The Critic and Advocate go back and forth. Each agent sees the other's last message and responds.

**Verifiable Output:** A terminal output showing a multi-round debate (at least 3 rounds) between two agents about a piece of code.

### Steps

1. **Build the Advocate agent**
   - Write `advocate_system.md`. The Advocate's job is NOT to blindly praise — it should defend the code's intent, argue for simplicity, acknowledge valid criticisms but pushback on nitpicks, and highlight strengths the Critic ignored.
   - Build `advocate.py` with the same interface as the Critic.
   - Test it in isolation: give it code + a Critic's review and see if the rebuttal makes sense.

2. **Design the debate state**
   - In `models.py`, define a `DebateState` — this is the shared state that flows through the debate. It should contain:
     - `code`: the original code being reviewed
     - `language`: detected programming language
     - `transcript`: list of `DebateMessage` objects (`agent_name`, `round_number`, `content`)
     - `current_round`: integer
     - `max_rounds`: integer (configurable)
   - This is your **state graph node** if you later move to LangGraph.

3. **Build the debate orchestrator**
   - In `debate.py`, write the core loop:
     ```
     for round in range(max_rounds):
         critic_response = critic.review(code, transcript_so_far)
         add to transcript
         advocate_response = advocate.respond(code, transcript_so_far)
         add to transcript
     ```
   - Each agent receives the FULL transcript so far (not just the last message). This lets them reference earlier points, which makes the debate feel real.
   - Print each message to the terminal as it arrives (stream if possible — watching the debate unfold live is half the fun).

4. **Tune the debate dynamics**
   - Run 5+ test debates. Watch for failure modes:
     - Agents agreeing too quickly (boring) — fix: instruct agents to find at least one point of disagreement per round even if they agree overall.
     - Agents repeating themselves — fix: add "do not repeat points already made" to the system prompts + include round number context.
     - Advocate being a pushover — fix: strengthen the Advocate's instructions to actively challenge the Critic's severity ratings.
     - Debates going in circles — fix: instruct agents to introduce NEW observations each round.
   - Adjust `max_rounds` — 3 rounds is usually the sweet spot. 2 feels rushed, 4+ gets repetitive.

### Checkpoint

Run a debate on a real piece of code. Read the full transcript. Does it feel like two engineers actually arguing? Do both agents make points you hadn't considered? If yes, move on. If it feels like two bots taking turns generating lists, rewrite the prompts.

---

## Phase 3: The Judge — Synthesizing the Verdict

**Goal:** A third agent reads the full debate and produces a final, structured, actionable review.

**Verifiable Output:** A clean verdict document with scores, a winner declaration, and prioritized action items.

### Steps

1. **Design the verdict schema**
   - In `models.py`, define `Verdict`:
     - `summary`: 2-3 sentence overall assessment
     - `score`: code quality score (e.g., 1-10)
     - `critic_wins`: list of points where the Critic was right
     - `advocate_wins`: list of points where the Advocate was right
     - `action_items`: prioritized list of things to fix (each with `priority`, `description`, `affected_lines`)
     - `strengths`: what the code does well (important — people need positive feedback too)
     - `winner`: which agent made the stronger overall case

2. **Build the Judge agent**
   - Write `judge_system.md`. The Judge must be impartial, evidence-based, and concrete. It should weigh arguments by their technical merit, not by how confidently they were stated.
   - The Judge should explicitly call out when an agent made a weak argument or was wrong.
   - Use structured output / JSON mode to get the verdict in your Pydantic schema.

3. **Integrate into the pipeline**
   - After the debate loop completes, pass the full transcript to the Judge.
   - The Judge should receive: original code + full debate transcript + language context.
   - Print the verdict in a nicely formatted way (even in terminal — use rich formatting, colors, or just clean markdown).

4. **Validate verdict quality**
   - Run 5+ end-to-end reviews. For each one, manually assess:
     - Are the action items actually useful?
     - Did the Judge correctly identify the stronger arguments?
     - Is the score reasonable?
   - If the Judge is too generous or too harsh, adjust the system prompt.

### Checkpoint

Run the full pipeline: code → debate → verdict. The verdict should be something you'd actually want to read and act on. Show it to a friend — if they say "this is actually useful," Phase 3 is done.

---

## Phase 4: Review Modes — Roast vs. Deep Review

**Goal:** Let users choose the intensity. A "roast" is fast, funny, and brutal. A "deep review" is thorough, architectural, and serious.

**Verifiable Output:** Running the same code through both modes produces noticeably different outputs in tone, depth, and structure.

### Steps

1. **Define the mode configurations**
   - Create a `ReviewMode` enum/config:
     - `ROAST` — 2 rounds, aggressive tone, short responses, humor encouraged, focuses on the most embarrassing issues, the Judge's verdict is delivered as a comedy roast.
     - `STANDARD` — 3 rounds, professional tone, balanced depth. The default.
     - `DEEP_REVIEW` — 4-5 rounds, serious tone, covers architecture/design patterns/testability/maintainability, agents can request to "zoom in" on specific functions, Judge produces an extended report.
   - Each mode should modify: `max_rounds`, system prompt tone instructions, output length expectations, and what categories agents focus on.

2. **Create mode-specific prompt overlays**
   - Don't rewrite the entire system prompt per mode. Instead, create a base prompt + mode-specific addendum that gets appended.
   - For ROAST: "You are reviewing code as if you're performing at a comedy roast. Be funny but technically accurate. Every joke must be grounded in a real code issue. Use analogies, sarcasm, and exaggeration."
   - For DEEP_REVIEW: "You are conducting a senior-engineer-level architectural review. Consider SOLID principles, testability, error handling philosophy, dependency management, and how this code would behave at 100x scale."

3. **Implement mode selection in the CLI**
   - `python main.py examples/sample_code.py --mode roast`
   - `python main.py examples/sample_code.py --mode deep`
   - Default to `standard` if no mode specified.

4. **Test and refine each mode**
   - Run the same code through all three modes. The outputs should feel like three completely different experiences.
   - The ROAST should make you laugh. If it's not funny, the prompt needs work.
   - The DEEP_REVIEW should teach you something about software architecture. If it's surface-level, add more specific instructions about what "deep" means.

### Checkpoint

Run all three modes on the same code file. Show someone the outputs side-by-side without labels. They should be able to tell which is which instantly.

---

## Phase 5: The Fixer — Rewriting the Code

**Goal:** After the debate and verdict, a fourth agent rewrites the code incorporating the feedback. Shows a before/after diff.

**Verifiable Output:** A fixed version of the code + a readable diff with inline explanations of each change.

### Steps

1. **Build the Fixer agent**
   - Write `fixer_system.md`. The Fixer receives: original code, the Judge's verdict (specifically the action items), and must produce corrected code.
   - Critical instruction: the Fixer should ONLY fix issues identified in the verdict. No unsolicited changes. This keeps the fix trustworthy.
   - The Fixer should also produce a changelog: for each change, explain WHAT changed and WHY (referencing the specific action item).

2. **Generate the diff**
   - Use Python's `difflib` to generate a unified diff between original and fixed code.
   - Annotate the diff with the Fixer's explanations (map each change to the corresponding verdict action item).

3. **Add a confirmation step**
   - Before applying fixes, show the user the proposed changes and let them approve/reject individual fixes (this is where it starts feeling like a real dev tool).
   - In the CLI, this can be a simple y/n per change.

4. **Test the Fixer's accuracy**
   - Run 5+ fixes. For each, verify:
     - Does the fixed code actually run?
     - Did it only change what the verdict said to change?
     - Are the changes correct?
   - If the Fixer introduces new bugs, add stronger constraints in the prompt.

### Checkpoint

Run the full pipeline end-to-end: code → debate → verdict → fix. The fixed code should be demonstrably better AND still functional. Run whatever tests/linters you have on both versions.

---

## Phase 6: Migrate to LangGraph

**Goal:** Replace the hand-rolled orchestration loop with a proper LangGraph state graph. This makes the project architecturally impressive and portfolio-ready.

**Verifiable Output:** The exact same functionality as before, but orchestrated through a LangGraph graph with visible nodes, edges, and state transitions.

### Steps

1. **Map your current flow to a graph**
   - Draw the state graph on paper first:
     ```
     [START] → [Critic] → [Advocate] → [Should Continue?]
                                            ├── YES → [Critic] (loop)
                                            └── NO  → [Judge] → [Fixer?] → [END]
     ```
   - Identify the nodes (agent calls), edges (transitions), and conditional edges (round check, whether to invoke Fixer).

2. **Define the LangGraph state schema**
   - Convert your `DebateState` Pydantic model into a LangGraph `TypedDict` or `State` class.
   - Make sure the state captures everything needed for any node to do its job.

3. **Build the graph**
   - Create each node as a function that takes state and returns updated state.
   - Wire up edges and conditional edges.
   - Add the `should_continue` conditional that checks round count.
   - Compile the graph.

4. **Add LangGraph-specific features**
   - **Streaming**: Stream agent outputs token-by-token through the graph (this is where the live debate experience gets really good).
   - **Human-in-the-loop**: Add an interrupt before the Fixer node so the user can approve/reject fixes.
   - **Visualization**: Export the graph as a Mermaid diagram for your README.

5. **Verify feature parity**
   - Run the same test cases from earlier phases. The output should be identical (or better, thanks to proper state management). If anything regressed, fix it before moving on.

### Checkpoint

The LangGraph graph runs all modes (roast, standard, deep) correctly. You can export a Mermaid diagram of the graph. Streaming works for the debate.

---

## Phase 7: The UI

**Goal:** Build a web frontend that makes the debate experience visual and fun.

**Verifiable Output:** A web app where you paste code, pick a mode, and watch two agents argue in a chat-like interface.

### Steps

1. **Build the backend API**
   - FastAPI or Flask. Endpoints:
     - `POST /review` — accepts `{code, language, mode}`, returns a streaming response (SSE or WebSocket) of the debate + verdict.
     - `GET /review/{id}` — retrieves a past review.
   - Use server-sent events (SSE) for streaming — it's simpler than WebSockets and perfect for this use case.

2. **Design the frontend**
   - Two-panel layout:
     - **Left**: Code editor (use Monaco or CodeMirror).
     - **Right**: Debate panel — a chat-like interface where messages from the Critic and Advocate appear in real time, styled differently (e.g., red for Critic, blue for Advocate).
   - Below the debate: the Judge's verdict card.
   - Below the verdict: the Fixer's diff view (use a side-by-side diff component).
   - Top bar: mode selector (Roast / Standard / Deep Review) with distinct visual styling per mode.

3. **Implement streaming on the frontend**
   - As debate messages arrive via SSE, append them to the chat panel with typing animations.
   - The "live debate" feeling is the killer feature. Don't skip this.

4. **Add mode-specific UI flavor**
   - ROAST mode: dark theme, flame emojis, shake animations on harsh critiques.
   - STANDARD mode: clean professional look.
   - DEEP REVIEW mode: academic/serious theme, expandable sections for deep dives.

5. **Polish**
   - Add syntax highlighting in the code editor.
   - Language auto-detection.
   - Copy-to-clipboard on the verdict and fixed code.
   - Loading states, error handling, empty states.

### Checkpoint

Someone who isn't you can open the web app, paste code, pick "Roast," and watch two agents argue about their code. They should say "this is cool" without you explaining anything.

---

## Phase 8: Persistence and History

**Goal:** Save reviews so users can track how their code improves over time.

**Verifiable Output:** A history page showing past reviews with diffs and scores.

### Steps

1. **Set up a database**
   - SQLite for local dev, PostgreSQL for production.
   - Tables: `reviews` (id, code, language, mode, score, created_at), `debate_messages` (review_id, agent, round, content), `verdicts` (review_id, summary, score, action_items_json), `fixes` (review_id, original_code, fixed_code, diff).

2. **Save reviews automatically**
   - After a full pipeline run, persist everything.
   - Generate a shareable link for each review.

3. **Build the history view**
   - List of past reviews with: date, language, mode, score, first line of code (preview).
   - Click to expand and see the full debate + verdict.
   - Score trend chart over time ("your code is getting better").

4. **Add comparison features**
   - Let users re-review updated code and see a side-by-side of old review vs. new review.
   - Highlight which action items from the old review were addressed.

### Checkpoint

You can run 5 reviews, go to the history page, and see a trend of your scores. You can click into any past review and read the full debate.

---

## Phase 9: Extensions and Polish

**Goal:** Add the features that make this go from "cool project" to "I'd actually use this."

### Extension Ideas (pick based on time)

- **Git integration** — Point it at a PR diff instead of a file. Review only the changed lines.
- **Team mode** — Multiple users can submit code, agents remember recurring issues across the team's codebase and call out patterns.
- **Custom personas** — Let users define their own agent personalities ("review this like a FAANG interviewer" or "review this like my very patient mentor").
- **Language-specific expertise** — Agents adapt their review based on language idioms (Pythonic code, idiomatic Rust, etc.).
- **CI/CD integration** — Run the review automatically on every push via GitHub Actions.
- **Debate replay** — A playback mode where you can watch the debate unfold at 2x speed like a podcast.

---

## Tech Stack Summary

| Layer | Technology |
|---|---|
| Orchestration | LangGraph |
| LLM | Claude API (or OpenAI) |
| Backend | FastAPI + SSE |
| Frontend | React (or Next.js) |
| Database | SQLite → PostgreSQL |
| Code Editor | Monaco / CodeMirror |
| Diff View | react-diff-viewer or similar |
| Deployment | Docker + Railway / Fly.io |

---

## Timeline Estimate

| Phase | Estimated Time | Cumulative |
|---|---|---|
| Phase 1: Foundation | 1-2 days | 1-2 days |
| Phase 2: Debate Loop | 2-3 days | 3-5 days |
| Phase 3: Judge | 1-2 days | 4-7 days |
| Phase 4: Review Modes | 1-2 days | 5-9 days |
| Phase 5: Fixer | 2-3 days | 7-12 days |
| Phase 6: LangGraph | 2-3 days | 9-15 days |
| Phase 7: UI | 3-5 days | 12-20 days |
| Phase 8: Persistence | 2-3 days | 14-23 days |
| Phase 9: Extensions | 3-5 days | 17-28 days |

---

## The One Rule

**Do not move to the next phase until the current phase's checkpoint passes.** Rushing to the UI before the debate quality is dialed in will give you a pretty wrapper around garbage output. The agents' prompt engineering IS the product — everything else is packaging.
