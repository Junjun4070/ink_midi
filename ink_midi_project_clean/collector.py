import sys
import time
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, QEvent, QPointF
from PySide6.QtGui import QColor, QPainter, QPen

from utils import build_metadata, save_stroke_json


class DrawingCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(600, 600)
        self.setStyleSheet("background-color: white; border: 1px solid #ccc;")
        self.setAttribute(Qt.WA_TabletTracking)
        self.reset_data()

    def reset_data(self):
        self.strokes = []
        self.current_stroke = None
        self.start_time = None
        self.stroke_start_time = None
        self.is_tablet_drawing = False
        self.update()

    def _normalize_pressure(self, pressure):
        return max(0.0, min(1.0, float(pressure or 0.0)))

    def _make_point(self, pos, pressure, now, point_type):
        return {
            "x": round(pos.x(), 3),
            "y": round(pos.y(), 3),
            "t": round((now - self.start_time) * 1000.0, 3) if self.start_time else 0.0,
            "t_stroke": round((now - self.stroke_start_time) * 1000.0, 3) if self.stroke_start_time else 0.0,
            "p": round(self._normalize_pressure(pressure), 4),
            "type": point_type,
        }

    def _append_point(self, pos, pressure, now, point_type):
        if not self.current_stroke:
            return

        point = self._make_point(pos, pressure, now, point_type)
        points = self.current_stroke["points"]

        if points:
            last = points[-1]
            if (
                abs(last["x"] - point["x"]) < 0.001
                and abs(last["y"] - point["y"]) < 0.001
                and abs(last["t"] - point["t"]) < 0.001
            ):
                return

        points.append(point)

    def get_all_strokes(self):
        all_strokes = list(self.strokes)
        if self.current_stroke and len(self.current_stroke["points"]) >= 2:
            all_strokes.append(self.current_stroke)
        return all_strokes

    def tabletEvent(self, event):
        pos = event.position()
        pressure = event.pressure()
        now = time.perf_counter()

        if event.type() == QEvent.TabletPress:
            if self.start_time is None:
                self.start_time = now
            self.stroke_start_time = now
            self.is_tablet_drawing = True
            self.current_stroke = {"stroke_index": len(self.strokes), "points": []}
            self._append_point(pos, pressure, now, "press")

        elif event.type() == QEvent.TabletMove and self.is_tablet_drawing:
            self._append_point(pos, pressure, now, "move")

        elif event.type() == QEvent.TabletRelease and self.is_tablet_drawing:
            self._append_point(pos, pressure, now, "release")
            if self.current_stroke and len(self.current_stroke["points"]) >= 2:
                self.strokes.append(self.current_stroke)
            self.current_stroke = None
            self.is_tablet_drawing = False
            self.stroke_start_time = None

        event.accept()
        self.update()

    def _draw_guides(self, painter):
        painter.setPen(QPen(QColor(220, 220, 220), 1, Qt.DashLine))
        painter.drawLine(300, 0, 300, 600)
        painter.drawLine(0, 300, 600, 300)
        painter.setPen(QPen(QColor(180, 180, 180), 2, Qt.SolidLine))
        painter.drawRect(2, 2, 596, 596)

    def _draw_stroke(self, painter, stroke, color):
        points = stroke["points"]
        pen = QPen(color, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            pen.setWidthF(1.0 + p1["p"] * 12.0)
            painter.setPen(pen)
            painter.drawLine(QPointF(p1["x"], p1["y"]), QPointF(p2["x"], p2["y"]))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self._draw_guides(painter)

        for stroke in self.strokes:
            self._draw_stroke(painter, stroke, Qt.black)
        if self.current_stroke:
            self._draw_stroke(painter, self.current_stroke, QColor(0, 120, 255))


class CollectorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ink MIDI Collector")

        layout = QVBoxLayout()

        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("タイトル / ラベル:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("例: あ / signature / sketch")
        self.name_input.setText("untitled")
        title_row.addWidget(self.name_input)
        layout.addLayout(title_row)

        self.canvas = DrawingCanvas()
        layout.addWidget(self.canvas)

        self.save_btn = QPushButton("今の描画を保存 (JSON)")
        self.save_btn.setFixedHeight(48)
        self.save_btn.clicked.connect(self.save_json)
        layout.addWidget(self.save_btn)

        self.clear_btn = QPushButton("キャンバスをクリア")
        self.clear_btn.clicked.connect(self.clear_canvas)
        layout.addWidget(self.clear_btn)

        self.status_label = QLabel("液タブで自由に描いてください")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def clear_canvas(self):
        self.canvas.reset_data()
        self.status_label.setText("液タブで自由に描いてください")

    def save_json(self):
        strokes = self.canvas.get_all_strokes()
        if not strokes:
            self.status_label.setText("保存失敗: 描画データがありません")
            return

        label = self.name_input.text().strip() or "untitled"
        metadata = build_metadata(
            strokes=strokes,
            canvas_width=self.canvas.width(),
            canvas_height=self.canvas.height(),
            device="tablet",
        )
        filepath = save_stroke_json(
            label=label,
            category="general",
            style="normal",
            strokes=strokes,
            metadata=metadata,
            data_dir=Path(__file__).resolve().parent / "data",
        )

        self.status_label.setText(f"保存成功: {filepath.name}")
        self.canvas.reset_data()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CollectorWindow()
    window.show()
    sys.exit(app.exec())
