# PRD: ReAct Agent Architecture with OpenAI Agents SDK

## Introduction

Rewrite the browser agent from a linear plan executor to a true ReAct (Reasoning + Acting) agent using the OpenAI Agents SDK. The current implementation creates a plan once via LLM, then executes steps deterministically with no inter-step reasoning, no failure recovery, and broken page observation. The rewrite replaces this with SDK-native agents that reason on every turn, observe results, adapt to failures, and use Playwright's async API throughout.

The core architecture becomes: **Planner Agent** decomposes the task into a high-level plan and hands off to **Navigator Agent**, which uses browser tools in a ReAct loop (observe → reason → act → observe → ...) powered by the SDK's built-in `Runner.run()` execution engine.

## Goals

- Replace custom FOR-loop orchestration with OpenAI Agents SDK `Runner.run()` ReAct loop
- Fix broken ARIA snapshot parsing so the agent can actually see page elements
- Replace wrong CSS `nth-of-type` selectors with Playwright `get_by_role()` locators
- Implement Planner → Navigator handoff using SDK's handoff mechanism
- Convert all browser actions to async `@function_tool` decorators
- Switch from sync to async Playwright throughout
- Replace frozen dataclasses with Pydantic BaseModel
- Achieve working end-to-end demo: agent observes, reasons, acts, recovers from failures
- Delete old test suite and write new tests for the new architecture

## User Stories

### US-001: Remove old test suite and dead code
**Description:** As a developer, I want to remove the old test suite and unused modules so subsequent stories can rewrite code without failing tests blocking commits.

**Acceptance Criteria:**
- [ ] Delete entire `tests/` directory
- [ ] Delete `src/browser_agent/core/recovery.py` (605 lines of dead code — never called from run.py)
- [ ] Delete `src/browser_agent/tools/hybrid_observe.py` (vision fallback not wired in)
- [ ] Delete `src/browser_agent/security/` directory (empty)
- [ ] Update `src/browser_agent/core/__init__.py`: remove all recovery.py imports (`RetryAttempt`, `RetryResult`, `StuckDetector`, `detect_and_handle_overlays`, `detect_stuck`, `needs_reobservation`, `retry_with_backoff`) and their `__all__` entries
- [ ] Update `scripts/run.py`: remove `StuckDetector` import and all `stuck_detector` usage (lines 16, 186, 263-271) — replace with a `pass` or simple comment placeholder. Do NOT rewrite run.py fully (that's US-011)
- [ ] Run `uv run python -c "import browser_agent"` — must succeed without ImportError
- [ ] Typecheck passes: `uv run mypy src/`

### US-002: Pydantic models
**Description:** As a developer, I want data models using Pydantic BaseModel so we get automatic validation, JSON serialization, and SDK-compatible structured output.

**Acceptance Criteria:**
- [ ] Rewrite `src/browser_agent/models/element.py`: replace `@dataclass(frozen=True)` with Pydantic `BaseModel` + `model_config = ConfigDict(frozen=True)`
- [ ] `BoundingBox`: fields `x: float, y: float, width: float, height: float` with `@field_validator` for non-negative width/height
- [ ] `InteractiveElement`: fields `ref: str, role: str, name: str = ""` (name is NOT required — many ARIA elements have empty names), `aria_label: str | None = None`, `placeholder: str | None = None`, `value_preview: str | None = None`, `bbox: BoundingBox | None = None`
- [ ] Rewrite `src/browser_agent/models/snapshot.py`: `PageSnapshot` as Pydantic BaseModel with `model_config = ConfigDict(frozen=True)`. Fields: `url: str, title: str, interactive_elements: list[InteractiveElement] = [], visible_text_excerpt: str = "", screenshot_path: str | None = None, notes: list[str] = [], version: int = 0`
- [ ] Rewrite `src/browser_agent/models/result.py`: `SuccessResult` and `FailureResult` as Pydantic BaseModel with `model_config = ConfigDict(frozen=True)`. Keep `success` and `error` as properties. Keep `success_result()` and `failure_result()` factory functions. Remove `updated_plan` field from SuccessResult (SDK handles replanning natively)
- [ ] Update `src/browser_agent/models/__init__.py` to export all new models
- [ ] `uv run python -c "from browser_agent.models import InteractiveElement, PageSnapshot, SuccessResult, FailureResult"` succeeds
- [ ] Typecheck passes: `uv run mypy src/`

### US-003: Fix ARIA snapshot parser
**Description:** As the agent, I need working page observation so I can see interactive elements. The current parser is fundamentally broken — it expects dict nodes with a `role` key, but Playwright's `aria_snapshot()` returns YAML where the role IS the dict key (e.g., `button "Submit"` is a key, not `{"role": "button", "name": "Submit"}`).

**Acceptance Criteria:**
- [ ] Rewrite `_traverse_aria_tree()` in `src/browser_agent/tools/observe.py` to handle the actual Playwright ARIA snapshot format
- [ ] After `yaml.safe_load()`, the parsed structure contains: (a) **string items** in lists like `'heading "Example Domain" [level=1]'`, (b) **dict items** where keys are like `'link "Learn more"'` or `'paragraph'` and values are content or children
- [ ] Use regex `r'^(\w+)(?:\s+"(.*)")?(?:\s+\[(.+)\])?$'` to parse role, name, attributes from both string items and dict keys
- [ ] `_traverse_aria_tree` recursively walks the parsed YAML: for each string item or dict key, extract (role, name) using the regex. If role is in `_ROLE_PRIORITY`, add to elements list. For dict values that are lists, recurse into children
- [ ] Skip keys starting with `/` (metadata like `/url`)
- [ ] Skip the `text` role (not interactive)
- [ ] Verified: `browser_observe()` on `https://example.com` returns at least 1 element (the "More information..." link). Test with: `uv run python -c "from playwright.sync_api import sync_playwright; from browser_agent.tools.observe import browser_observe; from browser_agent.core.registry import ElementRegistry; p = sync_playwright().start(); b = p.chromium.launch(); page = b.new_page(); page.goto('https://example.com'); r = ElementRegistry(); s = browser_observe(page, r); print(f'Found {len(s.interactive_elements)} elements'); [print(f'  {e.ref}: [{e.role}] {e.name!r}') for e in s.interactive_elements]; b.close(); p.stop()"`
- [ ] Typecheck passes: `uv run mypy src/`

### US-004: Element Registry with get_by_role locators
**Description:** As the agent, I need correct element locators. The current CSS `[role=X]:nth-of-type(N)` strategy is wrong — CSS `nth-of-type` works on HTML tag type, not role attribute, causing wrong elements to be clicked.

**Acceptance Criteria:**
- [ ] Change `RegistryEntry` in `src/browser_agent/core/registry.py` to store `role: str`, `name: str`, `nth: int` instead of `selector: str`. Use Pydantic BaseModel (consistent with US-002)
- [ ] Change `register_elements()` to accept `elements: list[InteractiveElement]` only (no selectors param). Internally, group elements by `(role, name)` tuple to compute `nth` index for disambiguation
- [ ] Change `get_locator()` to build locator as: `page.get_by_role(entry.role, name=entry.name).nth(entry.nth)` if name is non-empty, or `page.locator(f"[role={entry.role}]").nth(entry.nth)` if name is empty
- [ ] Update `ObservationResult` to Pydantic BaseModel
- [ ] Update `src/browser_agent/tools/observe.py`: call `registry.register_elements(elements)` without selectors
- [ ] Remove the `role_index_map` / `selectors` logic from `observe.py` (lines 82-88)
- [ ] Verified: after `browser_observe()` on `https://example.com`, `registry.get_locator(page, "elem-0")` returns a valid Locator that can be clicked without error
- [ ] Typecheck passes: `uv run mypy src/`

### US-005: Async browser context
**Description:** As the system, I need async Playwright support because the OpenAI Agents SDK is fully async (`Runner.run()` is a coroutine), and all `@function_tool` functions must be async.

**Acceptance Criteria:**
- [ ] Add `launch_persistent_context_async()` function to `src/browser_agent/core/browser.py` that uses `playwright.async_api` (`async_playwright`, `async BrowserContext`)
- [ ] Keep the existing sync `launch_persistent_context()` for backwards compatibility
- [ ] The async function has the same signature and behavior as the sync version
- [ ] Update `src/browser_agent/core/__init__.py` to also export `launch_persistent_context_async`
- [ ] Verified: `uv run python -c "import asyncio; from playwright.async_api import async_playwright; from browser_agent.core.browser import launch_persistent_context_async; asyncio.run(launch_persistent_context_async(async_playwright().start(), '/tmp/test-session'))"` — launches and closes without error (clean up after)
- [ ] Typecheck passes: `uv run mypy src/`

### US-006: OpenRouter async client for SDK
**Description:** As the system, I need the OpenAI Agents SDK configured to use OpenRouter (OpenAI-compatible API) so agents can make LLM calls through `Runner.run()`.

**Acceptance Criteria:**
- [ ] Update `src/browser_agent/core/llm.py`: add function `setup_openrouter_for_sdk()` that calls `set_default_openai_client()` from `agents` package with an `AsyncOpenAI` client configured for OpenRouter (`base_url="https://openrouter.ai/api/v1"`, `api_key` from `OPENROUTER_API_KEY` env var)
- [ ] Import: `from openai import AsyncOpenAI` and `from agents import set_default_openai_client`
- [ ] Keep existing sync `call_llm()` and `get_openrouter_client()` for now (will be removed when old code is fully replaced)
- [ ] Add `DEFAULT_SDK_MODEL` constant — set to `"google/gemini-2.5-flash-preview-05-20"` (current best flash model on OpenRouter)
- [ ] Update `src/browser_agent/core/__init__.py` to export `setup_openrouter_for_sdk` and `DEFAULT_SDK_MODEL`
- [ ] Verified: `uv run python -c "from browser_agent.core.llm import setup_openrouter_for_sdk; setup_openrouter_for_sdk(); print('SDK client configured')"` succeeds (requires OPENROUTER_API_KEY set)
- [ ] Typecheck passes: `uv run mypy src/`

### US-007: Browser tools as @function_tool
**Description:** As the SDK agent, I need browser actions exposed as `@function_tool` decorated async functions so the LLM can call them through the ReAct loop.

**Acceptance Criteria:**
- [ ] Create `src/browser_agent/tools/browser_tools.py` with a factory function `create_browser_tools(page, registry) -> list` that returns a list of `@function_tool` decorated async functions
- [ ] Import `from agents import function_tool`
- [ ] The factory uses closures so each tool captures `page` (async Playwright Page) and `registry` (ElementRegistry)
- [ ] Tools to create (each is an `async def` with `@function_tool` inside the factory):
  - `browser_observe() -> str` — calls observe logic, returns formatted string: "Page: {title}\nURL: {url}\n\nInteractive Elements:\n- elem-0: [{role}] \"{name}\"\n..." with up to 60 elements and 3000 chars visible text
  - `browser_click(element_id: str) -> str` — clicks element, returns success/failure message. Catches `StaleElementError` and `KeyError` with helpful messages
  - `browser_type(element_id: str, text: str) -> str` — types text into element, returns success/failure message
  - `browser_press(key: str) -> str` — presses keyboard key, returns success/failure message
  - `browser_scroll(direction: str) -> str` — scrolls page. `direction` is "up" or "down" (scroll by 500px). Returns success/failure message
  - `browser_navigate(url: str) -> str` — navigates to URL, returns success/failure. After successful navigate, increments registry version
  - `browser_wait(seconds: int) -> str` — waits specified seconds (max 10), returns message
  - `browser_extract(target: str) -> str` — extracts data from page (title, url, text, links, inputs), returns extracted data
  - `browser_done(summary: str) -> str` — signals task completion, returns the summary (this becomes the agent's final output)
- [ ] Each tool has a clear docstring (the LLM sees these to decide which tool to call)
- [ ] All tools use `await` for async Playwright operations (e.g., `await page.goto(url)`, `await locator.click()`)
- [ ] Update `src/browser_agent/tools/__init__.py` to export `create_browser_tools`
- [ ] Verified: `uv run python -c "from browser_agent.tools.browser_tools import create_browser_tools; print('Factory imported')"` succeeds
- [ ] Typecheck passes: `uv run mypy src/`

### US-008: Navigator Agent using SDK
**Description:** As the system, I need a Navigator agent built with the OpenAI Agents SDK that executes browser actions using the ReAct loop — the SDK automatically calls the LLM, which decides which tool to use, executes it, sees the result, and decides the next action.

**Acceptance Criteria:**
- [ ] Rewrite `src/browser_agent/agents/navigator.py`: delete the old `NavigatorAgent` class entirely
- [ ] Create function `create_navigator_agent(browser_tools: list) -> Agent` that returns an SDK `Agent` instance
- [ ] Import `from agents import Agent`
- [ ] The Agent is configured with:
  - `name="Browser Navigator"`
  - `instructions` — detailed system prompt explaining: (1) you control a browser via tools, (2) ALWAYS call browser_observe() first to see the page, (3) use element IDs from observation (elem-0, elem-1, ...) for click/type actions, (4) if an action fails, re-observe and try a different approach, (5) never repeat the exact same failed action, (6) call browser_done() when the task is complete, (7) if stuck after 3 failed attempts on the same goal, explain what's wrong
  - `tools=browser_tools` (the list from `create_browser_tools()`)
  - `model=DEFAULT_SDK_MODEL` (from core.llm)
- [ ] Update `src/browser_agent/agents/__init__.py` to export `create_navigator_agent`
- [ ] Verified: `uv run python -c "from browser_agent.agents import create_navigator_agent; print('Navigator factory imported')"` succeeds
- [ ] Typecheck passes: `uv run mypy src/`

### US-009: Planner Agent with handoff to Navigator
**Description:** As the system, I need a Planner agent that receives the user's task, creates a high-level plan, and hands off execution to the Navigator agent.

**Acceptance Criteria:**
- [ ] Rewrite `src/browser_agent/agents/planner.py`: delete the old `PlannerAgent` class entirely
- [ ] Create function `create_planner_agent(navigator_agent: Agent) -> Agent` that returns an SDK `Agent` with a handoff to Navigator
- [ ] Import `from agents import Agent`
- [ ] The Planner Agent is configured with:
  - `name="Task Planner"`
  - `instructions` — system prompt explaining: (1) you receive a user's browser automation task, (2) break it down into a high-level numbered plan (3-10 steps), (3) the plan should be general — do NOT include specific element IDs (the Navigator discovers those at runtime), (4) after creating the plan, hand off to the Browser Navigator to execute it, (5) example plan format: "1. Navigate to google.com\n2. Find the search box and type the query\n3. Press Enter to search\n4. Click the most relevant result\n5. Extract the needed information\n6. Signal completion"
  - `handoffs=[navigator_agent]`
  - `model=DEFAULT_SDK_MODEL`
- [ ] Update `src/browser_agent/agents/__init__.py` to export `create_planner_agent`
- [ ] Remove old `SafetyAgent` class from `safety.py` (safety will be handled in US-010)
- [ ] Update `src/browser_agent/agents/__init__.py`: remove `SafetyAgent` export, add `create_planner_agent` and `create_navigator_agent`
- [ ] Verified: `uv run python -c "from browser_agent.agents import create_navigator_agent, create_planner_agent; print('Both agent factories imported')"` succeeds
- [ ] Typecheck passes: `uv run mypy src/`

### US-010: Safety checks in browser tools
**Description:** As a user, I want the agent to confirm before destructive actions. Safety is enforced at CODE level (keyword matching in the tool functions), not LLM level — the LLM cannot bypass it.

**Acceptance Criteria:**
- [ ] Create `src/browser_agent/tools/safety.py` with function `is_destructive_action(action_description: str) -> bool` that checks for destructive keywords: "delete", "remove", "spam", "submit", "payment", "checkout", "confirm", "purchase", "buy", "order"
- [ ] Create async function `ask_user_confirmation(action_description: str) -> bool` that prints the action description to console (using `rich`) and prompts yes/no. Returns True if confirmed
- [ ] Integrate into `browser_click` and `browser_type` tools in `browser_tools.py`: before executing, get the element info from registry (`registry.get_element(element_id)`), check `is_destructive_action(f"{element.role} {element.name}")`. If destructive, call `ask_user_confirmation()`. If user declines, return "Action blocked by user — destructive action not confirmed" instead of executing
- [ ] The safety check is synchronous keyword matching (no LLM call) — deterministic and unbypassable
- [ ] Delete `src/browser_agent/agents/safety.py` (old SafetyAgent class) if not already deleted in US-009
- [ ] Verified: import succeeds: `uv run python -c "from browser_agent.tools.safety import is_destructive_action; print(is_destructive_action('delete account')); print(is_destructive_action('click search'))"` prints `True` then `False`
- [ ] Typecheck passes: `uv run mypy src/`

### US-011: Async run.py with Runner.run()
**Description:** As a user, I want the main CLI script to use the SDK's `Runner.run()` for true ReAct execution — the agent reasons on every step, adapts to failures, and completes tasks autonomously.

**Acceptance Criteria:**
- [ ] Rewrite `scripts/run.py` as fully async:
  - `async def main()` with `asyncio.run(main())` at bottom
  - Use `async_playwright()` context manager
  - Call `launch_persistent_context_async()` for browser setup
  - Call `setup_openrouter_for_sdk()` to configure the SDK client
  - Create browser tools: `tools = create_browser_tools(page, registry)`
  - Create agents: `navigator = create_navigator_agent(tools)` then `planner = create_planner_agent(navigator)`
  - Run: `result = await Runner.run(planner, task, max_turns=30)`
  - Import `from agents import Runner`
- [ ] Keep existing CLI argument parsing (argparse): `task`, `--session-dir`, `--headless`, `--auto-approve`, `--clean-cache`
- [ ] Keep Rich console output for welcome banner, task display, and completion
- [ ] After `Runner.run()` completes, print `result.final_output` as the completion report
- [ ] Handle `MaxTurnsExceeded` exception — print warning that agent reached turn limit
- [ ] Keep browser open after completion (same Ctrl+C behavior as current)
- [ ] Clean up old imports: remove `PlannerAgent`, `NavigatorAgent`, `SafetyAgent`, `StuckDetector`, `ContextTracker` (these are all replaced by SDK)
- [ ] Delete `src/browser_agent/core/context.py` (ContextTracker) — SDK manages context natively
- [ ] Update `src/browser_agent/core/__init__.py`: remove `ContextTracker` export and import
- [ ] Verified: `uv run python scripts/run.py --help` shows usage without errors
- [ ] Typecheck passes: `uv run mypy src/ scripts/`

### US-012: New test suite
**Description:** As a developer, I want tests for the new architecture to ensure reliability and catch regressions.

**Acceptance Criteria:**
- [ ] Create `tests/` directory with `__init__.py` and `conftest.py`
- [ ] `tests/models/test_element.py`: test InteractiveElement creation, optional name (empty string allowed), BoundingBox validation (negative width/height rejected), frozen immutability
- [ ] `tests/models/test_snapshot.py`: test PageSnapshot creation, default values, frozen immutability
- [ ] `tests/models/test_result.py`: test SuccessResult/FailureResult properties, factory functions
- [ ] `tests/tools/test_observe.py`: test `_traverse_aria_tree` with real ARIA snapshot samples. Include test data strings matching actual Playwright output format (from example.com and a more complex page). Verify correct element count, role extraction, name extraction
- [ ] `tests/tools/test_safety.py`: test `is_destructive_action` with destructive and non-destructive inputs
- [ ] `tests/core/test_registry.py`: test ElementRegistry: register_elements, get_locator with mock Page, version tracking, StaleElementError on version mismatch
- [ ] All tests use `pytest` and `pytest-asyncio` where needed
- [ ] `uv run pytest tests/ -v` — all tests pass
- [ ] Typecheck passes: `uv run mypy src/ tests/`

### US-013: End-to-end demo verification
**Description:** As a stakeholder, I want a working demo proving the ReAct architecture works — the agent observes, reasons, acts, and recovers from failures on a real browser task.

**Acceptance Criteria:**
- [ ] Run: `uv run python scripts/run.py "go to example.com and tell me what the page title is"` — agent completes the task
- [ ] Verify the agent's execution log shows the ReAct loop: (1) Planner creates plan, (2) handoff to Navigator, (3) Navigator calls browser_observe, (4) Navigator calls browser_navigate, (5) Navigator calls browser_observe again, (6) Navigator calls browser_extract or browser_done
- [ ] The agent uses at least 2 different tools in sequence (not just navigate + done)
- [ ] If an action fails (e.g., element not found), the agent re-observes and tries a different approach (visible in the execution log)
- [ ] Update `scripts/demo.py` to use the new async architecture (same pattern as run.py)
- [ ] Typecheck passes: `uv run mypy src/ scripts/`

## Functional Requirements

- FR-1: System must use OpenAI Agents SDK (`agents.Agent`, `agents.Runner`, `agents.function_tool`) for agent orchestration
- FR-2: All browser operations must use async Playwright (`playwright.async_api`)
- FR-3: LLM calls must go through OpenRouter via `set_default_openai_client()` with `AsyncOpenAI`
- FR-4: Agent must observe page state via ARIA snapshot before every action (browser_observe tool)
- FR-5: ARIA snapshot parser must correctly extract role and name from Playwright's format (`role "name" [attrs]`)
- FR-6: Element locators must use `page.get_by_role()` — NO CSS `nth-of-type` selectors
- FR-7: Agent must reason between actions — each tool result is fed back to the LLM for next decision
- FR-8: Agent must adapt to failures — re-observe, try different elements, try different approaches
- FR-9: Agent must never repeat the exact same failed action (SDK handles this via LLM memory)
- FR-10: Destructive actions must be blocked at CODE level (keyword matching) with user confirmation
- FR-11: Planner Agent creates high-level plan and hands off to Navigator Agent
- FR-12: Navigator Agent executes actions in ReAct loop with max 30 turns
- FR-13: All data models must use Pydantic BaseModel with frozen config
- FR-14: CLI must accept task input and display Rich-formatted progress
- FR-15: No hardcoded CSS/XPath selectors anywhere in codebase
- FR-16: No task-specific scripts or per-site branching

## Non-Goals (Out of Scope)

- No vision model / screenshot analysis (future enhancement)
- No coordinate-based clicking / bounding box population (future enhancement)
- No multi-tab browsing
- No CAPTCHA or 2FA solving
- No persistent conversation history (SQLite)
- No backwards compatibility with old architecture
- No adaptation of old tests — clean rewrite only

## Technical Considerations

### Dependencies (already in pyproject.toml)
- `openai-agents>=0.1.0` (installed: 0.7.0) — Agent, Runner, function_tool, set_default_openai_client
- `playwright>=1.48.0` — async_playwright, aria_snapshot()
- `pydantic>=2.10.0` — BaseModel, ConfigDict, field_validator
- `rich>=13.9.0` — Console output
- `pyyaml>=6.0.0` — ARIA snapshot YAML parsing
- `pytest-asyncio>=0.24.0` — async test support

### Architecture Pattern
```
User Task (natural language)
    │
    ▼
┌─────────────────┐
│  Planner Agent   │  SDK Agent — creates high-level plan
│  (LLM reasoning) │
└────────┬────────┘
         │ handoff (SDK native)
         ▼
┌─────────────────┐     ┌──────────────────┐
│ Navigator Agent  │────►│  Browser Tools    │
│ (ReAct loop)     │◄────│  (@function_tool) │
│ LLM reasons on   │     │                  │
│ every turn       │     │  browser_observe  │
└─────────────────┘     │  browser_click    │
    ▲                    │  browser_type     │
    │ Runner.run()       │  browser_press    │
    │ max_turns=30       │  browser_scroll   │
    │                    │  browser_navigate │
    ▼                    │  browser_wait     │
┌─────────────────┐     │  browser_extract  │
│  SDK Loop        │     │  browser_done     │
│  (built-in)      │     └──────────────────┘
│  1. Call LLM     │              │
│  2. Execute tool │              ▼
│  3. Feed result  │     ┌──────────────────┐
│  4. Repeat       │     │  Element Registry │
└─────────────────┘     │  (get_by_role)    │
                         └──────────────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │    Playwright     │
                         │  (async, headful) │
                         └──────────────────┘
```

### Key Design Decisions
- **Closure factory for tools**: `create_browser_tools(page, registry)` returns tool list with page/registry captured via closure. This avoids global state and keeps tools testable.
- **Safety at code level**: Destructive keyword matching happens inside tool functions, not via LLM guardrails. Deterministic and unbypassable.
- **Pydantic everywhere**: All data models use BaseModel. Consistent validation and serialization.
- **No context management module**: The SDK manages conversation context natively. ContextTracker is deleted.

### Constraints
- Requires `OPENROUTER_API_KEY` environment variable
- Single browser tab only
- Max 30 LLM turns per task
- 60 elements max per observation
- 3000 chars max visible text per observation

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| ReAct loop working | Agent uses observe → act → observe cycle | Visible in execution log |
| Failure recovery | Agent re-observes and changes approach on failure | At least 1 recovery in demo |
| Task completion | Agent completes example.com title extraction | End-to-end demo |
| Typecheck clean | No mypy errors | `uv run mypy src/` |
| Tests pass | All new tests green | `uv run pytest tests/ -v` |

## Open Questions

1. **Model choice**: Should Navigator and Planner use the same model, or should Planner use a more capable (slower) model?
2. **Turn budget**: Is 30 turns enough for complex tasks? Should it be configurable via CLI?
3. **Navigator ↔ Planner loop**: Should Navigator be able to hand back to Planner when stuck, creating a circular handoff? (Deferred — start with one-way handoff)

## Implementation Order

Stories must be implemented in priority order (1-13). Each story builds on the previous ones.

1. **US-001**: Clean slate (delete old tests + dead code)
2. **US-002**: Pydantic models (foundation)
3. **US-003**: ARIA parser fix (agent can see)
4. **US-004**: Registry with get_by_role (agent can target elements)
5. **US-005**: Async browser context (infrastructure)
6. **US-006**: OpenRouter async client (SDK talks to LLM)
7. **US-007**: Browser tools as @function_tool (SDK can act)
8. **US-008**: Navigator Agent (ReAct execution)
9. **US-009**: Planner Agent with handoff (task decomposition)
10. **US-010**: Safety checks (destructive action gating)
11. **US-011**: Async run.py (CLI orchestration)
12. **US-012**: New test suite (quality)
13. **US-013**: E2E demo verification (proof)
