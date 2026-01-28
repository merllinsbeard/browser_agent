#!/bin/bash
# Ralph Wiggum - Long-running AI agent loop
# Usage: ./ralph.sh [--tool amp|claude|claude-zai] [max_iterations]

set -e

# Cleanup handler for trap
cleanup() {
  local exit_code=$?
  # Kill any child processes
  local pids=$(jobs -p)
  if [ -n "$pids" ]; then
    kill $pids 2>/dev/null || true
    wait $pids 2>/dev/null || true
  fi
  # Free memory
  unset OUTPUT
  exit $exit_code
}

# Trap signals for proper cleanup
trap cleanup EXIT INT TERM HUP QUIT

# Parse arguments
TOOL="claude"  # Default to claude (official Anthropic API)
MAX_ITERATIONS=10

while [[ $# -gt 0 ]]; do
  case $1 in
    --tool)
      TOOL="$2"
      shift 2
      ;;
    --tool=*)
      TOOL="${1#*=}"
      shift
      ;;
    *)
      # Assume it's max_iterations if it's a number
      if [[ "$1" =~ ^[0-9]+$ ]]; then
        MAX_ITERATIONS="$1"
      fi
      shift
      ;;
  esac
done

# Validate tool choice
if [[ "$TOOL" != "amp" && "$TOOL" != "claude" && "$TOOL" != "claude-zai" ]]; then
  echo "Error: Invalid tool '$TOOL'. Must be 'amp', 'claude', or 'claude-zai'."
  exit 1
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRD_FILE="$SCRIPT_DIR/prd.json"
PROGRESS_FILE="$SCRIPT_DIR/progress.txt"
ARCHIVE_DIR="$SCRIPT_DIR/archive"
LAST_BRANCH_FILE="$SCRIPT_DIR/.last-branch"

# Load environment variables from .env (needed for OPENROUTER_API_KEY used by the browser agent)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [ -f "$PROJECT_ROOT/.env" ]; then
  set -a
  source "$PROJECT_ROOT/.env"
  set +a
  echo "Loaded environment from $PROJECT_ROOT/.env"
fi

# Validate Z.ai credentials when using claude-zai
if [[ "$TOOL" == "claude-zai" ]]; then
  if [ -z "$ZAI_API_KEY" ]; then
    echo "Error: ZAI_API_KEY is not set. Required for --tool claude-zai."
    echo "Set it in $PROJECT_ROOT/.env or export it."
    exit 1
  fi
fi

# Archive previous run if branch changed
if [ -f "$PRD_FILE" ] && [ -f "$LAST_BRANCH_FILE" ]; then
  CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
  LAST_BRANCH=$(cat "$LAST_BRANCH_FILE" 2>/dev/null || echo "")

  if [ -n "$CURRENT_BRANCH" ] && [ -n "$LAST_BRANCH" ] && [ "$CURRENT_BRANCH" != "$LAST_BRANCH" ]; then
    # Archive the previous run
    DATE=$(date +%Y-%m-%d)
    # Strip "ralph/" prefix from branch name for folder
    FOLDER_NAME=$(echo "$LAST_BRANCH" | sed 's|^ralph/||')
    ARCHIVE_FOLDER="$ARCHIVE_DIR/$DATE-$FOLDER_NAME"

    echo "Archiving previous run: $LAST_BRANCH"
    mkdir -p "$ARCHIVE_FOLDER"
    [ -f "$PRD_FILE" ] && cp "$PRD_FILE" "$ARCHIVE_FOLDER/"
    [ -f "$PROGRESS_FILE" ] && cp "$PROGRESS_FILE" "$ARCHIVE_FOLDER/"
    echo "   Archived to: $ARCHIVE_FOLDER"

    # Reset progress file for new run
    echo "# Ralph Progress Log" > "$PROGRESS_FILE"
    echo "Started: $(date)" >> "$PROGRESS_FILE"
    echo "---" >> "$PROGRESS_FILE"
  fi
fi

# Track current branch
if [ -f "$PRD_FILE" ]; then
  CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
  if [ -n "$CURRENT_BRANCH" ]; then
    echo "$CURRENT_BRANCH" > "$LAST_BRANCH_FILE"
  fi
fi

# Initialize progress file if it doesn't exist
if [ ! -f "$PROGRESS_FILE" ]; then
  echo "# Ralph Progress Log" > "$PROGRESS_FILE"
  echo "Started: $(date)" >> "$PROGRESS_FILE"
  echo "---" >> "$PROGRESS_FILE"
fi

echo "Starting Ralph - Tool: $TOOL - Max iterations: $MAX_ITERATIONS"

for i in $(seq 1 $MAX_ITERATIONS); do
  echo ""
  echo "==============================================================="
  echo "  Ralph Iteration $i of $MAX_ITERATIONS ($TOOL)"
  echo "==============================================================="

  # Run the selected tool with the ralph prompt
  if [[ "$TOOL" == "amp" ]]; then
    OUTPUT=$(cat "$SCRIPT_DIR/prompt.md" | amp --dangerously-allow-all 2>&1 | tee /dev/stderr) || true
  elif [[ "$TOOL" == "claude" ]]; then
    # Official Claude Code: uses your normal Anthropic API configuration
    OUTPUT=$(claude --dangerously-skip-permissions --print < "$SCRIPT_DIR/CLAUDE.md" 2>&1 | tee /dev/stderr) || true
  elif [[ "$TOOL" == "claude-zai" ]]; then
    # Claude Code via Z.ai proxy (glm-4.7)
    OUTPUT=$(env \
      ANTHROPIC_BASE_URL="https://api.z.ai/api/anthropic" \
      ANTHROPIC_AUTH_TOKEN="$ZAI_API_KEY" \
      ANTHROPIC_DEFAULT_OPUS_MODEL="${ANTHROPIC_DEFAULT_OPUS_MODEL:-glm-4.7}" \
      ANTHROPIC_DEFAULT_SONNET_MODEL="${ANTHROPIC_DEFAULT_SONNET_MODEL:-glm-4.7}" \
      ANTHROPIC_DEFAULT_HAIKU_MODEL="${ANTHROPIC_DEFAULT_HAIKU_MODEL:-glm-4.7}" \
      API_TIMEOUT_MS="${API_TIMEOUT_MS:-3000000}" \
      claude --dangerously-skip-permissions --print < "$SCRIPT_DIR/CLAUDE.md" 2>&1 | tee /dev/stderr) || true
  fi

  # Check for completion signal
  if echo "$OUTPUT" | grep -q "<promise>COMPLETE</promise>"; then
    echo ""
    echo "Ralph completed all tasks!"
    echo "Completed at iteration $i of $MAX_ITERATIONS"
    exit 0
  fi

  echo "Iteration $i complete. Continuing..."
  sleep 2
done

echo ""
echo "Ralph reached max iterations ($MAX_ITERATIONS) without completing all tasks."
echo "Check $PROGRESS_FILE for status."
exit 1
