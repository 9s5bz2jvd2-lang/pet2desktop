"""
Desktop pet window — transparent, frameless, always-on-top widget that
animates a pet sprite with idle / walk / blink / sleep behaviours.
"""

from __future__ import annotations

import os
import random
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QLabel, QMenu, QApplication, QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import (
    QPixmap, QTransform, QMouseEvent, QContextMenuEvent,
)

from core.animation import PetState, BUBBLE_MESSAGES, HEALTH_REMINDERS, BubblePopup
from core.movement import (
    get_screen_geometry, clamp_to_screen,
    random_walk_distance, random_walk_direction, random_idle_duration_ms,
    attention_position,
    WALK_TICK_MS, WALK_STEP_PX,
)


class PetWindow(QWidget):
    """A single desktop-pet instance.

    On construction the window loads sprite assets from *assets_dir*,
    positions itself near the bottom-right of the screen, and starts
    the autonomous behaviour loop.

    Right-click opens a context menu (upload / pause / resume / exit /
    reminder settings).
    Double-left-click shows a random speech bubble.

    **Health reminder** – every *reminder_interval_min* minutes the pet
    walks to the centre of the screen and shows a health tip bubble.
    """

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    # Default reminder interval in minutes
    DEFAULT_REMINDER_MIN = 45

    def __init__(self, assets_dir: str, start_x: int | None = None,
                 start_y: int | None = None) -> None:
        super().__init__()
        self._assets_dir = assets_dir
        self._start_x = start_x
        self._start_y = start_y

        # --- state ---------------------------------------------------
        self._current_state: str = PetState.IDLE.value
        self._paused = False
        self._dragging = False
        self._drag_offset = QPoint()

        # walk state
        self._walk_dir: str = "right"
        self._walk_remaining = 0

        # reminder state
        self._reminder_enabled = True
        self._reminder_interval_min = self.DEFAULT_REMINDER_MIN
        self._reminder_target: tuple[int, int] | None = None
        self._reminder_origin: tuple[int, int] | None = None
        self._load_config()

        # --- pixmaps -------------------------------------------------
        self._px_idle = QPixmap(os.path.join(assets_dir, "pet_idle.png"))
        self._px_blink = QPixmap(os.path.join(assets_dir, "pet_blink.png"))
        self._px_sleep = QPixmap(os.path.join(assets_dir, "pet_sleep.png"))
        self._px_idle_left = self._px_idle.transformed(
            QTransform().scale(-1, 1)
        )

        # --- window --------------------------------------------------
        self._setup_window()
        self._label = QLabel(self)
        self._label.setGeometry(0, 0, self.width(), self.height())
        self._label.setPixmap(self._px_idle)
        self._label.setAlignment(Qt.AlignCenter)

        # --- timers --------------------------------------------------
        self._action_timer = QTimer(self)
        self._action_timer.timeout.connect(self._next_action)

        self._walk_timer = QTimer(self)
        self._walk_timer.timeout.connect(self._walk_step)

        self._blink_recover_timer = QTimer(self)
        self._blink_recover_timer.setSingleShot(True)
        self._blink_recover_timer.timeout.connect(self._recover_blink)

        self._sleep_recover_timer = QTimer(self)
        self._sleep_recover_timer.setSingleShot(True)
        self._sleep_recover_timer.timeout.connect(self._recover_sleep)

        self._blink_chance_timer = QTimer(self)
        self._blink_chance_timer.timeout.connect(self._maybe_blink)

        # --- reminder timer ------------------------------------------
        self._reminder_timer = QTimer(self)
        self._reminder_timer.setSingleShot(True)
        self._reminder_timer.timeout.connect(self._fire_reminder)

        # --- bubble --------------------------------------------------
        self._bubble = BubblePopup()

        # --- go! -----------------------------------------------------
        self._start_behaviour()

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        """Make the window frameless, transparent, always-on-top.
        Position: use explicit coords if given, otherwise pick a random
        spot on screen so multiple pets don't stack."""
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(self._px_idle.size())

        screen_geo = get_screen_geometry()
        pw, ph = self.width(), self.height()

        if self._start_x is not None and self._start_y is not None:
            x, y = self._start_x, self._start_y
        else:
            # Random position with margin so pets spread across the screen
            margin = 60
            x = random.randint(screen_geo.left() + margin,
                               max(screen_geo.left() + margin + 1,
                                   screen_geo.right() - pw - margin))
            y = random.randint(screen_geo.top() + margin,
                               max(screen_geo.top() + margin + 1,
                                   screen_geo.bottom() - ph - margin))

        self.move(x, y)

    # ------------------------------------------------------------------
    # Behaviour state machine
    # ------------------------------------------------------------------

    def _start_behaviour(self) -> None:
        """Enter idle and kick off the behaviour loop."""
        self._current_state = PetState.IDLE.value
        self._label.setPixmap(self._px_idle)
        self._schedule_next_idle_action()
        self._blink_chance_timer.start(1500)
        self._arm_reminder()

    def _schedule_next_idle_action(self, delay_ms: int | None = None) -> None:
        """Arm the action timer to fire after *delay_ms* (random 3-10 s)."""
        if self._paused:
            return
        if delay_ms is None:
            delay_ms = random_idle_duration_ms()
        self._action_timer.stop()
        self._action_timer.setInterval(delay_ms)
        self._action_timer.start()

    def _next_action(self) -> None:
        """Pick a new action when the idle timer fires."""
        if self._paused or self._current_state != PetState.IDLE.value:
            return
        self._action_timer.stop()

        roll = random.random()
        if roll < 0.30:
            self._start_walk()
        elif roll < 0.60:
            self._start_sleep()
        else:
            self._schedule_next_idle_action()  # keep idling

    # -- walk ----------------------------------------------------------

    def _start_walk(self) -> None:
        direction = random_walk_direction()
        dist = random_walk_distance()

        self._walk_dir = direction
        self._walk_remaining = dist

        if direction == "left":
            self._current_state = PetState.WALK_LEFT.value
            self._label.setPixmap(self._px_idle_left)
        else:
            self._current_state = PetState.WALK_RIGHT.value
            self._label.setPixmap(self._px_idle)

        self._walk_timer.start(WALK_TICK_MS)

    def _walk_step(self) -> None:
        """Move one animation tick during walking."""
        bounds = get_screen_geometry()
        cur = self.pos()

        # --- targeted walk (reminder) ---------------------------------
        if self._reminder_target is not None:
            tx, ty = self._reminder_target
            dx = tx - cur.x()
            dy = ty - cur.y()
            if abs(dx) <= WALK_STEP_PX and abs(dy) <= WALK_STEP_PX:
                self.move(tx, ty)
                self._walk_timer.stop()
                self._reminder_target = None
                # Don't return to idle — the reminder flow will handle it
                return
            # Move horizontally toward target
            step_x = WALK_STEP_PX if dx > 0 else -WALK_STEP_PX
            nx = cur.x() + step_x
            ny = cur.y()
            nx, ny = clamp_to_screen(nx, ny, self.width(), self.height())
            self.move(nx, ny)
            return

        # --- normal random walk ---------------------------------------
        if self._walk_dir == "left":
            nx = cur.x() - WALK_STEP_PX
            if nx < bounds.left():
                nx = bounds.left()
                self._walk_remaining = 0
        else:
            nx = cur.x() + WALK_STEP_PX
            if nx + self.width() > bounds.right():
                nx = bounds.right() - self.width()
                self._walk_remaining = 0

        self.move(nx, cur.y())
        self._walk_remaining -= WALK_STEP_PX

        if self._walk_remaining <= 0:
            self._walk_timer.stop()
            self._return_to_idle()

    # -- blink ---------------------------------------------------------

    def _maybe_blink(self) -> None:
        """Periodic check: should we blink now?"""
        if self._paused or self._current_state != PetState.IDLE.value:
            return
        if random.random() < 0.18:
            self._start_blink()

    def _start_blink(self) -> None:
        self._current_state = PetState.BLINK.value
        self._label.setPixmap(self._px_blink)
        self._blink_recover_timer.start(200)

    def _recover_blink(self) -> None:
        if self._current_state == PetState.BLINK.value:
            self._current_state = PetState.IDLE.value
            self._label.setPixmap(self._px_idle)

    # -- sleep ---------------------------------------------------------

    def _start_sleep(self) -> None:
        self._current_state = PetState.SLEEP.value
        self._label.setPixmap(self._px_sleep)
        self._sleep_recover_timer.start(5000)

    def _recover_sleep(self) -> None:
        if self._current_state == PetState.SLEEP.value:
            self._return_to_idle()

    def _return_to_idle(self) -> None:
        """Transition back to idle and re-arm action timer."""
        self._current_state = PetState.IDLE.value
        self._label.setPixmap(self._px_idle)
        self._schedule_next_idle_action()

    # -- health reminder -----------------------------------------------

    def _arm_reminder(self) -> None:
        """Start (or restart) the reminder countdown."""
        self._reminder_timer.stop()
        if self._reminder_enabled:
            self._reminder_timer.start(self._reminder_interval_min * 60 * 1000)

    def _fire_reminder(self) -> None:
        """Called when the reminder timer expires.

        Walk the pet to the centre-bottom of the screen and show a
        health-tip bubble, then walk back after the bubble hides.
        """
        if self._paused or not self._reminder_enabled:
            return
        # Stop any current walk so we can commandeer movement
        self._walk_timer.stop()
        self._action_timer.stop()

        # Save current position so we can walk back later
        self._reminder_origin = (self.pos().x(), self.pos().y())
        target = attention_position(self.width(), self.height())
        self._reminder_target = target

        # Walk toward target
        self._current_state = PetState.WALK_RIGHT.value
        self._label.setPixmap(self._px_idle)
        self._walk_dir = "right"
        self._walk_timer.start(WALK_TICK_MS)

        # Show the bubble once we arrive (use a short poll)
        QTimer.singleShot(800, self._show_reminder_bubble)

    def _show_reminder_bubble(self) -> None:
        """Display a health reminder bubble near the pet."""
        if self._paused:
            return
        msg = random.choice(HEALTH_REMINDERS)
        bubble_pos = QPoint(
            self.pos().x() + self.width() + 6,
            self.pos().y() - 12,
        )
        self._bubble.show_message(
            msg, bubble_pos,
            duration_ms=BubblePopup.REMINDER_DURATION_MS,
        )
        # After bubble hides, walk back to original position
        QTimer.singleShot(
            BubblePopup.REMINDER_DURATION_MS + 500,
            self._reminder_walk_back,
        )

    def _reminder_walk_back(self) -> None:
        """Walk back to where the pet was before the reminder."""
        if self._reminder_origin is None:
            self._return_to_idle()
            return
        self._walk_timer.stop()
        ox, oy = self._reminder_origin
        # Determine direction
        if ox < self.pos().x():
            self._walk_dir = "left"
            self._label.setPixmap(self._px_idle_left)
        else:
            self._walk_dir = "right"
            self._label.setPixmap(self._px_idle)
        self._reminder_target = (ox, oy)
        self._current_state = (
            PetState.WALK_LEFT.value if self._walk_dir == "left"
            else PetState.WALK_RIGHT.value
        )
        self._walk_timer.start(WALK_TICK_MS)
        # Use another poll to detect arrival
        QTimer.singleShot(2000, self._reminder_finish)

    def _reminder_finish(self) -> None:
        """Clean up after reminder walk-back."""
        self._walk_timer.stop()
        self._reminder_origin = None
        self._reminder_target = None
        self._return_to_idle()
        # Re-arm for next cycle
        self._arm_reminder()

    # ------------------------------------------------------------------
    # Mouse interaction
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_offset = (
                event.globalPosition().toPoint() - self.pos()
            )

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            nx = event.globalPosition().toPoint().x() - self._drag_offset.x()
            ny = event.globalPosition().toPoint().y() - self._drag_offset.y()
            nx, ny = clamp_to_screen(nx, ny, self.width(), self.height())
            self.move(nx, ny)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._dragging = False

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._dragging = False  # cancel any in-progress drag
            msg = random.choice(BUBBLE_MESSAGES)
            bubble_pos = QPoint(
                self.pos().x() + self.width() + 6,
                self.pos().y() - 12,
            )
            self._bubble.show_message(msg, bubble_pos)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #fff;
                border: 1px solid #ccc;
                border-radius: 6px;
                padding: 4px 0;
            }
            QMenu::item {
                padding: 7px 28px;
                font-size: 13px;
            }
            QMenu::item:selected { background: #e8e8e8; }
            QMenu::separator {
                height: 1px;
                background: #ddd;
                margin: 3px 8px;
            }
        """)

        upload_act = menu.addAction("📷  Upload New Pet")
        upload_act.triggered.connect(self._on_upload_new_pet)
        menu.addSeparator()

        if self._paused:
            resume_act = menu.addAction("▶  Resume")
            resume_act.triggered.connect(self._on_resume)
        else:
            pause_act = menu.addAction("⏸  Pause")
            pause_act.triggered.connect(self._on_pause)

        menu.addSeparator()

        # --- Reminder settings submenu --------------------------------
        reminder_menu = menu.addMenu("⏰  Reminder Settings")
        toggle_text = (
            "✅  Enabled" if self._reminder_enabled else "⬜  Disabled"
        )
        toggle_act = reminder_menu.addAction(toggle_text)
        toggle_act.triggered.connect(self._toggle_reminder)
        reminder_menu.addSeparator()

        for mins in (15, 30, 45, 60, 120):
            label = f"{'▸ ' if mins == self._reminder_interval_min else '   '}{mins} min"
            act = reminder_menu.addAction(label)
            act.triggered.connect(
                checked=False,  # noqa: ARG005
                slot=lambda m=mins: self._set_reminder_interval(m),
            )

        menu.addSeparator()
        exit_act = menu.addAction("❌  Exit")
        exit_act.triggered.connect(QApplication.instance().quit)

        menu.exec(event.globalPos())

    def _on_pause(self) -> None:
        self._paused = True
        self._action_timer.stop()
        self._walk_timer.stop()
        self._blink_chance_timer.stop()
        self._blink_recover_timer.stop()
        self._sleep_recover_timer.stop()
        self._reminder_timer.stop()

    def _on_resume(self) -> None:
        self._paused = False
        self._start_behaviour()

    # -- reminder settings ---------------------------------------------

    def _toggle_reminder(self) -> None:
        self._reminder_enabled = not self._reminder_enabled
        if self._reminder_enabled:
            self._arm_reminder()
        else:
            self._reminder_timer.stop()
        self._save_config()

    def _set_reminder_interval(self, mins: int) -> None:
        self._reminder_interval_min = mins
        self._save_config()
        if self._reminder_enabled:
            self._arm_reminder()

    # -- config persistence -------------------------------------------

    def _config_path(self) -> str:
        return os.path.join(self._assets_dir, "pet_config.json")

    def _load_config(self) -> None:
        import json
        path = self._config_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self._reminder_enabled = cfg.get("reminder_enabled", True)
                self._reminder_interval_min = cfg.get(
                    "reminder_interval_min", self.DEFAULT_REMINDER_MIN,
                )
            except Exception:
                pass  # use defaults

    def _save_config(self) -> None:
        import json
        cfg = {
            "reminder_enabled": self._reminder_enabled,
            "reminder_interval_min": self._reminder_interval_min,
        }
        try:
            with open(self._config_path(), "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass

    def _on_upload_new_pet(self) -> None:
        """Let the user select a new photo and regenerate all assets."""
        from core.image_processor import ImageProcessor

        was_paused = self._paused
        self._on_pause()

        path, _ = QFileDialog.getOpenFileName(
            self, "Select Your Pet Photo", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if not path:
            if not was_paused:
                self._on_resume()
            return

        proc = ImageProcessor()
        if not proc.process(path, self._assets_dir):
            QMessageBox.critical(self, "Error", "Failed to process the image.")
            if not was_paused:
                self._on_resume()
            return

        # Reload pixmaps
        self._px_idle = QPixmap(os.path.join(self._assets_dir, "pet_idle.png"))
        self._px_blink = QPixmap(os.path.join(self._assets_dir, "pet_blink.png"))
        self._px_sleep = QPixmap(os.path.join(self._assets_dir, "pet_sleep.png"))
        self._px_idle_left = self._px_idle.transformed(QTransform().scale(-1, 1))
        self.setFixedSize(self._px_idle.size())
        self._label.resize(self._px_idle.size())

        if not was_paused:
            self._on_resume()
        else:
            self._label.setPixmap(self._px_idle)

