import argparse
import os
import re
import select
import sys
import time

from blessed import Terminal

from config import (
    FRAME_TIMEOUT, BUBBLE_INTERVAL, NPC_SPAWN_INTERVAL, MAX_NPC,
    GROWTH_THRESHOLDS, GROWTH_BAR_LEN,
    ENABLE_MOUSE, DISABLE_MOUSE, NPC_POINTS,
)
from entities import Player, NPCFish, Bubble, ScorePopup
from sea_floor import SeaFloor


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


def main(aqua_mode=False):
    term = Terminal()

    player = None if aqua_mode else Player(term.width, term.height)
    sea = SeaFloor(term.width, term.height)

    bubbles = []
    last_bubble_time = time.monotonic()
    npc_fish = []
    last_npc_spawn = time.monotonic()
    score_popups = []

    mouse_x = None
    mouse_y = None

    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        if not aqua_mode:
            sys.stdout.write(ENABLE_MOUSE)
            sys.stdout.flush()

        fd = sys.stdin.fileno()

        try:
            while True:
                # --- INPUT ---
                ready, _, _ = select.select([fd], [], [], FRAME_TIMEOUT)
                raw = b''
                if ready:
                    while select.select([fd], [], [], 0)[0]:
                        raw += os.read(fd, 1024)

                raw_str = raw.decode('utf-8', errors='ignore')
                plain = re.sub(r'\033\[<[^Mm]*[Mm]', '', raw_str)
                plain = re.sub(r'\033\[[^a-zA-Z]*[a-zA-Z]', '', plain)

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

                # NPC spawn
                if now - last_npc_spawn >= NPC_SPAWN_INTERVAL and len(npc_fish) < MAX_NPC:
                    last_npc_spawn = now
                    npc_fish.append(NPCFish.spawn(term.width, sea.floor_y, now))

                # NPC update + eat
                new_npc = []
                for f in npc_fish:
                    if not f.update(now, player, aqua_mode, sea.floor_y, term.width):
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

                # Score popups
                for p in score_popups:
                    output += p.draw(term, now)

                # Sea floor front layer
                output += sea.draw(term, now, 'front')

                print(output, end='', flush=True)

        finally:
            if not aqua_mode:
                sys.stdout.write(DISABLE_MOUSE)
                sys.stdout.flush()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='TermFrenzy - terminal Feeding Frenzy game')
    parser.add_argument('--aqua', action='store_true', help='Aquarium mode: no player, just watch the fish')
    args = parser.parse_args()
    main(aqua_mode=args.aqua)
