import math
import random
import time

from fish_sprites import PLAYER_SIZES, NPC_SPRITES, SHARK_SPRITE_RIGHT, SHARK_SPRITE_LEFT, JELLYFISH_FRAMES
from config import (
    BUBBLE_SPAWN_CHANCE, BUBBLE_POP_DURATION,
    BUBBLE_RISE_IV_RANGE, BUBBLE_WOBBLE_IV_RANGE,
    NPC_SPEED_RANGE, NPC_BOB_AMP_RANGE, NPC_BOB_SPEED_RANGE,
    FLEE_RADIUS, FLEE_SPEED_MULT,
    GROWTH_THRESHOLDS, CAN_EAT,
    NPC_LEVELS, NPC_POINTS, NPC_SPAWN_WEIGHTS,
    POPUP_DRIFT_SPEED, POPUP_LIFETIME, POPUP_FADE_TIME, POPUP_VANISH_TIME,
    SHARK_SPEED_RANGE, SHARK_POINTS, SHARK_CHASE_SPEED, SHARK_MAX_TURNS,
    SHARK_WARNING_DURATION, SHARK_AGGRO_RADIUS,
    NPC_FLEE_RADIUS,
    JELLY_RISE_SPEED, JELLY_DRIFT_SPEED, JELLY_ANIM_SPEED,
    JELLY_STING_DURATION, JELLY_STING_SPEED, JELLY_STING_FLASH,
    GOLD_FISH_SPEED_RANGE, GOLD_FRENZY_DURATION, GOLD_FRENZY_COLOR,
    GOLD_FRENZY_POINT_MULT,
    GOLD_SPARKLE_CHARS, GOLD_SPARKLE_RISE_SPEED, GOLD_SPARKLE_DRIFT_RANGE,
    GOLD_SPARKLE_LIFETIME,
)


class Player:
    DROP_DURATION = 1.0

    def __init__(self, term_width, term_height):
        self.px = term_width // 2
        self.target_y = term_height // 2
        self.py = 1  # start at top
        self.facing_right = True
        self.size = "small"
        self.score = 0
        self.drop_start = time.monotonic()
        self.dropping = True
        self.stung_until = 0.0
        self.sting_start = 0.0
        self.gold_frenzy_until = 0.0
        self._update_sprite()
        self.draw_x = self.px
        self.draw_y = self.py

    def _update_sprite(self):
        direction = "right" if self.facing_right else "left"
        self.sprite = PLAYER_SIZES[self.size][direction]
        self.fish_w = len(self.sprite[0])
        self.fish_h = len(self.sprite)

    def apply_sting(self, now):
        self.stung_until = now + JELLY_STING_DURATION
        self.sting_start = now

    def is_stung(self, now):
        return now < self.stung_until

    def activate_gold_frenzy(self, now):
        self.gold_frenzy_until = now + GOLD_FRENZY_DURATION

    def is_gold_frenzy(self, now):
        return now < self.gold_frenzy_until

    def update(self, mouse_x, mouse_y, term_width, term_height):
        now = time.monotonic()
        stung = self.is_stung(now)
        if self.dropping:
            elapsed = now - self.drop_start
            if elapsed >= self.DROP_DURATION:
                self.dropping = False
                self.py = self.target_y
            else:
                t = elapsed / self.DROP_DURATION
                # ease-out: decelerate as it lands
                t = 1 - (1 - t) ** 2
                self.py = int(1 + (self.target_y - 1) * t)
        elif not stung or random.random() < JELLY_STING_SPEED:
            if mouse_x is not None and mouse_y is not None:
                fish_cx = self.px + self.fish_w // 2
                fish_cy = self.py + self.fish_h // 2
                dx = mouse_x - fish_cx
                dy = mouse_y - fish_cy
                if abs(dx) > 1:
                    self.px += 1 if dx > 0 else -1
                    self.facing_right = dx > 0
                if abs(dy) > 1:
                    self.py += 1 if dy > 0 else -1

        self._update_sprite()
        self.draw_x = max(1, min(self.px, term_width - self.fish_w - 1))
        self.draw_y = max(1, min(self.py, term_height - self.fish_h - 1))

    def check_growth(self):
        threshold = GROWTH_THRESHOLDS.get(self.size)
        if threshold is not None and self.score >= threshold:
            if self.size == "small":
                self.size = "medium"
            elif self.size == "medium":
                self.size = "big"
            self._update_sprite()

    def draw(self, term):
        now = time.monotonic()
        flashing = now - self.sting_start < JELLY_STING_FLASH
        gold_active = self.is_gold_frenzy(now)
        output = ''
        for i, row in enumerate(self.sprite):
            if flashing and int(now / 0.05) % 2 == 0:
                row = ''.join('~' if ch not in ' ' else ' ' for ch in row)
            rendered = term.move_xy(self.draw_x, self.draw_y + i)
            if gold_active:
                rendered += term.yellow(row)
            else:
                rendered += row
            output += rendered
        return output


class NPCFish:
    SMALL_COLORS = ['orange', 'blue']

    def __init__(self, sprite_r, sprite_l, going_right, start_x, y, speed,
                 bob_amp, bob_speed, bob_offset, born, layer, skittish, level,
                 color_name=None, is_gold=False):
        self.x = float(start_x)
        self.start_x = float(start_x)
        self.y = y
        self.draw_y = float(y)
        self.sprite_r = sprite_r
        self.sprite_l = sprite_l
        self.going_right = going_right
        self.speed = speed
        self.bob_amp = bob_amp
        self.bob_speed = bob_speed
        self.bob_offset = bob_offset
        self.born = born
        self.layer = layer
        self.skittish = skittish
        self.last_update = born
        self.level = level
        self.stung_until = 0.0
        self.color_name = color_name
        self.is_gold = is_gold

    @classmethod
    def spawn(cls, term_width, floor_y, now):
        sprite_idx = random.choices(range(len(NPC_SPRITES)), weights=NPC_SPAWN_WEIGHTS, k=1)[0]
        sprite_r, sprite_l = NPC_SPRITES[sprite_idx]
        level = NPC_LEVELS[sprite_idx]
        going_right = random.choice([True, False])
        start_x = -len(sprite_r) if going_right else term_width
        skittish = len(sprite_r) <= 3
        color_name = random.choice(cls.SMALL_COLORS) if level == 0 else 'bright_magenta'
        return cls(
            sprite_r=sprite_r,
            sprite_l=sprite_l,
            going_right=going_right,
            start_x=start_x,
            y=random.randint(2, floor_y - 3),
            speed=random.uniform(*NPC_SPEED_RANGE),
            bob_amp=random.uniform(*NPC_BOB_AMP_RANGE),
            bob_speed=random.uniform(*NPC_BOB_SPEED_RANGE),
            bob_offset=random.random() * 6.28,
            born=now,
            layer=random.choice(['back', 'front']),
            skittish=skittish,
            level=level,
            color_name=color_name,
        )

    @classmethod
    def spawn_gold(cls, term_width, floor_y, now):
        sprite_idx = random.choice([0, 1, 2])  # always small
        sprite_r, sprite_l = NPC_SPRITES[sprite_idx]
        going_right = random.choice([True, False])
        start_x = -len(sprite_r) if going_right else term_width
        return cls(
            sprite_r=sprite_r,
            sprite_l=sprite_l,
            going_right=going_right,
            start_x=start_x,
            y=random.randint(2, floor_y - 3),
            speed=random.uniform(*GOLD_FISH_SPEED_RANGE),
            bob_amp=random.uniform(*NPC_BOB_AMP_RANGE),
            bob_speed=random.uniform(*NPC_BOB_SPEED_RANGE),
            bob_offset=random.random() * 6.28,
            born=now,
            layer='front',
            skittish=False,
            level=0,
            color_name=GOLD_FRENZY_COLOR,
            is_gold=True,
        )

    def _find_nearest_threat(self, player, aqua_mode, npc_fish, sharks):
        if self.is_gold:
            return None, None, float('inf')
        fx = self.x + len(self.sprite_r) / 2
        fy = self.y
        best_dist = float('inf')
        threat_x = None
        threat_y = None

        # Flee from player (if player can eat this fish)
        if not aqua_mode and player is not None:
            if self.level in CAN_EAT.get(player.size, set()):
                px = player.draw_x + player.fish_w / 2
                py = player.draw_y + player.fish_h / 2
                dist = math.sqrt((fx - px) ** 2 + (fy - py) ** 2)
                if dist < NPC_FLEE_RADIUS.get(self.level, 10) and dist < best_dist:
                    best_dist = dist
                    threat_x = px
                    threat_y = py

        # Flee from active sharks
        for s in sharks:
            if not s.active:
                continue
            sx = s.x + s.fish_w / 2
            sy = s.draw_y + s.fish_h / 2
            dist = math.sqrt((fx - sx) ** 2 + (fy - sy) ** 2)
            if dist < NPC_FLEE_RADIUS.get(self.level, 10) and dist < best_dist:
                best_dist = dist
                threat_x = sx
                threat_y = sy

        return threat_x, threat_y, best_dist

    def update(self, now, player, aqua_mode, floor_y, term_width, npc_fish=(), sharks=()):
        dt = now - self.last_update
        self.last_update = now

        stung = now < self.stung_until
        speed = self.speed * JELLY_STING_SPEED if stung else self.speed

        threat_x, threat_y, threat_dist = self._find_nearest_threat(
            player, aqua_mode, npc_fish, sharks)

        if threat_x is not None and threat_dist > 0:
            fx = self.x + len(self.sprite_r) / 2
            fy = self.y
            ddx = fx - threat_x
            ddy = fy - threat_y
            dist = threat_dist
            flee_speed = speed * FLEE_SPEED_MULT
            self.x += (ddx / dist) * flee_speed * dt
            self.y += (ddy / dist) * flee_speed * dt
            sprite_w = len(self.sprite_r)
            self.x = max(-sprite_w + 1, min(self.x, term_width - 1))
            self.y = max(2, min(self.y, floor_y - 3))
            new_right = ddx > 0
            if new_right != self.going_right:
                self.start_x = self.x
                self.born = now
                self.going_right = new_right
        elif self.skittish:
            if self.going_right:
                self.x += speed * dt
            else:
                self.x -= speed * dt
        else:
            elapsed = now - self.born
            if stung:
                if self.going_right:
                    self.x += speed * dt
                else:
                    self.x -= speed * dt
            elif self.going_right:
                self.x = self.start_x + speed * elapsed
            else:
                self.x = self.start_x - speed * elapsed

        # Off screen?
        if self.x > term_width + 5 or self.x < -10:
            return False

        # Bob
        self.draw_y = self.y + math.sin(now * self.bob_speed + self.bob_offset) * self.bob_amp
        return True

    def check_eat_collision(self, player, gold_frenzy=False):
        sprite = self.sprite_r if self.going_right else self.sprite_l
        fx = int(self.x)
        fy = int(self.draw_y)
        npc_w = len(sprite)
        if (fx < player.draw_x + player.fish_w and fx + npc_w > player.draw_x and
                fy >= player.draw_y and fy < player.draw_y + player.fish_h):
            if gold_frenzy or self.is_gold or self.level in CAN_EAT.get(player.size, set()):
                pts = NPC_POINTS[self.level]
                if gold_frenzy and not self.is_gold:
                    pts *= GOLD_FRENZY_POINT_MULT
                return pts
        return None

    def draw(self, term, gold_frenzy=False):
        sprite = self.sprite_r if self.going_right else self.sprite_l
        if gold_frenzy or self.is_gold:
            now = time.monotonic()
            fish_color = term.bold_yellow if int(now * 4) % 2 == 0 else term.yellow
        elif self.color_name:
            fish_color = getattr(term, self.color_name)
        else:
            fish_color = None
        fx = int(self.x)
        fy = int(self.draw_y)
        output = ''
        if 1 <= fy < term.height - 1:
            for i, ch in enumerate(sprite):
                cx = fx + i
                if 1 <= cx < term.width - 1:
                    output += term.move_xy(cx, fy) + (fish_color(ch) if fish_color else ch)
        return output


class Bubble:
    def __init__(self, x, y, rise_iv, wobble_iv, now):
        self.x = x
        self.y = y
        self.age = 0.0
        self.popping = False
        self.pop_start = 0.0
        self.rise_iv = rise_iv
        self.wobble_iv = wobble_iv
        self.next_rise = now + rise_iv
        self.next_wobble = now + wobble_iv
        self.born = now

    @classmethod
    def maybe_spawn(cls, now, term_width, term_height):
        if random.random() < BUBBLE_SPAWN_CHANCE:
            bx = random.randint(2, term_width - 3)
            by = random.randint(term_height // 2, term_height - 2)
            rise_iv = random.uniform(*BUBBLE_RISE_IV_RANGE)
            wobble_iv = random.uniform(*BUBBLE_WOBBLE_IV_RANGE)
            return cls(bx, by, rise_iv, wobble_iv, now)
        return None

    def update(self, now, term_width, player, npc_fish, aqua_mode):
        if self.popping:
            return now - self.pop_start < BUBBLE_POP_DURATION

        self.age = now - self.born

        if now >= self.next_rise:
            self.y -= 1
            self.next_rise = now + self.rise_iv

        if now >= self.next_wobble:
            self.x += random.choice([-1, 1])
            self.x = max(1, min(self.x, term_width - 2))
            self.next_wobble = now + self.wobble_iv

        if self.y <= 1:
            self.popping = True
            self.pop_start = now
            return True

        # Collision with player
        if not aqua_mode and player is not None:
            if (player.draw_x <= self.x < player.draw_x + player.fish_w and
                    player.draw_y <= self.y < player.draw_y + player.fish_h):
                if random.random() < 0.5:
                    self.popping = True
                    self.pop_start = now
                    return True

        # Collision with NPC fish
        for f in npc_fish:
            sprite = f.sprite_r if f.going_right else f.sprite_l
            fx = int(f.x)
            fy = int(f.draw_y)
            if fx <= self.x < fx + len(sprite) and fy == self.y:
                if random.random() < 0.5:
                    self.popping = True
                    self.pop_start = now
                break

        return True

    def draw(self, term, now, gold_frenzy=False):
        output = ''
        bx, by = self.x, self.y

        if gold_frenzy:
            # Render as gold sparkle instead of bubble
            sparkle_color = term.bold_yellow if int(now * 4) % 2 == 0 else term.yellow
            sparkle_chars = GOLD_SPARKLE_CHARS
            ch = sparkle_chars[int(now * 3 + bx) % len(sparkle_chars)]
            if self.popping:
                elapsed = now - self.pop_start
                if elapsed < 0.15:
                    for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                        sx, sy = bx + dx, by + dy
                        if 1 <= sx < term.width - 1 and 1 <= sy < term.height - 1:
                            output += term.move_xy(sx, sy) + sparkle_color(random.choice(sparkle_chars))
                elif elapsed < 0.3:
                    if 1 <= bx < term.width - 1 and 1 <= by < term.height - 1:
                        output += term.move_xy(bx, by) + sparkle_color('·')
            else:
                if 1 <= bx < term.width - 1 and 1 <= by < term.height - 1:
                    output += term.move_xy(bx, by) + sparkle_color(ch)
            return output

        bubble_color = term.blue
        pop_color = term.bright_blue

        if self.popping:
            elapsed = now - self.pop_start
            if elapsed < 0.1:
                if 1 <= bx < term.width - 1 and 1 <= by < term.height - 1:
                    output += term.move_xy(bx, by) + pop_color('*')
            elif elapsed < 0.25:
                for dx, dy, ch in [(-1,0,'-'), (1,0,'-'), (0,-1,'|'), (0,1,'|'),
                                    (-1,-1,'\''), (1,-1,'\''), (-1,1,'.'), (1,1,'.')]:
                    sx, sy = bx + dx, by + dy
                    if 1 <= sx < term.width - 1 and 1 <= sy < term.height - 1:
                        output += term.move_xy(sx, sy) + pop_color(ch)
            elif elapsed < 0.4:
                for dx, dy in [(-2,0), (2,0), (0,-1), (0,1)]:
                    sx, sy = bx + dx, by + dy
                    if 1 <= sx < term.width - 1 and 1 <= sy < term.height - 1:
                        output += term.move_xy(sx, sy) + pop_color('\u00b7')
        else:
            if self.age < 0.6:
                ch = '.'
            elif self.age < 1.5:
                ch = 'o'
            else:
                ch = 'O'
            if 1 <= bx < term.width - 1 and 1 <= by < term.height - 1:
                output += term.move_xy(bx, by) + bubble_color(ch)

        return output


class ScorePopup:
    def __init__(self, x, y, text, born):
        self.x = x
        self.y = float(y)
        self.text = text
        self.born = born

    def update(self, now):
        age = now - self.born
        if age >= POPUP_LIFETIME:
            return False
        self.y -= POPUP_DRIFT_SPEED
        return True

    def draw(self, term, now):
        age = now - self.born
        if age < POPUP_FADE_TIME:
            text = self.text
        elif age < POPUP_VANISH_TIME:
            text = '.'
        else:
            text = ''
        ppx = int(self.x)
        ppy = int(self.y)
        if text and 1 <= ppx < term.width - len(text) and 1 <= ppy < term.height - 1:
            return term.move_xy(ppx, ppy) + text
        return ''


class Shark:
    WARNING_LINES = ['/!\\', '---']

    def __init__(self, going_right, start_x, y, speed, born, term_width):
        self.going_right = going_right
        self.preferred_right = going_right
        self.x = float(start_x)
        self.y = float(y)
        self.speed = speed
        self.born = born
        self.warning_until = born + SHARK_WARNING_DURATION
        self.active = False
        self.active_since = 0.0
        self.last_update = born
        self.sprite_r = SHARK_SPRITE_RIGHT
        self.sprite_l = SHARK_SPRITE_LEFT
        self.fish_w = max(len(row) for row in self.sprite_r)
        self.fish_h = len(self.sprite_r)
        self.draw_y = float(y)
        self.turns_remaining = SHARK_MAX_TURNS
        # Warning sign position
        self.warning_y = int(y) + self.fish_h // 2
        if going_right:
            self.warning_x = 2
        else:
            self.warning_x = term_width - 5

    @classmethod
    def spawn(cls, term_width, floor_y, now):
        going_right = random.choice([True, False])
        speed = random.uniform(*SHARK_SPEED_RANGE)
        sprite_h = len(SHARK_SPRITE_RIGHT)
        y = random.randint(2, max(3, floor_y - sprite_h - 1))
        sprite_w = max(len(row) for row in SHARK_SPRITE_RIGHT)
        start_x = -sprite_w if going_right else term_width
        return cls(going_right, start_x, y, speed, now, term_width)

    def _find_nearest_target(self, npc_fish, player):
        best_dist = float('inf')
        target_x = None
        target_y = None
        shark_cx = self.x + self.fish_w / 2
        shark_cy = self.y + self.fish_h / 2
        for f in npc_fish:
            fx = f.x + len(f.sprite_r) / 2
            fy = f.draw_y
            dist = abs(fx - shark_cx) + abs(fy - shark_cy)
            if dist < best_dist:
                best_dist = dist
                target_x = fx
                target_y = fy
        if player is not None and player.size != "big":
            px = player.draw_x + player.fish_w / 2
            py = player.draw_y + player.fish_h / 2
            dist = abs(px - shark_cx) + abs(py - shark_cy)
            if dist < best_dist:
                best_dist = dist
                target_x = px
                target_y = py
        if best_dist > SHARK_AGGRO_RADIUS:
            return None, None
        return target_x, target_y

    def update(self, now, term_width, floor_y, npc_fish, player):
        if not self.active:
            if now >= self.warning_until:
                self.active = True
                self.active_since = now
                self.last_update = now
            return True

        dt = now - self.last_update
        self.last_update = now

        # Only chase after being active for 2 seconds
        chasing = now - self.active_since >= 2.0
        target_x, target_y = self._find_nearest_target(npc_fish, player) if chasing else (None, None)

        # Turn around to chase target (up to max turns), or revert to preferred direction
        if self.turns_remaining > 0 and target_x is not None:
            shark_cx = self.x + self.fish_w / 2
            target_is_right = target_x > shark_cx
            if target_is_right != self.going_right:
                self.going_right = target_is_right
                self.turns_remaining -= 1
        elif self.going_right != self.preferred_right:
            self.going_right = self.preferred_right

        # Horizontal: constant speed in facing direction
        if self.going_right:
            self.x += self.speed * dt
        else:
            self.x -= self.speed * dt

        # Vertical: chase nearest target
        if target_y is not None:
            shark_cy = self.y + self.fish_h / 2
            dy = target_y - shark_cy
            if abs(dy) > 0.5:
                self.y += SHARK_CHASE_SPEED * dt * (1 if dy > 0 else -1)
                self.y = max(2, min(self.y, floor_y - self.fish_h - 1))

        self.draw_y = self.y

        if self.x > term_width + 10 or self.x < -(self.fish_w + 10):
            return False
        return True

    def check_npc_collision(self, npc):
        if not self.active:
            return False
        sx = int(self.x)
        sy = int(self.draw_y)
        npc_sprite = npc.sprite_r if npc.going_right else npc.sprite_l
        fx = int(npc.x)
        fy = int(npc.draw_y)
        npc_w = len(npc_sprite)
        return (sx < fx + npc_w and sx + self.fish_w > fx and
                sy < fy + 1 and sy + self.fish_h > fy)

    def _mouth_hitbox(self):
        """Return (x, w) for the front half of the shark (the mouth)."""
        half_w = self.fish_w // 2
        if self.going_right:
            return int(self.x) + half_w, half_w
        else:
            return int(self.x), half_w

    def check_player_collision(self, player):
        if not self.active:
            return None
        mouth_x, mouth_w = self._mouth_hitbox()
        sy = int(self.draw_y)
        if not (mouth_x < player.draw_x + player.fish_w and mouth_x + mouth_w > player.draw_x and
                sy < player.draw_y + player.fish_h and sy + self.fish_h > player.draw_y):
            return None
        if player.size == "big":
            return 'killed'
        return 'eaten'

    def draw(self, term, now, gold_frenzy=False):
        if gold_frenzy:
            shark_color = term.bold_yellow if int(now * 4) % 2 == 0 else term.yellow
        else:
            shark_color = term.color_rgb(100, 100, 100)
        warning_color = term.bright_red
        output = ''
        if not self.active:
            # Flashing warning sign
            if int(now / 0.3) % 2 == 0:
                for i, line in enumerate(self.WARNING_LINES):
                    dy = self.warning_y - 1 + i
                    wx = self.warning_x
                    if 1 <= dy < term.height - 1 and 1 <= wx < term.width - len(line):
                        output += term.move_xy(wx, dy) + warning_color(line)
            return output

        sprite = self.sprite_r if self.going_right else self.sprite_l
        sx = int(self.x)
        sy = int(self.draw_y)
        for i, row in enumerate(sprite):
            dy = sy + i
            if 1 <= dy < term.height - 1:
                for j, ch in enumerate(row):
                    cx = sx + j
                    if ch != ' ' and 1 <= cx < term.width - 1:
                        output += term.move_xy(cx, dy) + shark_color(ch)
        return output


class Jellyfish:
    def __init__(self, x, y, drift_dir, born):
        self.x = float(x)
        self.y = float(y)
        self.drift_dir = drift_dir  # -1 or 1
        self.born = born
        self.last_update = born
        self.frames = JELLYFISH_FRAMES
        self.fish_w = max(len(row) for row in self.frames[0])
        self.fish_h = len(self.frames[0])
        self.draw_y = float(y)

    @classmethod
    def spawn(cls, term_width, floor_y, now):
        w = max(len(row) for row in JELLYFISH_FRAMES[0])
        x = random.randint(2, term_width - w - 2)
        y = floor_y - len(JELLYFISH_FRAMES[0]) - 1
        drift_dir = random.choice([-1, 1])
        return cls(x, y, drift_dir, now)

    def update(self, now, term_width):
        dt = now - self.last_update
        self.last_update = now

        self.y -= JELLY_RISE_SPEED * dt
        self.x += self.drift_dir * JELLY_DRIFT_SPEED * dt

        # Bounce off walls
        if self.x <= 1:
            self.drift_dir = 1
        elif self.x + self.fish_w >= term_width - 1:
            self.drift_dir = -1

        self.draw_y = self.y

        # Off top of screen
        if self.y < -(self.fish_h + 2):
            return False
        return True

    def check_player_collision(self, player, now):
        jx = int(self.x)
        jy = int(self.draw_y)
        if (jx < player.draw_x + player.fish_w and jx + self.fish_w > player.draw_x and
                jy < player.draw_y + player.fish_h and jy + self.fish_h > player.draw_y):
            if not player.is_stung(now):
                player.apply_sting(now)
                return True
        return False

    def check_npc_collision(self, npc, now):
        jx = int(self.x)
        jy = int(self.draw_y)
        sprite = npc.sprite_r if npc.going_right else npc.sprite_l
        fx = int(npc.x)
        fy = int(npc.draw_y)
        npc_w = len(sprite)
        if (jx < fx + npc_w and jx + self.fish_w > fx and
                jy < fy + 1 and jy + self.fish_h > fy):
            if now >= npc.stung_until:
                npc.stung_until = now + JELLY_STING_DURATION
                return True
        return False

    def draw(self, term, now, gold_frenzy=False):
        frame_idx = int(now * JELLY_ANIM_SPEED) % len(self.frames)
        sprite = self.frames[frame_idx]
        jelly_color = term.yellow if gold_frenzy else None
        sx = int(self.x)
        sy = int(self.draw_y)
        output = ''
        for i, row in enumerate(sprite):
            dy = sy + i
            if 1 <= dy < term.height - 1:
                for j, ch in enumerate(row):
                    cx = sx + j
                    if ch != ' ' and 1 <= cx < term.width - 1:
                        output += term.move_xy(cx, dy) + (jelly_color(ch) if jelly_color else ch)
        return output


class GoldSparkle:
    TRAIL_MAX = 5

    def __init__(self, x, y, now, is_trail=False):
        self.x = float(x)
        self.y = float(y)
        self.born = now
        self.last_update = now
        self.ch = random.choice(GOLD_SPARKLE_CHARS)
        self.drift = random.uniform(*GOLD_SPARKLE_DRIFT_RANGE)
        self.is_trail = is_trail

    @classmethod
    def maybe_spawn(cls, now, term_width, term_height):
        x = random.randint(2, term_width - 3)
        y = random.randint(2, term_height - 3)
        return cls(x, y, now)

    @classmethod
    def maybe_spawn_at(cls, x, y, now):
        return cls(x, y, now, is_trail=True)

    TRAIL_LIFETIME = 0.5

    def update(self, now):
        dt = now - self.last_update
        self.last_update = now
        lifetime = self.TRAIL_LIFETIME if self.is_trail else GOLD_SPARKLE_LIFETIME
        if not self.is_trail:
            self.y -= GOLD_SPARKLE_RISE_SPEED * dt
            self.x += self.drift * dt
        if now - self.born >= lifetime:
            return False
        return True

    def draw(self, term, now):
        age = now - self.born
        lifetime = self.TRAIL_LIFETIME if self.is_trail else GOLD_SPARKLE_LIFETIME
        # Fade: bright at start, dim near end
        if age < lifetime * 0.6:
            color = term.bold_yellow
        else:
            color = term.yellow
        sx = int(self.x)
        sy = int(self.y)
        if 1 <= sx < term.width - 1 and 1 <= sy < term.height - 1:
            return term.move_xy(sx, sy) + color(self.ch)
        return ''
