# Changelog

## v0.8.0
- Gold fish: rare fast-swimming golden NPC with sparkle trail, spawns every 45-60s in frenzy mode
- Gold Frenzy power-up: eating the gold fish triggers a 10s frenzy mode
  - All entities (NPC fish, jellyfish, sharks, bubbles, player) turn gold
  - Player can eat any fish regardless of size, plus jellyfish and sharks
  - All points doubled during frenzy
  - Gold sparkle particles float across the screen
  - Bubbles render as gold sparkles
  - Flashing "GOLD FRENZY" countdown in title bar
- New entity: GoldSparkle particle (trail + ambient effects)

## v0.7.0
- Added color to sea floor: yellow sand, green seaweed, grey rocks
- Bubbles are now blue with bright blue pop animation
- Small NPC fish randomly colored orange or blue
- Medium NPC fish colored purple
- Shark colored grey with bright red warning sign

## v0.6.0
- Jellyfish hazard: multi-row animated sprite, floats upward from sea floor
- Stings player and NPC fish on contact (30% speed for 1s)
- Wavy `~` flash effect on player when stung
- Appears in both frenzy and aquarium modes

## v0.5.0
- Shark predator: multi-row ASCII art, warning sign, aggro-radius chasing with turn-arounds
- Shark eats NPC fish and kills small/medium player (game over); big player eats shark for 10 pts
- All NPC fish now flee from predators (larger fish, sharks, player)
- Small fish spawn 3x more often via weighted selection
- Game over screen with restart (R) or quit (Q)

## v0.4.0
- Title screen with ASCII art logo and live aquarium background
- Mode selection: choose Frenzy or Aquarium from the menu
- Aquarium state carries over seamlessly when selected from title screen
- Player drop-in animation with ease-out curve on frenzy start
- Codebase refactored into modular OOP structure (config, entities, sea_floor)

## v0.3.0
- Eating mechanic: swim into smaller fish to eat them and earn points
- Auto-growth: player grows from small → medium → big based on score
- NPC fish split into level 0 (small, 2 pts) and level 1 (medium, 5 pts)
- Score display in title bar
- Floating score popups (+2, +5) on eating
- Removed manual 1/2/3 size switching

## v0.2.0
- Added `--aqua` aquarium mode: no player, just NPC fish swimming around
- Renamed title bar to TermFrenzy
- Moved source files to `src/`
- Added gameplay screenshot

## v0.1.0
- Initial release
- Mouse-controlled player fish with 3 sizes (small/medium/big)
- NPC fish with front/back depth layers
- Skittish small fish that flee from the player
- Bubbles with float physics and multi-stage pop animation
- Fish-triggered bubble popping (50% chance on contact)
- Sea floor with sand, swaying seaweed (two styles), and rocks
- Depth layering for sea floor decorations
