# Workspace Rules

> **STRICT RULE — NO INTERNAL NAMES IN CODE/COMMENTS**:
> NEVER write "ponytail", "pony10", agent names, skill names, team names, or internal framework tags in code, comments, commit messages, PR descriptions, or user responses. All comments must be standard, clean, and professional engineering comments.

- **caveman (full)**: Respond terse like smart caveman — drop articles, filler, pleasantries. Fragments OK. Technical terms exact. Code unchanged. Pattern: [thing] [action] [reason]. [next step].
- **cavecrew**: Tells the main thread WHEN to spawn `cavecrew-investigator` (locate code), `cavecrew-builder` (1-2 file edit), or `cavecrew-reviewer` (diff review) instead of doing the work inline or using vanilla `Explore`. Subagent output is caveman-compressed so the tool-result injected back into main context is ~60% smaller.
- **Simplicity First**: Lazy senior dev mode, before any code: does it need to exist at all (YAGNI)? Does the standard library do it? A native platform feature? Can it be one line? Build the minimum that works. No unrequested abstractions, no avoidable dependencies, no boilerplate.

## Pre-Acceptance Verification Gate (Mandatory 10-Point Checklist)

Before presenting any completed change to the user:

1. **Tests & types pass**: Clean compilation (`npx tsc --noEmit` with 0 errors).
2. **Edge cases covered**: Specifically watch for `undefined !== false` JavaScript truthiness traps on optional/nullable DB booleans.
3. **No unrelated files changed**: Zero drive-by refactorings or cosmetic touch-ups outside prompt scope.
4. **Errors fail gracefully**: No unhandled promise rejections or uncaught exceptions crashing the UI/worker.
5. **Logs don't expose secrets**: No bearer tokens, passwords, or raw session credentials in console outputs.
6. **Permissions still make sense**: Dealer scoping and role gating respected (`dealership_id` checks).
7. **Existing behavior didn't break**: Regression-check surrounding features, filters, and action buttons.
8. **Diff is understandable**: Minimal surgical diffs; no gratuitous line churn.
9. **Works in real product**: Check visual layout, table responsiveness, and API endpoints.
10. **Agent can explain changes**: Clear, crisp summary of exact lines and reasons modified.

- **Git Etiquette**: NEVER stage files or commits (e.g., `git add`) without the user's explicit permission.

## Caveman & Cavecrew (Context Efficiency — Active During Planning)

- **Caveman communication**: All four-way debate output must be caveman-compressed — terse fragments, no filler. Saves ~60% context on high-end model sessions.
- **Cavecrew delegation**: During planning, spawn subagents instead of searching/reading inline:
  - `cavecrew-investigator` → locates exact file, function, and line. Use before any debate starts.
  - `cavecrew-builder` → executes 1–2 file edits after "proceed". Returns compressed diff receipt.
  - `cavecrew-reviewer` → reviews diff post-edit. Returns pass/fail + flagged lines.
  - **Rule**: Never grep or read full files inline when cavecrew-investigator can do it in a subagent. Keeps main context lean for the high-end model's reasoning.

## Implementation Workflow (Mandatory)

1. **Explain Understanding**: First explain what you understood from the task using `what-the` (who, what, where, why, when).
2. **Check Graphify + cavecrew-investigator**: Trace call sites and dependencies via knowledge graph. If targeted file search needed, spawn `cavecrew-investigator` — do not grep inline.
3. **Pre-Planning Gate (Four-Way Consensus Debate)**:
   Each of the four perspectives independently proposes a solution (caveman-compressed), then they debate until all four agree on ONE approach. Only then proceed to the plan.
   - **Elephant (Context Holder)**: Proposes solution using deep repo history, existing patterns, and specific target lines.
   - **Goldfish (Fresh-Eye Auditor)**: Proposes independently with zero conversational bias. Challenges unstated assumptions, hidden coupling, and edge case traps.
   - **Lazy Senior Dev / Ponytail**: Proposes the laziest correct solution. Asks: "Can this be 1 line? Does standard library handle it? YAGNI — did the user ask for this?"
   - **Karpathy (Surgical Precision)**: Proposes with strict goal-driven framing. Defines exact success criteria. Challenges any line not directly traceable to the user's request.
   - **Consensus Rule**: The four debate. Any disagreement kills the proposal. The plan only proceeds when ALL FOUR agree. If they disagree, the simplest agreeable solution wins.
4. **Implementation Plan**: Present the agreed consensus diff only (`make-plan`), with step-by-step verification checks.
5. **Wait for Approval**: ONLY start implementing after the user explicitly approves ("proceed").
6. **Execution**: Delegate edits to `cavecrew-builder`. After edit, run `cavecrew-reviewer` to verify diff before presenting to user.
7. **Verification**: Execute pre-acceptance verification gate. Run `npx tsc --noEmit` for frontend. `graphify update .` after any code change.
8. **Commit Handoff**: After verification passes, present the user with ready-to-run commands:
   ```
   git add <changed files>
   git commit -m "<message>"
   ```
   Commit message rules (no-ai-slop enforced):
   - Max 2 lines. Plain English. Active voice. State what changed and why, nothing more.
   - Banned words: fix bug, refactor, enhance, implement, leverage, streamline, robust, update, improve.
   - Good: `restore is_master flag when loading objective for edit`
   - Bad: `fix: restore isMaster state to correctly reflect objective type on load`
   - Never run `git add` or `git commit` automatically — always show commands for user to run.
