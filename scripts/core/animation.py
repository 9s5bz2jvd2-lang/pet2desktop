"""
Animation utilities – sprite state definitions, bubble popup, constants.
"""

from enum import Enum
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt, QTimer, QPoint


class PetState(Enum):
    """Logical state of the desktop pet."""
    IDLE = "idle"
    WALK_LEFT = "walk_left"
    WALK_RIGHT = "walk_right"
    BLINK = "blink"
    SLEEP = "sleep"


# Health reminder messages shown periodically
HEALTH_REMINDERS: list[str] = [
    "🐾 站起来走走吧~",
    "👀 看看远处，让眼睛休息一下",
    "💧 该喝水啦！",
    "🧘 伸个懒腰，活动活动脖子",
    "🌿 深呼吸，放松肩膀~",
    "⏰ 已经坐很久了，动一动吧",
    "🪟 看看窗外的风景~",
    "💆 揉揉眼睛，休息几秒",
    "🏃 去倒杯水，顺便走走",
    "🌸 休息一下，效率更高哦",
    "☕ 该起来泡杯茶了",
    "🤸 扭扭腰，松松筋骨",
]


# Random messages shown on double-click
BUBBLE_MESSAGES: list[str] = [
    "(◕‿◕✿)",
    "♡＾▽＾♡",
    "✨",
    "💖",
    "(｡♥‿♥｡)",
    "🌸",
    "♪～(￣ε￣)",
    "(づ｡◕‿‿◕｡)づ",
    "🌟",
    "(≧∇≦)/",
    "💕",
    "(◠‿◠)",
    "🎀",
    "(✿◠‿◠)",
    "🍀",
    "(＾▽＾)",
    "💫",
    "(´｡• ᵕ •｡`)",
    "🎵",
    "(●´ω｀●)",
    "💝",
    "(⁄ ⁄>⁄ ▽ ⁄<⁄ ⁄)",
    "☁️",
    "(˘▽˘>ԅ( ˘⌣˘)",
]


class BubblePopup(QWidget):
    """A small, auto-hiding speech bubble that floats near the pet."""

    POPUP_DURATION_MS = 2500
    REMINDER_DURATION_MS = 6000  # longer display for health reminders

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self._label = QLabel(self)
        self._label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 235);
                border: 2px solid #bbb;
                border-radius: 14px;
                padding: 7px 15px;
                font-size: 15px;
                font-weight: bold;
                color: #333;
            }
        """)
        self._label.setAlignment(Qt.AlignCenter)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    def show_message(self, text: str, near_pos: QPoint,
                     duration_ms: int | None = None) -> None:
        """Display *text* in a bubble positioned at *near_pos*.

        *duration_ms* overrides the default display time (use
        ``REMINDER_DURATION_MS`` for health reminders).
        """
        self._label.setText(text)
        self._label.adjustSize()
        self.resize(self._label.size())
        self.move(near_pos)
        self.show()
        self._hide_timer.start(
            duration_ms if duration_ms is not None else self.POPUP_DURATION_MS
        )