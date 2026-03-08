import argparse
from blessed import Terminal
import fcntl
import math
import os
import random
import re
import select
import sys
import time

from fish_sprites import PLAYER_SIZES, NPC_SPRITES, NPC_LEVELS, NPC_POINTS

def main(aqua_mode=False):
    term = Terminal()

    px = term.width // 2
    py = term.height // 2
    facing_right = True
    size = "small"
    score = 0
    score_popups = []
    GROWTH_THRESHOLDS = {"small": 20, "medium": 50}
    CAN_EAT = {"small": {0}, "medium": {0, 1}, "big": {0, 1}}

    bubbles = []
    last_bubble_time = time.monotonic()
    BUBBLE_INTERVAL = 0.8  # seconds between spawn attempts

    # Mouse target (None = no target, fish stops)
    mouse_x = None
    mouse_y = None

    # Generate sea floor decorations (fixed at startup)
    floor_y = term.height - 2  # row just above bottom border
    sand_row = ''
    for x in range(1, term.width - 1):
        sand_row += random.choice(['~', '.', ',', '.', '~', '.'])

    # Seaweed positions: list of (x, height, sway_offset, style)
    seaweeds = []
    for x in range(3, term.width - 3, random.randint(6, 10)):
        x += random.randint(-2, 2)
        h = random.randint(2, 5)
        style = random.choice([('(', ')'), ('{', '}')])
        seaweeds.append((x, h, random.random() * 10, style, random.choice(['back', 'front'])))

    # Rocks: list of (x, style)
    rocks = []
    for x in range(5, term.width - 5, random.randint(12, 20)):
        x += random.randint(-3, 3)
        style = random.choice(['small', 'large'])
        rocks.append((x, style, random.choice(['back', 'front'])))

    # NPC fish: list of dicts
    npc_fish = []
    last_npc_spawn = time.monotonic()
    NPC_SPAWN_INTERVAL = 2.0
    MAX_NPC = 8

    # Enable SGR mouse tracking (movement + clicks)
    ENABLE_MOUSE = '\033[?1003h\033[?1006h'
    DISABLE_MOUSE = '\033[?1003l\033[?1006l'

    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        if not aqua_mode:
            sys.stdout.write(ENABLE_MOUSE)
            sys.stdout.flush()

        fd = sys.stdin.fileno()

        try:
            while True:
                # Wait for input or timeout
                ready, _, _ = select.select([fd], [], [], 0.05)
                raw = b''
                if ready:
                    # Read all available bytes
                    while select.select([fd], [], [], 0)[0]:
                        raw += os.read(fd, 1024)

                raw_str = raw.decode('utf-8', errors='ignore')

                # Strip escape sequences to find plain keypresses
                plain = re.sub(r'\033\[<[^Mm]*[Mm]', '', raw_str)
                plain = re.sub(r'\033\[[^a-zA-Z]*[a-zA-Z]', '', plain)

                if 'q' in plain:
                    break

                if not aqua_mode:
                    # Parse SGR mouse sequences: \033[<btn;x;yM or m
                    for match in re.finditer(r'\033\[<(\d+);(\d+);(\d+)([Mm])', raw_str):
                        btn, mx, my, action = match.groups()
                        mouse_x = int(mx) - 1
                        mouse_y = int(my) - 1

                    direction = "right" if facing_right else "left"
                    sprite = PLAYER_SIZES[size][direction]
                    fish_w = len(sprite[0])
                    fish_h = len(sprite)

                    # Move fish toward mouse position
                    if mouse_x is not None and mouse_y is not None:
                        fish_cx = px + fish_w // 2
                        fish_cy = py + fish_h // 2

                        dx = mouse_x - fish_cx
                        dy = mouse_y - fish_cy

                        if abs(dx) > 1:
                            px += 1 if dx > 0 else -1
                            facing_right = dx > 0
                        if abs(dy) > 1:
                            py += 1 if dy > 0 else -1

                    direction = "right" if facing_right else "left"
                    player_sprite = PLAYER_SIZES[size][direction]
                    fish_w = len(player_sprite[0])
                    fish_h = len(player_sprite)

                    # Clamped player draw position (used for collision + drawing)
                    draw_x = max(1, min(px, term.width - fish_w - 1))
                    draw_y = max(1, min(py, term.height - fish_h - 1))

                # Spawn a bubble occasionally near the bottom
                now = time.monotonic()
                if now - last_bubble_time >= BUBBLE_INTERVAL:
                    last_bubble_time = now
                    if random.random() < 0.4:
                        bx = random.randint(2, term.width - 3)
                        by = random.randint(term.height // 2, term.height - 2)
                        # rise_interval / wobble_interval in seconds
                        rise_iv = random.uniform(0.15, 0.5)
                        wobble_iv = random.uniform(0.2, 0.6)
                        bubbles.append({
                            'x': bx, 'y': by, 'age': 0.0,
                            'popping': 0.0,
                            'rise_iv': rise_iv, 'wobble_iv': wobble_iv,
                            'next_rise': now + rise_iv,
                            'next_wobble': now + wobble_iv,
                            'born': now,
                        })

                # Update bubbles
                new_bubbles = []
                for b in bubbles:
                    if b['popping'] > 0:
                        if now - b['pop_start'] < 0.5:
                            new_bubbles.append(b)
                        continue

                    b['age'] = now - b['born']

                    if now >= b['next_rise']:
                        b['y'] -= 1
                        b['next_rise'] = now + b['rise_iv']

                    if now >= b['next_wobble']:
                        b['x'] += random.choice([-1, 1])
                        b['x'] = max(1, min(b['x'], term.width - 2))
                        b['next_wobble'] = now + b['wobble_iv']

                    if b['y'] <= 1:
                        b['popping'] = 1
                        b['pop_start'] = now
                        new_bubbles.append(b)
                        continue

                    # Check collision with player fish
                    popped = False
                    if not aqua_mode:
                        if draw_x <= b['x'] < draw_x + fish_w and draw_y <= b['y'] < draw_y + fish_h:
                            if random.random() < 0.5:
                                b['popping'] = 1
                                b['pop_start'] = now
                                popped = True

                    # Check collision with NPC fish
                    if not popped:
                        for f in npc_fish:
                            fx = int(f['x'])
                            fy = int(f.get('draw_y', f['y']))
                            sprite = f['sprite_r'] if f['going_right'] else f['sprite_l']
                            if fx <= b['x'] < fx + len(sprite) and fy == b['y']:
                                if random.random() < 0.5:
                                    b['popping'] = 1
                                    b['pop_start'] = now
                                break

                    new_bubbles.append(b)

                bubbles = new_bubbles

                # Spawn NPC fish
                if now - last_npc_spawn >= NPC_SPAWN_INTERVAL and len(npc_fish) < MAX_NPC:
                    last_npc_spawn = now
                    sprite_idx = random.randrange(len(NPC_SPRITES))
                    sprite_r, sprite_l = NPC_SPRITES[sprite_idx]
                    level = NPC_LEVELS[sprite_idx]
                    going_right = random.choice([True, False])
                    if going_right:
                        start_x = -len(sprite_r)
                    else:
                        start_x = term.width
                    skittish = len(sprite_r) <= 3
                    npc_fish.append({
                        'x': float(start_x),
                        'start_x': float(start_x),
                        'y': random.randint(2, floor_y - 3),
                        'sprite_r': sprite_r,
                        'sprite_l': sprite_l,
                        'going_right': going_right,
                        'speed': random.uniform(4.0, 12.0),  # chars per second
                        'bob_amp': random.uniform(0.3, 1.5),
                        'bob_speed': random.uniform(1.0, 3.0),
                        'bob_offset': random.random() * 6.28,
                        'born': now,
                        'layer': random.choice(['back', 'front']),
                        'skittish': skittish,
                        'last_update': now,
                        'level': level,
                    })

                # Update NPC fish
                FLEE_RADIUS = 10
                FLEE_SPEED_MULT = 1.3
                new_npc = []
                for f in npc_fish:
                    dt = now - f['last_update']
                    f['last_update'] = now

                    if f['skittish'] and not aqua_mode:
                        # Check distance to player center
                        fish_cx = draw_x + fish_w // 2
                        fish_cy = draw_y + fish_h // 2
                        fx = f['x'] + len(f['sprite_r']) / 2
                        fy = f['y']
                        ddx = fx - fish_cx
                        ddy = fy - fish_cy
                        dist = math.sqrt(ddx * ddx + ddy * ddy)

                        if dist < FLEE_RADIUS and dist > 0:
                            # Flee away from player
                            flee_speed = f['speed'] * FLEE_SPEED_MULT
                            f['x'] += (ddx / dist) * flee_speed * dt
                            f['y'] += (ddy / dist) * flee_speed * dt
                            f['y'] = max(2, min(f['y'], floor_y - 3))
                            f['going_right'] = ddx > 0
                        else:
                            # Normal movement
                            if f['going_right']:
                                f['x'] += f['speed'] * dt
                            else:
                                f['x'] -= f['speed'] * dt
                    elif f['skittish']:
                        # Aqua mode: skittish fish just swim normally
                        if f['going_right']:
                            f['x'] += f['speed'] * dt
                        else:
                            f['x'] -= f['speed'] * dt
                    else:
                        elapsed = now - f['born']
                        if f['going_right']:
                            f['x'] = f['start_x'] + f['speed'] * elapsed
                        else:
                            f['x'] = f['start_x'] - f['speed'] * elapsed

                    # Remove if off screen
                    if f['x'] > term.width + 5 or f['x'] < -10:
                        continue

                    # Bob up and down
                    f['draw_y'] = f['y'] + math.sin(now * f['bob_speed'] + f['bob_offset']) * f['bob_amp']

                    # Check eating collision with player
                    if not aqua_mode:
                        sprite = f['sprite_r'] if f['going_right'] else f['sprite_l']
                        fx = int(f['x'])
                        fy = int(f['draw_y'])
                        npc_w = len(sprite)
                        if (fx < draw_x + fish_w and fx + npc_w > draw_x and
                                fy >= draw_y and fy < draw_y + fish_h):
                            if f['level'] in CAN_EAT.get(size, set()):
                                pts = NPC_POINTS[f['level']]
                                score += pts
                                score_popups.append({
                                    'x': fx + npc_w // 2,
                                    'y': float(fy),
                                    'text': f"+{pts}",
                                    'born': now,
                                })
                                continue

                    new_npc.append(f)

                npc_fish = new_npc

                # Auto-growth based on score
                if not aqua_mode:
                    threshold = GROWTH_THRESHOLDS.get(size)
                    if threshold is not None and score >= threshold:
                        if size == "small":
                            size = "medium"
                        elif size == "medium":
                            size = "big"
                        direction = "right" if facing_right else "left"
                        player_sprite = PLAYER_SIZES[size][direction]
                        fish_w = len(player_sprite[0])
                        fish_h = len(player_sprite)
                        draw_x = max(1, min(px, term.width - fish_w - 1))
                        draw_y = max(1, min(py, term.height - fish_h - 1))

                # Update score popups
                new_popups = []
                for p in score_popups:
                    age = now - p['born']
                    if age < 1.0:
                        p['y'] -= 0.05
                        new_popups.append(p)
                score_popups = new_popups

                # Draw frame
                output = term.home + term.clear

                # Border - top
                output += term.move_xy(0, 0) + '+' + '-' * (term.width - 2) + '+'
                # Border - sides
                for y in range(1, term.height - 1):
                    output += term.move_xy(0, y) + '|'
                    output += term.move_xy(term.width - 1, y) + '|'
                # Border - bottom
                output += term.move_xy(0, term.height - 1) + '+' + '-' * (term.width - 2) + '+'

                # Title
                if aqua_mode:
                    title = " TermFrenzy Aquarium | Q:quit "
                else:
                    threshold = GROWTH_THRESHOLDS.get(size)
                    if threshold is not None:
                        prev = GROWTH_THRESHOLDS.get(
                            "small" if size == "medium" else None, 0)
                        progress = score - prev
                        needed = threshold - prev
                        bar_len = 20
                        filled = min(bar_len, int(progress / needed * bar_len))
                        bar = '█' * filled + '░' * (bar_len - filled)
                        grow_info = f" [{bar}]"
                    else:
                        grow_info = f" [{'█' * 20}]"
                    title = f" TermFrenzy | Score:{score} | Growth:{grow_info} | Q:quit "
                output += term.move_xy(2, 0) + title

                # Sea floor - sand
                output += term.move_xy(1, floor_y) + sand_row

                # Sea floor - back-layer seaweed
                for sx, sh, soff, sw_style, sw_layer in seaweeds:
                    if sw_layer != 'back':
                        continue
                    for j in range(sh):
                        sway = int(math.sin(now * 1.5 + soff + j * 0.5) * 1.2)
                        draw_sx = sx + sway
                        draw_sy = floor_y - 1 - j
                        if 1 <= draw_sx < term.width - 1 and 1 <= draw_sy < term.height - 1:
                            leaf = sw_style[0] if (j + int(now * 2)) % 2 == 0 else sw_style[1]
                            output += term.move_xy(draw_sx, draw_sy) + leaf

                # Sea floor - back-layer rocks
                for rx, rstyle, rlayer in rocks:
                    if rlayer != 'back':
                        continue
                    if rstyle == 'small':
                        if 1 <= rx < term.width - 2:
                            output += term.move_xy(rx, floor_y - 1) + '/\\'
                    else:
                        if 1 <= rx < term.width - 3:
                            output += term.move_xy(rx, floor_y - 1) + '/~~\\'
                            output += term.move_xy(rx - 1, floor_y - 2) + '/    \\'

                # Draw bubbles
                for b in bubbles:
                    bx, by, age = b['x'], b['y'], b['age']
                    if b['popping'] > 0:
                        elapsed = now - b['pop_start']
                        if elapsed < 0.1:
                            # Stage 1: burst
                            if 1 <= bx < term.width - 1 and 1 <= by < term.height - 1:
                                output += term.move_xy(bx, by) + '*'
                        elif elapsed < 0.25:
                            # Stage 2: ring of droplets
                            for dx, dy, ch in [(-1,0,'-'), (1,0,'-'), (0,-1,'|'), (0,1,'|'),
                                                (-1,-1,'\''), (1,-1,'\''), (-1,1,'.'), (1,1,'.')]:
                                sx, sy = bx + dx, by + dy
                                if 1 <= sx < term.width - 1 and 1 <= sy < term.height - 1:
                                    output += term.move_xy(sx, sy) + ch
                        elif elapsed < 0.4:
                            # Stage 3: fading outward
                            for dx, dy in [(-2,0), (2,0), (0,-1), (0,1)]:
                                sx, sy = bx + dx, by + dy
                                if 1 <= sx < term.width - 1 and 1 <= sy < term.height - 1:
                                    output += term.move_xy(sx, sy) + '·'
                        # Stage 4 (0.4-0.5): nothing drawn, bubble fades out
                    else:
                        if age < 0.6:
                            ch = '.'
                        elif age < 1.5:
                            ch = 'o'
                        else:
                            ch = 'O'
                        if 1 <= bx < term.width - 1 and 1 <= by < term.height - 1:
                            output += term.move_xy(bx, by) + ch

                if aqua_mode:
                    # Draw all NPC fish (no player, no layer split needed)
                    for f in npc_fish:
                        sprite = f['sprite_r'] if f['going_right'] else f['sprite_l']
                        fx = int(f['x'])
                        fy = int(f['draw_y'])
                        if 1 <= fy < term.height - 1:
                            for i, ch in enumerate(sprite):
                                cx = fx + i
                                if 1 <= cx < term.width - 1:
                                    output += term.move_xy(cx, fy) + ch
                else:
                    # Draw back-layer NPC fish (behind player)
                    for f in npc_fish:
                        if f['layer'] != 'back':
                            continue
                        sprite = f['sprite_r'] if f['going_right'] else f['sprite_l']
                        fx = int(f['x'])
                        fy = int(f['draw_y'])
                        if 1 <= fy < term.height - 1:
                            for i, ch in enumerate(sprite):
                                cx = fx + i
                                if 1 <= cx < term.width - 1:
                                    output += term.move_xy(cx, fy) + ch

                    # Draw player fish
                    for i, row in enumerate(player_sprite):
                        output += term.move_xy(draw_x, draw_y + i) + row

                    # Draw front-layer NPC fish (in front of player)
                    for f in npc_fish:
                        if f['layer'] != 'front':
                            continue
                        sprite = f['sprite_r'] if f['going_right'] else f['sprite_l']
                        fx = int(f['x'])
                        fy = int(f['draw_y'])
                        if 1 <= fy < term.height - 1:
                            for i, ch in enumerate(sprite):
                                cx = fx + i
                                if 1 <= cx < term.width - 1:
                                    output += term.move_xy(cx, fy) + ch

                # Draw score popups
                for p in score_popups:
                    ppx = int(p['x'])
                    ppy = int(p['y'])
                    age = now - p['born']
                    text = p['text'] if age < 0.7 else ('.' if age < 0.85 else '')
                    if text and 1 <= ppx < term.width - len(text) and 1 <= ppy < term.height - 1:
                        output += term.move_xy(ppx, ppy) + text

                # Sea floor - front-layer seaweed
                for sx, sh, soff, sw_style, sw_layer in seaweeds:
                    if sw_layer != 'front':
                        continue
                    for j in range(sh):
                        sway = int(math.sin(now * 1.5 + soff + j * 0.5) * 1.2)
                        draw_sx = sx + sway
                        draw_sy = floor_y - 1 - j
                        if 1 <= draw_sx < term.width - 1 and 1 <= draw_sy < term.height - 1:
                            leaf = sw_style[0] if (j + int(now * 2)) % 2 == 0 else sw_style[1]
                            output += term.move_xy(draw_sx, draw_sy) + leaf

                # Sea floor - front-layer rocks
                for rx, rstyle, rlayer in rocks:
                    if rlayer != 'front':
                        continue
                    if rstyle == 'small':
                        if 1 <= rx < term.width - 2:
                            output += term.move_xy(rx, floor_y - 1) + '/\\'
                    else:
                        if 1 <= rx < term.width - 3:
                            output += term.move_xy(rx, floor_y - 1) + '/~~\\'
                            output += term.move_xy(rx - 1, floor_y - 2) + '/    \\'

                print(output, end='', flush=True)

        finally:
            if not aqua_mode:
                sys.stdout.write(DISABLE_MOUSE)
                sys.stdout.flush()

parser = argparse.ArgumentParser(description='TermFrenzy - terminal Feeding Frenzy game')
parser.add_argument('--aqua', action='store_true', help='Aquarium mode: no player, just watch the fish')
args = parser.parse_args()
main(aqua_mode=args.aqua)
