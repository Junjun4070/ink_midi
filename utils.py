import json
import re
import time
import unicodedata
from pathlib import Path


def build_metadata(strokes, canvas_width, canvas_height, device="tablet"):
    if not strokes:
        return {
            "device": device,
            "canvas_width": canvas_width,
            "canvas_height": canvas_height,
            "stroke_count": 0,
            "point_count": 0,
            "total_duration_ms": 0,
            "bbox": {"x": 0, "y": 0, "w": 0, "h": 0},
        }

    min_x = float("inf")
    min_y = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")
    point_count = 0
    total_duration_ms = 0.0

    for stroke in strokes:
        for pt in stroke["points"]:
            point_count += 1
            min_x = min(min_x, pt["x"])
            min_y = min(min_y, pt["y"])
            max_x = max(max_x, pt["x"])
            max_y = max(max_y, pt["y"])
            total_duration_ms = max(total_duration_ms, float(pt["t"]))

    return {
        "device": device,
        "canvas_width": canvas_width,
        "canvas_height": canvas_height,
        "stroke_count": len(strokes),
        "point_count": point_count,
        "total_duration_ms": round(total_duration_ms, 3),
        "bbox": {
            "x": round(min_x, 3),
            "y": round(min_y, 3),
            "w": round(max_x - min_x, 3),
            "h": round(max_y - min_y, 3),
        },
    }


def sanitize_label_for_filename(label: str) -> str:
    label = unicodedata.normalize("NFKC", label).strip()
    if not label:
        return "untitled"

    parts = []
    for ch in label:
        if re.match(r"[A-Za-z0-9_-]", ch):
            parts.append(ch)
        elif ch.isspace():
            parts.append("_")
        else:
            parts.append(f"u{ord(ch):04x}")

    sanitized = "".join(parts)
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized[:60] or "untitled"


def save_stroke_json(label, category, style, strokes, metadata, data_dir):
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    timestamp_sec = int(time.time())
    timestamp_ms = int(time.time() * 1000)

    payload = {
        "version": "0.1.0",
        "label": label,
        "category": category,
        "style": style,
        "metadata": {**metadata, "timestamp": timestamp_sec},
        "strokes": strokes,
    }

    safe_label = sanitize_label_for_filename(label)
    filepath = data_dir / f"stroke_{safe_label}_{timestamp_ms}.json"

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return filepath


def load_stroke_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
