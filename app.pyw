import sys
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget
from PySide6.QtCore import Qt

from collector import CollectorWindow
from player import PlayerWindow


class Launcher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ink MIDI Launcher")
        self.setFixedWidth(360)

        self.collector_window = None
        self.player_window = None

        layout = QVBoxLayout()
        layout.setSpacing(12)

        title = QLabel("Ink MIDI")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

        subtitle = QLabel("手書きをデータとして保存して、あとで再生する")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size: 13px; color: #444; padding-bottom: 6px;")
        layout.addWidget(subtitle)

        collect_btn = QPushButton("書いて保存する")
        collect_btn.setFixedHeight(52)
        collect_btn.clicked.connect(self.open_collector)
        layout.addWidget(collect_btn)

        play_btn = QPushButton("JSONを読み込んで再生する")
        play_btn.setFixedHeight(52)
        play_btn.clicked.connect(self.open_player)
        layout.addWidget(play_btn)

        hint = QLabel(
            "collector.py は筆跡収集、player.py は再生用。\n"
            "この画面は入口だけをまとめたランチャー。"
        )
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 12px; color: #666; padding-top: 6px;")
        layout.addWidget(hint)

        self.setLayout(layout)

    def open_collector(self):
        self.collector_window = CollectorWindow()
        self.collector_window.show()

    def open_player(self):
        self.player_window = PlayerWindow()
        self.player_window.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Launcher()
    window.show()
    sys.exit(app.exec())
