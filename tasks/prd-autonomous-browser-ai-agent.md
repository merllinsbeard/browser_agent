# PRD: Autonomous Browser AI Agent

## Introduction

An AI agent that autonomously controls a visible web browser to perform arbitrary multi-step tasks based on natural language input. The agent operates without task-specific scripts, hardcoded selectors, or site-specific logic. It observes page state through accessibility trees, plans actions using a hierarchical multi-agent architecture, and confirms with users before destructive actions.

The agent works in the user's existing browser session (already logged in to services) and demonstrates resilience to dynamic web elements, popups, and layout shifts.

## Goals

- Accept arbitrary textual tasks and execute autonomously without pre-written scripts
- Achieve 80%+ success rate on 5-10 arbitrary, unprepared tasks
- Maintain persistent user sessions (logins, cookies) across agent runs
- Handle errors gracefully with recovery strategies (no infinite stuck states)
- Require user confirmation before all destructive actions
- Limit context usage to prevent token bloat (<30 LLM calls per task)
- Demonstrate sub-agent architecture (Planner + Navigator + Safety)
- Work with visible browser window for transparency and trust

## User Stories

### US-001: Persistent Browser Context Setup
**Description:** As a user, I want the agent to preserve my login session so I don't need to re-authenticate.

**Acceptance Criteria:**
- [ ] Browser launches with persistent context using `user_data_dir`
- [ ] Cookies and localStorage persist across agent restarts
- [ ] Browser launches in headful mode (visible window)
- [ ] Session directory is configurable via CLI argument
- [ ] Typecheck passes

### US-002: Page Observation via Accessibility Tree
**Description:** As the agent, I need to observe page state without full DOM dumps to understand what actions are available.

**Acceptance Criteria:**
- [ ] `browser_observe()` tool returns compact PageSnapshot with url, title, interactive_elements
- [ ] Interactive elements limited to top 40-80 by visibility + relevance heuristic
- [ ] Each element receives unique `ref` ID (e.g., "e5", "e12") for action targeting
- [ ] Element data includes: role, name, aria_label, placeholder, value_preview
- [ ] Visible text excerpt truncated to 2-4K characters
- [ ] No full HTML/DOM included in snapshot
- [ ] Typecheck passes

### US-003: Element Registry for Dynamic Actions
**Description:** As the agent, I want to reference elements by ID rather than hardcoded selectors to avoid brittleness.

**Acceptance Criteria:**
- [ ] ElementRegistry assigns unique IDs during observation phase
- [ ] Each snapshot has a version number for element reference validation
- [ ] `browser_act()` tool accepts `element_id` parameter (ref ID, not selector)
- [ ] Executor maps ref ID to Playwright locator dynamically at action time
- [ ] Stale element references are detected and rejected with clear error
- [ ] Typecheck passes

### US-004: Action Execution Toolkit
**Description:** As the agent, I need a set of atomic actions to interact with web pages.

**Acceptance Criteria:**
- [ ] CLICK action accepts element_id and executes click
- [ ] TYPE action accepts element_id and text, fills input
- [ ] PRESS action accepts key name (Enter, Escape, etc.)
- [ ] SCROLL action accepts dx, dy parameters
- [ ] NAVIGATE action accepts URL
- [ ] WAIT action accepts timeout or condition
- [ ] EXTRACT action for generic data extraction
- [ ] DONE action signals task completion with summary
- [ ] All actions return ActionResult with success status and message
- [ ] Typecheck passes

### US-005: Planner Sub-Agent
**Description:** As the system, I want a Planner agent to break tasks into executable steps.

**Acceptance Criteria:**
- [ ] Planner agent receives user task and creates step-by-step execution plan
- [ ] Plan is stored in task memory for reference during execution
- [ ] Planner maintains URL history for backtracking on failures
- [ ] Planner handoffs to Navigator agent after planning phase
- [ ] Typecheck passes

### US-006: Navigator Sub-Agent
**Description:** As the system, I want a Navigator agent to execute browser actions based on the plan.

**Acceptance Criteria:**
- [ ] Navigator agent receives plan steps and executes sequentially
- [ ] Navigator calls browser_observe() before each action
- [ ] Navigator executes actions via browser_act() tool
- [ ] Navigator returns to Planner on completion or failure
- [ ] Typecheck passes

### US-007: Safety Sub-Agent with Confirmations
**Description:** As a user, I want the agent to ask confirmation before destructive actions.

**Acceptance Criteria:**
- [ ] Safety agent intercepts actions matching destructive patterns (delete, submit, payment)
- [ ] Destructive actions trigger `user.confirm()` with clear action summary
- [ ] Agent waits for yes/no response before proceeding
- [ ] Confirmation is required even if agent "thinks" it's safe
- [ ] Security policy is enforced at CODE level (keyword matching), not LLM level
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill (CLI interaction)

### US-008: Error Recovery and Retry Logic
**Description:** As the agent, I want to recover from failures without getting stuck.

**Acceptance Criteria:**
- [ ] Failed actions trigger re-observation of page state
- [ ] System detects overlays/popups and attempts dismissal
- [ ] Agent waits for network/selector with backoff retry (max 3 attempts)
- [ ] Agent never retries the exact same action twice
- [ ] After 3 consecutive failures, agent asks user for guidance
- [ ] Stuck detection triggers after 5 actions with no progress
- [ ] Typecheck passes

### US-009: Context Budget Management
**Description:** As the system, I want to limit token usage to control costs and latency.

**Acceptance Criteria:**
- [ ] Single-snapshot retention: only most recent snapshot in context
- [ ] Task memory compressed after each 10 steps (summarize older steps)
- [ ] ContextTracker monitors token usage per category (snapshot, history, tools)
- [ ] Alert when approaching token limit
- [ ] Target: <30 LLM calls per task
- [ ] Typecheck passes

### US-010: Hybrid Observation (Accessibility + Vision Fallback)
**Description:** As the agent, I want screenshots as fallback when accessibility tree is insufficient.

**Acceptance Criteria:**
- [ ] Primary observation via ARIA snapshot (compact, semantic)
- [ ] Screenshot captured on each observe() and saved to disk
- [ ] Vision model invoked when ARIA snapshot has <10 interactive elements
- [ ] Screenshot path included in PageSnapshot for vision analysis
- [ ] Typecheck passes

### US-011: CLI Interface
**Description:** As a user, I want an interactive CLI to launch the agent and input tasks.

**Acceptance Criteria:**
- [ ] `scripts/run.py` launches agent with visible browser
- [ ] CLI accepts task input via command line argument or interactive prompt
- [ ] CLI shows real-time progress (current step, action being taken)
- [ ] CLI handles confirmation prompts (destructive actions)
- [ ] CLI displays completion report at end
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill (CLI UX)

### US-012: OpenRouter LLM Integration
**Description:** As the system, I want to use OpenRouter API for LLM calls (OpenAI-compatible).

**Acceptance Criteria:**
- [ ] OpenRouter API key configured via environment variable
- [ ] Default model: GPT-4o or equivalent via OpenRouter
- [ ] Fallback to local Ollama models for development (optional)
- [ ] API calls include proper error handling and retry
- [ ] Typecheck passes

### US-013: Evaluation Script
**Description:** As a developer, I want a script to run smoke tests and evaluate agent performance.

**Acceptance Criteria:**
- [ ] `scripts/eval.py` runs predefined test tasks
- [ ] Measures success rate, step count, user input count, stuck situations
- [ ] Outputs report with metrics
- [ ] Can run against multiple test scenarios
- [ ] Typecheck passes

### US-014: Comprehensive Test Coverage
**Description:** As a developer, I want 80%+ test coverage to ensure reliability.

**Acceptance Criteria:**
- [ ] Unit tests for all browser tools (observe, act, screenshot)
- [ ] Unit tests for ElementRegistry (ID assignment, versioning)
- [ ] Unit tests for ContextTracker (budget management)
- [ ] Integration tests for agent handoffs (Planner -> Navigator)
- [ ] Integration tests for error recovery flows
- [ ] Tests for safety confirmation logic
- [ ] Coverage report shows >=80%
- [ ] Typecheck passes

### US-015: Demo Readiness
**Description:** As a project stakeholder, I want a working demo that demonstrates all key features.

**Acceptance Criteria:**
- [ ] Launch sequence shows browser opening and agent starting
- [ ] Demo includes normal step (search/navigation/form)
- [ ] Demo includes failure recovery (popup/error handling)
- [ ] Demo includes dangerous action with user confirmation
- [ ] Demo ends with completion report
- [ ] Demo uses novel task (not pre-scripted)
- [ ] Verify in browser using dev-browser skill (full demo run)

## Functional Requirements

- FR-1: System must accept arbitrary textual task input via CLI
- FR-2: Browser must launch in visible (headful) mode with persistent context
- FR-3: System must observe pages via accessibility tree, not full DOM
- FR-4: Interactive elements must be limited to 40-80 top-priority items
- FR-5: Each observation must assign unique ref IDs to elements
- FR-6: Actions must be executed by ref ID, not hardcoded selectors
- FR-7: Element references must include version numbers to detect staleness
- FR-8: System must implement hierarchical sub-agent architecture (Planner + Navigator + Safety)
- FR-9: Planner agent must break tasks into steps and maintain URL history
- FR-10: Navigator agent must execute actions using browser tools
- FR-11: Safety agent must require confirmation before destructive actions
- FR-12: Destructive action patterns (delete, submit, payment) must be blocked at code level
- FR-13: System must retry failed actions with different approaches (never same action twice)
- FR-14: System must detect stuck state after 5 actions with no progress
- FR-15: System must limit context to single snapshot + compressed history
- FR-16: System must target <30 LLM calls per task
- FR-17: System must use OpenRouter API (OpenAI-compatible) for LLM calls
- FR-18: System must capture screenshots as fallback for vision analysis
- FR-19: CLI must display real-time progress and confirmation prompts
- FR-20: System must provide completion report with actions taken and outcomes

## Non-Goals (Out of Scope)

- No task-specific scripts or predefined step lists
- No hardcoded CSS/XPath selectors
- No URL hints or per-site navigation assumptions
- No per-site branching logic (e.g., `if "github.com" in url: ...`)
- No automation of illegal activities
- No CAPTCHA solving (agent asks user for help)
- No 2FA automation (agent asks user for help)
- No password storage or management
- No multi-tab browsing (single tab only for MVP)
- No browser extension integration
- No mobile/responsive simulation
- No network traffic interception or modification

## Design Considerations

### UI/UX
- CLI must use `rich` library for colored, formatted output
- Progress indication: show current step, action being taken
- Confirmation prompts: clear description of action and consequences
- Completion report: structured summary with success/failure/next steps

### Architecture
- Sub-agents as separate classes in `src/browser_agent/agents/`
- Browser tools as pure functions in `src/browser_agent/tools/`
- Core loop in `src/browser_agent/core/` handles observation-action-recovery cycle
- Models defined with Pydantic in `src/browser_agent/models/`

### Component Reuse
- Use existing `rich` library for CLI output
- Use existing `pydantic` for structured data
- Use existing `pytest` for testing

## Technical Considerations

### Dependencies
- **Python 3.11+** with `uv` for dependency management
- **Playwright Python** for browser automation (headful + persistent context)
- **OpenAI Agents SDK** for multi-agent orchestration
- **OpenRouter API** for LLM calls (OpenAI-compatible)
- **Pydantic** for Action/PageSnapshot schemas
- **Rich** for CLI output
- **Pytest** for testing

### Constraints
- No hardcoded selectors in code (only runtime observation data)
- No full DOM/HTML in LLM context
- Context budget: 40-80 elements, 2-4K text, single snapshot retention
- Safety enforced at code level via keyword matching

### Performance Requirements
- Target <30 LLM calls per task
- Target <180 seconds per task
- Target 80%+ success rate on arbitrary tasks

### Integration Points
- OpenRouter API for LLM calls
- Playwright browser context
- File system for screenshot storage
- SQLite for session history (optional)

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Task completion rate | >=80% | 5-10 arbitrary, unprepared tasks |
| Average steps per task | <30 | Count LLM calls per task |
| Average task time | <180s | Time from task input to completion |
| Stuck situations per task | <1 | Count recovery triggers |
| False confirmations | <10% | Confirmations asked for non-destructive actions |
| Test coverage | >=80% | Pytest coverage report |

## Open Questions

1. **Vision Model**: Should we use GPT-4o Vision via OpenRouter or a separate vision provider for screenshot analysis?
2. **Local Development**: Should we include Ollama integration for offline development, or require OpenRouter from the start?
3. **Session Storage**: Should conversation history be persisted to SQLite or kept in-memory only?
4. **Screenshot Retention**: Should screenshots be deleted after task completion or kept for debugging?
5. **Demo Tasks**: What specific tasks should be prepared for the demo video (must be novel, not pre-scripted)?

## Implementation Order

1. **Phase 1**: Project setup (uv, dependencies, directory structure)
2. **Phase 2**: Browser tools (observe, act, screenshot) with ElementRegistry
3. **Phase 3**: Models (Action, PageSnapshot, ActionResult) with Pydantic
4. **Phase 4**: OpenAI Agents SDK integration (single agent first)
5. **Phase 5**: Sub-agent architecture (Planner, Navigator, Safety)
6. **Phase 6**: Core loop with error recovery
7. **Phase 7**: Context management and budget tracking
8. **Phase 8**: CLI interface with rich output
9. **Phase 9**: Safety layer with confirmations
10. **Phase 10**: Hybrid observation (vision fallback)
11. **Phase 11**: Comprehensive testing (80%+ coverage)
12. **Phase 12**: Demo preparation and evaluation

---

**Deliverables**:
- Repository with working solution at `/home/merlin/browser_agent`
- Video demonstration showing all acceptance criteria
- Test coverage report showing >=80%
