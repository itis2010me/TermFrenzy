# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Game

```bash
source venv/bin/activate   # required each terminal session
python src/game.py          # normal game mode
python src/game.py --aqua   # aquarium mode (no player)
```

The venv uses Python 3.12 and has `blessed` installed as the only dependency.

## Architecture

This is a terminal game (`src/game.py` + `src/fish_sprites.py`) inspired by PopCap's Feeding Frenzy, built with the [blessed](https://github.com/jquast/blessed) library.

### Game Loop Structure

The game accepts `--aqua` for aquarium mode (no player, no mouse tracking). The `main(aqua_mode)` function runs a loop with these phases per frame:
1. **Input** — raw bytes read from stdin via `select`/`os.read` (not `term.inkey`) to support SGR mouse tracking alongside keyboard input. In aqua mode, mouse tracking is disabled and only `q` is checked.
2. **Update** — player movement (toward mouse cursor, skipped in aqua mode), bubble physics, NPC fish movement, eating collision detection, auto-growth, score popup updates
3. **Draw** — build a single output string with `term.move_xy()` positioning, then flush once. In aqua mode, all NPC fish are drawn without layer splitting since there is no player.

### Timing Model

All animations (bubbles, NPC fish) use **wall-clock time** (`time.monotonic()`) rather than frame ticks, because mouse tracking events cause variable frame rates. Each entity stores its own timestamps for next movement.

### Key Design Decisions

- **Mouse input**: SGR mouse tracking (`\033[?1003h\033[?1006h`) is enabled/disabled manually via escape sequences. Mouse sequences are parsed with regex, then stripped from raw input to isolate keyboard presses.
- **Player fish sprites**: Multi-row ASCII art stored in `PLAYER_SIZES` dict in `fish_sprites.py`, keyed by size (`small`/`medium`/`big`) and direction (`left`/`right`). The `right` sprite has the head (eye `o`) on the right side.
- **NPC fish**: 1-row sprites from `NPC_SPRITES` in `fish_sprites.py` that spawn off-screen and swim across. Each has a `layer` (`back`/`front`) determining draw order relative to the player and a `level` (0=small, 1=medium) from `NPC_LEVELS`. Non-skittish fish use `start_x + speed * elapsed`; skittish fish (the 2 smallest, ≤3 chars) use incremental updates and flee from the player within a radius.
- **Eating**: Player eats NPC fish on AABB collision if `f['level'] in CAN_EAT[size]`. Eaten fish are removed, points added to `score`, and a score popup is created. Player auto-grows at score thresholds defined in `GROWTH_THRESHOLDS`.
- **Bubbles**: Dict-based entities with individual `rise_iv`/`wobble_iv` intervals. They grow through visual stages (`.` -> `o` -> `O`) based on age in seconds. Multi-stage pop animation (`*` -> droplet ring -> fade) triggers when reaching the top border or when a fish (player or NPC) touches them (50% chance).
- **Sea floor**: Decorations (sand, seaweed, rocks) are generated once at startup and redrawn each frame. Seaweed sways using `math.sin()` with wall-clock time. Seaweed has two styles (`()` and `{}`). Both seaweed and rocks have a `layer` (`back`/`front`) for depth relative to the player.

### Variable Naming Conventions

- `px`/`py` — player position
- `draw_x`/`draw_y` — clamped player draw position (computed before bubble updates for collision)
- `fish_w`/`fish_h` — player sprite dimensions
- `player_sprite` — current player sprite rows (use this name, NOT `sprite`, to avoid shadowing in NPC draw loops)
- `now` — `time.monotonic()` snapshot for the current frame
- `plain` — keyboard input after stripping all escape sequences
- `layer` — `'back'` or `'front'` on NPC fish, seaweed, and rocks for depth ordering
- `score` — player's current point total
- `score_popups` — list of floating "+N" text entities with position and birth time
- `level` — NPC fish level (0 or 1), determines edibility and point value
