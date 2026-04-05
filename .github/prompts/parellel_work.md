# Ralph Agent Instructions

You are an autonomous coding agent working on a software project.

## Your Task

1. Read the attached PRD
2. Read the progress log at `progress.txt` (check Codebase Patterns section first)
3. **Find and claim** the highest priority available story (see Task Claiming below)
4. **Create an isolated git worktree** for this story (see Worktree Isolation below)
5. Do all remaining work **inside the worktree directory**
6. Create a feature branch inside the worktree from the branch specified in the PRD, name it `feature-{purpose}`
7. Implement that single user story
8. Run `./scripts/ci_check.sh` to execute commit-readiness checks
9. Update AGENTS.md files if you discover reusable patterns (see below)
10. If checks pass, commit ALL changes with message: `feat: [Story ID] - [Story Title]`
11. Update the PRD to set `passes: true` for the completed story
12. Append your progress to `progress.txt`
13. **Release the claim and remove the worktree** (see Teardown below)

---

## Task Claiming

Claiming prevents two parallel agents from working on the same story simultaneously.
Claims are stored as JSON files in `tasks/claims/` in the **main repo root** (not the worktree).
A claim file is named `{story-id-lowercase}.json` (e.g. `us-003.json`).

### Step 1 — Clear stale claims
From the main repo root, delete any claim files older than 30 minutes:

```bash
find tasks/claims -name "*.json" -mmin +30 -delete 2>/dev/null
```

### Step 2 — Find an available story
A story is **available** if:
- `passes: false`, AND
- No claim file exists at `tasks/claims/{story-id-lower}.json`

Read the PRD, list the claim files, and pick the **highest priority** available story.

```bash
ls tasks/claims/   # see active claims
```

### Step 3 — Atomically create the claim
Use `set -C` (noclobber) so that if two agents race, only one succeeds:

```bash
STORY_ID="us-003"            # lowercase, from the story you picked
WORKTREE_DIR="../Arguably-$STORY_ID"
CLAIM_FILE="tasks/claims/${STORY_ID}.json"

if ( set -C
     printf '{"storyId":"%s","claimedAt":"%s","worktree":"%s"}\n' \
       "$STORY_ID" \
       "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
       "$WORKTREE_DIR" \
       > "$CLAIM_FILE"
   ) 2>/dev/null; then
  echo "Claimed $STORY_ID — proceeding"
else
  echo "Story $STORY_ID already claimed by another agent — re-pick a different story"
  # Go back to Step 1 and choose the next available story
fi
```

**If the claim fails**, another agent grabbed that story first. Go back to Step 1, skip that story, and claim the next available one.

### Releasing a claim
After the story is merged (or if work fails unrecoverably), delete the claim file from the **main repo root**:

```bash
rm -f "tasks/claims/${STORY_ID}.json"
```

---

## Worktree Isolation

Each agent run works in its own isolated git worktree so multiple agents can operate concurrently without interfering.

### Setup (do this after claiming, before any file edits)

```bash
# From the main repo root
STORY_ID="us-003"   # lowercase, derived from the story you claimed
WORKTREE_DIR="../Arguably-$STORY_ID"
BASE_BRANCH="<branch from PRD>"

# Use -b to create a unique local branch — avoids locking BASE_BRANCH
# so other agents can create their own worktrees simultaneously
git worktree add -b "worktree-$STORY_ID" "$WORKTREE_DIR" "$BASE_BRANCH"
cd "$WORKTREE_DIR"
```

- The worktree starts on a new branch (`worktree-$STORY_ID`) that is an exact copy of `$BASE_BRANCH` at creation time.
- All subsequent commands (installs, edits, CI checks, commits) run inside `$WORKTREE_DIR`.

### Teardown (do this after merging)

```bash
# 1. From the worktree, return to the main repo
cd ../Arguably

# 2. Merge feature branch into BASE_BRANCH
git checkout "$BASE_BRANCH"
git merge "feature-{purpose}" --no-ff
git checkout -          # return to previous branch

# 3. Remove the worktree
git worktree remove --force "../Arguably-$STORY_ID"

# 4. Delete the temporary worktree branch
git branch -d "worktree-$STORY_ID" 2>/dev/null || true

# 5. Release the claim
rm -f "tasks/claims/${STORY_ID}.json"
```

If `git worktree remove` fails because the directory is not empty, use `rm -rf "../Arguably-$STORY_ID"` followed by `git worktree prune`.

## Progress Report Format

APPEND to progress.txt (never replace, always append):
```
## [Date/Time] - [Story ID]
Thread: https://ampcode.com/threads/$AMP_CURRENT_THREAD_ID
- What was implemented
- Files changed
- **Learnings for future iterations:**
  - Patterns discovered (e.g., "this codebase uses X for Y")
  - Gotchas encountered (e.g., "don't forget to update Z when changing W")
  - Useful context (e.g., "the evaluation panel is in component X")
---
```

Include the thread URL so future iterations can use the `read_thread` tool to reference previous work if needed.

The learnings section is critical - it helps future iterations avoid repeating mistakes and understand the codebase better.

## Consolidate Patterns

If you discover a **reusable pattern** that future iterations should know, add it to the `## Codebase Patterns` section at the TOP of progress.txt (create it if it doesn't exist). This section should consolidate the most important learnings:

```
## Codebase Patterns
- Example: Use `sql<number>` template for aggregations
- Example: Always use `IF NOT EXISTS` for migrations
- Example: Export types from actions.ts for UI components
```

Only add patterns that are **general and reusable**, not story-specific details.

## Update AGENTS.md Files

Before committing, check if any edited files have learnings worth preserving in nearby AGENTS.md files:

1. **Identify directories with edited files** - Look at which directories you modified
2. **Check for existing AGENTS.md** - Look for AGENTS.md in those directories or parent directories
3. **Add valuable learnings** - If you discovered something future developers/agents should know:
   - API patterns or conventions specific to that module
   - Gotchas or non-obvious requirements
   - Dependencies between files
   - Testing approaches for that area
   - Configuration or environment requirements

**Examples of good AGENTS.md additions:**
- "When modifying X, also update Y to keep them in sync"
- "This module uses pattern Z for all API calls"
- "Tests require the dev server running on PORT 3000"
- "Field names must match the template exactly"

**Do NOT add:**
- Story-specific implementation details
- Temporary debugging notes
- Information already in progress.txt

Only update AGENTS.md if you have **genuinely reusable knowledge** that would help future work in that directory.

## Quality Requirements

- ALL commits must pass `./scripts/ci_check.sh` before commit
- Do NOT commit broken code
- Keep changes focused and minimal
- Follow existing code patterns

## Browser Testing (Required for Frontend Stories)

For any story that changes UI, you MUST verify it works in the browser:

1. Load the `dev-browser` skill
2. Navigate to the relevant page
3. Verify the UI changes work as expected
4. Take a screenshot if helpful for the progress log

A frontend story is NOT complete until browser verification passes.

## Stop Condition

After completing a user story, check if ALL stories have `passes: true`.

If ALL stories are complete and passing, reply with:
<promise>COMPLETE</promise>

If there are still stories with `passes: false`, end your response normally (another iteration will pick up the next story).

## Important

- Work on ONE story per iteration
- Commit frequently
- Keep CI green
- Read the Codebase Patterns section in progress.txt before starting