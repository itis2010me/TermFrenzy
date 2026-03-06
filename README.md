# TermFrenzy

A terminal-based game inspired by PopCap's Feeding Frenzy, built with Python and [blessed](https://github.com/jquast/blessed).

![Gameplay](assets/gameshot.png)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install blessed
```

## Run

```bash
python src/game.py
```

### Aquarium Mode

Watch the fish swim around without a player — like ASCIIQuarium:

```bash
python src/game.py --aqua
```

## Controls

| Input | Action |
|-------|--------|
| Mouse | Fish follows cursor (game mode only) |
| 1/2/3 | Switch fish size (game mode only) |
| Q | Quit |

## Features

- **Mouse-controlled** ASCII fish that swims toward your cursor
- Fish flips direction based on movement
- 3 multi-row fish sizes (small 3-row, medium 4-row, big 5-row)
- **NPC fish** with depth layers (some swim in front, some behind the player)
  - Small fish are skittish and flee from the player (but can be caught)
- **Bubbles** that:
  - Spawn near the bottom and float upward
  - Each bubble has its own rise speed and wobble rate
  - Grow through stages (`.` → `o` → `O`)
  - Multi-stage pop animation (`*` → ring of droplets → fade) when reaching the top or touched by a fish (50% chance)
  - Run on real wall-clock time (independent of frame rate)
- **Sea floor** with depth layers — sand, swaying seaweed (`()` and `{}` styles), and rocks appear in front of or behind the player

## Changelog

### v0.2.0
- Added `--aqua` aquarium mode: no player, just NPC fish swimming around
- Renamed title bar to TermFrenzy
- Moved source files to `src/`
- Added gameplay screenshot

### v0.1.0
- Initial release
- Mouse-controlled player fish with 3 sizes (small/medium/big)
- NPC fish with front/back depth layers
- Skittish small fish that flee from the player
- Bubbles with float physics and multi-stage pop animation
- Fish-triggered bubble popping (50% chance on contact)
- Sea floor with sand, swaying seaweed (two styles), and rocks
- Depth layering for sea floor decorations
