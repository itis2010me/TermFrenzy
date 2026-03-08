import math
import random

from config import (
    SAND_CHARS, SEAWEED_SPACING_RANGE, SEAWEED_STYLES,
    ROCK_SPACING_RANGE, ROCK_STYLES,
    SEAWEED_SWAY_SPEED, SEAWEED_SWAY_AMP, SEAWEED_ANIM_SPEED,
)


class SeaFloor:
    def __init__(self, term_width, term_height):
        self.floor_y = term_height - 2

        # Sand row
        self.sand_row = ''
        for x in range(1, term_width - 1):
            self.sand_row += random.choice(SAND_CHARS)

        # Seaweed: list of (x, height, sway_offset, style, layer)
        self.seaweeds = []
        for x in range(3, term_width - 3, random.randint(*SEAWEED_SPACING_RANGE)):
            x += random.randint(-2, 2)
            h = random.randint(2, 5)
            style = random.choice(SEAWEED_STYLES)
            self.seaweeds.append((x, h, random.random() * 10, style, random.choice(['back', 'front'])))

        # Rocks: list of (x, style, layer)
        self.rocks = []
        for x in range(5, term_width - 5, random.randint(*ROCK_SPACING_RANGE)):
            x += random.randint(-3, 3)
            style = random.choice(ROCK_STYLES)
            self.rocks.append((x, style, random.choice(['back', 'front'])))

    def draw(self, term, now, layer):
        output = ''

        # Sand (only on back layer to avoid double-drawing)
        if layer == 'back':
            output += term.move_xy(1, self.floor_y) + self.sand_row

        # Seaweed
        for sx, sh, soff, sw_style, sw_layer in self.seaweeds:
            if sw_layer != layer:
                continue
            for j in range(sh):
                sway = int(math.sin(now * SEAWEED_SWAY_SPEED + soff + j * 0.5) * SEAWEED_SWAY_AMP)
                draw_sx = sx + sway
                draw_sy = self.floor_y - 1 - j
                if 1 <= draw_sx < term.width - 1 and 1 <= draw_sy < term.height - 1:
                    leaf = sw_style[0] if (j + int(now * SEAWEED_ANIM_SPEED)) % 2 == 0 else sw_style[1]
                    output += term.move_xy(draw_sx, draw_sy) + leaf

        # Rocks
        for rx, rstyle, rlayer in self.rocks:
            if rlayer != layer:
                continue
            if rstyle == 'small':
                if 1 <= rx < term.width - 2:
                    output += term.move_xy(rx, self.floor_y - 1) + '/\\'
            else:
                if 1 <= rx < term.width - 3:
                    output += term.move_xy(rx, self.floor_y - 1) + '/~~\\'
                    output += term.move_xy(rx - 1, self.floor_y - 2) + '/    \\'

        return output
