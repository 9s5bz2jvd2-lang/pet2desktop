"""
Pet2Desktop — turn any pet photo into a desktop companion.

Usage:
    python main.py path/to/pet.jpg           # new pet with random id
    python main.py path/to/pet.jpg --id mypet # named pet
    python main.py                           # opens file picker (no args)

Multiple instances are supported — each gets its own assets/id/ directory
and a random starting position so pets don't overlap.
"""

from __future__ import annotations

import os
import random
import sys
import uuid
from pathlib import Path

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from PySide6.QtGui import QIcon

from core.image_processor import ImageProcessor
from core.pet_window import PetWindow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _this_dir() -> Path:
    """Directory containing this script."""
    return Path(__file__).resolve().parent


def _make_pet_id(name: str | None = None) -> str:
    """Generate a unique pet id — short uuid or user-supplied name."""
    if name:
        return name
    return uuid.uuid4().hex[:8]


def _parse_args(argv: list[str]) -> tuple[str | None, str | None]:
    """Parse CLI args: returns (image_path, pet_id)."""
    image_path: str | None = None
    pet_id: str | None = None
    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg == "--id" and i + 1 < len(argv):
            pet_id = argv[i + 1]
            i += 2
        elif not arg.startswith("-"):
            candidate = Path(arg)
            if candidate.is_file() and candidate.suffix.lower() in (
                ".png", ".jpg", ".jpeg", ".bmp", ".webp",
            ):
                image_path = str(candidate)
            i += 1
        else:
            i += 1
    return image_path, pet_id


def _prompt_for_image() -> str | None:
    """Show a file dialog so the user picks a pet photo. Returns the path
    or ``None`` if the user cancelled."""
    QMessageBox.information(
        None, "Pet2Desktop",
        "Welcome to Pet2Desktop!\n\n"
        "Please select a photo of your pet.\n"
        "Supported formats: PNG, JPG, JPEG, BMP, WEBP",
    )
    path, _ = QFileDialog.getOpenFileName(
        None, "Select Your Pet Photo", "",
        "Images (*.png *.jpg *.jpeg *.bmp *.webp)",
    )
    return path or None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Pet2Desktop")
    app.setApplicationVersion("1.2.0")

    base_dir = _this_dir() / "assets"
    base_dir.mkdir(exist_ok=True)

    image_path, pet_id = _parse_args(sys.argv)
    pet_id = pet_id or _make_pet_id()

    # Each pet gets its own isolated directory
    pet_dir = base_dir / pet_id
    pet_dir.mkdir(exist_ok=True)

    idle_file = pet_dir / "pet_idle.png"
    image_path_final: str | None = image_path

    # -- command-line image (zero-dialog path) ------------------------------
    if image_path_final:
        print(f"[Pet2Desktop] pet={pet_id}  Processing: {Path(image_path_final).name}")

    # -- first-run flow (only when no args and no existing assets) ---------
    if not idle_file.exists() and image_path_final is None:
        image_path_final = _prompt_for_image()
        if not image_path_final:
            QMessageBox.warning(None, "Pet2Desktop", "No image selected. Exiting.")
            sys.exit(0)

    # -- process image -----------------------------------------------------
    if image_path_final:
        processor = ImageProcessor()
        ok = processor.process(image_path_final, str(pet_dir))
        if not ok:
            QMessageBox.critical(
                None, "Pet2Desktop",
                "Failed to process the image. Make sure the file is a "
                "valid photo and that Pillow is installed.",
            )
            sys.exit(1)
        print(f"[Pet2Desktop] pet={pet_id}  Assets generated — launching")

    # -- launch pet --------------------------------------------------------
    pet = PetWindow(str(pet_dir))
    pet.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()