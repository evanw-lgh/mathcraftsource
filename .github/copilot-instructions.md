# Mathcraft project guidance

- Keep gameplay systems split by responsibility: world, player, blocks, maths, quests, settings, textures, and UI.
- Use the texture manifest in `textures.py` as the only block-art lookup surface.
- Preserve the maths gate: mining and placing cost one token, and successful answers award by difficulty.
- Prefer small deterministic helpers that can be tested without opening the Ursina window.
