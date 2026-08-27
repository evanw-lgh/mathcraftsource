# Mathcraft: Field Journal

Mathcraft is a modular 3D adventure/RPG built in Python with Ursina. The game
turns every physical action into a small learning loop: mining and placing
blocks spend one token, while correct maths answers replenish the wallet.

## Project map

The root modules are intentionally independent and readable:

- `main.py` starts the application.
- `config.py` owns world constants and paths.
- `blocks.py` defines the block catalogue and metadata.
- `world.py` generates terrain, trees, pools, and animated water.
- `player.py` handles movement, mining, placement, and stair orientation.
- `math_system.py` generates difficulty-scaled questions and tracks accuracy.
- `quests.py` contains the starter RPG quest journal.
- `settings_manager.py` persists sound, FOV, VSync, and difficulty.
- `textures.py` resolves the editable texture manifest and fallback.
- `ui.py` builds menus, settings, HUD, pause, and question panels.

## Install and run

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Controls

WASD moves, mouse looks, Space jumps, and Left Shift sprints. Left mouse mines
and right mouse places. Mouse wheel or 1-7 changes the selected block. Q opens
a maths challenge and Esc opens the pause menu.

## Difficulty rules

Easy uses operations with values from 1-10 and awards 1 token. Medium uses
values from 1-100 and awards 5 tokens. Hard adds powers and square roots up to
1000 and awards 10 tokens.

## Custom content

Place PNG files under `assets/textures/` and update the `BLOCK_TEXTURES` tuple
manifest in `textures.py`. Each entry is ordered as top, north, south, east,
west, and bottom. Missing files safely resolve to Ursina's white-cube fallback,
so the game remains playable while a texture pack is being built.
