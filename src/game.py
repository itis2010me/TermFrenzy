import argparse
import os
import random
import re
import select
import sys
import time

from blessed import Terminal

from config import (
    FRAME_TIMEOUT, BUBBLE_INTERVAL, NPC_SPAWN_INTERVAL, MAX_NPC,
    GROWTH_THRESHOLDS, GROWTH_BAR_LEN,
    ENABLE_MOUSE, DISABLE_MOUSE, NPC_POINTS,
    TITLE_ART,
    SHARK_SPAWN_INTERVAL_RANGE, MAX_SHARKS, SHARK_POINTS,
    JELLY_SPAWN_INTERVAL_RANGE, MAX_JELLIES,
)
from entities import Player, NPCFish, Bubble, ScorePopup, Shark, Jellyfish
from sea_floor import SeaFloor


def read_input(fd):
    ready, _, _ = select.select([fd], [], [], FRAME_TIMEOUT)
    raw = b''
    if ready:
        while select.select([fd], [], [], 0)[0]:
            raw += os.read(fd, 1024)
    return raw.decode('utf-8', errors='ignore')


def strip_escapes(raw_str):
    plain = re.sub(r'\033\[<[^Mm]*[Mm]', '', raw_str)
    plain = re.sub(r'\033\[[^a-zA-Z]*[a-zA-Z]', '', plain)
    return plain


def draw_border(term):
    output = term.move_xy(0, 0) + '+' + '-' * (term.width - 2) + '+'
    for y in range(1, term.height - 1):
        output += term.move_xy(0, y) + '|'
        output += term.move_xy(term.width - 1, y) + '|'
    output += term.move_xy(0, term.height - 1) + '+' + '-' * (term.width - 2) + '+'
    return output


def draw_title(term, player, aqua_mode):
    if aqua_mode:
        title = " TermFrenzy Aquarium | Q:quit "
    else:
        threshold = GROWTH_THRESHOLDS.get(player.size)
        if threshold is not None:
            prev = GROWTH_THRESHOLDS.get(
                "small" if player.size == "medium" else None, 0)
            progress = player.score - prev
            needed = threshold - prev
            filled = min(GROWTH_BAR_LEN, int(progress / needed * GROWTH_BAR_LEN))
            bar = '\u2588' * filled + '\u2591' * (GROWTH_BAR_LEN - filled)
            grow_info = f" [{bar}]"
        else:
            grow_info = f" [{'\u2588' * GROWTH_BAR_LEN}]"
        title = f" TermFrenzy | Score:{player.score} | Growth:{grow_info} | Q:quit "
    return term.move_xy(2, 0) + title


def draw_aqua_frame(term, sea, bubbles, npc_fish, jellies, now):
    output = term.home + term.clear
    output += draw_border(term)
    output += term.move_xy(2, 0) + " TermFrenzy "
    output += sea.draw(term, now, 'back')
    for b in bubbles:
        output += b.draw(term, now)
    for j in jellies:
        output += j.draw(term, now)
    for f in npc_fish:
        output += f.draw(term)
    output += sea.draw(term, now, 'front')
    return output


def update_aqua(sea, bubbles, npc_fish, jellies, last_bubble_time, last_npc_spawn,
                last_jelly_spawn, next_jelly_interval, now, term):
    # Bubble spawn
    if now - last_bubble_time >= BUBBLE_INTERVAL:
        last_bubble_time = now
        b = Bubble.maybe_spawn(now, term.width, term.height)
        if b:
            bubbles.append(b)

    # Bubble update
    bubbles[:] = [b for b in bubbles if b.update(now, term.width, None, npc_fish, True)]

    # NPC spawn
    if now - last_npc_spawn >= NPC_SPAWN_INTERVAL and len(npc_fish) < MAX_NPC:
        last_npc_spawn = now
        npc_fish.append(NPCFish.spawn(term.width, sea.floor_y, now))

    # NPC update
    npc_fish[:] = [f for f in npc_fish if f.update(now, None, True, sea.floor_y, term.width,
                                                      npc_fish=npc_fish)]

    # Jellyfish spawn
    if now - last_jelly_spawn >= next_jelly_interval and len(jellies) < MAX_JELLIES:
        last_jelly_spawn = now
        next_jelly_interval = random.uniform(*JELLY_SPAWN_INTERVAL_RANGE)
        jellies.append(Jellyfish.spawn(term.width, sea.floor_y, now))

    # Jellyfish update
    jellies[:] = [j for j in jellies if j.update(now, term.width)]

    return last_bubble_time, last_npc_spawn, last_jelly_spawn, next_jelly_interval


def title_screen(term, fd):
    sea = SeaFloor(term.width, term.height)
    bubbles = []
    npc_fish = []
    jellies = []
    last_bubble_time = time.monotonic()
    last_npc_spawn = time.monotonic()
    last_jelly_spawn = time.monotonic()
    next_jelly_interval = random.uniform(*JELLY_SPAWN_INTERVAL_RANGE)
    selected = 0  # 0 = Frenzy, 1 = Aquarium

    options = ["Frenzy Mode", "Aquarium Mode"]

    title_w = max(len(line) for line in TITLE_ART)
    title_x = (term.width - title_w) // 2

    box_w = 32
    box_h = 9
    box_x = (term.width - box_w) // 2
    # Position box below the title art with a 1-row gap
    title_top_y = (term.height - (len(TITLE_ART) + 1 + box_h)) // 2
    box_y = title_top_y + len(TITLE_ART) + 1

    while True:
        raw_str = read_input(fd)
        plain = strip_escapes(raw_str)

        if 'q' in plain:
            return None, None

        # Arrow keys: \033[A = up, \033[B = down
        if '\033[A' in raw_str:
            selected = (selected - 1) % len(options)
        if '\033[B' in raw_str:
            selected = (selected + 1) % len(options)

        if '\r' in plain or '\n' in plain:
            choice = 'frenzy' if selected == 0 else 'aquarium'
            state = (sea, bubbles, npc_fish, jellies,
                     last_bubble_time, last_npc_spawn,
                     last_jelly_spawn, next_jelly_interval)
            return choice, state

        now = time.monotonic()
        last_bubble_time, last_npc_spawn, last_jelly_spawn, next_jelly_interval = update_aqua(
            sea, bubbles, npc_fish, jellies, last_bubble_time, last_npc_spawn,
            last_jelly_spawn, next_jelly_interval, now, term)

        # Draw aquarium background
        output = draw_aqua_frame(term, sea, bubbles, npc_fish, jellies, now)

        # Draw ASCII art title
        for i, line in enumerate(TITLE_ART):
            ty = title_top_y + i
            if 1 <= ty < term.height - 1:
                output += term.move_xy(title_x, ty) + line

        # Draw menu box overlay
        output += term.move_xy(box_x, box_y) + '+' + '-' * (box_w - 2) + '+'
        for row in range(1, box_h - 1):
            output += term.move_xy(box_x, box_y + row) + '|' + ' ' * (box_w - 2) + '|'
        output += term.move_xy(box_x, box_y + box_h - 1) + '+' + '-' * (box_w - 2) + '+'

        # Options centered in box
        longest = max(len(o) for o in options)
        for i, opt in enumerate(options):
            if i == selected:
                line = '> ' + opt.ljust(longest) + ' <'
            else:
                line = '  ' + opt.ljust(longest) + '  '
            lx = box_x + (box_w - len(line)) // 2
            ly = box_y + (box_h - 1) // 2 - 1 + i * 2
            output += term.move_xy(lx, ly) + line

        print(output, end='', flush=True)


def main(term, fd, aqua_mode=False, aqua_state=None):
    player = None if aqua_mode else Player(term.width, term.height)

    if aqua_state is not None:
        (sea, bubbles, npc_fish, jellies,
         last_bubble_time, last_npc_spawn,
         last_jelly_spawn, next_jelly_interval) = aqua_state
    else:
        sea = SeaFloor(term.width, term.height)
        bubbles = []
        last_bubble_time = time.monotonic()
        npc_fish = []
        last_npc_spawn = time.monotonic()
        jellies = []
        last_jelly_spawn = time.monotonic()
        next_jelly_interval = random.uniform(*JELLY_SPAWN_INTERVAL_RANGE)

    score_popups = []
    sharks = []
    last_shark_spawn = time.monotonic()
    next_shark_interval = random.uniform(*SHARK_SPAWN_INTERVAL_RANGE)
    game_over = False

    mouse_x = None
    mouse_y = None

    if not aqua_mode:
        sys.stdout.write(ENABLE_MOUSE)
        sys.stdout.flush()

    try:
        while True:
            # --- INPUT ---
            raw_str = read_input(fd)
            plain = strip_escapes(raw_str)

            if 'q' in plain:
                break

            # --- UPDATE ---
            now = time.monotonic()

            if player is not None:
                for match in re.finditer(r'\033\[<(\d+);(\d+);(\d+)([Mm])', raw_str):
                    btn, mx, my, action = match.groups()
                    mouse_x = int(mx) - 1
                    mouse_y = int(my) - 1
                player.update(mouse_x, mouse_y, term.width, term.height)

            # Bubble spawn
            if now - last_bubble_time >= BUBBLE_INTERVAL:
                last_bubble_time = now
                b = Bubble.maybe_spawn(now, term.width, term.height)
                if b:
                    bubbles.append(b)

            # Bubble update
            bubbles = [b for b in bubbles if b.update(now, term.width, player, npc_fish, aqua_mode)]

            # NPC spawn (avoid spawning near a shark's entry point)
            if now - last_npc_spawn >= NPC_SPAWN_INTERVAL and len(npc_fish) < MAX_NPC:
                last_npc_spawn = now
                f = NPCFish.spawn(term.width, sea.floor_y, now)
                too_close = False
                for s in sharks:
                    if s.going_right == f.going_right and abs(f.y - s.warning_y) < 15:
                        too_close = True
                        break
                if not too_close:
                    npc_fish.append(f)

            # NPC update + eat
            new_npc = []
            for f in npc_fish:
                if not f.update(now, player, aqua_mode, sea.floor_y, term.width,
                                npc_fish=npc_fish, sharks=sharks):
                    continue
                if player is not None:
                    pts = f.check_eat_collision(player)
                    if pts is not None:
                        player.score += pts
                        sprite = f.sprite_r if f.going_right else f.sprite_l
                        score_popups.append(ScorePopup(
                            int(f.x) + len(sprite) // 2,
                            int(f.draw_y),
                            f"+{pts}",
                            now,
                        ))
                        continue
                new_npc.append(f)
            npc_fish = new_npc

            # Shark spawn (frenzy mode only)
            if not aqua_mode:
                if now - last_shark_spawn >= next_shark_interval and len(sharks) < MAX_SHARKS:
                    last_shark_spawn = now
                    next_shark_interval = random.uniform(*SHARK_SPAWN_INTERVAL_RANGE)
                    sharks.append(Shark.spawn(term.width, sea.floor_y, now))

            # Shark update
            new_sharks = []
            for s in sharks:
                if not s.update(now, term.width, sea.floor_y, npc_fish, player):
                    continue
                if s.active:
                    npc_fish = [f for f in npc_fish if not s.check_npc_collision(f)]
                if s.active and player is not None:
                    result = s.check_player_collision(player)
                    if result == 'eaten':
                        game_over = True
                    elif result == 'killed':
                        player.score += SHARK_POINTS
                        score_popups.append(ScorePopup(
                            int(s.x) + s.fish_w // 2,
                            int(s.draw_y),
                            f"+{SHARK_POINTS}",
                            now,
                        ))
                        continue
                new_sharks.append(s)
            sharks = new_sharks

            # Jellyfish spawn
            if now - last_jelly_spawn >= next_jelly_interval and len(jellies) < MAX_JELLIES:
                last_jelly_spawn = now
                next_jelly_interval = random.uniform(*JELLY_SPAWN_INTERVAL_RANGE)
                jellies.append(Jellyfish.spawn(term.width, sea.floor_y, now))

            # Jellyfish update + sting
            new_jellies = []
            for j in jellies:
                if not j.update(now, term.width):
                    continue
                if player is not None and not aqua_mode:
                    j.check_player_collision(player, now)
                for f in npc_fish:
                    j.check_npc_collision(f, now)
                new_jellies.append(j)
            jellies = new_jellies

            if game_over:
                break

            # Growth
            if player is not None:
                player.check_growth()

            # Popup update
            score_popups = [p for p in score_popups if p.update(now)]

            # --- DRAW ---
            output = term.home + term.clear
            output += draw_border(term)
            output += draw_title(term, player, aqua_mode)

            # Sea floor back layer
            output += sea.draw(term, now, 'back')

            # Bubbles
            for b in bubbles:
                output += b.draw(term, now)

            # Jellyfish
            for j in jellies:
                output += j.draw(term, now)

            if aqua_mode:
                for f in npc_fish:
                    output += f.draw(term)
            else:
                # Back-layer NPC
                for f in npc_fish:
                    if f.layer == 'back':
                        output += f.draw(term)

                # Player
                output += player.draw(term)

                # Front-layer NPC
                for f in npc_fish:
                    if f.layer == 'front':
                        output += f.draw(term)

                # Sharks
                for s in sharks:
                    output += s.draw(term, now)

            # Score popups
            for p in score_popups:
                output += p.draw(term, now)

            # Sea floor front layer
            output += sea.draw(term, now, 'front')

            print(output, end='', flush=True)

        if game_over and player is not None:
            sys.stdout.write(DISABLE_MOUSE)
            sys.stdout.flush()
            output = term.home + term.clear
            output += draw_border(term)
            cx = term.width // 2
            cy = term.height // 2
            go_text = "G A M E   O V E R"
            score_text = f"Final Score: {player.score}"
            prompt_text = "R: Restart  |  Q: Quit"
            output += term.move_xy(cx - len(go_text) // 2, cy - 2) + go_text
            output += term.move_xy(cx - len(score_text) // 2, cy) + score_text
            output += term.move_xy(cx - len(prompt_text) // 2, cy + 2) + prompt_text
            print(output, end='', flush=True)
            while True:
                raw_str = read_input(fd)
                plain = strip_escapes(raw_str)
                if 'r' in plain:
                    return 'restart'
                if 'q' in plain or plain:
                    return None
            return None

    finally:
        if not aqua_mode:
            sys.stdout.write(DISABLE_MOUSE)
            sys.stdout.flush()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='TermFrenzy - terminal Feeding Frenzy game')
    parser.add_argument('--aqua', action='store_true', help='Aquarium mode: no player, just watch the fish')
    args = parser.parse_args()

    term = Terminal()
    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        fd = sys.stdin.fileno()
        if args.aqua:
            main(term, fd, aqua_mode=True)
        else:
            choice, state = title_screen(term, fd)
            while choice is not None:
                aqua = choice == 'aquarium'
                result = main(term, fd, aqua_mode=aqua, aqua_state=state if aqua else None)
                if result == 'restart':
                    choice = 'frenzy'
                    state = None
                else:
                    break
