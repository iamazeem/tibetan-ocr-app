from PySide6.QtGui import QIcon, QEnterEvent
from PySide6.QtWidgets import QPushButton


class HeaderButton(QPushButton):
    def __init__(
            self,
            normal_icon: QIcon,
            hover_icon: QIcon,
            width: int = 40,
            height: int = 40,
            object_name: str = "MenuButton",
            parent=None):

        super().__init__()
        self.parent = parent
        self.setObjectName(object_name)
        self.normal_icon = normal_icon
        self.hover_icon = hover_icon
        self.active_icon = self.hover_icon

        self.setFixedWidth(width)
        self.setFixedHeight(height)

        self.setIcon(self.normal_icon)
        self.is_active = False

    def set_icon(self, icon: QIcon) -> None:
        self.normal_icon = icon
        self.setIcon(icon)

    def set_hover_icon(self, icon: QIcon) -> None:
        self.hover_icon = icon

    def activate(self) -> None:
        self.is_active = True
        self.setIcon(self.hover_icon)

    def deactivate(self) -> None:
        self.is_active = False
        self.setIcon(self.normal_icon)

    def enterEvent(self, event):
        if isinstance(event, QEnterEvent):
            self.setIcon(self.hover_icon)
            return super().enterEvent(event)

    def leaveEvent(self, event):
        """
        Note: the check 'if isinstance(event, QEvent.QLeaveEvent)' kind of fails.
        However, checking for the internal event value works, see: https://doc.qt.io/qt-6/qevent.html
        """
        if event.type() == 11:
            if not self.is_active:
                self.setIcon(self.normal_icon)
            return super().leaveEvent(event)