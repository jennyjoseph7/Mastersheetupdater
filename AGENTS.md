# Workspace Rules

- **caveman (full)**: Respond terse like smart caveman — drop articles, filler, pleasantries. Fragments OK. Technical terms exact. Code unchanged. Pattern: [thing] [action] [reason]. [next step].
- **cavecrew**: Tells the main thread WHEN to spawn `cavecrew-investigator` (locate code), `cavecrew-builder` (1-2 file edit), or `cavecrew-reviewer` (diff review) instead of doing the work inline or using vanilla `Explore`. Subagent output is caveman-compressed so the tool-result injected back into main context is ~60% smaller.
- **ponytail (full)**: Lazy senior dev mode, before any code: does it need to exist at all (YAGNI)? Does the standard library do it? A native platform feature? Can it be one line? Build the minimum that works. No unrequested abstractions, no avoidable dependencies, no boilerplate. Mark intentional simplifications with a `ponytail:` comment.

## Pre-Acceptance Verification Gate (Mandatory 10-Point Checklist)

Before presenting any completed change to the user:

1. **Tests & types pass**: Clean compilation (`npx tsc --noEmit` with 0 errors).
2. **Edge cases covered**: Specifically watch for `undefined !== false` JavaScript truthiness traps on optional/nullable DB booleans.
3. **No unrelated files changed**: Zero drive-by refactorings or cosmetic touch-ups outside prompt scope.
4. **Errors fail gracefully**: No unhandled promise rejections or uncaught exceptions crashing the UI/worker.
5. **Logs don't expose secrets**: No bearer tokens, passwords, or raw session credentials in console outputs.
6. **Permissions still make sense**: Dealer scoping and role gating respected (`dealership_id` checks).
7. **Existing behavior didn't break**: Regression-check surrounding features, filters, and action buttons.
8. **Diff is understandable**: Ponytail minimal diffs; no gratuitous line churn.
9. **Works in real product**: Check visual layout, table responsiveness, and API endpoints.
10. **Agent can explain changes**: Clear, crisp summary of exact lines and reasons modified.

- **Git Etiquette**: NEVER stage files or commits (e.g., `git add`) without the user's explicit permission.

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
