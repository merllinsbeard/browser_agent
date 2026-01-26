# CLAUDE.md
Guidance for Claude Code when working in this repository.

## Goal
Build an autonomous browser AI agent that controls a visible (headful) browser to complete arbitrary multi-step tasks.
The user provides a free-form task in natural language; the agent runs autonomously until it needs user input or finishes.

## Non-Negotiable Constraints (from the test)
- NO task-specific scripts (no predefined step lists per use case).
- NO hardcoded selectors (CSS/XPath/QA attributes).
- NO URL hints or per-site navigation assumptions.
- NO per-site branching (e.g., `if "hh.ru" in url: ...` is forbidden).
- Runtime page text/ARIA is allowed ONLY as observed data (not hardcoded strings in code).

## Tech Decisions (locked for MVP)
- Language: Python
- Env/deps: uv
- Browser: Playwright (headful + persistent context via user_data_dir)
- Agent framework: OPENAI Agents SDK
- MCP: optional for dev/debug; runtime must work without MCP.

## Required Components
1) Sub-agent architecture (at least one): e.g., Planner + Navigator + Safety.
2) Error handling: retries, recovery strategies, “stuck” detection.
3) Security layer: confirm before destructive actions.
4) Context management: never send full HTML/DOM; summarize and limit tokens.

## Core Design: Element Registry (no hardcoded selectors)
The model never writes selectors. It only acts on element_id returned by observe().

observe() returns a compact snapshot:
- url, title
- interactive_elements: [{id, role, name, aria_label, placeholder, value_preview, bbox}]
- visible_text_excerpt (trimmed)
- screenshot_path (optional)
- notes: popups/overlays detected, navigation in progress, etc.

The agent chooses actions:
- CLICK {element_id}
- TYPE  {element_id, text}
- PRESS {key}
- SCROLL {dx, dy}
- NAVIGATE {url}
- WAIT {condition/timeout}
- EXTRACT {target}  (generic extraction helper)
- DONE {summary}

Executor maps element_id -> Playwright locator dynamically (no stored selectors).

## Tool Contract (keep tools dumb & inspectable)
Tools must be pure and return structured results:
- browser.observe() -> PageSnapshot
- browser.act(Action) -> ActionResult
- browser.screenshot() -> path
- user.ask(question) -> answer (only when required)
- user.confirm(destructive_action_summary) -> yes/no

## Security Policy
Always require user.confirm() for:
- deleting emails / moving to spam/trash
- sending forms / applying to jobs
- finalizing checkout / payment confirmation
- any irreversible action

## Context Budget Rules
- interactive_elements: top N (e.g., 40–80) by visibility + relevance heuristic
- visible_text_excerpt: max K chars/tokens (e.g., 2–4k chars)
- never include full DOM; no full-page dumps
- keep a running task memory: completed steps summary + open questions (short)

## Recovery Strategy
When an action fails:
- re-observe; detect overlays/popups; try dismiss
- wait for network/selector; retry with backoff
- if stuck for M steps: navigate back/reload; ask user if login/2FA needed

## Definition of Done (what must be demo-able)
- Visible browser window (not headless).
- Persistent session: user logs in once; agent continues without losing state.
- Autonomy: can run a novel task without scripted steps.
- Sub-agent + security confirm implemented.
- Context mgmt present (no full-page stuffing).
- `scripts/run.py` interactive CLI + `scripts/eval.py` generic smoke.

## Commands (uv)
uv pip install -e ".[dev]"
uv run python -m browser_agent.cli
uv run python scripts/eval.py
uv run pytest
