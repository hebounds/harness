# PRD: Harness — An Opinionated Agent Orchestration System

## Introduction/Overview

Harness is a standalone, language-agnostic agent orchestration system extracted from the Ralph system in the Arguably codebase. It manages the full lifecycle of AI-driven codebase evolution — from PRD-driven feature implementation to automated refactoring, repo review, and maintenance — by removing deterministic operations from LLM prompts and executing them as code, dramatically reducing token waste and increasing reliability.

The core insight: LLMs are bad at deterministic operations (file naming conventions, git worktree management, JSON schema validation, atomic file claiming) but current agent systems embed these as natural-language instructions that consume context window and fail unpredictably. Harness moves all deterministic logic into a Python orchestration layer that wraps AI invocations, exposes read-only context via MCP tools, and provides pluggable per-language code understanding (AST, linting, formatting) so the agent always has deep structural awareness of the code it's modifying.

**Implementation language:** Python 3.12+ (managed via UV).
**Runtime target:** VS Code Copilot CLI (first-class).
**Architecture:** Designed for future container isolation and network gapping without requiring a rewrite.

### Why Python
- **Uniform language profile architecture:** Every language profile (TypeScript, Python, Go, Rust, etc.) works identically — shell out to the language's native toolchain (`tsc`, `mypy`, `go vet`, `cargo check`), parse structured output, expose via MCP. No special-cased programmatic API for any single language.
- **Pydantic v2:** Config validation, serialization, IDE autocomplete, discriminated unions, computed fields — strictly superior to alternatives for structured data modeling.
- **UV:** Eliminates Python's historical packaging pain. `uv run harness` just works.
- **MCP SDK:** Python is a reference implementation of the Model Context Protocol. First-class support.
- **Agent ecosystem:** LangChain, CrewAI, AutoGen, instructor, DSPy — all Python-first. Community patterns and knowledge are native.
- **tree-sitter:** Mature Python bindings for uniform cross-language AST parsing.
- **asyncio:** Clean subprocess management and structured concurrency for parallel agent orchestration.

## Goals

- Extract all deterministic operations from prompt files into callable Python functions managed by a parent harness
- Reduce system prompt token consumption by 60%+ by replacing natural-language instructions with harness-managed lifecycle hooks
- Provide pluggable, per-language code intelligence profiles (AST parsing, linting, formatting, type checking) loadable on demand
- Extend the progress.txt system to be PRD-scoped with structured machine-readable entries
- Enable multi-agent orchestrated workflows (implement, refactor, review, maintain) with a single CLI entrypoint
- Expose read-only context (patterns, progress, PRD status, codebase structure) to the agent via a local MCP server
- Ship with curated MCP server recommendations and integration guides for common dev tools
- Model PRD stories as a dependency DAG with explicit `dependsOn` edges, enabling maximum parallel agent execution across independent subgraphs
- Auto-subdivide coarse user stories into parallelizable sub-tasks via hybrid deterministic + agent-driven planning (V2)
- Provide vector DB-backed semantic memory (SQLite + sqlite-vss) that indexes progress, patterns, and code for efficient retrieval — replacing full-file prompt stuffing with similarity search
- Architect all interfaces with container isolation and network gapping as a future execution mode (V2)

## User Stories

### US-001: Core Harness CLI & Configuration
**Description:** As a developer, I want a CLI tool (`harness`) that reads a `harness_config.py` file and orchestrates agent invocations so that I don't need to manually manage the agent lifecycle.

**Acceptance Criteria:**
- [ ] `harness init` scaffolds a `harness_config.py` with a Pydantic `HarnessConfig` model and sensible defaults
- [ ] `harness run` reads config, resolves the active PRD, and begins the agent loop
- [ ] Config model supports: `model`, `runtime` (copilot), `max_iterations`, `prd_path`, `progress_path`, `tool_allowlist`, `tool_denylist`, `language_profiles`
- [ ] Harness exits on completion signal, max iterations, or unrecoverable error
- [ ] `mypy --strict` passes

### US-002: Deterministic Lifecycle Manager
**Description:** As a harness system, I want to execute all deterministic operations (claiming, worktree setup, branch creation, merging, archiving, progress appending) as code before/after each AI invocation so that the agent prompt contains zero lifecycle instructions.

**Acceptance Criteria:**
- [ ] `ClaimManager` — atomic claim creation/release/stale-cleanup using `os.open` with `O_CREAT | O_EXCL` (replaces bash `set -C` noclobber)
- [ ] `WorktreeManager` — create/teardown git worktrees, symlink `.env`, install deps
- [ ] `BranchManager` — create feature branches, merge back to base, handle conflicts (pause for human)
- [ ] `ArchiveManager` — archive old PRDs with date-stamped directories
- [ ] `ProgressManager` — append structured entries to progress files
- [ ] Each manager is independently testable with injected dependencies (no global state)
- [ ] No deterministic operation instructions remain in agent system prompts
- [ ] `mypy --strict` passes
- [ ] Tests pass

### US-003: PRD-Scoped Progress System
**Description:** As a developer, I want progress tracking to be scoped per-PRD rather than a single global `progress.txt` so that each feature's learnings, patterns, and history are self-contained and don't pollute unrelated work.

**Acceptance Criteria:**
- [ ] Each PRD gets a companion `progress/prd-{name}.progress.md` file
- [ ] Global `progress/codebase-patterns.md` holds cross-cutting learnings (extracted from current `## Codebase Patterns` section)
- [ ] Progress entries are structured with machine-readable frontmatter (story ID, timestamp, files changed, status)
- [ ] `ProgressManager.append()` writes entries; `ProgressManager.summarize()` produces a context-window-friendly summary for the agent
- [ ] When injecting progress into agent context, harness selects: (1) codebase patterns, (2) current PRD progress, (3) relevant entries from other PRDs (by file overlap)
- [ ] `mypy --strict` passes
- [ ] Tests pass

### US-004: Minimal Agent System Prompt & Token Budget
**Description:** As a harness system, I want to generate a minimal, focused system prompt for each agent invocation that contains only: the task description, relevant codebase patterns, and tool usage guidance — no lifecycle instructions — with a token ceiling that prevents context overflow.

**Acceptance Criteria:**
- [ ] `PromptBuilder` class assembles the system prompt from Jinja2 templates
- [ ] Prompt sections: role, current story (from PRD), relevant patterns (from vector DB), available tools (from MCP), language-specific guidance (from active profile)
- [ ] Total system prompt is under 2,000 tokens for a typical story (vs. current ~4,000+ with lifecycle instructions)
- [ ] Prompt includes a "MUST USE" directive for available code intelligence tools (AST, linting) — the agent should prefer structural tools over grep when they're available
- [ ] Template variables (`{{STORY_ID}}`, `{{BASE_BRANCH}}`, `{{WORKTREE_DIR}}`) are resolved by the harness, not left for the agent
- [ ] Token ceiling: configurable `max_prompt_tokens` in `harness_config.py`; when assembled prompt exceeds limit, lowest-priority section is truncated with a warning log
- [ ] Token counting uses `tiktoken` for accurate estimation
- [ ] `mypy --strict` passes

### US-005: Language Profile System
**Description:** As a developer, I want pluggable language profiles that provide linting, formatting, type-checking, symbol extraction, and reference finding so that the agent has deep structural code understanding for whatever language it's working in.

**Acceptance Criteria:**
- [ ] `LanguageProfile` Protocol with methods: `lint(file) -> list[Diagnostic]`, `format(file) -> str`, `typecheck(project) -> list[Diagnostic]`, `get_symbols(file) -> list[Symbol]`, `find_references(symbol, project) -> list[Location]`
- [ ] Every profile works identically: shell out to the language's native toolchain / language server, parse structured output. No special-cased programmatic APIs.
- [ ] `find_references` integrates with language servers (`tsserver` for TS, `pyright` for Python) for cross-file reference resolution
- [ ] TypeScript profile ships built-in: `tsc --noEmit` for typecheck, `eslint --format=json` for linting, `prettier --write` for formatting, tree-sitter for symbols, `tsserver` for references
- [ ] Python profile ships built-in: `mypy --output=json` for typecheck, `ruff check --output-format=json` for linting, `ruff format` for formatting, tree-sitter for symbols, `pyright` for references
- [ ] Profiles loaded on-demand from `harness/profiles/{language}.py`
- [ ] Auto-detection from config files (tsconfig.json → TS, pyproject.toml → Python, go.mod → Go, Cargo.toml → Rust)
- [ ] Agent system prompt includes profile capabilities as tool descriptions
- [ ] `mypy --strict` passes

### US-006: Local MCP Server for Agent Context
**Description:** As an agent, I want read-only MCP tools that expose codebase context (PRD status, progress, patterns, file structure, language profile results) so that I can query for relevant information without relying on prompt stuffing.

**Acceptance Criteria:**
- [ ] MCP server starts as a subprocess managed by the harness, communicates via stdio
- [ ] Tools exposed: `get_prd_status` (stories, passes, priorities), `get_patterns` (codebase patterns relevant to current story via vector similarity), `get_progress` (current PRD progress entries), `get_file_symbols` (AST symbols for a file via active language profile), `get_diagnostics` (lint/type errors for a file or project), `search_references` (find usages of a symbol), `search_memory` (semantic search across all indexed progress/patterns/code)
- [ ] All tools are read-only — no mutation of harness state via MCP
- [ ] MCP server config is auto-generated and injected into Copilot's MCP settings
- [ ] `mypy --strict` passes
- [ ] Tests pass

### US-007: Multi-Agent Workflow Orchestrator
**Description:** As a developer, I want to define multi-agent workflows (implement → review → refine, or parallel feature work with sequential merge) so that complex operations are broken into specialized agent passes.

**Acceptance Criteria:**
- [ ] `Workflow` dataclass defines a DAG of agent invocations with named stages
- [ ] Built-in workflows: `implement` (current Ralph loop), `review` (repo-review skill), `refactor` (targeted refactoring with AST analysis), `full-cycle` (implement → lint-fix → review → address-review)
- [ ] Each workflow stage can specify: system prompt overrides, tool permissions, max iterations, success criteria
- [ ] Workflow state is persisted (JSON) so a crashed harness can resume from the last completed stage
- [ ] `harness run --workflow full-cycle` executes the named workflow
- [ ] Parallel stages are supported via `asyncio.gather` (e.g., parallel feature implementation before sequential merge)
- [ ] `mypy --strict` passes

### US-008: MCP Server Recommendations & Briefings
**Description:** As a developer, I want the harness to ship with recommended MCP server configs and usage briefings so that agents can leverage external tools (GitHub, databases, browsers) when available.

**Acceptance Criteria:**
- [ ] `harness/mcp_catalog/` directory with recommended MCP server configs: `github.json`, `filesystem.json`, `browser.json`, `database.json`
- [ ] Each config includes: server package name, install command, required env vars, capability description, and a brief agent-facing usage guide
- [ ] `harness init` prompts for which MCP servers to enable and writes their configs
- [ ] Agent system prompt includes an "Available External Tools" section listing enabled MCP servers with 1-line usage notes
- [ ] Briefings tell the agent WHEN to use each tool (e.g., "Use github MCP to check PR status before merging" or "Use browser MCP to verify UI changes")
- [ ] `mypy --strict` passes

### US-009: Container Isolation Interface (V2 Architecture)
**Description:** As a harness architect, I want all agent execution to go through an `ExecutionEnvironment` interface so that swapping from local worktree execution to Docker container execution requires only a new implementation, not a rewrite.

**Acceptance Criteria:**
- [ ] `ExecutionEnvironment` Protocol with methods: `async setup(story) -> Context`, `async execute(command) -> Result`, `get_filesystem() -> FS`, `async teardown()`
- [ ] `LocalWorktreeEnvironment` implements the protocol (V1 default — current worktree behavior)
- [ ] `ContainerEnvironment` is stubbed with `raise NotImplementedError` but the protocol is fully typed
- [ ] All harness managers (Claim, Worktree, Branch) operate through the `ExecutionEnvironment` protocol, never directly calling `os`/`subprocess`
- [ ] Protocol supports a `network_policy` option (`full`, `restricted`, `gapped`) for V2 network isolation
- [ ] `mypy --strict` passes

### US-010: Dependency DAG Scheduler
**Description:** As a developer, I want PRD stories modeled as a dependency graph so the harness can automatically identify which stories are parallelizable and schedule them for concurrent agent execution.

**Acceptance Criteria:**
- [ ] PRD JSON schema extended with `dependsOn: list[str]` (story IDs) and optional `parallelGroup: str`
- [ ] `DagScheduler` builds a dependency graph from PRD stories, validates for cycles, and returns the set of "ready" stories (all dependencies satisfied)
- [ ] `harness run` claims and dispatches all ready stories in parallel (up to `max_parallel_agents` from config)
- [ ] As stories complete, scheduler re-evaluates the graph and dispatches newly-unblocked stories
- [ ] Stories with no `dependsOn` field are treated as depending on nothing (immediately ready)
- [ ] `harness plan` prints the execution plan: parallel groups, critical path, estimated waves
- [ ] `mypy --strict` passes
- [ ] Tests pass

### US-011: Vector DB Semantic Memory
**Description:** As a harness system, I want a vector database that indexes progress entries, codebase patterns, and code summaries so that agents can semantically retrieve relevant context instead of receiving full file dumps.

**Acceptance Criteria:**
- [ ] SQLite + sqlite-vss as the embedded vector store (zero external services)
- [ ] `MemoryIndex` class with methods: `index_progress(entry)`, `index_pattern(pattern)`, `index_code_summary(file, symbols)`, `search(query, top_k) -> list[MemoryResult]`
- [ ] Embeddings generated via `fastembed` (ONNX-based, ~50MB, no PyTorch dependency) as the default provider
- [ ] Optional OpenAI embeddings API as a configurable alternative for higher quality
- [ ] Progress entries auto-indexed on append; code summaries re-indexed on file change
- [ ] MCP tool `search_memory` delegates to `MemoryIndex.search()`
- [ ] `get_patterns` MCP tool uses vector similarity to retrieve relevant patterns instead of dumping the entire patterns file
- [ ] DB file stored at `.harness/memory.db` in the project root (gitignored)
- [ ] `mypy --strict` passes
- [ ] Tests pass

### US-012: Agent Output Parsing & Completion Detection
**Description:** As a harness system, I want to parse agent stdout to detect completion, success, failure, and partial progress so that the harness can decide whether to commit, retry, or escalate to a human.

**Acceptance Criteria:**
- [ ] `AgentOutputParser` class consumes agent stdout/stderr stream in real-time
- [ ] Detects completion signal (configurable, default: `<promise>COMPLETE</promise>` for backward compat with Ralph)
- [ ] Detects failure signals (agent explicitly reporting it cannot complete the task)
- [ ] Post-invocation validation: checks `git status` for uncommitted changes, verifies the agent actually modified files relevant to the story
- [ ] Handles partial completion: if agent ran out of context mid-task, harness logs state and can re-invoke with narrower scope or flag for human review
- [ ] Retry logic: configurable `max_retries` per story; on failure, re-invokes with error context appended to prompt
- [ ] All completion/failure events logged with structured metadata for debugging
- [ ] `mypy --strict` passes
- [ ] Tests pass

### US-013: CI Verification Gate
**Description:** As a harness system, I want to run automated verification checks (lint, typecheck, tests) between agent completion and merge so that broken code never reaches the base branch.

**Acceptance Criteria:**
- [ ] `VerificationGate` class runs configured checks after agent signals completion
- [ ] Default checks sourced from active language profile: `profile.lint()`, `profile.typecheck()`; optional: project-level test command from config (`verification_command` in `harness_config.py`)
- [ ] On success: proceed to merge
- [ ] On failure with retries remaining: re-invoke agent with diagnostic output (lint errors, type errors, test failures) appended to prompt as "Fix these issues"
- [ ] On failure with no retries: preserve worktree, log full diagnostic output, mark story as `failed` in PRD, alert human
- [ ] Gate results logged as structured progress entries
- [ ] `mypy --strict` passes
- [ ] Tests pass

## Functional Requirements

- **FR-1:** The harness CLI must be installable via `uv tool install harness` or runnable via `uv run harness`
- **FR-2:** All deterministic operations (claim, worktree, branch, archive, progress) must execute as Python functions, never as LLM-interpreted natural language instructions
- **FR-3:** The harness must inject the agent's system prompt dynamically based on current story, available tools, active language profile, and context budget
- **FR-4:** Language profiles must be hot-loadable — the harness detects the project language and loads the appropriate profile without restart
- **FR-5:** The MCP server must start and stop automatically with the harness process — no manual server management
- **FR-6:** Progress entries must be machine-parseable (structured frontmatter) AND human-readable (markdown body)
- **FR-7:** The harness must handle agent crashes gracefully: release claims, preserve worktree state for debugging, log failure context
- **FR-8:** All managers must accept a `root_path` parameter and perform I/O relative to it, enabling future redirection to container-mounted paths without requiring an abstraction layer
- **FR-9:** The harness must support `--dry-run` mode that shows what it would do without invoking the agent
- **FR-10:** Workflow definitions must be expressible as Python code (not JSON/YAML) for full type safety and conditional logic
- **FR-11:** The agent system prompt must include a directive that when AST/lint/typecheck tools are available, the agent SHOULD use them instead of text-based grep for structural code queries
- **FR-12:** PRD stories must support explicit `dependsOn` edges forming a DAG; the scheduler must resolve parallel execution order from this graph
- **FR-13:** Vector memory index must auto-update on progress append and support semantic search via MCP tool
- **FR-14:** The harness must parse agent output in real-time and detect completion, failure, and partial-completion signals
- **FR-15:** No agent-produced code may be merged without passing a configurable verification gate (lint + typecheck at minimum)

## Non-Goals (Out of Scope)

- **Custom LLM hosting** — Harness uses Copilot CLI as the runtime; no OpenAI/Anthropic API key management
- **Web UI / Dashboard** — CLI-only interface; no web-based monitoring
- **Real-time collaboration** — Single developer operating the harness; no multi-user coordination
- **Container execution (V1)** — Architected for it, but V1 ships with local worktree execution only
- **Network gapping (V1)** — Protocol supports `network_policy` but enforcement is V2
- **IDE plugin** — No VS Code extension; harness is a CLI tool that happens to invoke Copilot CLI
- **Go/Rust profiles (V1)** — Protocol is pluggable; only TypeScript + Python profiles ship in V1
- **Billing/usage tracking** — No token cost estimation or usage dashboards
- **Auto story subdivision (V2)** — Hybrid deterministic + agent-driven sub-task generation; humans write fine-grained stories for V1
- **sentence-transformers embeddings (V3)** — PyTorch-based embeddings for higher quality; V1 uses `fastembed` (ONNX, ~50MB, no PyTorch)

## Design Considerations

### Directory Structure
```
harness/
├── src/
│   └── harness/
│       ├── __init__.py
│       ├── cli.py             # CLI entrypoint (typer)
│       ├── config.py          # Pydantic HarnessConfig model
│       ├── core/
│       │   ├── claim.py       # ClaimManager
│       │   ├── worktree.py    # WorktreeManager
│       │   ├── branch.py      # BranchManager
│       │   ├── archive.py     # ArchiveManager
│       │   ├── progress.py    # ProgressManager
│       │   ├── scheduler.py   # DagScheduler
│       │   ├── output.py      # AgentOutputParser
│       │   └── verify.py      # VerificationGate
│       ├── prompt/
│       │   ├── builder.py     # PromptBuilder + token ceiling
│       │   └── templates/     # Jinja2 prompt templates
│       ├── mcp/
│       │   ├── server.py      # MCP server (stdio transport)
│       │   └── tools.py       # Tool definitions
│       ├── memory/
│       │   ├── index.py       # MemoryIndex (sqlite-vss)
│       │   └── embeddings.py  # Embedding provider (fastembed default)
│       ├── profiles/
│       │   ├── base.py        # LanguageProfile Protocol
│       │   ├── typescript.py  # TS profile (tsc, eslint, prettier, tsserver)
│       │   └── python.py      # Python profile (mypy, ruff, pyright)
│       ├── workflows/
│       │   ├── engine.py      # Workflow DAG engine
│       │   └── builtins.py    # implement, review, refactor, full-cycle
│       └── execution/
│           ├── base.py        # ExecutionEnvironment Protocol
│           ├── local.py       # LocalWorktreeEnvironment
│           └── container.py   # ContainerEnvironment (stub)
├── mcp_catalog/               # Recommended MCP server configs + briefings
├── templates/                 # Default config template, prompt templates
├── tests/
├── pyproject.toml
└── uv.lock
```

### Lifecycle Flow (Single Story)
```
harness run
  → Read harness_config.py (Pydantic validation)
  → Load PRD → DagScheduler.build_graph()
  → For each "ready" story (dependencies satisfied):
    → ClaimManager.claim() — atomic via O_CREAT|O_EXCL
    → WorktreeManager.create() — git worktree + symlinks + deps
    → LanguageProfile.detect() — load appropriate profile
    → MemoryIndex.search(story) — retrieve relevant context
    → MCP server start (stdio subprocess)
    → PromptBuilder.build() — minimal prompt within token ceiling
    → Copilot CLI invocation
      → AgentOutputParser monitors stdout/stderr in real-time
      → On completion signal detected:
        → VerificationGate.run() — lint, typecheck, optional tests
        → If gate PASSES:
          → ProgressManager.append() — structured entry
          → MemoryIndex.index_progress() — update vector store
          → BranchManager.merge() — merge feature branch
          → WorktreeManager.teardown() — clean up
          → ClaimManager.release()
          → PRD update (passes: true)
        → If gate FAILS + retries remaining:
          → Re-invoke agent with diagnostics appended to prompt
        → If gate FAILS + no retries:
          → Preserve worktree, mark story failed, alert human
      → On failure/partial signal:
        → Log context, retry or escalate per config
    → DagScheduler.reevaluate() — find newly-unblocked stories
  → Loop until DAG complete or max iterations
```

### Lifecycle Flow (Parallel Agents)
```
harness run --parallel 3
  → Build DAG → identify all ready stories
  → asyncio.gather(agent_1(US-001), agent_2(US-002), agent_3(US-004))
  → As each completes → re-evaluate DAG → dispatch next ready story to free slot
  → Sequential merge pass when all parallel stories in a wave complete
```

### Relationship to Existing Ralph System
- `work.md` / `parellel_work.md` → harness lifecycle + minimal prompt template
- `parallel_merge.md` → `BranchManager` + merge workflow stage
- `ralph.sh` → `harness run` CLI
- `progress.txt` → PRD-scoped progress files + global patterns file + vector index
- `tasks/claims/` → `ClaimManager` (same semantics, Python instead of bash)
- Skills (prd, ralph, repo-review) → workflow stages with dedicated prompts

## Technical Considerations

- **MCP Protocol:** `mcp` (Python reference SDK) — stdio transport
- **Git operations:** `GitPython` or `pygit2` for programmatic worktree/branch/merge
- **Token counting:** `tiktoken` for accurate context budget management
- **AST parsing:** tree-sitter Python bindings (`tree-sitter`) — uniform cross-language AST for all profiles
- **Language toolchains:** Each profile shells out to native tools (`tsc`, `eslint`, `mypy`, `ruff`, `go vet`, `cargo check`) and parses structured JSON output
- **Process management:** `asyncio.create_subprocess_exec` for Copilot CLI + MCP server subprocesses
- **Config/validation:** Pydantic v2 for `harness_config.py` and all internal data models
- **Templating:** Jinja2 for prompt templates
- **CLI framework:** `typer` (built on click, gives type-safe CLI args with zero boilerplate)
- **Vector DB:** `sqlite-vss` extension for SQLite — zero external services, file-based
- **Embeddings:** `fastembed` (ONNX-based, ~50MB, no PyTorch) as default; optional OpenAI embeddings API for higher quality; `sentence-transformers` deferred to V3
- **Language servers:** `tsserver` (bundled with TypeScript) and `pyright` for cross-file reference resolution in profiles
- **DAG operations:** Standard library (`graphlib.TopologicalSorter` in Python 3.9+) — no external dependency needed
- **Testing:** `pytest` + `pytest-asyncio`

### Container Isolation (V2 Design Notes)
- `ContainerEnvironment` will build a Docker image with: project source, `.env`, language tooling, MCP server
- Volume mount for worktree directory enables file persistence across container restarts
- Network policies map to Docker network modes: `full` (bridge), `restricted` (internal + allowlisted hosts), `gapped` (none)
- Agent invocation inside container: `docker exec <container> copilot ...`
- MCP server runs inside container; harness communicates via Docker exec stdio

### Cutting-Edge Techniques Incorporated
1. **Dependency DAG scheduling** — Stories modeled as a graph; harness resolves parallel execution order and dispatches multiple agents concurrently across independent subgraphs
2. **Semantic memory retrieval** — Vector DB indexes progress, patterns, and code; agents query via MCP instead of receiving full file dumps
3. **Automated verification gate** — Language profile-driven lint/typecheck/test between agent completion and merge; failures trigger re-invocation with diagnostics
4. **Real-time output parsing** — Stream-based agent output monitoring with completion/failure/partial-progress detection and configurable retry logic
5. **Context distillation** — `ProgressManager.summarize()` compresses verbose history into token-efficient summaries
6. **Structural-first code understanding** — Agent instructed to prefer AST/symbol/reference tools over text grep when profiles are available; language server integration for cross-file analysis
7. **Deterministic extraction** — All predictable operations removed from LLM decision space
8. **Workflow DAGs** — Multi-agent passes with typed stage definitions and conditional routing
9. **Token budgeting** — Token ceiling on assembled prompts prevents context overflow
10. **Execution environment abstraction** — Clean protocol boundary enables local → container → cloud migration path
11. **MCP-native context delivery** — Agent pulls context on-demand vs. prompt stuffing everything upfront

## Success Metrics

- System prompt token count reduced by 60%+ compared to current `work.md` approach
- Zero deterministic operation failures due to LLM misinterpretation (file naming, claim races, git commands)
- Agent can complete a typical user story in ≤2 Copilot invocations (vs. current single long invocation)
- Language profile integration: agent uses AST/symbol/reference tools for ≥50% of code navigation queries when profile is active
- Verification gate catches ≥90% of agent-introduced lint/type errors before merge
- PRD-scoped progress files contain structured, queryable history for every completed story
- Harness can orchestrate 3+ parallel agents without race conditions or worktree conflicts
- DAG scheduler achieves ≥2x throughput improvement over sequential execution on PRDs with parallelizable stories
- Vector memory search returns relevant patterns in <100ms for 95th percentile queries
- New language profile addable in <150 lines of Python via the plugin protocol

## Open Questions

1. **Claim persistence across harness crashes** — Should claims survive harness process death (current behavior via filesystem), or should the harness register a SIGTERM handler that always releases? Recommendation: keep filesystem persistence + stale timeout (current 30min approach) since it's more robust.

2. **MCP tool granularity** — Should `get_file_symbols` return the full AST or a filtered summary? Full AST could be too large for context. Recommendation: return a summary (function names, class names, exports) with a `get_symbol_detail(name)` follow-up tool for drilling down.

3. **Workflow definition location** — Should custom workflows live in `harness_config.py` (centralized) or as separate files in `harness/workflows/`? Recommendation: built-in workflows in the package, custom workflows in `harness_config.py`.

4. **Progress format migration** — How to handle the existing `progress.txt` with its global patterns + per-story entries? Recommendation: one-time migration script that splits into `progress/codebase-patterns.md` + `progress/prd-{name}.progress.md`.
