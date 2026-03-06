# Feeding Frenzy

A terminal-based game inspired by PopCap's Feeding Frenzy, built with Python and [blessed](https://github.com/jquast/blessed).

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install blessed
```

## Run

```bash
python game.py
```

## Controls

| Input | Action |
|-------|--------|
| Mouse | Fish follows cursor |
| 1/2/3 | Switch fish size (small/medium/big) |
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
