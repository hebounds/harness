# Sequential Merge Instructions for Parallel Work

You are responsible for merging completed work from parallel agents into the main branch sequentially.

## Your Task

1. Read the PRD to identify all completed stories (those with `passes: true`)
2. **Merge all feature branches sequentially** into the base branch
3. Handle any merge conflicts that arise
4. Update the PRD and progress.txt with merge completion status
5. Clean up worktrees and claims

---

## Setup

```bash
# From the main repo root
cd /Users/hayesbounds/Arguably

# Ensure you're on the base branch
BASE_BRANCH="<branch from PRD>"  # e.g., main, develop
git checkout "$BASE_BRANCH"
git pull origin "$BASE_BRANCH"   # Ensure you have the latest
```

---

## Merging Workflow

### Step 1 — Identify Completed Stories

Read the PRD file and list all stories where `passes: true`. These are your merge candidates.

```bash
# Example: if the PRD is prd-my-feature.json
cat tasks/prd-my-feature.json | grep -A 5 '"passes": true'
```

### Step 2 — Merge Each Story in Order

For each completed story (in priority order):

```bash
STORY_ID="us-001"  # the story ID you're merging
FEATURE_BRANCH="feature-<purpose>"  # the branch name from the story

git merge "$FEATURE_BRANCH" --no-ff --no-edit

# If there are conflicts:
# 1. Resolve conflicts manually
# 2. Run: git add .
# 3. Run: git commit -m "merge: Resolve conflicts from $STORY_ID"
```

**Commit message format for clean merges:**
```
merge: $STORY_ID - $STORY_TITLE (no conflicts)
```

**Commit message format for conflict resolution:**
```
merge: $STORY_ID - $STORY_TITLE (resolved conflicts)
```

### Step 3 — Verify the Merge

After each merge:

```bash
# Run CI checks to ensure nothing broke
./scripts/ci_check.sh

# If checks fail, you can:
# Option A: Revert the merge and fix the branch before merging again
git merge --abort
# Fix the feature branch, then retry the merge

# Option B: Fix the issues in the current branch
# (resolve conflicts, fix code, etc.)
# Then add and commit
git add .
git commit -m "fix: Resolve merge issues from $STORY_ID"
```

### Step 4 — Push to Remote

After all merges are complete and CI passes:

```bash
git push origin "$BASE_BRANCH"
```

---

## Cleanup

After all merges are successfully pushed:

### Remove Worktrees

For each completed story:

```bash
STORY_ID="us-001"
WORKTREE_DIR="../Arguably-$STORY_ID"

# Remove the worktree
git worktree remove --force "$WORKTREE_DIR" 2>/dev/null || rm -rf "$WORKTREE_DIR"

# Prune dead worktrees
git worktree prune
```

### Delete Feature Branches

```bash
FEATURE_BRANCH="feature-<purpose>"

# Delete from local repo
git branch -d "$FEATURE_BRANCH" 2>/dev/null || true

# Delete from remote (optional, depends on your team's policy)
# git push origin --delete "$FEATURE_BRANCH"
```

### Release Claims

```bash
# Delete all claim files to release them
rm -f tasks/claims/*.json
```

---

## Handling Merge Conflicts

If you encounter merge conflicts:

1. **Identify the conflicting files:**
   ```bash
   git status
   ```

2. **Review the conflicts** in your editor and resolve them.

3. **Consult the original PRD branch** if context is needed about what each branch intended:
   ```bash
   git show FEATURE_BRANCH:path/to/file
   git show BASE_BRANCH:path/to/file
   ```

4. **After resolving all conflicts:**
   ```bash
   git add .
   git commit -m "merge: Resolve conflicts from $STORY_ID"
   ```

If merges become too complicated, consider reverting and having the parallel agents rebase their branches before re-merging.

---

## Progress Report

After all merges are complete, append to `progress.txt`:

```
## [Date/Time] - Sequential Merge Complete
- Merged stories: US-001, US-002, US-003
- Conflicts resolved: [list any non-trivial conflict resolutions]
- All CI checks: PASS
- Pushed to: origin/$BASE_BRANCH
---
```

---

## Stop Condition

After all merges are complete and pushed:

1. Verify all worktrees are removed
2. Verify all claims are released
3. Verify CI is green on the main branch
4. Reply with: <promise>COMPLETE</promise>

---

## Important Notes

- **Merge in priority order** — follow the story priority from the PRD
- **Never force-push** — this can overwrite other work
- **Keep merges atomic** — one story per merge commit when possible
- **Test locally before pushing** — run CI checks after each merge
- **Communicate conflicts** — if a conflict indicates a design problem, consider pausing and discussing with the team
