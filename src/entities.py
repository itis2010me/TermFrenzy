import math
import random
import time

from fish_sprites import PLAYER_SIZES, NPC_SPRITES
from config import (
    BUBBLE_SPAWN_CHANCE, BUBBLE_POP_DURATION,
    BUBBLE_RISE_IV_RANGE, BUBBLE_WOBBLE_IV_RANGE,
    NPC_SPEED_RANGE, NPC_BOB_AMP_RANGE, NPC_BOB_SPEED_RANGE,
    FLEE_RADIUS, FLEE_SPEED_MULT,
    GROWTH_THRESHOLDS, CAN_EAT,
    NPC_LEVELS, NPC_POINTS,
    POPUP_DRIFT_SPEED, POPUP_LIFETIME, POPUP_FADE_TIME, POPUP_VANISH_TIME,
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
        self._update_sprite()
        self.draw_x = self.px
        self.draw_y = self.py

    def _update_sprite(self):
        direction = "right" if self.facing_right else "left"
        self.sprite = PLAYER_SIZES[self.size][direction]
        self.fish_w = len(self.sprite[0])
        self.fish_h = len(self.sprite)

    def update(self, mouse_x, mouse_y, term_width, term_height):
        if self.dropping:
            elapsed = time.monotonic() - self.drop_start
            if elapsed >= self.DROP_DURATION:
                self.dropping = False
                self.py = self.target_y
            else:
                t = elapsed / self.DROP_DURATION
                # ease-out: decelerate as it lands
                t = 1 - (1 - t) ** 2
                self.py = int(1 + (self.target_y - 1) * t)
        else:
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
        output = ''
        for i, row in enumerate(self.sprite):
            output += term.move_xy(self.draw_x, self.draw_y + i) + row
        return output


class NPCFish:
    def __init__(self, sprite_r, sprite_l, going_right, start_x, y, speed,
                 bob_amp, bob_speed, bob_offset, born, layer, skittish, level):
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

    @classmethod
    def spawn(cls, term_width, floor_y, now):
        sprite_idx = random.randrange(len(NPC_SPRITES))
        sprite_r, sprite_l = NPC_SPRITES[sprite_idx]
        level = NPC_LEVELS[sprite_idx]
        going_right = random.choice([True, False])
        start_x = -len(sprite_r) if going_right else term_width
        skittish = len(sprite_r) <= 3
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
        )

    def update(self, now, player, aqua_mode, floor_y, term_width):
        dt = now - self.last_update
        self.last_update = now

        if self.skittish and not aqua_mode and player is not None:
            fish_cx = player.draw_x + player.fish_w // 2
            fish_cy = player.draw_y + player.fish_h // 2
            fx = self.x + len(self.sprite_r) / 2
            fy = self.y
            ddx = fx - fish_cx
            ddy = fy - fish_cy
            dist = math.sqrt(ddx * ddx + ddy * ddy)

            if dist < FLEE_RADIUS and dist > 0:
                flee_speed = self.speed * FLEE_SPEED_MULT
                self.x += (ddx / dist) * flee_speed * dt
                self.y += (ddy / dist) * flee_speed * dt
                self.y = max(2, min(self.y, floor_y - 3))
                self.going_right = ddx > 0
            else:
                if self.going_right:
                    self.x += self.speed * dt
                else:
                    self.x -= self.speed * dt
        elif self.skittish:
            if self.going_right:
                self.x += self.speed * dt
            else:
                self.x -= self.speed * dt
        else:
            elapsed = now - self.born
            if self.going_right:
                self.x = self.start_x + self.speed * elapsed
            else:
                self.x = self.start_x - self.speed * elapsed

        # Off screen?
        if self.x > term_width + 5 or self.x < -10:
            return False

        # Bob
        self.draw_y = self.y + math.sin(now * self.bob_speed + self.bob_offset) * self.bob_amp
        return True

    def check_eat_collision(self, player):
        sprite = self.sprite_r if self.going_right else self.sprite_l
        fx = int(self.x)
        fy = int(self.draw_y)
        npc_w = len(sprite)
        if (fx < player.draw_x + player.fish_w and fx + npc_w > player.draw_x and
                fy >= player.draw_y and fy < player.draw_y + player.fish_h):
            if self.level in CAN_EAT.get(player.size, set()):
                return NPC_POINTS[self.level]
        return None

    def draw(self, term):
        sprite = self.sprite_r if self.going_right else self.sprite_l
        fx = int(self.x)
        fy = int(self.draw_y)
        output = ''
        if 1 <= fy < term.height - 1:
            for i, ch in enumerate(sprite):
                cx = fx + i
                if 1 <= cx < term.width - 1:
                    output += term.move_xy(cx, fy) + ch
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

    def draw(self, term, now):
        output = ''
        bx, by = self.x, self.y

        if self.popping:
            elapsed = now - self.pop_start
            if elapsed < 0.1:
                if 1 <= bx < term.width - 1 and 1 <= by < term.height - 1:
                    output += term.move_xy(bx, by) + '*'
            elif elapsed < 0.25:
                for dx, dy, ch in [(-1,0,'-'), (1,0,'-'), (0,-1,'|'), (0,1,'|'),
                                    (-1,-1,'\''), (1,-1,'\''), (-1,1,'.'), (1,1,'.')]:
                    sx, sy = bx + dx, by + dy
                    if 1 <= sx < term.width - 1 and 1 <= sy < term.height - 1:
                        output += term.move_xy(sx, sy) + ch
            elif elapsed < 0.4:
                for dx, dy in [(-2,0), (2,0), (0,-1), (0,1)]:
                    sx, sy = bx + dx, by + dy
                    if 1 <= sx < term.width - 1 and 1 <= sy < term.height - 1:
                        output += term.move_xy(sx, sy) + '\u00b7'
        else:
            if self.age < 0.6:
                ch = '.'
            elif self.age < 1.5:
                ch = 'o'
            else:
                ch = 'O'
            if 1 <= bx < term.width - 1 and 1 <= by < term.height - 1:
                output += term.move_xy(bx, by) + ch

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
