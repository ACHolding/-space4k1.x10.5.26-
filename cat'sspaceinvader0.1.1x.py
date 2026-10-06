#!/usr/bin/env python3
"""Space4K - a Space Invaders tribute in one file, no asset files.

Every sprite is built from strings and every beep/boop is synthesized at
startup with math.sin square waves and noise. The loop is locked at 60 FPS and
all speeds are pixels (or frames) per 60 FPS frame.

Controls: Left/Right or A/D move, Space fire/start, P pause, F3 FPS, Esc quit.
"""
import math
import random
import sys
from array import array

import pygame

# --- constants ---------------------------------------------------------------

W, H = 224, 256          # original arcade logical resolution
SCALE = 3
FPS = 60
RATE = 22050

WHITE = (255, 255, 255)
GREEN = (32, 255, 32)
RED = (255, 40, 40)
BLACK = (0, 0, 0)
CLEAR = (0, 0, 0, 0)

HUD_BOTTOM = 32
UFO_Y = 40
SHIELD_Y = 192
PLAYER_Y = 216
GROUND_Y = 239
LEFT_EDGE, RIGHT_EDGE = 8, 216

PLAYER_SPEED = 1
SHOT_SPEED = 4
BOMB_SPEED = 2
MAX_BOMBS = 3
EXTRA_LIFE_AT = 1500
WAVE_TOPS = [64, 80, 88, 96, 104, 104, 104, 104]
POINTS = {"squid": 30, "crab": 20, "octopus": 10}
UFO_POINTS = (50, 100, 150, 300)

TITLE, PLAYING, OVER = "title", "playing", "over"

# --- sprites (X = pixel) -----------------------------------------------------

SPRITE_ROWS = {
    "squid": [
        ["...XX...",
         "..XXXX..",
         ".XXXXXX.",
         "XX.XX.XX",
         "XXXXXXXX",
         "..X..X..",
         ".X.XX.X.",
         "X.X..X.X"],
        ["...XX...",
         "..XXXX..",
         ".XXXXXX.",
         "XX.XX.XX",
         "XXXXXXXX",
         ".X.XX.X.",
         "X......X",
         ".X....X."],
    ],
    "crab": [
        ["..X.....X..",
         "...X...X...",
         "..XXXXXXX..",
         ".XX.XXX.XX.",
         "XXXXXXXXXXX",
         "X.XXXXXXX.X",
         "X.X.....X.X",
         "...XX.XX..."],
        ["..X.....X..",
         "X..X...X..X",
         "X.XXXXXXX.X",
         "XXX.XXX.XXX",
         "XXXXXXXXXXX",
         ".XXXXXXXXX.",
         "..X.....X..",
         ".X.......X."],
    ],
    "octopus": [
        ["....XXXX....",
         ".XXXXXXXXXX.",
         "XXXXXXXXXXXX",
         "XXX..XX..XXX",
         "XXXXXXXXXXXX",
         "...XX..XX...",
         "..XX.XX.XX..",
         "XX........XX"],
        ["....XXXX....",
         ".XXXXXXXXXX.",
         "XXXXXXXXXXXX",
         "XXX..XX..XXX",
         "XXXXXXXXXXXX",
         "..XXX..XXX..",
         ".XX..XX..XX.",
         "..XX....XX.."],
    ],
    "player": [
        ["......X......",
         ".....XXX.....",
         ".....XXX.....",
         ".XXXXXXXXXXX.",
         "XXXXXXXXXXXXX",
         "XXXXXXXXXXXXX",
         "XXXXXXXXXXXXX",
         "XXXXXXXXXXXXX"],
    ],
    "pdeath": [
        [".....X..........",
         "..........X.....",
         "...X.X.X........",
         ".....X.....X....",
         "..X.XXX.X.......",
         ".XXXXXXXX.X.....",
         "XXXXXXXXXXX..X..",
         "XXXXXXXXXXXXX..."],
        ["X.......X.......",
         "....X.......X...",
         "..X..X..X.......",
         "......X....X....",
         "X..XX.X.XX......",
         ".XXXXXXXX.X.X...",
         "XXXXXXXXXXXX....",
         "XXXXXXXXXXXXX..."],
    ],
    "ufo": [
        [".....XXXXXX.....",
         "...XXXXXXXXXX...",
         "..XXXXXXXXXXXX..",
         ".XX.XX.XX.XX.XX.",
         "XXXXXXXXXXXXXXXX",
         "..XXX..XX..XXX..",
         "...X........X..."],
    ],
    "boom": [
        ["....X...X....",
         ".X...X.X...X.",
         "..X.......X..",
         "...X.....X...",
         "XX.........XX",
         "...X.....X...",
         "..X..X.X..X..",
         ".X..X...X..X."],
    ],
    "shot_boom": [
        ["X...X..X",
         "..X...X.",
         ".XXXXXX.",
         "XXXXXXXX",
         ".XXXXXX.",
         "..X..X..",
         "X..X...X",
         "...X.X.."],
    ],
    "bomb_blast": [
        ["..X...",
         "X...X.",
         "..XX.X",
         ".XXXX.",
         "X.XXX.",
         ".XXXXX",
         "X.XXX.",
         ".X.X.X"],
    ],
    "zig": [
        ["X..", ".X.", "..X", ".X.", "X..", ".X.", "..X"],
        ["..X", ".X.", "X..", ".X.", "..X", ".X.", "X.."],
    ],
    "plunger": [
        [".X.", ".X.", ".X.", ".X.", ".X.", "XXX", ".X."],
        [".X.", "XXX", ".X.", ".X.", ".X.", ".X.", ".X."],
    ],
}


def shield_rows():
    rows = []
    for y in range(16):
        if y < 4:
            pad = 4 - y
            rows.append("." * pad + "X" * (22 - 2 * pad) + "." * pad)
        elif y < 12:
            rows.append("X" * 22)
        elif y == 12:
            rows.append("X" * 7 + "." * 8 + "X" * 7)
        else:
            rows.append("X" * 6 + "." * 10 + "X" * 6)
    return rows


SPRITE_ROWS["shield"] = [shield_rows()]


def make_sprite(rows, color=WHITE):
    surf = pygame.Surface((len(rows[0]), len(rows)), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c == "X":
                surf.set_at((x, y), color)
    return surf


def offsets(rows):
    """Pixel offsets of a pattern, centered on its middle (used to blast shields)."""
    w, h = len(rows[0]), len(rows)
    return [(x - w // 2, y - h // 2)
            for y, row in enumerate(rows) for x, c in enumerate(row) if c == "X"]


SPR = {}
SHOT_BLAST = offsets(SPRITE_ROWS["shot_boom"][0])
BOMB_BLAST = offsets(SPRITE_ROWS["bomb_blast"][0])


def build_sprites():
    for name, frames in SPRITE_ROWS.items():
        SPR[name] = [make_sprite(f) for f in frames]


# --- sound: math-made beeps n boops --------------------------------------------

class Sfx:
    def __init__(self):
        self.sounds = {}
        init = pygame.mixer.get_init()
        if not init:
            print("space4k: no audio device, running silent", file=sys.stderr)
            return
        self.rate, _, self.channels = init
        try:
            pygame.mixer.set_num_channels(16)
            self.build()
        except (pygame.error, ValueError) as e:
            print(f"space4k: sound disabled ({e})", file=sys.stderr)
            self.sounds = {}

    def env(self, i, n):
        attack = max(1, int(self.rate * 0.002))
        release = max(1, min(n // 3, int(self.rate * 0.015)))
        if i < attack:
            return i / attack
        if i > n - release:
            return (n - i) / release
        return 1.0

    def tone(self, freq, ms, wave="square", vol=0.3, slide=0.0,
             warble=0.0, warble_hz=0.0, fade=True):
        n = int(self.rate * ms / 1000)
        step = 2 * math.pi / self.rate
        out = array("h")
        phase = 0.0
        for i in range(n):
            f = freq + slide * i / n + warble * math.sin(warble_hz * i * step)
            phase += f * step
            s = math.sin(phase)
            if wave == "square":
                s = 1.0 if s >= 0 else -1.0
            out.append(int(32767 * vol * s * (self.env(i, n) if fade else 1.0)))
        return out

    def noise(self, ms, vol=0.3, hold=(1, 1)):
        """Sample-and-hold noise; a growing hold period makes it rumble down."""
        n = int(self.rate * ms / 1000)
        out = array("h")
        v, count = 0.0, 0
        for i in range(n):
            count -= 1
            if count <= 0:
                v = random.uniform(-1, 1)
                count = int(hold[0] + (hold[1] - hold[0]) * i / n)
            out.append(int(32767 * vol * v * (1 - i / n) ** 1.5))
        return out

    @staticmethod
    def mix(*tracks):
        out = array("h", [0]) * max(len(t) for t in tracks)
        for t in tracks:
            for i, s in enumerate(t):
                out[i] = max(-32767, min(32767, out[i] + s))
        return out

    def to_sound(self, samples):
        if self.channels > 1:
            wide = array("h")
            for s in samples:
                wide.extend((s,) * self.channels)
            samples = wide
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def build(self):
        made = {
            "shoot": self.tone(1400, 110, vol=0.16, slide=-1150),
            "inv_hit": self.noise(170, vol=0.32, hold=(2, 8)),
            "pdie": self.mix(self.noise(1000, vol=0.35, hold=(3, 24)),
                             self.tone(440, 1000, vol=0.12, slide=-380)),
            "ufo": self.tone(640, 250, vol=0.10, warble=220, warble_hz=8, fade=False),
            "ufo_hit": self.tone(220, 450, vol=0.18, slide=900, warble=120, warble_hz=24),
            "extra": sum((self.tone(f, 70, vol=0.2) for f in (523, 659, 784, 1047)), array("h")),
        }
        for i, f in enumerate((98, 87, 78, 73)):
            made[f"march{i}"] = self.tone(f, 90, vol=0.4)
        self.sounds = {name: self.to_sound(s) for name, s in made.items()}

    def play(self, name):
        s = self.sounds.get(name)
        if s:
            s.play()

    def loop(self, name):
        s = self.sounds.get(name)
        if s:
            s.play(loops=-1)

    def stop(self, name):
        s = self.sounds.get(name)
        if s:
            s.stop()


# --- game objects -----------------------------------------------------------------

class Invader:
    __slots__ = ("kind", "x", "y", "col", "frame", "alive", "w")

    def __init__(self, kind, x, y, col):
        self.kind, self.x, self.y, self.col = kind, x, y, col
        self.frame = 0
        self.alive = True
        self.w = SPR[kind][0].get_width()

    @property
    def rect(self):
        return pygame.Rect(self.x, self.y, self.w, 8)


class Bomb:
    __slots__ = ("x", "y", "kind", "frame")

    def __init__(self, x, y, kind):
        self.x, self.y, self.kind, self.frame = x, y, kind, 0


class Shield:
    def __init__(self, x):
        self.surf = make_sprite(SPRITE_ROWS["shield"][0], WHITE)
        self.rect = pygame.Rect(x, SHIELD_Y, 22, 16)

    def hit(self, rect, blast, upward):
        """If rect touches a solid pixel, blast a hole there and return True."""
        r = rect.clip(self.rect)
        if not r.w or not r.h:
            return False
        ys = range(r.bottom - 1, r.top - 1, -1) if upward else range(r.top, r.bottom)
        for y in ys:
            for x in range(r.left, r.right):
                lx, ly = x - self.rect.x, y - self.rect.y
                if self.surf.get_at((lx, ly)).a:
                    self.blast(lx, ly + (-2 if upward else 2), blast)
                    return True
        return False

    def blast(self, cx, cy, pattern):
        w, h = self.surf.get_size()
        for dx, dy in pattern:
            x, y = cx + dx, cy + dy
            if 0 <= x < w and 0 <= y < h:
                self.surf.set_at((x, y), CLEAR)

    def erase(self, rect):
        r = rect.clip(self.rect)
        if r.w and r.h:
            self.surf.fill(CLEAR, r.move(-self.rect.x, -self.rect.y))


# --- the game ------------------------------------------------------------------

class Game:
    def __init__(self, sfx):
        self.sfx = sfx
        self.hi = 0
        self.state = TITLE
        self.t = 0
        self.over_t = 0
        self.paused = False
        self.show_fps = False
        self.fps = 0.0
        self.fonts = {}
        self.ufo = None
        self.reset()

    # setup

    def reset(self):
        self.score = 0
        self.lives = 3
        self.bonus_given = False
        self.wave = 0
        self.start_wave()

    def start_wave(self):
        self.new_formation()
        self.shields = [Shield(32 + i * 45) for i in range(4)]
        self.px = 24
        self.shot = None
        self.bombs = []
        self.explosions = []   # [sprite, x, y, frames_left]
        self.popups = []       # [text, center_x, y, frames_left]
        self.kill_ufo()
        self.ufo_timer = random.randint(1200, 1800)
        self.fire_timer = 60
        self.march_timer = 30
        self.march_i = 0
        self.inv_freeze = 0
        self.dying = 0
        self.next_wave = 0

    def new_formation(self):
        top = WAVE_TOPS[self.wave % len(WAVE_TOPS)]
        self.invaders = []
        for row in range(4, -1, -1):      # bottom row first = ripple order
            kind = "squid" if row == 0 else "crab" if row < 3 else "octopus"
            for col in range(11):
                w = SPR[kind][0].get_width()
                self.invaders.append(Invader(kind, 24 + col * 16 + (16 - w) // 2,
                                             top + row * 16, col))
        self.alive_count = len(self.invaders)
        self.cursor = 0
        self.dx = 2
        self.dropping = False

    def start(self):
        self.reset()
        self.state = PLAYING
        self.paused = False

    # input

    def key(self, k):
        if k == pygame.K_F3:
            self.show_fps = not self.show_fps
        elif self.state == TITLE and k == pygame.K_SPACE:
            self.start()
        elif self.state == OVER and k == pygame.K_SPACE and self.over_t > 60:
            self.start()
        elif self.state == PLAYING:
            if k == pygame.K_p:
                self.paused = not self.paused
                if pygame.mixer.get_init():
                    (pygame.mixer.pause if self.paused else pygame.mixer.unpause)()
            elif k == pygame.K_SPACE and not self.paused:
                self.fire()

    def fire(self):
        if self.shot is None and not self.dying:
            self.shot = [self.px + 6, PLAYER_Y - 4]
            self.sfx.play("shoot")

    # update

    def update(self, keys):
        self.t += 1
        if self.state == OVER:
            self.over_t += 1
            return
        if self.state != PLAYING or self.paused:
            return
        self.tick_effects()
        if self.dying:
            self.dying -= 1
            if not self.dying:
                self.after_death()
            return
        self.update_player(keys)
        self.update_shot()
        self.update_bombs()
        if self.dying:
            return
        self.update_ufo()
        if self.next_wave:
            self.next_wave -= 1
            if not self.next_wave:
                self.wave += 1
                self.start_wave()
            return
        if self.inv_freeze:
            self.inv_freeze -= 1
        else:
            self.step_formation()
        self.update_march()
        self.enemy_fire()

    def tick_effects(self):
        for group in (self.explosions, self.popups):
            for e in group:
                e[3] -= 1
            group[:] = [e for e in group if e[3] > 0]

    def update_player(self, keys):
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.px -= PLAYER_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.px += PLAYER_SPEED
        self.px = max(LEFT_EDGE, min(RIGHT_EDGE - 13, self.px))

    def add_score(self, pts):
        self.score += pts
        self.hi = max(self.hi, self.score)
        if not self.bonus_given and self.score >= EXTRA_LIFE_AT:
            self.bonus_given = True
            self.lives += 1
            self.sfx.play("extra")

    def small_boom(self, x, y):
        self.explosions.append([SPR["shot_boom"][0], x - 4, y, 16])

    def update_shot(self):
        if not self.shot:
            return
        self.shot[1] -= SHOT_SPEED
        x, y = self.shot
        swept = pygame.Rect(x, y, 1, 4 + SHOT_SPEED)
        if y <= HUD_BOTTOM:
            self.small_boom(x, HUD_BOTTOM)
            self.shot = None
            return
        if self.ufo and swept.colliderect(pygame.Rect(self.ufo[0], UFO_Y, 16, 7)):
            pts = random.choice(UFO_POINTS)
            self.add_score(pts)
            self.popups.append([str(pts), self.ufo[0] + 8, UFO_Y, 90])
            self.kill_ufo()
            self.sfx.play("ufo_hit")
            self.shot = None
            return
        for inv in self.invaders:
            if inv.alive and swept.colliderect(inv.rect):
                inv.alive = False
                self.alive_count -= 1
                self.add_score(POINTS[inv.kind])
                self.explosions.append([SPR["boom"][0], inv.x + inv.w // 2 - 6, inv.y, 16])
                self.inv_freeze = 16
                self.sfx.play("inv_hit")
                self.shot = None
                if not self.alive_count:
                    self.next_wave = 90
                return
        for b in self.bombs:
            if swept.colliderect(pygame.Rect(b.x, int(b.y), 3, 7)):
                self.bombs.remove(b)
                self.small_boom(x, y)
                self.shot = None
                return
        for sh in self.shields:
            if sh.hit(swept, SHOT_BLAST, upward=True):
                self.shot = None
                return

    def update_bombs(self):
        player_parts = (pygame.Rect(self.px + 5, PLAYER_Y, 3, 3),
                        pygame.Rect(self.px, PLAYER_Y + 3, 13, 5))
        for b in self.bombs[:]:
            b.y += BOMB_SPEED
            if self.t % 4 == 0:
                b.frame ^= 1
            swept = pygame.Rect(b.x, int(b.y) - BOMB_SPEED, 3, 7 + BOMB_SPEED)
            if swept.bottom >= GROUND_Y:
                self.small_boom(b.x + 1, GROUND_Y - 8)
                self.bombs.remove(b)
            elif any(sh.hit(swept, BOMB_BLAST, upward=False) for sh in self.shields):
                self.bombs.remove(b)
            elif swept.collidelist(player_parts) != -1:
                self.bombs.remove(b)
                self.kill_player()
                return

    def step_formation(self):
        """Move one invader per frame, like the arcade's ripple march."""
        if not self.alive_count:
            return
        while True:
            if self.cursor >= len(self.invaders):
                self.end_pass()
            inv = self.invaders[self.cursor]
            self.cursor += 1
            if inv.alive:
                break
        if self.dropping:
            inv.y += 8
        else:
            inv.x += self.dx
        inv.frame ^= 1
        if inv.y + 8 > SHIELD_Y:
            r = inv.rect
            for sh in self.shields:
                sh.erase(r)
        if inv.y + 8 >= PLAYER_Y:
            self.kill_player(invaded=True)

    def end_pass(self):
        self.cursor = 0
        if self.dropping:
            self.dropping = False
            self.dx = -self.dx
            return
        for inv in self.invaders:
            if inv.alive and (inv.x + inv.w + self.dx > RIGHT_EDGE or inv.x + self.dx < LEFT_EDGE):
                self.dropping = True
                return

    def update_march(self):
        self.march_timer -= 1
        if self.march_timer <= 0 and self.alive_count:
            self.sfx.play(f"march{self.march_i}")
            self.march_i = (self.march_i + 1) % 4
            self.march_timer = max(5, self.alive_count)

    def enemy_fire(self):
        self.fire_timer -= 1
        if self.fire_timer > 0 or len(self.bombs) >= MAX_BOMBS or not self.alive_count:
            return
        base = max(12, 50 - self.wave * 4 - self.score // 400)
        self.fire_timer = random.randint(base // 2, base)
        bottoms = {}
        for inv in self.invaders:
            if inv.alive and (inv.col not in bottoms or inv.y > bottoms[inv.col].y):
                bottoms[inv.col] = inv
        if random.random() < 0.4:
            target = self.px + 6
            shooter = min(bottoms.values(), key=lambda i: abs(i.x + i.w / 2 - target))
        else:
            shooter = random.choice(list(bottoms.values()))
        self.bombs.append(Bomb(shooter.x + shooter.w // 2 - 1, shooter.y + 8,
                               random.choice(("zig", "plunger"))))

    def update_ufo(self):
        if self.ufo is None:
            self.ufo_timer -= 1
            if self.ufo_timer <= 0:
                self.ufo_timer = random.randint(1200, 1800)
                if self.alive_count >= 8:
                    d = random.choice((-1, 1))
                    self.ufo = [-16 if d > 0 else W, d]
                    self.sfx.loop("ufo")
            return
        self.ufo[0] += self.ufo[1]
        if self.ufo[0] < -16 or self.ufo[0] > W:
            self.kill_ufo()

    def kill_ufo(self):
        self.ufo = None
        self.sfx.stop("ufo")

    def kill_player(self, invaded=False):
        self.dying = 120
        self.lives = 0 if invaded else self.lives - 1
        self.shot = None
        self.bombs.clear()
        self.kill_ufo()
        self.sfx.play("pdie")

    def after_death(self):
        if self.lives > 0:
            self.px = 24
            self.fire_timer = 60
        else:
            self.state = OVER
            self.over_t = 0
            self.hi = max(self.hi, self.score)

    # drawing

    def text(self, surf, msg, x, y, size=14, center=False, color=WHITE):
        font = self.fonts.get(size)
        if font is None:
            font = self.fonts[size] = pygame.font.Font(None, size)
        img = font.render(msg, False, color)
        surf.blit(img, (x - img.get_width() // 2 if center else x, y))

    def draw(self, s):
        s.fill(BLACK)
        self.text(s, "SCORE", 8, 3)
        self.text(s, f"{self.score:05d}", 8, 14)
        self.text(s, "HI-SCORE", W // 2, 3, center=True)
        self.text(s, f"{self.hi:05d}", W // 2, 14, center=True)
        self.text(s, "WAVE", 180, 3)
        self.text(s, str(self.wave + 1), 180, 14)

        if self.state == TITLE:
            self.draw_title(s)
        else:
            self.draw_play(s)
            if self.state == OVER:
                msg = "GAME OVER"[:min(9, self.over_t // 6)]
                self.text(s, msg, W // 2, 56, size=24, center=True)
                if self.over_t > 60 and (self.t // 30) % 2 == 0:
                    self.text(s, "PRESS SPACE TO RESTART", W // 2, 80, center=True)
            elif self.paused:
                self.text(s, "PAUSED", W // 2, 120, size=24, center=True)

        # the cellophane overlay: red UFO band, green player band
        s.fill(RED, (0, HUD_BOTTOM, W, 16), special_flags=pygame.BLEND_MULT)
        s.fill(GREEN, (0, 184, W, 56), special_flags=pygame.BLEND_MULT)
        s.fill(GREEN, (24, 240, 112, 16), special_flags=pygame.BLEND_MULT)

        if self.show_fps:
            self.text(s, f"{self.fps:4.1f}", W - 30, 244, size=12)

    def draw_title(self, s):
        self.text(s, "SPACE4K", W // 2, 56, size=36, center=True)
        self.text(s, "*SCORE ADVANCE TABLE*", W // 2, 104, center=True)
        frame = (self.t // 30) % 2
        rows = [("ufo", 0, "= ? MYSTERY"), ("squid", frame, "= 30 POINTS"),
                ("crab", frame, "= 20 POINTS"), ("octopus", frame, "= 10 POINTS")]
        for i, (name, f, label) in enumerate(rows):
            spr = SPR[name][f]
            y = 124 + i * 14
            s.blit(spr, (72 - spr.get_width() // 2, y))
            self.text(s, label, 88, y - 1)
        if (self.t // 30) % 2 == 0:
            self.text(s, "PRESS SPACE", W // 2, 200, center=True)
        self.text(s, "ARROWS MOVE  SPACE FIRE  P PAUSE", W // 2, 220, size=12, center=True)

    def draw_play(self, s):
        for sh in self.shields:
            s.blit(sh.surf, sh.rect)
        for inv in self.invaders:
            if inv.alive:
                s.blit(SPR[inv.kind][inv.frame], (inv.x, inv.y))
        if self.ufo:
            s.blit(SPR["ufo"][0], (self.ufo[0], UFO_Y))
        if self.state == PLAYING:
            if self.dying > 30:
                s.blit(SPR["pdeath"][(self.dying // 6) % 2], (self.px, PLAYER_Y))
            elif not self.dying:
                s.blit(SPR["player"][0], (self.px, PLAYER_Y))
        if self.shot:
            s.fill(WHITE, (self.shot[0], self.shot[1], 1, 4))
        for b in self.bombs:
            s.blit(SPR[b.kind][b.frame], (b.x, int(b.y)))
        for spr, x, y, _ in self.explosions:
            s.blit(spr, (x, y))
        for msg, x, y, _ in self.popups:
            self.text(s, msg, x, y - 2, center=True)

        s.fill(WHITE, (0, GROUND_Y, W, 1))
        self.text(s, str(self.lives), 8, 242)
        for i in range(min(self.lives - 1, 6)):
            s.blit(SPR["player"][0], (24 + i * 16, 244))


# --- main loop -------------------------------------------------------------------

def main():
    pygame.mixer.pre_init(RATE, -16, 1, 512)
    pygame.init()
    screen = pygame.display.set_mode((W * SCALE, H * SCALE))
    pygame.display.set_caption("Space4K")
    build_sprites()
    canvas = pygame.Surface((W, H))
    clock = pygame.time.Clock()
    game = Game(Sfx())

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                pygame.quit()
                return
            if ev.type == pygame.KEYDOWN:
                game.key(ev.key)
        game.update(pygame.key.get_pressed())
        game.draw(canvas)
        screen.blit(pygame.transform.scale(canvas, screen.get_size()), (0, 0))
        pygame.display.flip()
        game.fps = clock.get_fps()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
