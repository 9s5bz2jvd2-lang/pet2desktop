# 🐱 Pet2Desktop · 宠物陪你

> Turn any pet photo into a living desktop companion · 把照片变成会动会眨眼的桌面小伙伴
>
> One command, zero dialogs · 一个命令，零弹窗

## Quick Start

```bash
# 1. Install
pip install -r scripts/requirements.txt

# 2. Launch
python scripts/main.py path/to/your-pet.jpg
```

Done. Your pet appears on screen, walking and blinking autonomously.

## What It Does

| Feature | Detail |
|---------|--------|
| Background removal | Automatic (edge-sampling, instant, no downloads) |
| Animation | Idle → walk → blink → nap → idle loop |
| Walk | 50–300 px left or right |
| Blink | ~18% chance every 1.5 s |
| Sleep | 5 s with fade + Zzz |
| Drag | Left-click to move the pet anywhere |
| Bubble | Double-click for a random emoji message |
| Upload | Right-click → change the pet photo anytime |
| Health reminder | Pet walks to screen centre and shows a health tip (default 45 min) |
| Reminder settings | Right-click → ⏰ Reminder Settings → toggle / set interval (15–120 min) |
| Multi-pet | Run it again with another photo — they coexist |

## Multiple Pets

Each call creates an independent pet:

```bash
python scripts/main.py cat.jpg           # pet #1 (random id)
python scripts/main.py dog.jpg --id dog  # pet #2 (named)
python scripts/main.py bird.jpg          # pet #3
```

All three run side by side. Right-click → Exit to remove one.

## Optional: AI Background Removal

For complex backgrounds, enable rembg:

```bash
# Install once
pip install rembg onnxruntime

# First launch auto-downloads the 24 MB model (~/.u2net/u2netp.onnx)
set PET2DESKTOP_USE_REMBG=1
python scripts/main.py your-pet.jpg
```

## OpenClaw Skill Installation

This repo doubles as an OpenClaw skill. Place it under
`~/.qclaw/skills/pet2desktop/` and send your pet photo in chat —
the skill runs automatically with no file dialogs.

## Requirements

- Python 3.10+
- Windows / macOS / Linux
- PySide6 + Pillow (auto-installed by requirements.txt)

## License

MIT

---

> **禁止抄袭商用，违者等同盗法，因果自负**
> **Plagiarism and commercial use are strictly prohibited. Violators shall be deemed as thieves of sacred scriptures and shall face divine karmic retribution themselves.**
>
> 公益开源项目，禁止商用 | Public welfare open-source project, commercial use prohibited
> License: CC BY-NC 4.0
