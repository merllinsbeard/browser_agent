# Autonomous Browser AI Agent Project: Comprehensive Documentation

This document serves as the final, comprehensive description of the Autonomous Browser AI Agent project. It compiles the Product Requirements Document (PRD), technical guidance, chosen technologies and libraries (with justifications based on research), project structure, expanded user stories, implementation details, and other key elements. The goal is to provide a complete blueprint for building, demonstrating, and evaluating the system.

The project is designed to create an AI agent that autonomously controls a visible web browser to perform arbitrary multi-step tasks based on natural language input from the user. It adheres strictly to the constraints of no task-specific scripts, hardcoded selectors, URLs, or site-specific logic. Research was conducted on AI agent frameworks, focusing on Python-based options suitable for multi-agent architectures, error handling, and integration with browser automation tools like Playwright.

## 1. Product Requirements Document (PRD)

### 1.1 Description of the Product
Autonomous AI-agent that manages a web browser and performs complex multi-step tasks based on a textual user request. The agent operates without micromanagement: it executes steps independently until clarification or confirmation is needed. The user observes the agent's work in real time.

### 1.2 Goals and Value
**Goals**:
- The user can describe any task in natural language, and the agent begins executing it in the browser.
- The agent performs the task autonomously: the user does not need to control the steps.
- The agent is secure: it does not perform potentially dangerous actions without explicit confirmation.
- The agent is resilient to real-world sites (dynamics, popups, layout shifts) and continues working in the user's session.

**Value for Evaluators**:
- Demonstrate ability to build systems in uncertainty.
- Show proper product compromises.
- Illustrate competent work with AI assistants.
- Provide a practical implementation (not just an "idea").

### 1.3 Users and Usage Context
**Primary User**: Engineer or general user who is already logged in to necessary services and wants to delegate a multi-step task in the browser.
**Context**: Tasks like email management, job applications, purchases, or form submissions, with real constraints (logins, CAPTCHAs, popups).

### 1.4 User Stories
As a user:
- I enter a textual task, and the agent starts executing it in the browser without my involvement.
- I see what the agent is doing (for transparency and trust).
- I receive requests for clarification only when truly necessary (e.g., 2FA or missing data).
- I confirm dangerous actions (deletion, submission, final purchase).
- At the end, I receive a report on what was done, what failed, and what is required next.

### 1.5 Functional Requirements (No Technical Details)
**5.1 Task Input**:
- User provides an arbitrary task in text.
- Agent starts execution without scripts tailored to specific tasks.

**5.2 Autonomous Execution**:
- Agent independently decides "what to do next."
- Agent continues until the task is complete or user input is needed.

**5.3 Work in User's Session**:
- Assumes user is already logged in to services.
- Agent must continue in the existing session.

**5.4 Resilience**:
- Agent correctly responds to errors (failed actions, page changes, unexpected windows).
- Agent can "recover" and try alternative approaches.

**5.5 Security and Confirmations**:
- Before dangerous actions, agent must request confirmation.
- Agent clearly explains what it plans to do and why it's dangerous.

**5.6 Result Report**:
- Upon completion, agent provides a brief report on actions performed and outcomes.

### 1.6 Non-Functional Requirements
- **Transparency**: User sees the execution progress (and understands what's happening).
- **Controllability**: Ability to stop/cancel execution.
- **Predictability**: No "runaway" infinite loops; limits and stop criteria exist.
- **Security**: No "silent" irreversible actions.
- **Reproducibility**: Launch and demo process is clear and repeatable.

### 1.7 Constraints and Prohibitions (Mandatory)
- No solutions based on pre-defined scenarios for specific cases.
- No use of pre-prepared hints on site structures.
- No logic tied to specific sites.
- No reliance on pre-prepared "manual" instructions for elements.
(Technical interpretation and formulations are fixed in the technical guidance section.)

### 1.8 Required Advanced Patterns
Must implement at least one, but ideally all three, as they enhance the demonstration:
- Sub-agent pattern (at minimum, a safety sub-agent).
- Error handling/recovery (adaptation on failed actions).
- Security layer (confirmation of dangerous actions).

### 1.9 Acceptance Criteria
The system is ready if:
- Agent accepts an arbitrary textual task and starts execution.
- Execution is autonomous (user does not control steps).
- Agent's work is visible "live."
- User's session is preserved (login not broken, agent continues).
- Dangerous actions require confirmation.
- Agent resiliently handles errors and does not get stuck indefinitely.
- Clear report at completion.
- Demo does not look "trained for 3 cases."

### 1.10 Demonstration Plan (What to Show in Video)
- Launch, task input, agent starts acting.
- Example of a "normal" step (search/navigation/form).
- Example of a "failure" (popup/error) and recovery.
- Example of a "dangerous" step and user confirmation.
- Final report.

### 1.11 Risks and Mitigation (Product Level)
- Risk "Seems like a prefab": Demonstrate a new, unprepared task.
- Risk "Agent fails on dynamics": Show handling of popups/redraws/retries.
- Risk "Dangerous actions without control": Strict confirm gate and visible UX for confirmation.
- Risk "Too much content in context": Prove agent works on compressed page representation (words/logs), without full page dumps.

### 1.12 Quality Metrics (Simple)
- Task completion rate (on a set of 5–10 arbitrary tasks).
- Average number of steps to result.
- Percentage of tasks requiring user input.
- Number of "stuck" situations per task.
- Number of false confirms (asks too often) vs. missed dangerous actions (unacceptable).

### 1.13 Deliverables
- Repository with working solution.
- Video demonstration.

## 2. Technical Guidance and Principles
This section is based on the locked technical decisions and constraints for the MVP.

### 2.1 Goal
Build an autonomous browser AI agent that controls a visible (headful) browser to complete arbitrary multi-step tasks. The user provides a free-form task in natural language; the agent runs autonomously until it needs user input or finishes.

### 2.2 Non-Negotiable Constraints
- NO task-specific scripts (no predefined step lists per use case).
- NO hardcoded selectors (CSS/XPath/QA attributes).
- NO URL hints or per-site navigation assumptions.
- NO per-site branching (e.g., `if "hh.ru" in url: ...` is forbidden).
- Runtime page text/ARIA is allowed ONLY as observed data (not hardcoded strings in code).

### 2.3 Required Components
1. Sub-agent architecture (at least one): e.g., Planner + Navigator + Safety.
2. Error handling: retries, recovery strategies, “stuck” detection.
3. Security layer: confirm before destructive actions.
4. Context management: never send full HTML/DOM; summarize and limit tokens.

### 2.4 Core Design: Element Registry (No Hardcoded Selectors)
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

### 2.5 Tool Contract (Keep Tools Dumb & Inspectable)
Tools must be pure and return structured results:
- browser.observe() -> PageSnapshot
- browser.act(Action) -> ActionResult
- browser.screenshot() -> path
- user.ask(question) -> answer (only when required)
- user.confirm(destructive_action_summary) -> yes/no

### 2.6 Security Policy
Always require user.confirm() for:
- Deleting emails / moving to spam/trash
- Sending forms / applying to jobs
- Finalizing checkout / payment confirmation
- Any irreversible action

### 2.7 Context Budget Rules
- interactive_elements: top N (e.g., 40–80) by visibility + relevance heuristic
- visible_text_excerpt: max K chars/tokens (e.g., 2–4k chars)
- Never include full DOM; no full-page dumps
- Keep a running task memory: completed steps summary + open questions (short)

### 2.8 Recovery Strategy
When an action fails:
- Re-observe; detect overlays/popups; try dismiss
- Wait for network/selector; retry with backoff
- If stuck for M steps: navigate back/reload; ask user if login/2FA needed

### 2.9 Definition of Done (What Must Be Demo-able)
- Visible browser window (not headless).
- Persistent session: user logs in once; agent continues without losing state.
- Autonomy: can run a novel task without scripted steps.
- Sub-agent + security confirm implemented.
- Context mgmt present (no full-page stuffing).
- `scripts/run.py` interactive CLI + `scripts/eval.py` generic smoke.

### 2.10 Commands (uv)
- uv pip install -e ".[dev]"
- uv run python -m browser_agent.cli
- uv run python scripts/eval.py
- uv run pytest

## 3. Chosen Technologies and Libraries
Based on research into Python AI agent frameworks (focusing on multi-agent support, lightweight design, error handling, and extensibility for browser automation), the following choices are committed for the MVP. Justifications reference current (2026) trends from sources like GitHub stars, framework reviews, and suitability for sub-agents and Playwright integration.

| Component | Choice | Justification |
|-----------|--------|---------------|
| **Language** | Python | Locked in technical guidance; widely used for AI and automation. |
| **Environment/Dependency Manager** | uv | Locked; efficient for Python projects, handles virtual envs and installs. |
| **Browser Automation** | Playwright (Python bindings) | Locked; supports headful mode, persistent contexts (via user_data_dir), and is resilient to dynamic sites. Superior to Selenium for modern web (async, anti-detection features). Integrates well with AI tools via custom actions. |
| **Agent Framework** | OPENAI Agents SDK | Chosen from options like LangGraph, CrewAI, AutoGen. OPENAI Agents SDK is lightweight, Python-native, focused on ergonomic multi-agent orchestration (fits sub-agent pattern, e.g., Planner, Safety agents). Highly controllable/testable; integrates LLMs (e.g., GPT models) for decision-making. Extensible with custom tools (e.g., Playwright actions). GitHub stars: High adoption in AI agent communities. Alternatives like CrewAI were considered for "crews," but OPENAI Agents SDK's simplicity avoids over-abstraction for this MVP. No direct Playwright integration, but easy to add as tools. |
| **LLM Integration** | OpenAI API (e.g., GPT-4o or similar) | Complements OPENAI Agents SDK; provides reasoning for agent decisions. Local alternatives (e.g., via Ollama) possible for offline dev, but API for reliability. |
| **Other Libraries** | - pydantic (structured data)<br>- rich (CLI output)<br>- pytest (testing) | - Pydantic: For defining Action/PageSnapshot schemas (ensures type safety).<br>- Rich: Enhances transparency in CLI (colored logs, progress).<br>- Pytest: For unit/integration tests, including smoke tests in eval.py. |
| **MCP (Multi-Context Prompting)** | Optional (not used in MVP) | Locked as optional; skipped for simplicity in dev/debug, but runtime works without it. |

**Research Notes**: Frameworks were evaluated for Python support, multi-agent capabilities, and browser extensibility. OPENAI Agents SDK stood out for its focus on lightweight orchestration without heavy dependencies, aligning with constraints like context management. Browser-specific tools (e.g., Hyperbrowser AI) extend Playwright but were not chosen as full frameworks; instead, integrate via custom tools in OPENAI Agents SDK.

## 4. Project Structure
The repository follows a standard Python structure, emphasizing modularity for agents, tools, and scripts. This ensures reproducibility and ease of extension.

```
browser-agent/
├── src/
│   ├── browser_agent/
│   │   ├── __init__.py
│   │   ├── agents/          # Sub-agent implementations (e.g., planner.py, safety.py)
│   │   ├── tools/           # Browser tools (observe.py, act.py, screenshot.py)
│   │   ├── core/            # Main loop, context manager, error handler
│   │   ├── security/        # Confirmation logic
│   │   ├── models/          # Pydantic schemas (Action, PageSnapshot)
│   │   └── cli.py           # Interactive CLI entrypoint
├── scripts/
│   ├── run.py               # Main script for launching (uv run python scripts/run.py)
│   └── eval.py              # Smoke tests and evaluation
├── tests/                   # Pytest tests (unit for tools, integration for agents)
├── pyproject.toml           # uv config, dependencies
├── README.md                # Setup, usage, demo instructions
└── CLAUDE.md                # Technical guidance (this file)
```

- **src/browser_agent/**: Core code; modular to allow sub-agents as separate classes.
- **scripts/**: Entry points for CLI and eval.
- **tests/**: Covers 80%+ code, focusing on error recovery and security.

## 5. Expanded User Stories
Building on PRD, these are refined with acceptance criteria and ties to technical components.

1. **As a user, I enter a textual task, so the agent starts autonomously.**
   - Acceptance: Task parsed via LLM; OPENAI Agents SDK orchestrates initial planning sub-agent.
   - Ties to: Task input, autonomous execution.

2. **As a user, I observe real-time progress, building trust.**
   - Acceptance: Visible browser + CLI logs (via rich); screenshots on key steps.
   - Ties to: Transparency, headful Playwright.

3. **As a user, I provide input only when essential (e.g., 2FA).**
   - Acceptance: user.ask() triggered sparingly; recovery strategy handles most issues.
   - Ties to: Resilience, user.ask tool.

4. **As a user, I confirm destructive actions, ensuring safety.**
   - Acceptance: Security sub-agent intercepts; user.confirm() with clear summary.
   - Ties to: Security layer, policy.

5. **As a user, I receive a completion report, summarizing outcomes.**
   - Acceptance: DONE action triggers structured report (success/fails/next steps).
   - Ties to: Result report, task memory.

## 6. Implementation Plan
- **Phase 1: Setup**: Install deps with uv; initialize Playwright with persistent context.
- **Phase 2: Tools**: Implement dumb tools (observe, act, etc.) with context limits.
- **Phase 3: Agents**: Use OPENAI Agents SDK to define sub-agents (Planner for steps, Safety for confirms, Executor for actions).
- **Phase 4: Core Loop**: Main loop in core/ handles observation-action-recovery cycle.
- **Phase 5: Testing/Demo**: Write tests; record video per demo plan.
- **Edge Cases**: Handle dynamics via retries; ensure no full DOM in prompts.

## 7. Additional Notes
- **Scalability**: Design allows adding more sub-agents (e.g., Extractor).
- **Ethical Considerations**: Adheres to security policy; no automation of illegal tasks.
- **Future Enhancements**: Integrate vision models for screenshots; support no-code task input.

This document is self-contained and ready for implementation. For any updates, refer back to core constraints.
