# Future Work

The project is feature-complete per the original 9-phase roadmap. The real
question now isn't "what feature is missing" — it's **"what gives this the
most portfolio weight per hour of work."** Here is an opinionated tier list.

## Tier 1 — Force multipliers (do these first)

These massively change how the project lands when a recruiter clicks the
GitHub link.

1. **README with screenshots, a GIF of the live debate streaming, the
   LangGraph Mermaid diagram embedded, and a "how to run" block.** Right now
   the repo has no description — a recruiter sees nothing in 10 seconds and
   bounces. This is the single highest-leverage improvement.
2. **Deploy to Fly.io or Railway.** Backend + frontend behind one URL. Turns
   the project from "code on GitHub" into "click here to try it." Friends,
   recruiters, and tweets can all link to a live thing.

## Tier 2 — High signal, low effort polish

3. **Shareable review URLs** — `/r/<review-id>` permalinks. The DB already
   stores everything; just a route + a small frontend handler.
4. **Score-trend chart in the history modal** — "your code is getting better
   over time." Roadmap Phase 8 mentioned this; finishing it closes the spec.
5. **Export verdict as markdown** — one button that copies a clean report to
   the clipboard, ready to paste into a PR. Real users would actually use it.
6. **Mode-specific visual flair** — the roadmap explicitly called for
   Roast = dark + flames, Deep = academic theme. Currently all modes look
   identical. ~30 minutes of CSS.

## Tier 3 — Engineering maturity signals

7. **GitHub Actions CI** — type-check Python + frontend on every push. Green
   badge in the README.
8. **Tests for the non-LLM bits** — `core/personas`, `core/modes`,
   `core/graph` routing logic. Maybe 100 lines of pytest. Shows you write
   tests.

## Tier 4 — Feature extensions (pick one if you want depth over breadth)

9. **Git / PR integration** — point at a GitHub PR URL, review only the
   changed lines. Real-world utility.
10. **Custom personas via the UI** — users write their own persona prompt,
    save to DB. Closes the "extensible system" story.
11. **Debate replay at 2x** — playback past debates like a podcast.
    Demo-friendly, slightly playful.

---

**Strong recommendation:** Do Tier 1 next (README + deploy) before anything
else. A live URL plus a good README make every other improvement compound.
Without them, even Tier 4 extensions just sit unseen in a repo nobody opens.

### Tier 1 starter questions

When picking up Tier 1, two open decisions:

- **Deploy target:** Fly.io (free tier, Docker-friendly, good for full-stack)
  vs Railway (zero-config, slightly easier but with a ~$5/mo floor after the
  trial).
- **README scope:** quick (overview + setup + one screenshot) vs full
  (overview, architecture diagram, screenshots/GIF, prompt-engineering notes,
  per-phase breakdown). The full version reads like a case study and is what
  recruiters actually skim.
