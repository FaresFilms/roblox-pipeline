# Studio Context for AI Assistants

Paste this at the start of a chat. It explains how our Roblox game studio operates so you can help without us re-explaining. Read it as authoritative background, not as a task. Time-sensitive facts (model versions, plan prices, platform policy) may have moved since this was written — verify those before relying on them.

---

## Who we are

A small Roblox game studio (2 founders, growing). We run a **portfolio model**: ship many tight, polished, retention-focused games efficiently, kill the ones that don't retain, and double down on the ones that take off. Speed and polish per game both matter; a polished small game beats a broken big one.

We come up with ideas and design; **Claude does the coding** via Claude Code connected to Roblox Studio through an MCP. We source models/audio where needed.

## How a game gets made (the pipeline)

Everything runs through a fixed command pipeline in Claude Code. The commands live globally in `~/.claude/commands/` and are installed by a setup script (`prepare.py`). The flow:

1. **`/doc <1-2 sentence idea>`** → writes `design/game-document.md`, a complete, decision-complete Game Document (250-400 lines, real numbers, every choice made — no open questions). **This is the single source of truth and the only review step.** All our design thinking goes here; we edit it until it's final.
2. **`/use <name>`** (optional) → pulls a reusable system spec (e.g. `/use pets`) from `~/.claude/definitions/` and folds it into the Game Document, adapted to this game. Used only on games that want that system.
3. **`/prompts`** → reads the finalized document and writes the full set of detailed, self-contained build prompts as files in `prompts/` (one per step), plus an index.
4. **`/next`** (repeat) → builds the next prompt in Studio via the MCP, then **playtests and screenshots its own work to verify it actually appears/works on screen**, then stops. We test it ourselves and log bugs as we go. It does NOT ask us questions mid-build — it follows the document and notes any judgement calls.
5. **`/fixbugs`** → at the end, reads our logged bug list (`design/bugs.md`) and fixes them in one batch pass.

`CLAUDE.md` (in each game folder) holds standing code/build standards and is read automatically on every task.

Per-game folder layout: `Projects/<GameName>/` containing `CLAUDE.md`, `design/` (game-document.md, build-log.md, bugs.md), and `prompts/`.

## Toolchain & setup facts

- **Claude Code on a Max subscription**, not the API. We deliberately avoid per-token API billing. The one thing that silently switches Claude Code to per-token billing is an `ANTHROPIC_API_KEY` set in the environment — it must NOT be set; we stay logged in on the subscription and decline any "API credits" prompt.
- **Roblox Studio MCP** gives Claude Code direct control of Studio: build scripts/instances, generate meshes/terrain/materials, insert Creator Store assets, run playtests, and — critically — **screenshot the running game** to verify visually.
- **`prepare.py`** is our one-command per-game setup: it scaffolds the folders, installs the commands + definitions globally, writes `CLAUDE.md`, and runs safety checks. New team members run it per game; the only one-time-per-machine steps are installing Claude Code, logging in on the subscription, and connecting the Studio MCP.
- Each person uses their **own** subscription (no account sharing or multi-account limit-evasion — that risks bans). Below ~5 people we use individual plans (Pro for light/design users, Max for heavy builders); at ~5+ we'd move to a Team plan with mixed seats.
- Model/effort: we use Opus for heavy reasoning steps (`/doc`, `/prompts`) and lighter settings/Sonnet for routine `/next` passes to conserve usage.

## Non-negotiable design & code standards

Respect these in any advice you give us. They are hard rules, not preferences.

- **ONE core loop**, fun within 60 seconds. Depth comes from deepening that loop, never from piling on features. A thin-feeling game is a weak-loop problem, not a too-few-features problem.
- **Retention-focused.** Roblox's discovery algorithm ranks on long-term retention across Day 1 / Days 2-7 / Days 8-28 (organic players). Design for all three windows and a fast first-session hook.
- **Mobile-first.** Most players are on phones: responsive UI, touch controls.
- **A real 3D environment and game feel** — never an empty baseplate with UI on top. The environment is a first-class, early build phase.
- **Server-authoritative** code (never trust the client), **ProfileStore** session-locked persistence, modular ModuleScripts with a ServerBootstrap, validated + rate-limited remotes, no magic numbers (Config modules).
- **Monetization compliance (HARD):** NO paid random items — nothing random obtainable with Robux or any Robux-bought currency (no loot boxes, gacha, egg-hatching, wheels). Randomness is earned-only. Sell deterministic cosmetics, passes, and non-pay-to-win convenience. Every Robux purchase is deterministic; ProcessReceipt is idempotent.
- **No background music** (sound effects are fine).
- **Professional, original UI** — never a default Roblox template or a generic AI-looking layout.
- **Realistic scope:** v1 must be buildable and polished by a 2-person team in ~4-5 days.

## Reusable definitions

Common cross-game systems are written once in `~/.claude/definitions/` and pulled in by name with `/use`. Currently defined: **pets**. The pets spec: pets follow the player (social flex / FOMO), give stacking multipliers/bonuses, server-authoritative and persisted; monetized via a foot-in-the-door ladder — a bland Beginner Pet on earned currency so everyone gets one, pets #2-4 cheap (~50-60 Robux), then a price jump at pet #5 and normal scaling after; deterministic purchases only (no Robux egg-hatching). The point of definitions is "define once, offer everywhere, force nowhere."

## Hard-won lessons (do NOT re-suggest these)

- **Don't generate all build prompts blind/thin up front and run them without checking.** That produced a game that was all systems and menus with no environment ("empty void with floating objects"). The fix was: a complete Game Document first, a dedicated environment phase, and screenshot-based self-verification on every step. Keep those.
- **"Polished UI" is not "finished game."** A finished game needs the environment, game feel, audio, FTUE, and mobile — UI is one slice.
- **Never skip the environment phase or the visual/screenshot verification.**
- **Don't pile on features to fix a "bland" game** — fix the core loop.
- **Don't suggest account-sharing, multi-accounting to multiply usage, or routing subscription OAuth tokens through third-party tools** — ban risk, and the economics don't even favor it.
- **Don't suggest API/per-token for our interactive building** — subscription is far cheaper for this workload.
- The Game Document's completeness determines build quality. If a build comes out vague, the fix is to improve the document and regenerate prompts — not to answer questions mid-build.

## How to help us

When we ask for help, good advice: respects the hard rules above; favors cutting scope over adding it; grounds recommendations in current, verifiable facts (search if it's time-sensitive — Roblox policy, plan prices, model/tool versions all change); and is honest about tradeoffs and risks (including monetization-of-minors and dark-pattern risk) rather than just agreeing. We value direct, constructive pushback over flattery.
