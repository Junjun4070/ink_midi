import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QTransform

from utils import load_stroke_json


class PlaybackCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(600, 600)
        self.setStyleSheet("background-color: white; border: 1px solid #ccc;")

        self.strokes = []
        self.current_time_ms = 0.0

        self.thickness_multiplier = 1.0
        self.is_rainbow = False
        self.show_pen_tip = True
        self.show_grid = True

        self.scale = 1.0
        self.offset = QPointF(0, 0)
        self.last_mouse_pos = QPointF()
        self.is_panning = False

    def load_strokes(self, strokes):
        self.strokes = strokes
        self.current_time_ms = 0.0
        self.reset_view()
        self.update()

    def set_time(self, time_ms):
        self.current_time_ms = time_ms
        self.update()

    def set_rainbow(self, enabled):
        self.is_rainbow = enabled
        self.update()

    def set_thickness(self, mult):
        self.thickness_multiplier = mult
        self.update()

    def set_show_pen_tip(self, show):
        self.show_pen_tip = show
        self.update()

    def set_show_grid(self, show):
        self.show_grid = show
        self.update()

    def reset_view(self):
        self.scale = 1.0
        self.offset = QPointF(0, 0)
        self.update()

    def _get_color_for_time(self, t):
        if self.is_rainbow:
            hue = int(t / 10) % 360
            return QColor.fromHsv(hue, 220, 200)
        return Qt.black

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        transform = QTransform()
        transform.translate(self.offset.x(), self.offset.y())
        transform.scale(self.scale, self.scale)
        painter.setTransform(transform)

        if self.show_grid:
            painter.setPen(QPen(QColor(220, 220, 220), 1.0 / self.scale, Qt.DashLine))
            painter.drawLine(300, -5000, 300, 5000)
            painter.drawLine(-5000, 300, 5000, 300)
            painter.setPen(QPen(QColor(180, 180, 180), 2.0 / self.scale, Qt.SolidLine))
            painter.drawRect(2, 2, 596, 596)

        if not self.strokes:
            return

        pen = QPen(Qt.black, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        last_pt = None

        for stroke in self.strokes:
            points = stroke["points"]
            if len(points) < 2:
                continue

            for i in range(len(points) - 1):
                p1 = points[i]
                p2 = points[i + 1]

                if p1["t"] > self.current_time_ms:
                    break

                if p2["t"] <= self.current_time_ms:
                    pen.setWidthF((1.0 + p1["p"] * 12.0) * self.thickness_multiplier)
                    pen.setColor(self._get_color_for_time(p1["t"]))
                    painter.setPen(pen)
                    painter.drawLine(QPointF(p1["x"], p1["y"]), QPointF(p2["x"], p2["y"]))
                    last_pt = p2
                elif p1["t"] <= self.current_time_ms < p2["t"]:
                    ratio = (self.current_time_ms - p1["t"]) / max(p2["t"] - p1["t"], 0.001)
                    ix = p1["x"] + (p2["x"] - p1["x"]) * ratio
                    iy = p1["y"] + (p2["y"] - p1["y"]) * ratio
                    ip = p1["p"] + (p2["p"] - p1["p"]) * ratio
                    pen.setWidthF((1.0 + ip * 12.0) * self.thickness_multiplier)
                    pen.setColor(self._get_color_for_time(self.current_time_ms))
                    painter.setPen(pen)
                    painter.drawLine(QPointF(p1["x"], p1["y"]), QPointF(ix, iy))
                    last_pt = {"x": ix, "y": iy, "p": ip, "t": self.current_time_ms}
                    break

        if self.show_pen_tip and last_pt:
            p_val = float(last_pt.get("p", 0.5))
            tip_color = self._get_color_for_time(last_pt.get("t", self.current_time_ms)) if self.is_rainbow else QColor(255, 50, 50)
            tip_color.setAlpha(int(150 + p_val * 105) if p_val > 0 else 100)
            painter.setPen(Qt.NoPen)
            painter.setBrush(tip_color)
            radius = (4.0 + p_val * 6.0) * self.thickness_multiplier
            painter.drawEllipse(QPointF(last_pt["x"], last_pt["y"]), radius, radius)

    def wheelEvent(self, event):
        mouse_pos = event.position()
        old_scale = self.scale
        factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        self.scale = max(0.1, min(self.scale * factor, 30.0))
        self.offset = mouse_pos - (mouse_pos - self.offset) * (self.scale / old_scale)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.is_panning = True
            self.last_mouse_pos = event.position()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self.is_panning:
            delta = event.position() - self.last_mouse_pos
            self.offset += delta
            self.last_mouse_pos = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self.is_panning = False
            self.setCursor(Qt.ArrowCursor)


class PlayerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ink MIDI Player")

        self.max_time_ms = 0.0
        self.current_time_ms = 0.0
        self.is_playing = False
        self.is_scrubbing = False

        self.timer_interval = 16
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer_tick)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout()

        self.info_label = QLabel("JSONファイルを読み込んでください")
        self.info_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.info_label)

        self.canvas = PlaybackCanvas()
        main_layout.addWidget(self.canvas)

        timeline = QHBoxLayout()
        self.play_btn = QPushButton("▶ 再生")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self.toggle_playback)
        timeline.addWidget(self.play_btn)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setEnabled(False)
        self.slider.sliderPressed.connect(self.on_slider_pressed)
        self.slider.sliderMoved.connect(self.on_slider_moved)
        self.slider.sliderReleased.connect(self.on_slider_released)
        timeline.addWidget(self.slider)

        self.time_label = QLabel("0.00s / 0.00s")
        timeline.addWidget(self.time_label)
        main_layout.addLayout(timeline)

        conf_group = QGroupBox("エフェクト / 表示")
        conf_layout = QVBoxLayout()

        row1 = QHBoxLayout()
        self.loop_cb = QCheckBox("ループ")
        self.loop_cb.setChecked(True)
        row1.addWidget(self.loop_cb)

        self.tip_cb = QCheckBox("ペン先")
        self.tip_cb.setChecked(True)
        self.tip_cb.toggled.connect(self.canvas.set_show_pen_tip)
        row1.addWidget(self.tip_cb)

        self.rainbow_cb = QCheckBox("虹")
        self.rainbow_cb.toggled.connect(self.canvas.set_rainbow)
        row1.addWidget(self.rainbow_cb)

        self.grid_cb = QCheckBox("格子")
        self.grid_cb.setChecked(True)
        self.grid_cb.toggled.connect(self.canvas.set_show_grid)
        row1.addWidget(self.grid_cb)

        conf_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("線の太さ:"))
        self.thick_slider = QSlider(Qt.Horizontal)
        self.thick_slider.setRange(5, 50)
        self.thick_slider.setValue(10)
        self.thick_slider.valueChanged.connect(lambda v: self.canvas.set_thickness(v / 10.0))
        row2.addWidget(self.thick_slider)

        self.reset_btn = QPushButton("表示リセット (100%)")
        self.reset_btn.clicked.connect(self.canvas.reset_view)
        row2.addWidget(self.reset_btn)
        conf_layout.addLayout(row2)

        conf_group.setLayout(conf_layout)
        main_layout.addWidget(conf_group)

        bottom = QHBoxLayout()
        self.load_btn = QPushButton("JSONを開く")
        self.load_btn.clicked.connect(self.load_json)
        bottom.addWidget(self.load_btn)

        self.speed_combo = QComboBox()
        self.speed_combo.addItem("0.5x", 0.5)
        self.speed_combo.addItem("1.0x", 1.0)
        self.speed_combo.addItem("2.0x", 2.0)
        self.speed_combo.addItem("5.0x", 5.0)
        self.speed_combo.addItem("10.0x", 10.0)
        self.speed_combo.setCurrentIndex(1)
        bottom.addWidget(self.speed_combo)

        main_layout.addLayout(bottom)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def update_time_label(self):
        self.time_label.setText(f"{self.current_time_ms / 1000:.2f}s / {self.max_time_ms / 1000:.2f}s")

    def load_json(self):
        self.pause()
        self.current_time_ms = 0.0

        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "JSONを開く",
            str(Path(__file__).resolve().parent / "data"),
            "*.json",
        )
        if not filepath:
            return

        data = load_stroke_json(filepath)
        strokes = data.get("strokes", [])
        if not strokes:
            return

        metadata = data.get("metadata", {})
        self.max_time_ms = float(metadata.get("total_duration_ms", 0)) or float(strokes[-1]["points"][-1]["t"])
        self.slider.setEnabled(True)
        self.slider.setRange(0, int(self.max_time_ms))
        self.slider.setValue(0)

        self.play_btn.setEnabled(True)
        self.canvas.load_strokes(strokes)
        self.info_label.setText(f"ロード完了: {data.get('label', 'Untitled')}")
        self.update_time_label()
        self.play()

    def on_timer_tick(self):
        if self.is_scrubbing:
            return

        mult = float(self.speed_combo.currentData())
        self.current_time_ms += self.timer_interval * mult

        if self.current_time_ms >= self.max_time_ms:
            if self.loop_cb.isChecked():
                self.current_time_ms = 0.0
            else:
                self.current_time_ms = self.max_time_ms
                self.pause()

        self.slider.setValue(int(self.current_time_ms))
        self.update_time_label()
        self.canvas.set_time(self.current_time_ms)

    def toggle_playback(self):
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def play(self):
        if self.current_time_ms >= self.max_time_ms and self.max_time_ms > 0:
            self.current_time_ms = 0.0
            self.slider.setValue(0)
            self.canvas.set_time(0.0)
            self.update_time_label()

        self.is_playing = True
        self.play_btn.setText("⏸ 停止")
        self.timer.start(self.timer_interval)

    def pause(self):
        self.is_playing = False
        self.play_btn.setText("▶ 再生")
        self.timer.stop()

    def on_slider_pressed(self):
        self.is_scrubbing = True

    def on_slider_moved(self, value):
        self.current_time_ms = float(value)
        self.update_time_label()
        self.canvas.set_time(self.current_time_ms)

    def on_slider_released(self):
        self.is_scrubbing = False
        self.current_time_ms = float(self.slider.value())
        self.update_time_label()
        self.canvas.set_time(self.current_time_ms)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PlayerWindow()
    window.show()
    sys.exit(app.exec())
