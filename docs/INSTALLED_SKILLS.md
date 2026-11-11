# Agent Skills & Workflows Sync Catalog

This document tracks all skills, workflows, and standing rules across `autobot_agents` and `Mastersheetupdater`, highlighting new additions and synchronization status.

---

## 1. Newly Added in `autobot_agents/.agents` (Nov 11)

| Item | Type | Path | Purpose |
|---|---|---|---|
| **`andrej-karpathy-skills`** | Skill | `.agents/skills/andrej-karpathy-skills/` | Think-before-code discipline, YAGNI, surgical 1-5 line diffs, goal-driven verification loops. |
| **`elephant-goldfish-model`** | Skill | `.agents/skills/elephant-goldfish-model/` | Dual-perspective planning: Elephant holds long repo context to draft; Goldfish audits cold with zero bias. |
| **`design`** | Workflow | `.agents/workflows/design.md` | Master 5-phase frontend design pipeline: Hallmark floor → UI-UX Pro Max → Typography → UI-Styling/shadcn → Impeccable audit. |
| **Implementation Triad** | Rules | `.agents/AGENTS.md` | Mandatory Pre-Planning Gate enforcing `andrej-karpathy-skills` + `ponytail` + `elephant-goldfish-model`. |

---

## 2. Synchronization Matrix Across Repositories

| # | Skill / Workflow Name | Category | In `autobot_agents`? | In `Mastersheetupdater`? | Sync Action Needed |
|---|---|---|:---:|:---:|:---:|
| 1 | **`andrej-karpathy-skills`** | Codecraft / Pre-Planning | ✅ Present | ❌ Missing | **Copy to Mastersheetupdater** |
| 2 | **`elephant-goldfish-model`** | Spec Review / Pre-Planning | ✅ Present | ❌ Missing | **Copy to Mastersheetupdater** |
| 3 | **`design` (workflow)** | Frontend Master Pipeline | ✅ Present | ❌ Missing | **Copy to Mastersheetupdater** |
| 4 | **`autobot-codecraft`** | Domain Authority Baseline | ✅ Present | ✅ Present | Synchronized |
| 5 | **`no-ai-slop`** | Anti-AI Prose Editor | ✅ Present | ✅ Present | Synchronized |
| 6 | **`open-code-review`** | Code Review CLI (`ocr`) | ✅ Present | ✅ Present | Synchronized |
| 7 | **`security-audit`** | Cloudflare Security Scanner | ✅ Present | ✅ Present | Synchronized |
| 8 | **`frontend-design`** | Visual Design Baseline | ✅ Present | ✅ Present | Synchronized |
| 9 | **`design-taste-frontend`** | Taste 2.5 Anti-Slop UI | ✅ Present | ✅ Present | Synchronized |
| 10 | **`hallmark`** | 21 Themes & 58 Audits | ✅ Present | ✅ Present | Synchronized |
| 11 | **`better-typography`** | Jakub Krehel Type Scales | ✅ Present | ✅ Present | Synchronized |
| 12 | **`interface-design`** | Craft-First Dashboard UI | ✅ Present | ✅ Present | Synchronized |
| 13 | **`ui-ux-pro-max`** | 192 Palettes / 119 UX Rules | ✅ Present | ✅ Present | Synchronized |
| 14 | **`ui-styling`** | Radix + Tailwind Components | ✅ Present | ✅ Present | Synchronized |
| 15 | **`impeccable`** | 6-Pillar UI Polish Engine | ✅ Present | ✅ Present | Synchronized |
| 16 | **`design-system`** | 3-Tier Design Tokens | ✅ Present | ✅ Present | Synchronized |
| 17 | **`hue`** | Meta Design Skill Generator | ✅ Present | ✅ Present | Synchronized |
| 18 | **`shadcn`** | shadcn/ui Component Registry | ✅ Present | ✅ Present | Synchronized |
| 19 | **`stitch-extract-design-md`** | Codebase to Stitch DESIGN.md | ✅ Present | ✅ Present | Synchronized |
| 20 | **`design-md`** | Google Stitch Design Tokens | ✅ Present | ✅ Present | Synchronized |
| 21 | **`graphify`** | AST Knowledge Graph & MCP | ✅ Present | ✅ Present | Synchronized |
| 22 | **`ponytail`** | Lazy Senior Dev Mode (YAGNI) | ✅ Present | ✅ Present | Synchronized |
| 23 | **`cavecrew`** | Subagent Dispatcher | ❌ Missing | ✅ Present | Optional sync to autobot |
| 24 | **`caveman`** | Ultra-Terse Communication | ❌ Missing | ✅ Present | Optional sync to autobot |
| 25 | **`ponytail-audit`** | Whole-Repo Bloat Audit | ❌ Missing | ✅ Present | Optional sync to autobot |
| 26 | **`ponytail-debt`** | Deferred Shortcuts Ledger | ❌ Missing | ✅ Present | Optional sync to autobot |
| 27 | **`ponytail-gain`** | Token/Line Reduction Score | ❌ Missing | ✅ Present | Optional sync to autobot |
| 28 | **`ponytail-help`** | Ponytail Quick-Reference | ❌ Missing | ✅ Present | Optional sync to autobot |
| 29 | **`ponytail-review`** | Complexity Code Review | ❌ Missing | ✅ Present | Optional sync to autobot |

---

## 3. Profiles of the New Skills

### 1. `andrej-karpathy-skills`
* **Trigger**: Any task requiring implementation planning or code modifications.
* **Core Tenets**:
  * **Think Before Coding**: Surface hidden assumptions; stop and clarify ambiguity before writing lines.
  * **Simplicity First**: Minimum code that solves the problem. No single-use abstractions or speculative configurability.
  * **Surgical Changes**: Touch only necessary lines; do not "clean up" unrelated adjacent code.
  * **Goal-Driven Execution**: Define exact step-by-step verification checks.

### 2. `elephant-goldfish-model`
* **Trigger**: Prior to finalizing any implementation plan.
* **Core Tenets**:
  * **Elephant Role**: Uses deep repository memory and data flow awareness to draft the technical approach.
  * **Goldfish Role**: Audits the draft with zero conversational bias against a 5-point checklist (unstated assumptions, hidden coupling, over-complexity, edge case traps, testability).

### 3. `design` Workflow (`workflows/design.md`)
* **Trigger**: Substantial UI work (new pages, modals, tables, redesigns).
* **Pipeline Structure**:
  1. *Hallmark Anti-Slop Floor*: Strict theme tokens only, safe CSS transitions, no arbitrary hex codes, no AI design cliches.
  2. *UI-UX Pro Max*: 60-30-10 palette rules and searchable design styles.
  3. *Interface Design & Typography*: Descending scale hierarchy, column constraints, responsive tables.
  4. *UI-Styling & shadcn*: Radix primitives, accessible focus rings.
  5. *Impeccable Audit*: Contrast, spacing, and polish verification.

---

## 4. Sync Instructions (To Apply in `Mastersheetupdater`)

To install the new skills and workflow into `Mastersheetupdater`:

```bash
# 1. Copy new skills from autobot_agents
cp -r /home/jejo/autobot_agents/.agents/skills/andrej-karpathy-skills /home/jejo/Mastersheetupdater/.agents/skills/
cp -r /home/jejo/autobot_agents/.agents/skills/elephant-goldfish-model /home/jejo/Mastersheetupdater/.agents/skills/

# 2. Copy master design workflow
cp /home/jejo/autobot_agents/.agents/workflows/design.md /home/jejo/Mastersheetupdater/.agents/workflows/

# 3. Verify detection
cd /home/jejo/Mastersheetupdater && npx skills list
```

