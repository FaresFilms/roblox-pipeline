# Definition: Pets

The canonical spec for pets. When a game includes pets, adapt the numbers, currency names, and theming to that game - but keep the rules, especially the monetization-compliance rules, intact.

To use: place this file in `~/.claude/definitions/pets.md`, then run `/use pets` in a game (after `/doc`, before `/prompts`).

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
