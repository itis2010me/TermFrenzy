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

This is a terminal game inspired by PopCap's Feeding Frenzy, built with the [blessed](https://github.com/jquast/blessed) library.

### File Structure

```
src/
  game.py          — game loop orchestrator (input → update → draw)
  config.py        — all constants and tuning values
  entities.py      — Player, NPCFish, Bubble, ScorePopup classes
  sea_floor.py     — SeaFloor class (generation + rendering)
  fish_sprites.py  — sprite art data (PLAYER_SIZES, NPC_SPRITES only)
```

### Game Loop Structure

The game accepts `--aqua` for aquarium mode (no player, no mouse tracking). The `main(aqua_mode)` function in `game.py` runs a loop with these phases per frame:
1. **Input** — raw bytes read from stdin via `select`/`os.read` (not `term.inkey`) to support SGR mouse tracking alongside keyboard input. In aqua mode, mouse tracking is disabled and only `q` is checked.
2. **Update** — `player.update()`, bubble spawn/update, NPC spawn/update/eat, `player.check_growth()`, popup update
3. **Draw** — border → title → sea_floor(back) → bubbles → npc(back) → player → npc(front) → popups → sea_floor(front). All `draw()` methods return string fragments with `term.move_xy()` for single-flush compositing.

### Timing Model

All animations (bubbles, NPC fish) use **wall-clock time** (`time.monotonic()`) rather than frame ticks, because mouse tracking events cause variable frame rates. Each entity stores its own timestamps for next movement.

### Entity Classes (entities.py)

- **Player** — state: `px`, `py`, `facing_right`, `size`, `score`, `draw_x`, `draw_y`, `fish_w`, `fish_h`, `sprite`. Methods: `update()`, `check_growth()`, `draw()`.
- **NPCFish** — classmethod `spawn()` factory. Methods: `update()` (movement/bob/flee, returns False if off-screen), `check_eat_collision()` (returns points or None), `draw()`.
- **Bubble** — classmethod `maybe_spawn()` factory. Methods: `update()` (physics + collision, returns False if expired), `draw()` (with pop animation stages).
- **ScorePopup** — Methods: `update()` (drift up, returns False if expired), `draw()` (with fade).

### Key Design Decisions

- **Mouse input**: SGR mouse tracking (`\033[?1003h\033[?1006h`) is enabled/disabled manually via escape sequences. Mouse sequences are parsed with regex, then stripped from raw input to isolate keyboard presses.
- **Player fish sprites**: Multi-row ASCII art stored in `PLAYER_SIZES` dict in `fish_sprites.py`, keyed by size (`small`/`medium`/`big`) and direction (`left`/`right`). The `right` sprite has the head (eye `o`) on the right side.
- **NPC fish**: 1-row sprites from `NPC_SPRITES` in `fish_sprites.py` that spawn off-screen and swim across. Each has a `layer` (`back`/`front`) determining draw order relative to the player and a `level` (0=small, 1=medium) from `NPC_LEVELS` in `config.py`. Non-skittish fish use `start_x + speed * elapsed`; skittish fish (the 2 smallest, ≤3 chars) use incremental updates and flee from the player within a radius.
- **Eating**: Player eats NPC fish on AABB collision if `f.level in CAN_EAT[player.size]`. Eaten fish are removed, points added to `player.score`, and a ScorePopup is created. Player auto-grows at score thresholds defined in `GROWTH_THRESHOLDS`.
- **Bubbles**: Bubble objects with individual `rise_iv`/`wobble_iv` intervals. They grow through visual stages (`.` -> `o` -> `O`) based on age in seconds. Multi-stage pop animation (`*` -> droplet ring -> fade) triggers when reaching the top border or when a fish (player or NPC) touches them (50% chance).
- **Sea floor**: `SeaFloor` class generates decorations (sand, seaweed, rocks) once at startup. `draw(term, now, layer)` renders for a given layer. Seaweed sways using `math.sin()` with wall-clock time. Both seaweed and rocks have a `layer` for depth relative to the player.
- **Aqua mode**: `player is None` guards all player-dependent paths. `aqua_mode` bool passed to `NPCFish.update()` to disable skittish flee behavior.

### Config (config.py)

All magic numbers and tuning constants are centralized in `config.py`: timing intervals, spawn limits, speed ranges, growth thresholds, eat rules, popup timing, sea floor generation params, and mouse escape sequences.
