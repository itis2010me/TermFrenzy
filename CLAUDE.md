# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Game

```bash
source venv/bin/activate   # required each terminal session
python src/game.py          # launches title screen (select Frenzy or Aquarium)
python src/game.py --aqua   # skip title screen, go straight to aquarium mode
```

The venv uses Python 3.12 and has `blessed` installed as the only dependency (see `requirements.txt`).

## Architecture

This is a terminal game inspired by PopCap's Feeding Frenzy, built with the [blessed](https://github.com/jquast/blessed) library.

### File Structure

```
requirements.txt   — Python dependencies
CHANGELOG.md       — version history
src/
  game.py          — game loop orchestrator (input → update → draw)
  config.py        — all constants and tuning values
  entities.py      — Player, NPCFish, Shark, Jellyfish, Bubble, ScorePopup, GoldSparkle classes
  sea_floor.py     — SeaFloor class (generation + rendering)
  fish_sprites.py  — sprite art data (PLAYER_SIZES, NPC_SPRITES, SHARK_SPRITE_RIGHT/LEFT, JELLYFISH_FRAMES)
```

### Title Screen

`title_screen(term, fd)` in `game.py` runs a live aquarium as background with a centered ASCII art logo (`TITLE_ART` in `config.py`) and a selection box. Arrow keys switch between Frenzy and Aquarium mode, Enter selects, `q` quits. Pressing `T` toggles the menu box on/off (hidden feature, useful for screenshots). The terminal context (`fullscreen`, `cbreak`, `hidden_cursor`) is shared between the title screen and the game to avoid screen flash. When Aquarium mode is selected, the aquarium state (sea floor, fish, bubbles, jellyfish) carries over seamlessly.

### Game Loop Structure

The `main(term, fd, aqua_mode, aqua_state)` function runs a loop with these phases per frame:
1. **Input** — `read_input(fd)` reads raw bytes via `select`/`os.read`, `strip_escapes()` isolates keyboard presses. In aqua mode, mouse tracking is disabled and only `q` is checked.
2. **Update** — `player.update()`, bubble spawn/update, NPC spawn/update/eat (incl. gold fish trail), gold fish spawn, shark spawn/update/eat, jellyfish spawn/update/sting-or-eat, `player.check_growth()`, popup update, gold sparkle spawn/update
3. **Draw** — border → title → sea_floor(back) → bubbles → jellyfish → npc(back) → player → npc(front) → sharks → popups → gold sparkles → sea_floor(front). All `draw()` methods return string fragments with `term.move_xy()` for single-flush compositing. Many `draw()` methods accept a `gold_frenzy` param to override colors during Gold Frenzy.

### Timing Model

All animations (bubbles, NPC fish) use **wall-clock time** (`time.monotonic()`) rather than frame ticks, because mouse tracking events cause variable frame rates. Each entity stores its own timestamps for next movement.

### Entity Classes (entities.py)

- **Player** — state: `px`, `py`, `facing_right`, `size`, `score`, `draw_x`, `draw_y`, `fish_w`, `fish_h`, `sprite`, `dropping`, `stung_until`, `gold_frenzy_until`, `color_scheme`. Has a drop-in animation on spawn (`DROP_DURATION = 1.0s`, ease-out curve) — mouse tracking starts after the drop completes. When stung by jellyfish, movement slows to 30% for 1s with a 0.3s wavy `~` flash effect. Gold frenzy state tracks the power-up timer. A random color scheme is chosen on init from `PLAYER_COLOR_SCHEMES`. The `draw()` method colorizes per-character: eye, tail, dot (`·`), and body characters each get their own color from the scheme. Methods: `update()`, `check_growth()`, `apply_sting()`, `is_stung()`, `activate_gold_frenzy()`, `is_gold_frenzy()`, `_resolve_colors()`, `_colorize_char()`, `draw()`.
- **NPCFish** — classmethod `spawn()` factory (weighted: small fish spawn 3x more via `NPC_SPAWN_WEIGHTS`). Also `spawn_gold()` factory for the rare gold fish (always small, fast, `is_gold=True`, never flees). Each fish gets a `color_name` on spawn: small fish (level 0) are randomly orange or blue (`SMALL_COLORS`), medium fish (level 1) are purple (`bright_magenta`), gold fish are yellow with shimmer. Methods: `update()` (movement/bob/flee from threats, returns False if off-screen), `check_eat_collision(player, gold_frenzy)` (returns points or None; bypasses `CAN_EAT` and applies 2x multiplier during gold frenzy), `draw(term, gold_frenzy)`. All NPC fish flee from predators: player (if eatable), larger NPC fish (`NPC_CAN_EAT`), and active sharks within `NPC_FLEE_RADIUS`. Gold fish never flees.
- **Shark** — multi-row predator NPC (4-row ASCII art), rendered in grey with a bright red flashing warning sign. Spawns with a 2s flashing warning sign at the screen edge, then swims straight for 2s before chasing. Has a preferred direction (its spawn direction) that it reverts to when not chasing. Chases nearest target (NPC or small/medium player) within `SHARK_AGGRO_RADIUS` — vertical pursuit + up to `SHARK_MAX_TURNS` direction reversals. Player collision uses a mouth-only hitbox (front half); NPC collision uses full body. Big player eats shark for 10 pts; shark mouth hits small/medium player → game over. NPC fish won't spawn near the shark's entry point (within 15 rows of the warning sign on the same edge). Only spawns in frenzy mode, max 1 on screen.
- **Jellyfish** — multi-row hazard NPC (7-row, 2-frame animated sprite with wavy `()` tentacles). Spawns near the sea floor every 12-18s, floats upward while drifting sideways, bounces off walls. Stings player (slows to 30% speed for 1s + wavy `~` flash effect) and NPC fish (slows to 30% speed for 1s) on AABB collision. During gold frenzy, jellyfish become edible for `JELLY_POINTS * 2` pts. Spawns in both frenzy and aquarium modes, max 2 on screen.
- **Bubble** — classmethod `maybe_spawn()` factory. Methods: `update()` (physics + collision, returns False if expired), `draw(term, now, gold_frenzy)` (with pop animation stages; renders as gold sparkle characters during gold frenzy).
- **ScorePopup** — Methods: `update()` (drift up, returns False if expired), `draw()` (with fade).
- **GoldSparkle** — particle effect for gold fish trail and frenzy ambient sparkles. Trail sparkles (`is_trail=True`) stay in place and fade in 0.5s, capped at 5. Ambient sparkles float upward with drift, fade in 2s, capped at 15. Methods: `maybe_spawn()` (random position), `maybe_spawn_at(x, y)` (trail), `update()`, `draw()`.

### Key Design Decisions

- **Mouse input**: SGR mouse tracking (`\033[?1003h\033[?1006h`) is enabled/disabled manually via escape sequences. Mouse sequences are parsed with regex, then stripped from raw input to isolate keyboard presses.
- **Player fish sprites**: Multi-row ASCII art stored in `PLAYER_SIZES` dict in `fish_sprites.py`, keyed by size (`small`/`medium`/`big`) and direction (`left`/`right`). The `right` sprite has the head (eye `o`) on the right side. Sprites use curved contours (`` /`·. `` top, `` \,·' `` bottom), `}>`/`}>>`/`}}>` tail fins, `o` eye, `)` nose, and `·` dot texture for scales. Small is 3 rows, medium is 4 rows, big is 5 rows.
- **NPC fish**: 1-row sprites from `NPC_SPRITES` in `fish_sprites.py` that spawn off-screen and swim across. Each has a `layer` (`back`/`front`) determining draw order relative to the player and a `level` (0=small, 1=medium) from `NPC_LEVELS` in `config.py`. Non-skittish fish use `start_x + speed * elapsed`; skittish fish (the 2 smallest, ≤3 chars) use incremental updates. All NPC fish flee from threats (player, larger NPC fish, sharks) within flee radius.
- **Eating**: Player eats NPC fish on AABB collision if `f.level in CAN_EAT[player.size]` (or any fish during gold frenzy). Eaten fish are removed, points added to `player.score` (doubled during gold frenzy), and a ScorePopup is created. Player auto-grows at score thresholds defined in `GROWTH_THRESHOLDS`.
- **Shark**: Multi-row predator from `SHARK_SPRITE_RIGHT/LEFT` in `fish_sprites.py`. Spawns every 15-20s (`SHARK_SPAWN_INTERVAL_RANGE`) with a 2s warning sign, then swims straight for 2s before chasing. Has a `preferred_right` direction (spawn direction) it reverts to when no target is in range. Chases targets within `SHARK_AGGRO_RADIUS` (vertical pursuit + horizontal turn-arounds up to `SHARK_MAX_TURNS`). Player kill uses mouth-only hitbox (`_mouth_hitbox()` — front half of sprite); NPC collision uses full body. NPC fish are prevented from spawning near the shark's warning sign (within 15 rows on the same edge).
- **Jellyfish**: Multi-row hazard from `JELLYFISH_FRAMES` in `fish_sprites.py` (2 animation frames). Spawns every 12-18s near sea floor, floats up with sideways drift. Stings on AABB collision: player gets `~` flash + 30% speed for 1s; NPC fish get 30% speed for 1s. During gold frenzy, player eats jellyfish instead of getting stung (eat check runs before sting check).
- **Game over**: Shark killing the player triggers a game over screen with restart (R) or quit (Q) option. `main()` returns `'restart'` to loop back.
- **Bubbles**: Bubble objects with individual `rise_iv`/`wobble_iv` intervals. They grow through visual stages (`.` -> `o` -> `O`) based on age in seconds, rendered in blue. Multi-stage pop animation (`*` -> droplet ring -> fade) in bright blue triggers when reaching the top border or when a fish (player or NPC) touches them (50% chance).
- **Sea floor**: `SeaFloor` class generates decorations (sand, seaweed, rocks) once at startup. `draw(term, now, layer)` renders for a given layer with colors: yellow sand, RGB green seaweed, grey rocks. Seaweed sways using `math.sin()` with wall-clock time. Both seaweed and rocks have a `layer` for depth relative to the player.
- **Gold fish**: Rare NPC (`is_gold=True`) using `spawn_gold()` factory. Always small (level 0), very fast (speed 24-32), swims in a straight line and never flees. Leaves a constant trail of up to 5 `GoldSparkle` particles behind its tail. Spawns every 45-60s in frenzy mode only, max 1 on screen. Eating it activates a 10s Gold Frenzy on the player.
- **Gold Frenzy**: Temporary power-up tracked via `Player.gold_frenzy_until` (same timer pattern as jellyfish sting). During frenzy: all entities turn gold (via `gold_frenzy` param on `draw()` methods), player can eat any NPC regardless of level, jellyfish become edible (eat check before sting check), shark `'eaten'` result overridden to `'killed'`, all points doubled (`GOLD_FRENZY_POINT_MULT`). Visual effects: gold sparkle particles float across the screen, bubbles render as gold sparkle characters, flashing "GOLD FRENZY" countdown in title bar. Gold fish trail sparkles persist independently of frenzy state.
- **Aqua mode**: `player is None` guards all player-dependent paths. `aqua_mode` bool passed to `NPCFish.update()` to disable skittish flee behavior. Gold fish does not spawn in aquarium mode.

### Colors

Colors are applied in each entity's `draw()` method using `blessed` terminal attributes (e.g., `term.blue`, `term.color_rgb(r, g, b)`). Each color is assigned to a local variable at the top of `draw()` for easy tuning. Current palette:
- **Sea floor**: yellow sand, RGB `(0,200,0)` seaweed, RGB `(150,150,150)` rocks
- **Bubbles**: blue (growing), bright blue (popping)
- **Small NPC fish**: randomly orange or blue (`NPCFish.SMALL_COLORS`)
- **Medium NPC fish**: bright magenta (purple)
- **Shark**: RGB `(100,100,100)` body, bright red warning sign
- **Gold fish**: yellow with bold yellow shimmer (alternates at 4Hz)
- **Player fish**: per-character coloring with a random scheme chosen each game from `PLAYER_COLOR_SCHEMES` in `config.py`. Four schemes: cyan/white/orange, orange/white/yellow, blue/yellow/green, green/white/orange/yellow-dots. Each scheme specifies separate colors for body, eye, tail (`}><{`), and dot (`·`) characters. Character sets defined by `PLAYER_TAIL_CHARS`, `PLAYER_EYE_CHARS`, `PLAYER_DOT_CHARS` in config.
- **Gold Frenzy**: all entities override to yellow/bold yellow; bubbles become gold sparkle characters; ambient gold sparkle particles (`✦ ✧ ★ · ✶ *`) in bold yellow fading to yellow; title bar frenzy text flashes bold yellow/yellow
- Jellyfish, score popups, border, title, and game over screen are not yet colored.

### Config (config.py)

All magic numbers and tuning constants are centralized in `config.py`: timing intervals, spawn limits, speed ranges, growth thresholds, eat rules, popup timing, sea floor generation params, mouse escape sequences, the `TITLE_ART` ASCII logo, gold fish params (`GOLD_FISH_SPAWN_INTERVAL_RANGE`, `GOLD_FISH_SPEED_RANGE`, `GOLD_FISH_POINTS`, `JELLY_POINTS`), gold frenzy params (`GOLD_FRENZY_DURATION`, `GOLD_FRENZY_POINT_MULT`, `GOLD_FRENZY_COLOR`, `GOLD_SPARKLE_*` constants), and player color params (`PLAYER_COLOR_SCHEMES`, `PLAYER_TAIL_CHARS`, `PLAYER_EYE_CHARS`, `PLAYER_DOT_CHARS`).
