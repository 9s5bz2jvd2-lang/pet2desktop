"""
Image processing module for Pet2Desktop.

Handles resizing and animation frame generation
from a user-supplied pet photo.
"""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


class ImageProcessor:
    """Processes a pet photo into desktop pet sprite assets."""

    MAX_SIZE = 300  # longest side in pixels

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, input_path: str, output_dir: str) -> bool:
        """Convert *input_path* into pet_idle / pet_blink / pet_sleep inside
        *output_dir*.  Returns ``True`` on success."""
        try:
            img = Image.open(input_path).convert("RGBA")

            img = self._remove_background(img)
            img = self._resize_to_max(img)

            # Save the clean idle image
            idle_path = os.path.join(output_dir, "pet_idle.png")
            img.save(idle_path, "PNG")

            # Copy as canonical pet image
            pet_path = os.path.join(output_dir, "pet.png")
            img.save(pet_path, "PNG")

            # Derived animation frames
            self._generate_blink(img).save(
                os.path.join(output_dir, "pet_blink.png"), "PNG"
            )
            self._generate_sleep(img).save(
                os.path.join(output_dir, "pet_sleep.png"), "PNG"
            )

            return True
        except Exception as exc:
            print(f"[ImageProcessor] process failed: {exc}")
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _remove_background(self, img: Image.Image) -> Image.Image:
        """Remove background — edge-sampling first (instant, clean for uniform
        backgrounds), rembg as optional fallback for complex scenes.

        To force rembg: set env variable PET2DESKTOP_USE_REMBG=1
        """
        import os as _os

        force_rembg = _os.environ.get("PET2DESKTOP_USE_REMBG", "") == "1"

        # 1. Edge-sampling colour key — fast, clean for uniform backgrounds
        if not force_rembg:
            return self._edge_colour_key(img)

        # 2. rembg AI (only when explicitly requested)
        model_path = Path.home() / ".u2net" / "u2netp.onnx"
        if model_path.exists():
            try:
                from rembg import remove, new_session
                session = new_session("u2netp")
                return remove(img, session=session)
            except Exception as exc:
                print(f"[ImageProcessor] rembg: {exc}")

        return self._edge_colour_key(img)

    # -- edge-sampling colour-key fallback ------------------------------

    def _edge_colour_key(self, img: Image.Image) -> Image.Image:
        """Sample colours from image edges to build a background mask.

        Works well for photos with relatively uniform backgrounds
        (walls, grass, sky).  No external model needed.
        """
        import statistics
        from PIL import ImageFilter

        w, h = img.size
        pixels = img.load()

        # Sample from 4 corners + 4 edge midpoints
        samples: list[tuple[int, int, int]] = []
        margin = max(3, min(w, h) // 20)
        corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
        for cx, cy in corners:
            for dx in range(margin):
                for dy in range(margin):
                    x = max(0, min(w - 1, cx + (dx if cx == 0 else -dx)))
                    y = max(0, min(h - 1, cy + (dy if cy == 0 else -dy)))
                    r, g, b, a = pixels[x, y]
                    if a > 128:
                        samples.append((r, g, b))

        # Edge midpoints
        edges = [
            (w // 2, 0),
            (w // 2, h - 1),
            (0, h // 2),
            (w - 1, h // 2),
        ]
        for ex, ey in edges:
            for d in range(margin * 3):
                x = max(0, min(w - 1, ex + (0 if ex in (0, w - 1) else d - margin)))
                y = max(0, min(h - 1, ey + (0 if ey in (0, h - 1) else d - margin)))
                r, g, b, a = pixels[x, y]
                if a > 128:
                    samples.append((r, g, b))

        if len(samples) < 20:
            return img

        # Median colour per channel (robust to outliers)
        bg_r = int(statistics.median(s[0] for s in samples))
        bg_g = int(statistics.median(s[1] for s in samples))
        bg_b = int(statistics.median(s[2] for s in samples))

        # Tolerance: 25 % of colour-space distance
        tol = 60

        # Build alpha mask
        mask = Image.new("L", (w, h), 0)
        mp = mask.load()
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                if a < 128:
                    mp[x, y] = 0
                    continue
                dist = abs(r - bg_r) + abs(g - bg_g) + abs(b - bg_b)
                # Map distance → alpha (0 = keep, 255 = transparent)
                alpha = int(min(255, dist * 255 / tol))
                mp[x, y] = alpha

        # Blur mask for smooth edges
        mask = mask.filter(ImageFilter.GaussianBlur(radius=3))

        # Apply mask
        out = img.copy()
        out.putalpha(mask)
        print("[ImageProcessor] edge-colour keying applied")
        return out

    def _resize_to_max(self, img: Image.Image) -> Image.Image:
        """Scale so the longest side equals ``MAX_SIZE``, keeping aspect."""
        w, h = img.size
        if max(w, h) <= self.MAX_SIZE:
            return img
        if w >= h:
            nw, nh = self.MAX_SIZE, int(h * self.MAX_SIZE / w)
        else:
            nw, nh = int(w * self.MAX_SIZE / h), self.MAX_SIZE
        return img.resize((nw, nh), Image.LANCZOS)

    # -- animation frame generators -----------------------------------

    def _generate_blink(self, img: Image.Image) -> Image.Image:
        """Simulate a blink by compressing height 10 % and centering."""
        w, h = img.size
        squished_h = int(h * 0.90)
        squished = img.resize((w, squished_h), Image.LANCZOS)

        frame = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        y_off = (h - squished_h) // 2
        frame.paste(squished, (0, y_off), squished)
        return frame

    def _generate_sleep(self, img: Image.Image) -> Image.Image:
        """Simulate sleep: reduce opacity 40 % + draw 'Zzz' text."""
        w, h = img.size
        frame = img.copy()

        # Reduce alpha channel
        pixels = frame.getdata()
        faded = []
        for r, g, b, a in pixels:
            faded.append((r, g, b, int(a * 0.60)))
        frame.putdata(faded)

        # Draw "Zzz"
        draw = ImageDraw.Draw(frame)
        font = self._load_font(max(20, w // 4))
        text = "Zzz"
        tb = draw.textbbox((0, 0), text, font=font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]

        tx = w - tw - 8
        ty = 4
        draw.text((tx + 2, ty + 2), text, font=font, fill=(0, 0, 0, 160))
        draw.text((tx, ty), text, font=font, fill=(120, 200, 255, 220))
        return frame

    @staticmethod
    def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Try to load a system truetype font; degrade to default."""
        candidates = ["arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"]
        for name in candidates:
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
        return ImageFont.load_default()
