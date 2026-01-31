# Ableton Music Pattern Generation Skill

このスキルはAbleton Live用のMIDIパターンを自然言語から生成するためのガイドです。

## MIDIノート形式

`execute_pattern`ツールで使用するノート形式:
```python
(pitch, start_time, duration, velocity, mute)
```

| パラメータ | 範囲 | 説明 |
|-----------|------|------|
| pitch | 0-127 | MIDIノート番号 (60=C4) |
| start_time | 0.0~ | 拍単位 (4.0 = 1小節) |
| duration | 0.0~ | 拍単位 |
| velocity | 0-127 | 音の強さ |
| mute | 0/1 | ミュート |

---

## ドラムマップ (General MIDI)

```python
KICK = 36
SNARE = 38
RIMSHOT = 37
CLAP = 39
CLOSED_HAT = 42
OPEN_HAT = 46
PEDAL_HAT = 44
TOM_LOW = 45
TOM_MID = 47
TOM_HIGH = 50
CRASH = 49
RIDE = 51
```

---

## 音階とスケール

### ルートノート
```python
C = 0, D = 2, E = 4, F = 5, G = 7, A = 9, B = 11
# オクターブ: C1=24, C2=36, C3=48, C4=60, C5=72
```

### スケール（半音オフセット）
```python
MAJOR = [0, 2, 4, 5, 7, 9, 11]
MINOR = [0, 2, 3, 5, 7, 8, 10]
DORIAN = [0, 2, 3, 5, 7, 9, 10]
PENTATONIC_MAJOR = [0, 2, 4, 7, 9]
PENTATONIC_MINOR = [0, 3, 5, 7, 10]
BLUES = [0, 3, 5, 6, 7, 10]
```

### コード構成音
```python
MAJOR_CHORD = [0, 4, 7]
MINOR_CHORD = [0, 3, 7]
MAJ7 = [0, 4, 7, 11]
MIN7 = [0, 3, 7, 10]
DOM7 = [0, 4, 7, 10]
DIM = [0, 3, 6]
AUG = [0, 4, 8]
SUS4 = [0, 5, 7]
```

---

## ジャンル別リズムパターン

### EDM / House (BPM 120-130)
```python
# Four on the floor + オフビートハイハット
for bar in range(bars):
    for beat in range(4):
        t = bar * 4 + beat
        notes.append((36, t, 0.5, 100, 0))        # Kick: 4つ打ち
        notes.append((42, t + 0.5, 0.25, 70, 0))  # HH: オフビート
    notes.append((39, bar * 4 + 1, 0.25, 90, 0))  # Clap: 2, 4拍
    notes.append((39, bar * 4 + 3, 0.25, 90, 0))
```

### Trap (BPM 140-160)
```python
# ダブルタイムハイハット + 808キック
for bar in range(bars):
    t = bar * 4
    notes.append((36, t, 0.5, 100, 0))            # Kick: 1拍目
    notes.append((36, t + 2.5, 0.25, 90, 0))      # Kick: シンコペ
    notes.append((38, t + 1, 0.25, 100, 0))       # Snare: 2拍目
    notes.append((38, t + 3, 0.25, 100, 0))       # Snare: 4拍目
    for i in range(16):                           # HH: 16分
        vel = 90 if i % 4 == 0 else 60
        notes.append((42, t + i * 0.25, 0.1, vel, 0))
```

### Lo-Fi Hip Hop (BPM 70-90)
```python
# ゆるいスウィング + ゴーストノート
swing = 0.1  # スウィング量
for bar in range(bars):
    t = bar * 4
    notes.append((36, t, 0.5, 85, 0))
    notes.append((36, t + 2.25, 0.25, 75, 0))     # 遅めのキック
    notes.append((38, t + 1 + swing, 0.25, 80, 0))
    notes.append((38, t + 3 + swing, 0.25, 80, 0))
    # ゴーストスネア
    notes.append((38, t + 2.5, 0.1, 40, 0))
```

### Drum & Bass (BPM 170-180)
```python
# 2ステップ + 高速ブレイクビーツ
for bar in range(bars):
    t = bar * 4
    notes.append((36, t, 0.25, 100, 0))
    notes.append((38, t + 1, 0.25, 100, 0))
    notes.append((36, t + 1.75, 0.25, 90, 0))     # シンコペキック
    notes.append((38, t + 3, 0.25, 100, 0))
    # 高速ハイハット
    for i in range(8):
        notes.append((42, t + i * 0.5, 0.1, 70, 0))
```

### Funk (BPM 100-120)
```python
# シンコペーション重視
for bar in range(bars):
    t = bar * 4
    notes.append((36, t, 0.25, 100, 0))
    notes.append((36, t + 0.75, 0.25, 80, 0))     # &で入る
    notes.append((36, t + 2.5, 0.25, 90, 0))      # 3拍裏
    notes.append((38, t + 1, 0.25, 100, 0))
    notes.append((38, t + 3, 0.25, 100, 0))
    # 16分ハイハット with アクセント
    for i in range(16):
        vel = 90 if i % 4 == 0 else (70 if i % 2 == 0 else 50)
        notes.append((42, t + i * 0.25, 0.1, vel, 0))
```

### Reggae / Dub (BPM 70-90)
```python
# One Drop - 1拍目キックなし
for bar in range(bars):
    t = bar * 4
    notes.append((36, t + 2.5, 0.5, 90, 0))       # 3拍目裏にキック
    notes.append((37, t + 1, 0.25, 100, 0))       # リムショット: 2, 4
    notes.append((37, t + 3, 0.25, 100, 0))
```

---

## ベースラインパターン

### ルートオクターブ（基本）
```python
root = 36  # C1
for bar in range(bars):
    t = bar * 4
    notes.append((root, t, 0.5, 100, 0))
    notes.append((root + 12, t + 2, 0.5, 90, 0))  # オクターブ上
```

### ウォーキングベース
```python
root = 36
scale = [0, 2, 4, 5, 7, 9, 10, 12]  # ドリアン
for bar in range(bars):
    for beat in range(4):
        note = root + scale[beat % len(scale)]
        notes.append((note, bar * 4 + beat, 0.9, 90, 0))
```

### シンコペーションベース
```python
root = 36
for bar in range(bars):
    t = bar * 4
    notes.append((root, t, 0.25, 100, 0))
    notes.append((root + 7, t + 0.75, 0.25, 85, 0))   # 5度
    notes.append((root + 5, t + 1.5, 0.5, 90, 0))     # 4度
    notes.append((root, t + 2.25, 0.25, 80, 0))
    notes.append((root + 3, t + 3, 0.5, 95, 0))       # 短3度
```

### 808ベース（Trap）
```python
root = 24  # 低いC0
for bar in range(bars):
    t = bar * 4
    notes.append((root, t, 1.5, 100, 0))             # 長いスライド
    notes.append((root + 5, t + 2, 0.5, 90, 0))
    notes.append((root, t + 2.75, 1.0, 95, 0))
```

---

## コード進行パターン

### ポップ進行 (I-V-vi-IV)
```python
root = 48  # C3
progressions = [
    [0, 4, 7],      # C (I)
    [7, 11, 14],    # G (V)
    [9, 12, 16],    # Am (vi)
    [5, 9, 12],     # F (IV)
]
for bar, chord in enumerate(progressions):
    t = bar * 4
    for note in chord:
        notes.append((root + note, t, 3.5, 80, 0))
```

### ダークプログレッション (i-VI-III-VII)
```python
root = 48
progressions = [
    [0, 3, 7],      # Cm (i)
    [8, 12, 15],    # Ab (VI)
    [3, 7, 10],     # Eb (III)
    [10, 14, 17],   # Bb (VII)
]
```

### Lo-Fi進行 (ii7-V7-Imaj7-vi7)
```python
root = 48
progressions = [
    [2, 5, 9, 12],   # Dm7
    [7, 11, 14, 17], # G7
    [0, 4, 7, 11],   # Cmaj7
    [9, 12, 16, 19], # Am7
]
```

---

## 雰囲気からの変換ルール

### 「エモい」「切ない」
- **スケール**: マイナー、ドリアン
- **コード**: マイナーセブンス多用
- **リズム**: ゆっくり、スペース多め
- **ベロシティ**: 控えめ (60-80)

### 「攻撃的」「激しい」
- **スケール**: マイナー、フリジアン
- **リズム**: 速め、16分多用
- **ベロシティ**: 強め (90-127)
- **キック**: ダブルキック

### 「明るい」「ハッピー」
- **スケール**: メジャー、リディアン
- **コード**: メジャーセブンス
- **リズム**: 跳ねる感じ
- **ベロシティ**: 中程度 (70-90)

### 「浮遊感」「アンビエント」
- **スケール**: ペンタトニック、全音階
- **コード**: sus4、add9
- **リズム**: まばら、長いノート
- **ベロシティ**: 弱め (40-70)

### 「グルーヴィー」「ファンキー」
- **リズム**: シンコペーション多用
- **ゴーストノート**: スネアの弱音追加
- **ベース**: 16分のスタッカート

---

## 使用例

### 例1: 「トラップ風の暗いビートを4小節」
```python
notes = []
for bar in range(4):
    t = bar * 4
    # 808キック
    notes.append((36, t, 0.5, 100, 0))
    notes.append((36, t + 2.5, 0.25, 90, 0))
    # スネア
    notes.append((38, t + 1, 0.25, 100, 0))
    notes.append((38, t + 3, 0.25, 100, 0))
    # ハイハットロール
    for i in range(16):
        vel = 80 if i % 4 == 0 else 50
        notes.append((42, t + i * 0.25, 0.1, vel, 0))
```

### 例2: 「Lo-Fiなコード進行を8小節」
```python
notes = []
root = 48
swing = 0.08
chords = [
    ([2, 5, 9, 12], 2),   # Dm7, 2小節
    ([7, 11, 14, 17], 2), # G7
    ([0, 4, 7, 11], 2),   # Cmaj7
    ([9, 12, 16, 19], 2), # Am7
]
beat = 0
for chord, length in chords:
    for note in chord:
        notes.append((root + note, beat + swing, length * 4 - 0.5, 70, 0))
    beat += length * 4
```

### 例3: 「ファンキーなベースライン」
```python
notes = []
root = 36
for bar in range(4):
    t = bar * 4
    notes.append((root, t, 0.2, 100, 0))
    notes.append((root, t + 0.5, 0.15, 70, 0))      # ゴースト
    notes.append((root + 7, t + 0.75, 0.2, 90, 0))  # 5度
    notes.append((root + 5, t + 1.25, 0.2, 85, 0))  # 4度
    notes.append((root, t + 2, 0.3, 95, 0))
    notes.append((root + 10, t + 2.75, 0.2, 80, 0)) # 7度
    notes.append((root + 7, t + 3.25, 0.2, 85, 0))
    notes.append((root + 5, t + 3.75, 0.2, 75, 0))
```

---

## 推奨音源

| 種類 | Ableton標準音源 | 特徴 |
|------|----------------|------|
| ドラム | Drum Rack | 自由度高い |
| ベース | Operator, Wavetable | シンセベース |
| コード | Electric, Wavetable | パッド系 |
| リード | Analog, Drift | メロディ |

---

## execute_pattern ツールの使い方

```
ツール: execute_pattern
パラメータ:
  - track_name: トラック名（例: "Funky Bass"）
  - notes_code: ノートを生成するPythonコード
  - bars: 小節数（デフォルト: 4）
```

`notes_code`内では:
- `bars` 変数が利用可能
- `notes` リストにノートを追加
- `random`, `math` モジュールが利用可能
- `range`, `len`, `min`, `max`, `enumerate`, `zip` 等が利用可能
