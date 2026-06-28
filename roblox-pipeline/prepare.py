#!/usr/bin/env python3
"""
prepare.py - One-command setup for a new Roblox game project.

WHAT IT DOES
  1. Checks the GitHub repo for a newer prepare.py and self-updates (once configured)
  2. Installs the Claude Code commands globally (~/.claude/commands):
     /doc, /prompts, /next, /fixbugs, /define
  3. Installs reusable definitions (~/.claude/definitions/) and the shared asset
     libraries (~/.claude/sound-library.json, ~/.claude/models-library.json)
  4. Scaffolds the per-game folders (design/, prompts/) + CLAUDE.md + asset-requests.md
  5. Runs safety checks: Node, Claude Code, the per-token billing trap
     (ANTHROPIC_API_KEY), and whether a Roblox Studio MCP is connected

SETUP
  Edit GITHUB_USER and GITHUB_REPO near the top once to turn on auto-update.

USAGE
  Put this file in your "Projects" folder, then either:

    # A) create AND set up a new game folder in one go (recommended):
    python prepare.py "Grow A Trophy"

    # B) or, from inside an existing game folder:
    python prepare.py

Re-running is safe. It refreshes the global commands but never overwrites
your CLAUDE.md edits or your design documents.
"""

import os
import sys
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path

# ----------------------------------------------------------------------------
# Auto-update: each run checks the repo for a newer prepare.py and the latest
# shared asset libraries. EDIT THESE TWO LINES once with your GitHub details.
# Until you do, auto-update stays off and the script runs from its local copy.
# ----------------------------------------------------------------------------
VERSION = 2  # bump this every time you push a new prepare.py to the repo
GITHUB_USER = "FaresFilms"
GITHUB_REPO = "https://github.com/FaresFilms/roblox-pipeline"
GITHUB_BRANCH = "main"
RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}"
CONFIGURED = "<YOUR_" not in RAW_BASE  # True once you've set USER/REPO above

# ----------------------------------------------------------------------------
# Embedded content: the code standards + the detailed builder commands.
# These are the real, detailed prompts - not generic "make a game" filler.
# ----------------------------------------------------------------------------


CLAUDE_MD = """# Studio Code & Build Standards

These standards apply to every build task in this project. Follow them without being reminded.

## Studio rules (always apply)
- Never add background music. Sound effects (UI, actions, feedback, ambience) are fine; looping/background music is not.

## Before you build (every task)
- INSPECT the live project first: read the DataModel / instance tree and existing scripts via the Studio MCP so you build on what exists. Never assume; look.
- Identify where the new work plugs into existing services and the bootstrap. Do not create orphan systems.

## Architecture
- Server-authoritative. The client sends intents only; the server validates and computes every outcome (currency, progression, rolls, values). Never trust a client-supplied number.
- Modular ModuleScripts, one responsibility each. A single ServerBootstrap requires and initializes services in dependency order. Every new service MUST be registered there.
- No magic numbers in logic; all tunables live in Config ModuleScripts in ReplicatedStorage/Shared.

## Persistence
- ProfileStore, session-locked (StartSessionAsync / EndSession on leave). One versioned profile template with a dataVersion field and a migration path. Per-player data only; global/ranked data uses OrderedDataStore.
- Save on interval and on leave; handle shutdown (BindToClose) and datastore failures with retries.

## Remotes & anti-exploit
- One remote-middleware layer: validate sender, rate-limit per player, and sanity-check every argument (type, range, ownership, cooldown). Assume any client value can be forged. Sanity-check positions and movement where relevant. Reject and log abuse; never throw to the client.
- No client-side authority over currency, items, or stats - ever.

## Monetization compliance (hard)
- No paid random items. No currency that buys randomness is purchasable with Robux, directly or indirectly. No Robux-purchasable luck / odds boosts. Every Robux purchase is deterministic. ProcessReceipt is idempotent.

## Audio & visual assets (NEVER generate - always use existing assets)
- HARD RULE: never GENERATE any audio, texture, material, model, or mesh. Do NOT use AI asset-generation tools (no generate_mesh, no generate_material, no audio generation, no inventing/guessing asset IDs). Every sound, image, texture, and model must be an EXISTING Roblox asset.
- Source order for any asset: (1) our libraries first - sounds from ~/.claude/sound-library.json, models/textures from ~/.claude/models-library.json (pick a fitting category; choose at random when several IDs exist); (2) if nothing fits, search the Roblox Studio Toolbox / Creator Store via the MCP and insert a real, high-rated, free asset; (3) only if BOTH fail, leave a clearly-commented placeholder and log a request (below). Never fall back to generating something.
- SOUNDS specifically: use only rbxassetid:// values that already exist (from our sound library, or Toolbox audio). Never synthesize, hum, or invent audio, and never guess an ID.
- If nothing fitting exists in our libraries OR the Toolbox: leave a clearly-commented TODO placeholder so the build still runs, and APPEND a request to design/asset-requests.md (type, what's needed, where it's used, how many variants, what placeholder you left). Do NOT stop to ask in chat, and do NOT generate a substitute.
- Never add background music. Ambience and SFX only.

## World, UI & platform
- This is a 3D experience. Work happens inside a real, intentional environment, not an empty baseplate. Shape the space with terrain sculpting and lighting/atmosphere, and DRESS it by inserting existing Toolbox / Creator Store models and our library assets - never by generating meshes or materials. Integrate team-supplied models when provided.
- Mobile-first: most players are on phones. UI must be responsive with usable tap targets; controls must work on touch. Test both.
- UI is professional and original - never a default Roblox template or a generic AI layout.

## Verify before you report done (every task)
- Run a playtest via the MCP, then use screen_capture to LOOK at the result. Confirm visually that what you built actually appears and works in the running game - not just that the code compiles.
- Check the acceptance criteria one by one. Confirm no earlier system regressed. Report what you verified and describe the screenshot evidence.

## Code quality
- Luau types where practical, defensive error handling, clear naming. Each pass must not silently rebuild or break earlier systems. No placeholder logic or TODO stubs in shipped systems.
"""

DOC_MD = """---
description: Turn a 1-2 sentence idea into a complete, decision-complete Game Document
argument-hint: [1-2 sentence game idea]
disable-model-invocation: true
---
You are a senior Roblox game designer and Luau architect in a small studio that ships polished, retention-focused games. Turn the idea below into a COMPLETE Game Document that is the single source of truth for the entire build. Every design decision must be MADE here - later build steps must never have to ask a question.

Be specific and concrete. Never produce generic "make a fun game" filler. Every section must contain real, game-specific decisions, mechanics, and numbers. If you catch yourself writing something that would be true of any game, replace it with a concrete choice for THIS game.

Standards this game is held to:
- ONE core loop that is genuinely fun and easy to understand within the first 60 seconds, and strong enough to build a whole game on. Depth comes from deepening that loop, not from unrelated features.
- Multiple, clearly designed retention hooks mapped to Day 1, Days 2-7, and Days 8-28 (Roblox's algorithm ranks on long-term retention across those windows and counts only organically-acquired players).
- Realistic scope: buildable and polished by a 2-person team in ~4-5 days with Claude Code + the Roblox Studio MCP. Cut anything that doesn't serve the loop or first session into a "Deferred" list.
- A real 3D environment and strong game feel - never an empty baseplate with UI on top.
- Mobile-first (most players are on phones).
- Monetization that is compliant and non-exploitative: NO paid random items (nothing random obtainable with Robux, or with any currency that can be bought with Robux); any randomness is earned through gameplay only; sell deterministic cosmetics, passes, and non-pay-to-win convenience. No real gambling.
- Professional, original UI that does not look like a default Roblox template or an AI-generated layout.
- Production-grade, server-authoritative code with ProfileStore persistence.

DECIDE, don't defer. Wherever there's a choice (mechanics, counts, ownership models, economy tuning, monetization), pick the best option and state it with a one-line rationale. No open questions, no TBDs anywhere in the document.

Write the document with these sections, concrete and specific (aim ~250-400 lines, real numbers throughout):

1. Pitch & core fantasy - one or two sentences.
2. Target audience & positioning - who it's for, why (age skew, genre fans), and the retention/monetization implications of that choice; confirm mobile-first. Roblox pays a higher revenue share on adult spend and the algorithm rewards long retention, so consider whether to aim older - and design to the choice you make.
3. Core loop - the single loop as the exact steps and the time per cycle. This is the spine of the game.
4. First-session / FTUE flow - minute by minute for the first ~5 minutes: what the player does, sees, and is rewarded with, and why they return tomorrow.
5. Retention architecture - what specifically brings players back, mapped to Day 1 (the first-session hook and first reward, delivered fast), Days 2-7 (a daily reason to return plus short-session re-engagement, including a reason to come back for a second, shorter session within 24-72 hours), and Days 8-28 (progression depth, social, events). These are the windows Roblox's algorithm scores separately.
6. World & art direction - the actual space players move through: layout, setting, mood, color and lighting direction, and the specific areas/models/props needed. Note which to MCP-generate or auto-insert from the Creator Store now vs which to swap for sourced assets later.
7. Audio direction - music mood and every sound effect the loop needs.
8. Full systems spec - every system in v1, each described concretely enough to build from: inputs, outputs, rules, edge cases.
9. Economy & progression - ALL the numbers: costs, rewards, timings, rarity weights/odds, sell values, and progression pacing across a session and across days.
10. Monetization - the exact deterministic products, game passes, and cosmetics with prices in Robux. Explicitly confirm there are no paid random items.
11. Data schema - the full ProfileStore profile template (every persisted field) with a version field and migration note.
12. Server-authority & anti-exploit - the specific protections this game needs (what the server owns, what to validate, where dupes/exploits could occur).
13. Phased build plan - the game broken into build phases in dependency order. This is the build order, not a maybe-list; every phase will be built. Phase 1 is the playable core-loop foundation (functional, minimal art and UI) we can play to confirm the loop is fun; build a real blockout environment early so the loop is never tested in a void; later phases add systems, content, polished UI, game feel, audio, and mobile, then hardening and optimization. Keep Phase 1 genuinely minimal.
14. Analytics events - the exact events and payloads to fire (onboarding funnel, core-loop completion, economy, monetization, retention).
15. Decisions log - the key choices you made and the reasoning, especially anything a builder might otherwise stop to ask about.
16. Deferred (post-launch) - what is intentionally out of v1.

Keep the document decision-ready and favor cutting scope over adding it. If the idea is too thin to support a loop that retains, say so and propose the smallest change that fixes it.

The game idea:
$ARGUMENTS

Write the result to design/game-document.md, then STOP. Tell me to review and edit the document until it is final - this is the only place we do design review. Do not generate build prompts or build anything yet.
"""

PROMPTS_MD = """---
description: Generate the full set of detailed build prompts from the finalized Game Document
disable-model-invocation: true
---
Read design/game-document.md (our finalized, reviewed Game Document - the single source of truth) and CLAUDE.md. Produce the COMPLETE set of build prompts that take this game from nothing to a polished v1, each as its own file in prompts/. These are executed one at a time with /next, so they must be FULL and self-contained - complete specs, not summaries or single paragraphs.

First write prompts/00-index.md: the ordered list of every build prompt with a one-line scope each. Cover EVERY aspect or mark it out-of-scope with a reason: architecture & ServerBootstrap; config/content tables; ProfileStore persistence; server-authoritative core loop; offline/timed logic; the ENVIRONMENT/world (blockout early, art pass later); lighting/atmosphere; models/props; progression; economy; functional UI; full polished UI; monetization (deterministic); FTUE; game feel (VFX/animation/camera/juice); audio; mobile/responsive + settings; analytics; anti-exploit hardening; performance; loading/first-spawn; discovery assets (icon/thumbnails); final self-QA.

Order by dependency, de-risk early, and follow the Phased build plan in the Game Document. Build Prompt 1 is the Phase 1 foundation: the playable core loop, server-authoritative, with data persistence and functional (unpolished) placeholders - the version we play to confirm the loop is fun. Build a blockout environment early and wire the loop into it so it is never tested in a void. After the foundation, each later prompt adds ONE focused slice in this kind of order: a single system, then a content batch, then a functional UI, then a polished UI pass, then monetization, then FTUE, then game feel, then audio, then mobile/responsive + settings, then analytics instrumentation, then a final optimization + anti-exploit hardening pass at the end.

Then write one file per build prompt: prompts/01-<slug>.md, prompts/02-<slug>.md, ... Generate them one at a time, in order, re-reading the Game Document for the exact specs/numbers each needs. Each prompt file must contain:
- TITLE + step number.
- WHAT ALREADY EXISTS (from prior prompts) and WHAT THIS PROMPT BUILDS - in full detail, with the specific numbers/specs/models pulled from the Game Document. Do not make the builder re-derive anything.
- EXACTLY where it plugs into the existing structure (services / ServerBootstrap / config / remotes / data) and WHAT NOT TO TOUCH OR REBUILD.
- For environment/visual steps: shape the space with terrain and lighting, and DRESS it by inserting existing Toolbox / Creator Store assets and our library assets - never generate meshes or materials. Leave a clearly-marked OPTIONAL note for swapping in team-sourced assets later - never block on sourcing.
- For steps needing the Roblox dashboard (dev products, icon upload): build everything codeable and leave a short, NON-BLOCKING team note for the dashboard action.
- All CLAUDE.md standards.
- ACCEPTANCE CRITERIA as a concrete checklist - a definition of done we can verify in Studio (what should work, what the player should see and do) - INCLUDING self-verification: run a playtest, screen_capture the result (and a mobile viewport for UI), confirm it actually appears/works on screen, confirm no earlier system regressed, and fix before reporting done. This is the builder checking its own work, NOT asking the user.

Favor completeness over brevity - each prompt should capture every detail needed to build that slice without further input. When all files are written, finalize prompts/00-index.md and STOP, listing the files you created.
"""

NEXT_MD = """---
description: Build the next game prompt, one at a time, with no questions
disable-model-invocation: true
---
We build by executing the files in prompts/ one at a time, in order.

1. Read prompts/00-index.md and prompts/progress.md (create it if missing) to find the next not-yet-done prompt. Tell me which one you're running.
2. Read that prompt file, CLAUDE.md, and design/game-document.md. INSPECT the live project via the Studio MCP so you build on what exists.
3. Execute the prompt EXACTLY as written. It is a complete spec - do NOT ask me clarifying questions. If you hit an ambiguity, choose the option most consistent with the Game Document, proceed, and note the choice in design/build-log.md. Only stop to ask if there is a hard technical blocker you cannot work around (MCP disconnected, or a required prior step is missing).
4. Self-verify before finishing: run a playtest, screen_capture the result (plus a mobile viewport if it's UI/controls), confirm against the prompt's acceptance criteria that it works on screen, and confirm the core loop and prior systems didn't regress. Fix anything broken, then re-verify.
5. ASSETS: when this step needs a sound, model, or texture, follow the asset rules in CLAUDE.md - pull from the libraries (~/.claude/sound-library.json, ~/.claude/models-library.json); if nothing fits, search the Creator Store via the MCP; only if that fails, leave a clear placeholder and append a request to design/asset-requests.md. Never invent sounds or guess asset IDs.
6. Mark the prompt done in prompts/progress.md, give me a 2-3 line summary + the screenshot evidence, and STOP. Do not auto-continue to the next prompt.

I will test it myself and log bugs separately; we fix those at the end with /fixbugs. Your job here is to build the step and confirm it visibly works - not to interview me.
"""

FIXBUGS_MD = """---
description: Fix a batch of logged bugs after the build is complete
disable-model-invocation: true
---
Read design/bugs.md (the bug list - I've pasted my bugs there), CLAUDE.md, and design/game-document.md.

For each bug, in order:
1. Understand/reproduce it by inspecting the live project + scripts via the Studio MCP. Identify the root cause.
2. Fix it with the smallest change that resolves it - do NOT refactor working systems or change designed behavior; match the Game Document.
3. Self-verify: playtest, screen_capture, confirm the bug is gone and nothing else regressed.
4. Mark it fixed in design/bugs.md with a one-line note on what changed.

Work through every bug. If an item is actually a design change rather than a defect, flag it separately instead of guessing. When done, summarize what was fixed and anything you couldn't reproduce. Don't ask me questions mid-pass unless a fix would change designed behavior.
"""

DEFINE_MD = """---
description: Pull a reusable system definition into the current game's design
argument-hint: [definition name, e.g. pets]
disable-model-invocation: true
---
Read the canonical definition file at ~/.claude/definitions/$ARGUMENTS.md - our write-once spec for this system. If it doesn't exist, list the files in ~/.claude/definitions/ and stop.

If design/game-document.md does not exist yet, tell me to run /doc first, then stop.

Otherwise, integrate the definition into design/game-document.md as a fully specified part of THIS game:
- Adapt its numbers, currency names, and theming to fit this game's economy and setting.
- Keep its rules intact, especially the monetization-compliance rules (no paid random items; deterministic purchases only).
- Place it in the right sections (systems spec, economy, monetization, data schema) rather than dumping it in one block.
- Record in the Decisions log that this system was added from the '$ARGUMENTS' definition.

Then STOP for my review. Do not generate build prompts or build anything.
"""

PETS_MD = """# Definition: Pets

The canonical spec for pets. When a game includes pets, adapt the numbers, currency names, and theming to that game - but keep the rules, especially the monetization-compliance rules, intact.

## What pets are
- Collectable companions that follow the player around the world and are visible to other players. That visibility is the point: pets are a social flex and a source of FOMO, and they signal progression to everyone nearby.
- Pets grant gameplay bonuses - multipliers and/or stat boosts to the game's core resource (e.g. more coins/cash/score per action). Higher-tier pets give bigger bonuses.
- Pets accelerate the core loop; they do not replace it. Non-paying players must still have a real path through the game.

## Ownership, equipping & bonuses (server-authoritative)
- The server owns pet ownership and equipped state and computes all bonuses. The client only displays pets and sends equip/unequip intents. Never trust a client-supplied pet, tier, or bonus value.
- Define a max number of equipped pets (default: 3) in Config. Equipped pets' bonuses stack (pick additive or multiplicative for the game and state it).
- Pets and bonuses persist in the ProfileStore profile (owned list + equipped list) and are re-applied on join from saved data.
- All pet data (id, displayName, tier, bonus, cost, currency, model/skin) lives in a data-driven PetConfig - no pet stats hardcoded in services.

## Monetization ladder (follow this shape; adapt the exact numbers per game)
Pets use a deliberate foot-in-the-door ladder:

1. The Beginner Pet (pet #1): bought with the game's EARNED, non-premium currency, priced so any active player can afford it within their first session or two. It is intentionally BLAND - plain looks, small bonus. Its job is to get everyone holding a pet, so they see the bonus and the empty upgrade slots and feel the urge to upgrade. Everyone can get a pet; that is the hook.

2. Pets #2-#4 (foot-in-the-door): these ARE premium (Robux), but very cheap - roughly 50-60 Robux each. They are a clear, satisfying jump in looks and bonus over the beginner pet, so the first small purchase feels worth it. The goal is the first Robux purchase, not profit.

3. Pet #5 and beyond (where the revenue is): a deliberate PRICE JUMP at pet #5 (e.g. from ~60 Robux up to a few hundred), then prices scale up normally from there as bonuses grow. Each higher pet is a bigger deterministic upgrade.

Example starting numbers (adapt to the game's economy):
- Beginner Pet: ~500 earned coins, +5% core-resource bonus, plain model.
- Pets #2-#4: 59 / 59 / 79 Robux; +15% / +25% / +40% bonus; clearly nicer models.
- Pet #5: ~199 Robux (the jump), then scale upward (e.g. ~+50% price per tier) with steadily larger bonuses.

## Monetization compliance (hard - never break these)
- Pets are sold DETERMINISTICALLY: the player always sees and chooses the exact pet they are buying before paying.
- NO random pet hatching, eggs, crates, or gacha for Robux (directly, or via any currency that can be bought with Robux). Random pet hatching for Robux is a paid random item - legally restricted and not allowed here. If a game wants a hatch feel, the egg must be bought with EARNED currency only, or the outcome must be non-random.
- No Robux-purchasable luck/odds boosts tied to pets. All Robux pet purchases go through an idempotent ProcessReceipt.

## Analytics
- Fire: beginner_pet_acquired, first_premium_pet_purchased (the key conversion event), pet_purchased (with pet id + price), pet_equipped. Watch the beginner -> first-premium conversion rate; it is the point of the ladder.
"""

SOUND_LIBRARY_STARTER = """{
  "_comment": "Sound library: Roblox asset IDs grouped by category. Claude reads this when a game needs a sound and picks at random from a fitting category. Humans add IDs after uploading audio to Roblox (Creator Dashboard -> Audio). Audio must be uploaded and moderation-approved before it will play. This file is the shared source of truth - edit it in the repo so everyone gets updates.",
  "_usage": "Reference as rbxassetid://<id> on a Sound instance. Never use a local file path or cloud URL - Roblox only plays uploaded, approved audio.",
  "categories": {
    "ui_click": { "description": "Button presses, menu taps, toggles.", "ids": [] },
    "ui_purchase_success": { "description": "Successful buy / reward claim.", "ids": [] },
    "ui_error": { "description": "Invalid action, can't afford, denied.", "ids": [] },
    "coin_pickup": { "description": "Collecting currency / small reward pops.", "ids": [] },
    "reward_small": { "description": "Common reward / minor success.", "ids": [] },
    "reward_big": { "description": "Rare reward / jackpot / big celebration.", "ids": [] },
    "level_up": { "description": "Progression milestone, upgrade unlocked.", "ids": [] },
    "impact_soft": { "description": "Light hits, taps, soft landings.", "ids": [] },
    "impact_hard": { "description": "Heavy hits, big landings, breaks.", "ids": [] },
    "whoosh": { "description": "Movement, transitions, swipes, dashes.", "ids": [] },
    "ambient_loop": { "description": "Looping environmental ambience (SFX, not music).", "ids": [] },
    "footstep": { "description": "Player/character movement steps.", "ids": [] }
  }
}
"""

MODELS_LIBRARY_STARTER = """{
  "_comment": "Model & texture library: trusted Roblox asset IDs grouped by category. Claude prefers these over generating geometry. Each entry: id (number), name, source ('uploaded' or 'creator-store'). If nothing here fits, Claude searches the Creator Store via the MCP for a high-rated free asset; if that also fails it logs a request to the game's design/asset-requests.md. Shared source of truth - edit in the repo.",
  "_usage": "Insert by asset id (rbxassetid:// / InsertService / MCP insert). Verify the asset is free/owned and appropriate before use.",
  "categories": {
    "prop_small": { "description": "Small set-dressing props (crates, plants, signs).", "assets": [] },
    "prop_large": { "description": "Large props / structures (buildings, vehicles).", "assets": [] },
    "character_pet": { "description": "Pet / companion models.", "assets": [] },
    "character_npc": { "description": "NPC / character models.", "assets": [] },
    "environment_ground": { "description": "Terrain pieces, floors, paths, platforms.", "assets": [] },
    "environment_nature": { "description": "Trees, rocks, foliage, water features.", "assets": [] },
    "texture_material": { "description": "Surface textures / decals / material variants.", "assets": [] },
    "fx_particle": { "description": "Particle / VFX assets for game feel.", "assets": [] }
  }
}
"""

ASSET_REQUESTS_SEED = """# Asset requests

Claude appends here during /next when it needs a sound, model, or texture the libraries don't have. Fulfil in batch: source/create the asset, upload to Roblox (or find a Creator Store ID), add the ID to the right library (~/.claude/sound-library.json or ~/.claude/models-library.json), then run a swap pass so placeholders become real IDs.

Format per request:
---
- TYPE: sound | model | texture
- CATEGORY/NEED: e.g. "reward_big" or "wooden crate model"
- USED IN: which prompt/system and what for
- VARIANTS WANTED: how many (sounds: 3-5 per category for randomisation)
- PLACEHOLDER LEFT: the stand-in currently in the build
- STATUS: open | fulfilled
---

## Requests
"""

COMMANDS = {
    "doc.md": DOC_MD,
    "prompts.md": PROMPTS_MD,
    "next.md": NEXT_MD,
    "fixbugs.md": FIXBUGS_MD,
    "define.md": DEFINE_MD,
}

# Global, reusable system definitions, pulled into a game on demand via /define.
DEFINITIONS = {
    "pets.md": PETS_MD,
}

# Shared asset libraries installed to ~/.claude/. Fetched fresh from the repo each
# run when configured (repo = source of truth); embedded starters are the offline
# / first-run fallback. Key = path in the repo, value = (filename, starter content).
LIBRARY_TARGETS = {
    "sounds/sound-library.json": ("sound-library.json", SOUND_LIBRARY_STARTER),
    "models/models-library.json": ("models-library.json", MODELS_LIBRARY_STARTER),
}

# Per-game seed files (created only if missing, so edits/work are never clobbered)
SEED_FILES = {
    "design/bugs.md": "# Bug log\n\nPaste bugs here (one per line or short blocks), then run /fixbugs.\n",
    "design/build-log.md": "# Build log\n\n/next records any judgement calls it made here.\n",
    "design/asset-requests.md": ASSET_REQUESTS_SEED,
    "prompts/progress.md": "# Build progress\n\n/next marks completed prompts here.\n",
}


def say(tag, msg):
    print(f"  [{tag}] {msg}")


def write_file(path: Path, content: str, overwrite: bool):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        say("SKIP", f"{path} already exists - left untouched")
        return
    path.write_text(content, encoding="utf-8")
    say("OK", str(path))


def install_global_commands():
    print("\nInstalling Claude Code commands (global, shared by every game)...")
    cmd_dir = Path.home() / ".claude" / "commands"
    cmd_dir.mkdir(parents=True, exist_ok=True)
    for name, content in COMMANDS.items():
        write_file(cmd_dir / name, content, overwrite=True)  # always refresh
    say("INFO", f"Location: {cmd_dir}")


def install_global_definitions():
    print("\nInstalling reusable system definitions (global, pulled in via /define)...")
    def_dir = Path.home() / ".claude" / "definitions"
    def_dir.mkdir(parents=True, exist_ok=True)
    for name, content in DEFINITIONS.items():
        write_file(def_dir / name, content, overwrite=True)  # always refresh
    say("INFO", f"Location: {def_dir}")


def install_libraries():
    print("\nInstalling shared asset libraries (sounds + models)...")
    home = Path.home() / ".claude"
    home.mkdir(parents=True, exist_ok=True)
    for repo_path, (fname, starter) in LIBRARY_TARGETS.items():
        dest = home / fname
        remote = fetch_text(RAW_BASE + "/" + repo_path) if CONFIGURED else None
        if remote:
            dest.write_text(remote, encoding="utf-8")
            say("OK", f"{dest} (latest from repo)")
        elif not dest.exists():
            dest.write_text(starter, encoding="utf-8")
            say("OK", f"{dest} (starter - populate it with real asset IDs)")
        else:
            say("SKIP", f"{dest} kept (couldn't fetch latest; using existing)")
    say("INFO", f"Location: {home}")


def fetch_text(url, timeout=5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.read().decode("utf-8")
    except Exception:
        return None


def self_update():
    if "--no-update" in sys.argv:
        return
    if not CONFIGURED:
        say("INFO", "Auto-update off (set GITHUB_USER/GITHUB_REPO near the top of prepare.py).")
        return
    remote = fetch_text(RAW_BASE + "/prepare.py")
    if not remote:
        say("INFO", "Update check skipped (couldn't reach GitHub).")
        return
    m = re.search(r"^VERSION\s*=\s*(\d+)", remote, re.M)
    if not m:
        return
    remote_version = int(m.group(1))
    if remote_version > VERSION:
        say("OK", f"Updating prepare.py: v{VERSION} -> v{remote_version}, relaunching...")
        try:
            Path(__file__).write_text(remote, encoding="utf-8")
        except Exception as e:
            say("WARN", f"Couldn't write update ({e}); continuing on current version.")
            return
        # Relaunch the freshly-downloaded script; --no-update prevents a loop.
        os.execv(sys.executable, [sys.executable, __file__, *sys.argv[1:], "--no-update"])
    else:
        say("OK", f"prepare.py is up to date (v{VERSION}).")


def scaffold_game(game_dir: Path):
    print(f"\nScaffolding game project: {game_dir}")
    game_dir.mkdir(parents=True, exist_ok=True)
    (game_dir / "design").mkdir(exist_ok=True)
    (game_dir / "prompts").mkdir(exist_ok=True)
    write_file(game_dir / "CLAUDE.md", CLAUDE_MD, overwrite=False)
    for rel, content in SEED_FILES.items():
        write_file(game_dir / rel, content, overwrite=False)


def run_checks():
    print("\nRunning environment checks...")

    # Node / npm
    node = shutil.which("node")
    npm = shutil.which("npm")
    if node:
        say("OK", "Node.js found")
    else:
        say("WARN", "Node.js not found - install it from https://nodejs.org (Claude Code needs it)")

    # Claude Code CLI
    claude = shutil.which("claude")
    if claude:
        say("OK", "Claude Code (claude) found")
    elif npm:
        say("ACTION", "Claude Code not found - attempting to install it now...")
        try:
            subprocess.run([npm, "install", "-g", "@anthropic-ai/claude-code"], check=True)
            say("OK", "Claude Code installed")
            claude = shutil.which("claude")
        except Exception:
            say("WARN", "Auto-install failed. Run this yourself:")
            say("    ", "npm install -g @anthropic-ai/claude-code")
    else:
        say("WARN", "Can't install Claude Code (no npm). Install Node first, then:")
        say("    ", "npm install -g @anthropic-ai/claude-code")

    # The per-token billing trap
    if os.environ.get("ANTHROPIC_API_KEY"):
        say("WARN", "ANTHROPIC_API_KEY is set in your environment!")
        say("    ", "This makes Claude Code bill PER TOKEN and ignore your Max subscription.")
        say("    ", "Remove it to stay on your plan:  (PowerShell) Remove-Item Env:\\ANTHROPIC_API_KEY")
        say("    ", "                                 (Mac/Linux)  unset ANTHROPIC_API_KEY")
        say("    ", "Also delete it from your shell profile / system env vars so it doesn't return.")
    else:
        say("OK", "No ANTHROPIC_API_KEY set (good - you'll bill against your subscription)")

    # Roblox Studio MCP connection (best-effort)
    mcp_ok = False
    if claude:
        try:
            out = subprocess.run([claude, "mcp", "list"], capture_output=True, text=True, timeout=20)
            if "roblox" in (out.stdout + out.stderr).lower():
                mcp_ok = True
        except Exception:
            pass
    if mcp_ok:
        say("OK", "A Roblox Studio MCP appears to be registered with Claude Code")
    else:
        say("ACTION", "No Roblox Studio MCP detected - do the one-time MCP setup (see below)")

    return claude is not None, mcp_ok


def print_next_steps(claude_ok, mcp_ok):
    print("\n" + "=" * 70)
    print("  DONE. Per-game setup is complete.")
    print("=" * 70)

    one_time = []
    if not claude_ok:
        one_time.append("Install Claude Code:  npm install -g @anthropic-ai/claude-code")
    one_time.append(
        "Log in on your SUBSCRIPTION (so you are not billed per token):\n"
        "        claude logout\n"
        "        claude login        (sign in with your Pro/Max account; decline any API-credit prompt)"
    )
    if not mcp_ok:
        one_time.append(
            "Connect the Roblox Studio MCP (one time per machine):\n"
            "        Official: download the installer from https://create.roblox.com/docs/studio/mcp\n"
            "        then register it with Claude Code, e.g.\n"
            "          claude mcp add --transport stdio Roblox_Studio -- <path-to-rbx-studio-mcp> --stdio\n"
            "        In Studio, open the Plugins tab and toggle the MCP plugin ON."
        )

    if one_time:
        print("\n  ONE-TIME per machine (only if you haven't already):")
        for i, step in enumerate(one_time, 1):
            print(f"    {i}. {step}")

    print("\n  EVERY game, to start building:")
    print("    1. Open Roblox Studio with your place; toggle the Studio MCP plugin ON.")
    print("    2. From this game folder, run:  claude")
    print("    3. Type / and confirm you see: doc, prompts, next, fixbugs, define")
    print("    4. /doc <your 1-2 sentence game idea>   -> review & edit design/game-document.md")
    print("    5. /define <name>  (optional)           -> e.g. /define pets, on games that want it")
    print("    6. /prompts                             -> generates the full build prompts")
    print("    7. /next   (repeat)                     -> builds one step at a time")
    print("    8. /fixbugs                             -> after pasting bugs into design/bugs.md")
    print()


def main():
    print("=" * 70)
    print("  Roblox game project setup")
    print("=" * 70)

    # Resolve the game folder: arg -> create/use that subfolder; else current dir.
    if len(sys.argv) > 1:
        game_dir = Path.cwd() / sys.argv[1]
    else:
        game_dir = Path.cwd()

    self_update()
    install_global_commands()
    install_global_definitions()
    install_libraries()
    scaffold_game(game_dir)
    claude_ok, mcp_ok = run_checks()
    print_next_steps(claude_ok, mcp_ok)


if __name__ == "__main__":
    main()
