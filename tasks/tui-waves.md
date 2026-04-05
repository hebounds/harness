# TUI Waves Completion Feature

## What's already in your favor

- **`DagScheduler` produces clean wave data** — `ExecutionPlan.waves: list[list[Story]]` is a ready-made layout structure. Each wave is a column, each story in that wave is a card.
- **`StoryStatus` is a proper state machine** — `NOT_STARTED → IN_PROGRESS → PASSED/FAILED` drives all the visual transitions without extra modeling.
- **Rich is already in use**, and **[Textual](https://github.com/Textualize/textual)** (from the same authors) is a direct upgrade — async-native, composable widgets, CSS theming.
- **`Orchestrator.run()` is async** — Textual's event loop is `asyncio`-based, so they compose without a threading shim.

## The TUI Design

```
Wave 1          Wave 2          Wave 3
┌──────────┐    ┌──────────┐    ┌──────────┐
│ US-001   │    │ US-003   │    │ US-006   │
│ ✓ PASSED │ ──▶│ ⟳ RUNNING│    │ · WAITING│
└──────────┘    │ ▓▓▓░░░░░ │    └──────────┘
                └──────────┘
```

- Waves render left-to-right; cards pulse/animate while `IN_PROGRESS`
- When a wave completes, the next wave animates in (the "literal wave" effect)
- A modal overlay fires when the orchestrator needs human resolution — the story card changes to an `⚠ BLOCKED` state, the overlay captures input, then resumes

## What Needs Building

1. **`HarnessApp(textual.App)`** — replaces `asyncio.run(orchestrator.run(...))` in `src/harness/cli/commands/run.py`
2. **`StoryCard(Widget)`** — CSS-driven state transitions, spinner while running
3. **`WaveColumn(Vertical)`** — one per wave from `ExecutionPlan.waves`
4. **Orchestrator event protocol** — lightweight message bus (`asyncio.Queue` or Textual `Message` subclasses) that the orchestrator posts status updates to, which the TUI subscribes to
5. **`BlockedModal`** — a `Screen` or `ModalScreen` that pauses the card and collects input when an agent op needs resolution

## The One Non-Trivial Part

The orchestrator/TUI boundary. Right now `Orchestrator.run()` is a black box. It needs to yield or emit events rather than block — something like a `status_callback: Callable[[str, StoryStatus], None]` or posting to a `Queue`. That's a minor design choice but needs to be deliberate so the TUI isn't polling.

## Verdict

A week of focused work could produce something compelling. Textual is the right tool, the data model is already correct, and the async foundation is there.
