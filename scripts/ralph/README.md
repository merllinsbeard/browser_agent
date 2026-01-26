# Ralph Autonomous Agent

## Setup

1. Copy `.env.example` to `.env`:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set your ZAI_API_KEY:
   ```
   ZAI_API_KEY=your-actual-key-here
   ```

## Usage

Run Ralph with default 10 iterations:

```bash
./scripts/ralph/ralph.sh
```

Run Ralph with custom iteration count:

```bash
./scripts/ralph/ralph.sh 300
```

## How It Works

1. Loads `.env` for Z.ai API configuration
2. Reads `prd.json` for user stories
3. Iteratively implements stories with `passes: false`
4. Runs quality checks (typecheck, lint, test)
5. Commits changes and updates progress
6. Stops when all stories complete or max iterations reached

## Environment Variables

The following variables are loaded from `.env`:

| Variable                         | Description              | Default                          |
| -------------------------------- | ------------------------ | -------------------------------- |
| `ZAI_API_KEY`                    | Your Z.ai API key        | _Required_                       |
| `ANTHROPIC_BASE_URL`             | API base URL             | `https://api.z.ai/api/anthropic` |
| `ANTHROPIC_DEFAULT_OPUS_MODEL`   | Model for complex tasks  | `glm-4.7`                        |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | Model for standard tasks | `glm-4.7`                        |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL`  | Model for quick tasks    | `glm-4.7`                        |
| `API_TIMEOUT_MS`                 | Request timeout          | `3000000`                        |

## Files

- `prd.json` - Product Requirements Document with user stories
- `progress.txt` - Progress log with codebase patterns
- `CLAUDE.md` - Agent instructions for Claude Code
- `prompt.md` - Alternative instructions for amp tool
