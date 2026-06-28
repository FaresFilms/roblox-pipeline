# Roblox Build Pipeline

Tooling for our Roblox game studio. `prepare.py` sets up a new game project with one command: it installs our Claude Code commands, definitions, and shared asset libraries, scaffolds the game folder, and runs safety checks. It also self-updates from this repo on every run.

## Repo layout

```
prepare.py                     # the one-command setup script (self-updating)
definitions/
  pets.md                      # reusable system spec, pulled into a game with /define pets
  README.md
sounds/
  sound-library.json           # shared sound asset IDs (rbxassetid), by category
models/
  models-library.json          # shared model/texture asset IDs, by category
```

`prepare.py` fetches `sounds/sound-library.json` and `models/models-library.json` from this repo on each run, so editing them here updates everyone.

## First-time setup (per person, once)

1. Install Node.js, then `npm install -g @anthropic-ai/claude-code`.
2. `claude logout` then `claude login` on your Pro/Max account (decline any API-credit prompt — this keeps you off per-token billing).
3. Connect the Roblox Studio MCP.
4. Download `prepare.py` from this repo into your `Projects` folder.

## Using it (per game)

From your `Projects` folder:

```
python prepare.py "My Game Name"
```

Then open Studio + the MCP, run `claude` from the game folder, and: `/doc <idea>` -> review -> `/prompts` -> `/next` (repeat) -> `/fixbugs`.

## Updating the pipeline

- **Commands / prompts / standards** (anything inside `prepare.py`): edit, **bump `VERSION`**, push. Everyone gets it on their next run.
- **Sounds / models**: edit `sounds/sound-library.json` or `models/models-library.json`, push. No version bump needed (fetched fresh every run).
- **New definition**: add it to the `DEFINITIONS` block in `prepare.py` (and drop a copy in `definitions/`), bump `VERSION`, push.

## Security

`prepare.py` runs the latest version from this repo on each teammate's machine. Keep `main` protected (require PR review) and only add trusted collaborators — anyone who can push to `prepare.py` can run code on everyone's machines.
