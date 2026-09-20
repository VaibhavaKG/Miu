"""
Cosmetics and Appearance Architecture for Oneko Desktop Companion.

Manages:
- Body color themes (classic, ginger, black, sakura, calico, siamese, tuxedo, midnight_blue)
- Accessories (none, tophat, wizard_hat, beret, bowtie, scarf, glasses, flower, crown, party_hat)
- Eyes & Expressions (normal, sparkle, winking, sleepy, scholar)
- Sprite frame tinting & procedural pixel-art Cairo overlays
- Extensibility for custom PNG assets in ~/.local/share/miu/accessories/
"""

import os
import math
import cairo
import gi
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, Gdk

COSMETIC_CATALOG = {
    "themes": [
        {"id": "classic", "name": "Classic Neko", "desc": "Original cream with warm brown markings"},
        {"id": "ginger", "name": "Ginger Tabby", "desc": "Cozy marmalade orange tabby"},
        {"id": "black", "name": "Midnight Black", "desc": "Sleek obsidian coat with radiant eyes"},
        {"id": "sakura", "name": "Sakura Blossom", "desc": "Soft pastel cherry blossom tint"},
        {"id": "calico", "name": "Calico Patch", "desc": "Tricolor calico with tortoiseshell pattern"},
        {"id": "siamese", "name": "Siamese Seal", "desc": "Cream coat with dark seal points"},
        {"id": "tuxedo", "name": "Tuxedo Cat", "desc": "Formal black jacket with white bib"},
        {"id": "midnight_blue", "name": "Midnight Slate", "desc": "Atmospheric slate-blue moonlit coat"},
    ],
    "accessories": [
        {"id": "none", "name": "None", "desc": "Natural, unadorned companion"},
        {"id": "tophat", "name": "Gentleman Top Hat", "desc": "Dapper black silk top hat"},
        {"id": "wizard_hat", "name": "Wizard Hat", "desc": "Pointed celestial cap with gold star"},
        {"id": "beret", "name": "Artist Beret", "desc": "Warm Parisian artist beret"},
        {"id": "bowtie", "name": "Crimson Bowtie", "desc": "Crisp red gentleman's bowtie"},
        {"id": "scarf", "name": "Winter Scarf", "desc": "Cozy knit scarf wrapped at neck"},
        {"id": "glasses", "name": "Scholar Spectacles", "desc": "Round wire-rim reading glasses"},
        {"id": "flower", "name": "Blossom Pin", "desc": "Delicate flower tucked behind ear"},
        {"id": "crown", "name": "Golden Crown", "desc": "Regal 3-peak miniature crown"},
        {"id": "party_hat", "name": "Party Hat", "desc": "Festive striped celebration cone"},
    ],
    "expressions": [
        {"id": "normal", "name": "Standard", "desc": "Natural calm expression"},
        {"id": "sparkle", "name": "Sparkle Eyes", "desc": "Bright gleam and happy twinkle"},
        {"id": "winking", "name": "Playful Wink", "desc": "Cheeky winking eye"},
        {"id": "sleepy", "name": "Sleepy Eyes", "desc": "Gentle, drowsy half-lidded gaze"},
        {"id": "scholar", "name": "Thoughtful", "desc": "Contemplative focused look"},
    ],
}


class SpriteManager:
    """Manages sprite frame slicing, scale caching, and skin theme tinting."""
    SPRITE_MAP = {
        "idle": [(3, 3)],
        "alert": [(7, 3)],
        "scratchSelf": [(5, 0), (6, 0), (7, 0)],
        "scratchWallN": [(0, 0), (0, 1)],
        "scratchWallS": [(7, 1), (6, 2)],
        "scratchWallE": [(2, 2), (2, 3)],
        "scratchWallW": [(4, 0), (4, 1)],
        "tired": [(3, 2)],
        "sleeping": [(2, 0), (2, 1)],
        "N": [(1, 2), (1, 3)],
        "NE": [(0, 2), (0, 3)],
        "E": [(3, 0), (3, 1)],
        "SE": [(5, 1), (5, 2)],
        "S": [(6, 3), (7, 2)],
        "SW": [(5, 3), (6, 1)],
        "W": [(4, 2), (4, 3)],
        "NW": [(1, 0), (1, 1)]
    }

    def __init__(self, sheet_path, scale=1.25, theme="classic"):
        self.sheet_path = sheet_path
        self.scale = scale
        self.theme = theme
        self.raw_sheet = GdkPixbuf.Pixbuf.new_from_file(sheet_path)
        self.cached_frames = {}
        self._load_frames()

    def set_theme(self, theme):
        if theme != self.theme:
            self.theme = theme
            self._load_frames()

    def set_scale(self, scale):
        if scale != self.scale:
            self.scale = scale
            self._load_frames()

    def _apply_theme(self, pixbuf):
        if self.theme == "classic":
            return pixbuf

        copy = pixbuf.copy()
        pixels = copy.get_pixels()
        n_channels = copy.get_n_channels()
        rowstride = copy.get_rowstride()
        w = copy.get_width()
        h = copy.get_height()
        ba = bytearray(pixels)

        for y in range(h):
            row_start = y * rowstride
            for x in range(w):
                pos = row_start + x * n_channels
                alpha = ba[pos + 3] if n_channels == 4 else 255
                if alpha <= 25:
                    continue

                r, g, b = ba[pos], ba[pos + 1], ba[pos + 2]
                is_light = (r > 160 and g > 160 and b > 160)
                is_dark = (r < 90 and g < 90 and b < 90)

                if self.theme == "ginger":
                    if is_light:
                        ba[pos] = min(255, int(r * 1.08))
                        ba[pos + 1] = int(g * 0.72)
                        ba[pos + 2] = int(b * 0.38)
                    elif is_dark:
                        ba[pos] = 160
                        ba[pos + 1] = 75
                        ba[pos + 2] = 20

                elif self.theme == "black":
                    if is_light:
                        ba[pos] = 36
                        ba[pos + 1] = 36
                        ba[pos + 2] = 42
                    elif is_dark:
                        ba[pos] = 18
                        ba[pos + 1] = 18
                        ba[pos + 2] = 22

                elif self.theme == "sakura":
                    if is_light:
                        ba[pos] = min(255, int(r * 1.05))
                        ba[pos + 1] = int(g * 0.82)
                        ba[pos + 2] = int(b * 0.88)
                    elif is_dark:
                        ba[pos] = 180
                        ba[pos + 1] = 80
                        ba[pos + 2] = 120

                elif self.theme == "calico":
                    # Patchwork: left side orange, right side dark slate
                    if is_light:
                        if (x + y) % 9 < 4:
                            ba[pos] = min(255, int(r * 1.1))
                            ba[pos + 1] = int(g * 0.70)
                            ba[pos + 2] = int(b * 0.35)
                    elif is_dark:
                        ba[pos] = 45
                        ba[pos + 1] = 45
                        ba[pos + 2] = 50

                elif self.theme == "siamese":
                    # Cream body with dark mask/ears/paws
                    dist_to_center = math.hypot(x - 16, y - 16)
                    if dist_to_center > 9 or y < 9:
                        if is_light:
                            ba[pos] = 85
                            ba[pos + 1] = 65
                            ba[pos + 2] = 55
                    else:
                        if is_light:
                            ba[pos] = 245
                            ba[pos + 1] = 235
                            ba[pos + 2] = 220

                elif self.theme == "tuxedo":
                    # Black body with white chest
                    in_bib = (10 <= x <= 22 and 16 <= y <= 27)
                    if in_bib:
                        ba[pos] = 250
                        ba[pos + 1] = 250
                        ba[pos + 2] = 252
                    elif is_light or is_dark:
                        ba[pos] = 32
                        ba[pos + 1] = 32
                        ba[pos + 2] = 38

                elif self.theme == "midnight_blue":
                    if is_light:
                        ba[pos] = 60
                        ba[pos + 1] = 75
                        ba[pos + 2] = 110
                    elif is_dark:
                        ba[pos] = 25
                        ba[pos + 1] = 30
                        ba[pos + 2] = 55

        return GdkPixbuf.Pixbuf.new_from_data(
            bytes(ba), GdkPixbuf.Colorspace.RGB, n_channels == 4, 8, w, h, rowstride
        )

    def _load_frames(self):
        self.cached_frames.clear()
        target_size = int(32 * self.scale)
        for name, coords in self.SPRITE_MAP.items():
            frames = []
            for (col, row) in coords:
                sub = GdkPixbuf.Pixbuf.new_subpixbuf(self.raw_sheet, col * 32, row * 32, 32, 32)
                tinted = self._apply_theme(sub)
                if self.scale != 1.0:
                    scaled = tinted.scale_simple(target_size, target_size, GdkPixbuf.InterpType.NEAREST)
                    frames.append(scaled)
                else:
                    frames.append(tinted)
            self.cached_frames[name] = frames

    def get_frame(self, name, index=0):
        frames = self.cached_frames.get(name, self.cached_frames["idle"])
        return frames[index % len(frames)]


class CosmeticManager:
    """Renders modular accessories and eye expressions onto the pet sprite canvas."""

    def __init__(self, accessories_dir=None):
        if accessories_dir is None:
            try:
                from paths import USER_ACCESSORIES_DIR
                self.accessories_dir = USER_ACCESSORIES_DIR
            except ImportError:
                self.accessories_dir = os.path.expanduser("~/.local/share/oneko-plus/accessories")
        else:
            self.accessories_dir = accessories_dir
        self.custom_assets = {}
        self._scan_custom_assets()

    def _scan_custom_assets(self):
        if os.path.exists(self.accessories_dir):
            for fname in os.listdir(self.accessories_dir):
                if fname.endswith(".png"):
                    base_id = os.path.splitext(fname)[0]
                    fpath = os.path.join(self.accessories_dir, fname)
                    try:
                        self.custom_assets[base_id] = GdkPixbuf.Pixbuf.new_from_file(fpath)
                    except Exception:
                        pass

    def draw_expression(self, cr, expression_id, sprite_name, cx, cy, scale):
        """Draws subtle eye / brow expressions over the cat head."""
        if expression_id == "normal" or sprite_name == "sleeping":
            return

        s = scale
        # Determine approximate face anchor based on direction
        # Default front/alert face center
        fx = cx + 16 * s
        fy = cy + 14 * s

        cr.save()
        if expression_id == "sparkle":
            # Twinkling white catchlights in eyes
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.95)
            cr.arc(fx - 4 * s, fy - 1 * s, 1.2 * s, 0, 2 * math.pi)
            cr.fill()
            cr.arc(fx + 4 * s, fy - 1 * s, 1.2 * s, 0, 2 * math.pi)
            cr.fill()

        elif expression_id == "winking":
            # Left eye happy arch wink, right eye sparkle
            cr.set_source_rgba(0.1, 0.1, 0.15, 0.9)
            cr.set_line_width(1.2 * s)
            cr.arc(fx - 4 * s, fy - 0.5 * s, 2.0 * s, math.pi * 1.1, math.pi * 1.9)
            cr.stroke()
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.95)
            cr.arc(fx + 4 * s, fy - 1 * s, 1.2 * s, 0, 2 * math.pi)
            cr.fill()

        elif expression_id == "sleepy":
            # Soft half-lidded droop
            cr.set_source_rgba(0.2, 0.2, 0.25, 0.8)
            cr.set_line_width(1.1 * s)
            cr.move_to(fx - 6 * s, fy - 2 * s)
            cr.line_to(fx - 2 * s, fy - 1 * s)
            cr.stroke()
            cr.move_to(fx + 2 * s, fy - 1 * s)
            cr.line_to(fx + 6 * s, fy - 2 * s)
            cr.stroke()

        elif expression_id == "scholar":
            # Thoughtful slight furrowed brow
            cr.set_source_rgba(0.2, 0.2, 0.25, 0.85)
            cr.set_line_width(1.0 * s)
            cr.move_to(fx - 6 * s, fy - 4 * s)
            cr.line_to(fx - 2 * s, fy - 3 * s)
            cr.stroke()
            cr.move_to(fx + 2 * s, fy - 3 * s)
            cr.line_to(fx + 6 * s, fy - 4 * s)
            cr.stroke()

        cr.restore()

    def draw_accessory(self, cr, accessory_id, sprite_name, cx, cy, scale):
        """Draws procedural or custom accessory overlays."""
        if accessory_id == "none" or not accessory_id:
            return

        # Check for custom PNG overlay first
        if accessory_id in self.custom_assets:
            pixbuf = self.custom_assets[accessory_id]
            target_size = int(32 * scale)
            scaled = pixbuf.scale_simple(target_size, target_size, GdkPixbuf.InterpType.BILINEAR)
            Gdk.cairo_set_source_pixbuf(cr, scaled, cx, cy)
            cr.paint()
            return

        s = scale
        head_x = cx + 16 * s
        head_y = cy + 9 * s

        if sprite_name == "sleeping":
            head_x = cx + 19 * s
            head_y = cy + 20 * s

        cr.save()

        if accessory_id == "tophat":
            # Miniature Victorian black top hat
            bx = head_x - 7 * s
            by = head_y - 10 * s
            # Brim
            cr.set_source_rgba(0.12, 0.12, 0.14, 0.98)
            cr.rectangle(bx - 3 * s, by + 8 * s, 20 * s, 2.5 * s)
            cr.fill()
            # Crown
            cr.rectangle(bx + 1 * s, by, 12 * s, 8 * s)
            cr.fill()
            # Satin Ribbon Band
            cr.set_source_rgba(0.78, 0.18, 0.22, 0.95)
            cr.rectangle(bx + 1 * s, by + 6 * s, 12 * s, 2 * s)
            cr.fill()

        elif accessory_id == "wizard_hat":
            # Pointed wizard hat with star
            bx = head_x
            by = head_y - 12 * s
            cr.set_source_rgba(0.20, 0.22, 0.45, 0.98)
            cr.move_to(bx, by)
            cr.line_to(bx + 9 * s, by + 11 * s)
            cr.line_to(bx - 9 * s, by + 11 * s)
            cr.close_path()
            cr.fill()
            # Brim
            cr.set_source_rgba(0.15, 0.16, 0.35, 0.98)
            cr.rectangle(bx - 10 * s, by + 10 * s, 20 * s, 2.5 * s)
            cr.fill()
            # Star
            cr.set_source_rgba(0.96, 0.82, 0.28, 0.98)
            cr.arc(bx, by + 6 * s, 1.8 * s, 0, 2 * math.pi)
            cr.fill()

        elif accessory_id == "beret":
            # Soft Parisian artist beret
            bx = head_x - 2 * s
            by = head_y - 4 * s
            cr.set_source_rgba(0.68, 0.20, 0.22, 0.96)
            cr.save()
            cr.translate(bx, by)
            cr.scale(1.4, 0.8)
            cr.arc(0, 0, 7 * s, 0, 2 * math.pi)
            cr.fill()
            cr.restore()
            # Stem
            cr.set_source_rgba(0.50, 0.12, 0.15, 0.96)
            cr.rectangle(bx - 0.8 * s, by - 6.5 * s, 1.6 * s, 2.5 * s)
            cr.fill()

        elif accessory_id == "bowtie":
            # Red bowtie at collar
            neck_x = cx + 16 * s
            neck_y = cy + 22 * s
            if sprite_name == "sleeping":
                neck_x = cx + 15 * s
                neck_y = cy + 22 * s
            cr.set_source_rgba(0.85, 0.20, 0.25, 0.98)
            # Left wing
            cr.move_to(neck_x, neck_y)
            cr.line_to(neck_x - 5 * s, neck_y - 3 * s)
            cr.line_to(neck_x - 5 * s, neck_y + 3 * s)
            cr.close_path()
            cr.fill()
            # Right wing
            cr.move_to(neck_x, neck_y)
            cr.line_to(neck_x + 5 * s, neck_y - 3 * s)
            cr.line_to(neck_x + 5 * s, neck_y + 3 * s)
            cr.close_path()
            cr.fill()
            # Center knot
            cr.set_source_rgba(0.98, 0.78, 0.28, 0.98)
            cr.arc(neck_x, neck_y, 1.6 * s, 0, 2 * math.pi)
            cr.fill()

        elif accessory_id == "scarf":
            # Warm knit scarf
            neck_x = cx + 16 * s
            neck_y = cy + 20 * s
            cr.set_source_rgba(0.25, 0.65, 0.55, 0.96)
            cr.rectangle(neck_x - 7 * s, neck_y - 2 * s, 14 * s, 4 * s)
            cr.fill()
            # Tail
            cr.rectangle(neck_x + 3 * s, neck_y, 3.5 * s, 7 * s)
            cr.fill()

        elif accessory_id == "glasses":
            # Round scholar wire-rim glasses
            gx = head_x
            gy = head_y + 4 * s
            cr.set_source_rgba(0.85, 0.75, 0.35, 0.95)
            cr.set_line_width(1.1 * s)
            # Left lens
            cr.arc(gx - 4 * s, gy, 2.5 * s, 0, 2 * math.pi)
            cr.stroke()
            # Right lens
            cr.arc(gx + 4 * s, gy, 2.5 * s, 0, 2 * math.pi)
            cr.stroke()
            # Bridge
            cr.move_to(gx - 1.5 * s, gy)
            cr.line_to(gx + 1.5 * s, gy)
            cr.stroke()

        elif accessory_id == "flower":
            # Sakura blossom tucked behind left ear
            fl_x = head_x - 7 * s
            fl_y = head_y - 3 * s
            cr.set_source_rgba(0.98, 0.68, 0.82, 0.95)
            for angle in [0, 72, 144, 216, 288]:
                rad = math.radians(angle)
                px = fl_x + math.cos(rad) * 3 * s
                py = fl_y + math.sin(rad) * 3 * s
                cr.arc(px, py, 2 * s, 0, 2 * math.pi)
                cr.fill()
            cr.set_source_rgba(1.0, 0.90, 0.35, 0.98)
            cr.arc(fl_x, fl_y, 1.4 * s, 0, 2 * math.pi)
            cr.fill()

        elif accessory_id == "crown":
            # Golden 3-peak royal crown
            cx_pos = head_x - 6 * s
            cy_pos = head_y - 8 * s
            cr.set_source_rgba(0.96, 0.78, 0.20, 0.98)
            cr.move_to(cx_pos, cy_pos + 6 * s)
            cr.line_to(cx_pos, cy_pos + 1 * s)
            cr.line_to(cx_pos + 3 * s, cy_pos + 3.5 * s)
            cr.line_to(cx_pos + 6 * s, cy_pos)
            cr.line_to(cx_pos + 9 * s, cy_pos + 3.5 * s)
            cr.line_to(cx_pos + 12 * s, cy_pos + 1 * s)
            cr.line_to(cx_pos + 12 * s, cy_pos + 6 * s)
            cr.close_path()
            cr.fill()
            # Ruby jewels
            cr.set_source_rgba(0.90, 0.20, 0.25, 0.98)
            cr.arc(cx_pos + 6 * s, cy_pos + 4.5 * s, 1.2 * s, 0, 2 * math.pi)
            cr.fill()

        elif accessory_id == "party_hat":
            # Festive party cone
            px = head_x
            py = head_y - 12 * s
            cr.set_source_rgba(0.95, 0.35, 0.45, 0.98)
            cr.move_to(px, py)
            cr.line_to(px + 6 * s, py + 11 * s)
            cr.line_to(px - 6 * s, py + 11 * s)
            cr.close_path()
            cr.fill()
            # Polka dots
            cr.set_source_rgba(0.98, 0.92, 0.35, 0.98)
            cr.arc(px, py + 5 * s, 1.2 * s, 0, 2 * math.pi)
            cr.fill()
            cr.arc(px - 2.5 * s, py + 8 * s, 1.2 * s, 0, 2 * math.pi)
            cr.fill()
            cr.arc(px + 2.5 * s, py + 8 * s, 1.2 * s, 0, 2 * math.pi)
            cr.fill()
            # Pom pom
            cr.arc(px, py, 1.8 * s, 0, 2 * math.pi)
            cr.fill()

        cr.restore()
