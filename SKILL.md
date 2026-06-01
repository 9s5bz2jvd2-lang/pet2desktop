---
name: pet2desktop-宠物陪你
description: >
  Pet2Desktop / 宠物陪你 — 把宠物照片变成会动会眨眼的桌面小伙伴。
  Turn any pet photo into a living desktop companion. Provides a complete
  Python application (PySide6 + Pillow) that resizes the image, generates
  idle/blink/sleep animation frames, and launches a transparent always-on-top
  window with autonomous behaviours (walk, blink, nap, idle). Supports
  multiple pets on screen simultaneously.
  Use when the user asks: 桌面宠物 / 宠物陪你 / desktop pet / make a photo
  into a desktop pet / run Pet2Desktop / 把这照片做成桌面宠物 / 猫狗萌宠
  desktop companion.
---

# Pet2Desktop · 宠物陪你

Turn a pet photo into an animated desktop companion · 把宠物照片变成会动的小伙伴

## Workflow (zero-interaction — no file dialogs)

1. User sends a pet photo in chat → save it to a temp path.  Do **not**
   ask the user anything — just save and proceed.
2. First time only, ensure deps:
   `pip install -r scripts/requirements.txt`
3. Launch directly (no file dialog, no QMessageBox).  Each call creates
   an independent pet with its own assets directory and a random starting
   position.  Old pets are **not** killed — you can have as many as you
   want on screen at once:
   `python scripts/main.py <saved-image-path> [--id <pet-name>]`

To stop a pet, right-click it and choose ❌ Exit.  To stop all pets
at once: `Get-Process python* | Where-Object MainWindowTitle -like '*Pet2Desktop*' | Stop-Process -Force`

## Optional: AI Background Removal

Set `PET2DESKTOP_USE_REMBG=1` before launch to force rembg-based
background removal.  The u2net model must be cached at
`~/.u2net/u2netp.onnx`.  Without the env var, the fast
edge-sampling keyer is used instead (no downloads, works offline).

## Behaviour After Launch

The pet appears as a frameless, transparent, always-on-top window with:

| Action | Trigger |
|--------|---------|
| Walk (left/right, 50–300 px) | Random, after 3–10 s idle |
| Blink (200 ms) | ~18 % chance every 1.5 s during idle |
| Sleep (5 s, faded + "Zzz") | Random, during idle |
| Speech bubble | Double-click the pet |
| Move | Left-click drag |
| Health reminder | Every N min (default 45) → walks to screen centre, shows tip |
| Context menu (upload / pause / exit / reminder settings) | Right-click |

## Scripts

| File | Purpose |
|------|---------|
| `scripts/main.py` | Entry point — file picker or CLI image arg |
| `scripts/requirements.txt` | PySide6, Pillow |
| `scripts/core/image_processor.py` | Resize, frame generation (optional rembg) |
| `scripts/core/pet_window.py` | Transparent window + behaviour state machine |
| `scripts/core/animation.py` | PetState enum, bubble popup |
| `scripts/core/movement.py` | Screen bounds, walk parameters |

Generated assets are saved to `scripts/assets/` at runtime.