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
python src/game.py          # launches title screen
python src/game.py --aqua   # skip title screen, straight to aquarium
```

A title screen lets you choose between **Frenzy Mode** (gameplay) and **Aquarium Mode** (passive watching). The `--aqua` flag skips the title screen.

## Controls

| Input | Action |
|-------|--------|
| Arrow keys | Navigate title screen menu |
| Enter | Select menu option |
| Mouse | Fish follows cursor (frenzy mode only) |
| Q | Quit |
| R | Restart (on game over screen) |

## Features

- **Mouse-controlled** ASCII fish that swims toward your cursor
- **Eat smaller fish** to earn points and auto-grow (small → medium → big)
  - Level 0 fish (small sprites) give 2 points, level 1 fish give 5 points
  - Grow to medium at 20 points, big at 50 points
  - Score popup floats up from eaten fish
- **NPC fish** with depth layers (some swim in front, some behind the player)
  - Small fish spawn 3x more often than large fish
  - All fish flee from predators — player, larger NPC fish, and sharks
- **Bubbles** that:
  - Spawn near the bottom and float upward
  - Each bubble has its own rise speed and wobble rate
  - Grow through stages (`.` → `o` → `O`)
  - Multi-stage pop animation (`*` → ring of droplets → fade) when reaching the top or touched by a fish (50% chance)
  - Run on real wall-clock time (independent of frame rate)
- **Shark** predator that hunts fish and the player
  - Warning sign flashes at screen edge 2 seconds before the shark appears
  - Chases nearest target vertically and can turn around up to 5 times
  - Eats NPC fish on contact; eats small/medium player → game over
  - Big player can eat the shark for 10 points
- **Game over & restart** — shark killing the player shows a game over screen with final score; press R to restart or Q to quit
- **Sea floor** with depth layers — sand, swaying seaweed (`()` and `{}` styles), and rocks appear in front of or behind the player

## Features Coming

- Eating animation
- Fish groups
- More fish varieties (always)

## Changelog

### v0.5.0
- Shark predator: multi-row ASCII art, warning sign, aggro-radius chasing with turn-arounds
- Shark eats NPC fish and kills small/medium player (game over); big player eats shark for 10 pts
- All NPC fish now flee from predators (larger fish, sharks, player)
- Small fish spawn 3x more often via weighted selection
- Game over screen with restart (R) or quit (Q)

### v0.4.0
- Title screen with ASCII art logo and live aquarium background
- Mode selection: choose Frenzy or Aquarium from the menu
- Aquarium state carries over seamlessly when selected from title screen
- Player drop-in animation with ease-out curve on frenzy start
- Codebase refactored into modular OOP structure (config, entities, sea_floor)

### v0.3.0
- Eating mechanic: swim into smaller fish to eat them and earn points
- Auto-growth: player grows from small → medium → big based on score
- NPC fish split into level 0 (small, 2 pts) and level 1 (medium, 5 pts)
- Score display in title bar
- Floating score popups (+2, +5) on eating
- Removed manual 1/2/3 size switching

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
