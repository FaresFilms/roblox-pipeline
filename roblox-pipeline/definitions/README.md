# Definitions

Reusable, write-once specs for systems that recur across our games (pets, and more to come). The point is **define once, offer everywhere, force nowhere** — a definition is pulled into a game only when you choose, never auto-added.

## How to use a definition

1. Download the definition file you want (e.g. `pets.md`) from this folder.
2. Put it in your Claude commands folder: `~/.claude/definitions/pets.md`
   (Windows: `C:\Users\<you>\.claude\definitions\pets.md`)
3. In a game, after `/doc` and before `/prompts`, run:  `/define pets`
   It reads the file, adapts the numbers/theme to that game, folds it into `design/game-document.md`, and stops for your review.

> If you set up the game with `prepare.py`, the current definitions are installed automatically — you only download from here to grab one `prepare.py` doesn't include yet, or a newer version.

## Adding a new definition

Create `<name>.md` in this folder. Keep it self-contained and adaptable: describe what the system is, the server-authoritative ownership/persistence rules, the monetization (deterministic — no paid random items), and any analytics events. Then anyone can `/define <name>` it.

## Available definitions

- **pets.md** — collectable companions that follow the player (social flex / FOMO), give stacking multipliers, sold via a foot-in-the-door price ladder. Deterministic purchases only.
