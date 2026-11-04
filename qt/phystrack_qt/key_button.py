"""
A button with its keyboard shortcut: the label on the left, and the key on the right in italics, as
in "Plots" ... "p". The button's text is the label; the key is set once, when the button is made.
"""

from PySide6.QtGui import QPalette
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QStyle, QStylePainter, QStyleOptionButton


class KeyButton(QPushButton):
    def __init__(self, label: str, key: str) -> None:
        super().__init__(label)
        self.key = key

    def paintEvent(self, event) -> None:
        painter = QStylePainter(self)
        option = QStyleOptionButton()
        self.initStyleOption(option)
        label, option.text = option.text, ""  # The bevel (and its flash outline) alone, then the text
        painter.drawControl(QStyle.ControlElement.CE_PushButton, option)
        contents = self.style().subElementRect(QStyle.SubElement.SE_PushButtonContents, option, self)
        contents = contents.adjusted(6, 0, -6, 0)
        group = QPalette.ColorGroup.Normal if self.isEnabled() else QPalette.ColorGroup.Disabled
        painter.setPen(self.palette().color(group, QPalette.ColorRole.ButtonText))
        align = Qt.AlignmentFlag.AlignVCenter
        painter.drawText(contents, align | Qt.AlignmentFlag.AlignLeft, label)
        if self.key:
            font = painter.font()
            font.setItalic(True)
            painter.setFont(font)
            painter.drawText(contents, align | Qt.AlignmentFlag.AlignRight, self.key)
