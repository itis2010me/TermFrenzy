# Timing
FRAME_TIMEOUT = 0.05
BUBBLE_INTERVAL = 0.8
BUBBLE_SPAWN_CHANCE = 0.4
NPC_SPAWN_INTERVAL = 2.0

# Limits
MAX_NPC = 8
BUBBLE_POP_DURATION = 0.5

# Bubble ranges
BUBBLE_RISE_IV_RANGE = (0.15, 0.5)
BUBBLE_WOBBLE_IV_RANGE = (0.2, 0.6)

# NPC ranges
NPC_SPEED_RANGE = (4.0, 12.0)
NPC_BOB_AMP_RANGE = (0.3, 1.5)
NPC_BOB_SPEED_RANGE = (1.0, 3.0)

# Player
FLEE_RADIUS = 10
FLEE_SPEED_MULT = 1.3
GROWTH_THRESHOLDS = {"small": 20, "medium": 50}
CAN_EAT = {"small": {0}, "medium": {0, 1}, "big": {0, 1}}
GROWTH_BAR_LEN = 20

# Score popups
POPUP_DRIFT_SPEED = 0.05
POPUP_LIFETIME = 1.0
POPUP_FADE_TIME = 0.7
POPUP_VANISH_TIME = 0.85

# Sea floor
SEAWEED_SPACING_RANGE = (6, 10)
SEAWEED_STYLES = [('(', ')'), ('{', '}')]
ROCK_STYLES = ['small', 'large']
SAND_CHARS = ['~', '.', ',', '.', '~', '.']
SEAWEED_SWAY_SPEED = 1.5
SEAWEED_SWAY_AMP = 1.2
SEAWEED_ANIM_SPEED = 2
ROCK_SPACING_RANGE = (12, 20)

# Mouse escape sequences
ENABLE_MOUSE = '\033[?1003h\033[?1006h'
DISABLE_MOUSE = '\033[?1003l\033[?1006l'

# NPC levels and points (indexed parallel to NPC_SPRITES in fish_sprites.py)
NPC_LEVELS = [0, 0, 0, 1, 1, 1]
NPC_POINTS = {0: 2, 1: 5}
