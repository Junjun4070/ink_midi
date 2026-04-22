# Ink MIDI (Specification Draft v0.1.0)

Ink MIDIは、デジタル描画のプロセスを**時間付きストロークデータ**として記録・再生するためのオープンなデータフォーマット案である。  
描画を静止画という「結果」だけでなく、運筆・時間・筆圧を伴う「過程」として扱う。

---

## 概要

従来の形式は、それぞれ次のものを保存する。

- **PNG / JPG**: 描画結果
- **MP4 / タイムラプス**: 再生結果

Ink MIDIはそれらとは異なり、描画そのものを**行為のデータ**として保持する。  
各ストロークは、座標・時間・筆圧の列として記録される。  
これにより、描画は単なる映像ではなく、**再生・解析・再解釈可能なプロセス**になる。

---

## Why “MIDI”?

MIDIが音そのものではなく、**演奏情報**を記録する形式であるのと同様に、  
Ink MIDIは画像そのものではなく、**描画情報**を記録することを目指す。

- MIDI: 音の結果ではなく、演奏の指示
- Ink MIDI: 絵の結果ではなく、描画の指示

この意味で、Ink MIDIは描画の「楽譜」に相当する。

---

## 主な内容

このパッケージには以下が含まれる。

- `app.pyw`  
  ランチャー

- `collector.py`  
  液タブ入力を取得してJSON保存するリファレンス実装

- `player.py`  
  Ink MIDI JSONを再生するPython版プレイヤー

- `web_viewer.html`  
  ブラウザだけで再生できるWeb版ビューア

- `utils.py`  
  共通処理

- `data/sample_hiragana_a.json`  
  サンプルデータ

---

## 使い方

### Python版
PySide6 を入れた上で、次のいずれかを実行する。

```bash
python app.pyw
```

または

```bash
python collector.py
python player.py
```

### Web版
`web_viewer.html` をブラウザで開き、JSONをドラッグ＆ドロップする。

---

## データ構造（Draft）

```json
{
  "version": "0.1.0",
  "label": "Artwork_ID",
  "metadata": {
    "total_duration_ms": 1234,
    "timestamp": "2026-04-21T05:00:00Z"
  },
  "strokes": [
    {
      "points": [
        { "x": 100.0, "y": 200.0, "t": 0, "p": 0.50 },
        { "x": 105.0, "y": 205.0, "t": 16, "p": 0.55 }
      ]
    }
  ]
}
```

---

## Origin

- **Created**: 2026-04-21
- **Author**: Origami Lover（折り紙が好きな人）

本リポジトリは、Ink MIDIという概念・名称・初期仕様・初期実装を公開記録として残すことを目的とする。

---

## Statement

Ink MIDI is a public draft specification for treating drawing as replayable time-based stroke data.

This repository serves as a timestamped public record of that formulation.

---

## License

MIT License
