# Ableton MCP 開発ガイド

## プロジェクト概要

Ableton LiveをClaude Desktop/MCPから自然言語で操作するためのサーバー。
AbletonOSC経由でAbleton Liveと通信し、MIDIトラック/クリップ/ノートを生成する。

## 技術スタック

- Python 3.10+
- MCP (Model Context Protocol) - Claude Desktopとの通信
- python-osc - AbletonOSCとのOSC通信
- uv - パッケージ管理

## ディレクトリ構成

```
AbletonMCP/
├── src/
│   ├── mcp_server.py      # MCPサーバー本体（ツール定義・ハンドラ）
│   ├── ableton_osc.py     # OSC通信クラス
│   ├── synth_generator.py # メロディ/ベース/コード生成
│   ├── arrangement_generator.py # アレンジメント生成
│   ├── mixing_assistant.py     # ミキシング提案
│   ├── sample_search.py        # サンプル検索
│   ├── agent.py           # CLIエージェント（旧）
│   └── cli.py             # CLIエントリポイント
├── skills/
│   └── ableton-music/
│       └── SKILL.md       # パターン生成リファレンス
├── pyproject.toml         # プロジェクト設定
└── claude_desktop_config.json  # Claude Desktop設定例
```

## 開発環境セットアップ

```bash
# uv でインストール
uv sync

# 仮想環境有効化（Windows）
.venv\Scripts\activate

# 構文チェック
.venv/Scripts/python.exe -m py_compile src/mcp_server.py
```

## MCPサーバー起動

```bash
# 直接起動
.venv/Scripts/python.exe -m src.mcp_server

# Claude Desktop設定
# %APPDATA%\Claude\claude_desktop_config.json に追加
```

## 主要クラス・関数

### mcp_server.py

| 関数/クラス | 説明 |
|------------|------|
| `AbletonState` | グローバル状態管理（tempo, key, tracks等） |
| `handle_list_tools()` | MCPツール一覧定義 |
| `handle_call_tool()` | ツール実行ハンドラ |
| `MUSIC_PATTERN_GUIDE` | execute_pattern用プロンプト |

### ableton_osc.py

| メソッド | OSCアドレス | 説明 |
|---------|------------|------|
| `play()` | `/live/song/start_playing` | 再生開始 |
| `stop()` | `/live/song/stop_playing` | 停止 |
| `set_tempo(bpm)` | `/live/song/set/tempo` | テンポ設定 |
| `create_midi_track(index)` | `/live/song/create_midi_track` | MIDIトラック作成 |
| `create_clip(track, clip, length)` | `/live/clip_slot/create_clip` | クリップ作成 |
| `add_notes(track, clip, notes)` | `/live/clip/add/notes` | ノート追加 |
| `load_device(track, uri)` | `/live/track/load_device` | デバイス読み込み |

### synth_generator.py

| クラス | 説明 |
|-------|------|
| `Scale` | スケール定義（MAJOR, MINOR, DORIAN等） |
| `ChordType` | コード定義（MAJOR, MIN7, DOM7等） |
| `MelodyGenerator` | メロディ生成 |
| `BasslineGenerator` | ベースライン生成 |
| `ChordProgressionGenerator` | コード進行生成 |
| `ArpeggiatorGenerator` | アルペジオ生成 |

## MIDIノート形式

```python
(pitch, start_time, duration, velocity, mute)
# pitch: 0-127 (60=C4, 36=C2)
# start_time: 拍単位 (4.0 = 1小節)
# duration: 拍単位
# velocity: 0-127
# mute: 0/1 または False/True
```

## MCPツール一覧

### 基本操作
- `ableton_connect` - Abletonに接続
- `set_tempo` - テンポ設定
- `play` / `stop` - 再生/停止

### トラック生成
- `create_drum_track` - ドラムトラック（プリセットパターン）
- `create_melody` - メロディ生成
- `create_bassline` - ベースライン生成
- `create_chords` - コード進行生成
- `create_arpeggio` - アルペジオ生成
- `execute_pattern` - **カスタムMIDIパターン（動的コード実行）**

### エフェクト・ミキシング
- `add_effect` - エフェクト追加
- `add_sidechain` - サイドチェイン設定
- `set_track_volume` - ボリューム設定
- `fix_mixing_issue` - ミキシング提案

### その他
- `generate_arrangement` - アレンジメント生成
- `modify_mood` - 雰囲気変更
- `search_samples` - サンプル検索
- `get_project_info` - プロジェクト情報
- `list_genres` - ジャンル一覧

## execute_pattern ツール

動的にPythonコードを実行してMIDIパターンを生成する。

```python
# safe_builtins で許可されている関数
range, len, int, float, abs, min, max, round
list, tuple, enumerate, zip, sum, sorted, reversed
random, math  # モジュールとして利用可能
```

### 例
```python
notes = []
for bar in range(bars):
    t = bar * 4
    notes.append((36, t, 0.5, 100, 0))  # Kick
    notes.append((38, t + 1, 0.25, 100, 0))  # Snare
```

## OSCポート設定

| 用途 | ポート |
|------|--------|
| AbletonOSC受信 | 11000 |
| Python送受信 | 11001 |

## AbletonOSC 必須設定

Ableton Liveに [AbletonOSC](https://github.com/ideoforms/AbletonOSC) をインストール必要。

---

## ⚠️ Ableton エフェクト操作時の注意事項

### EQ Eight: フィルタータイプによるパラメータの解釈の違い

EQ Eightでは、**Filter Type（フィルタータイプ）によってGainパラメータの意味が変わる**。
これを理解せずに操作すると、意図しない結果になる。

| Filter Type | Gainの意味 |
|-------------|-----------|
| Bell / Peak | そのままブースト/カット量（+dB = ブースト、-dB = カット） |
| Low Shelf / High Shelf | シェルフのブースト/カット量 |
| **Low Pass / High Pass** | **レゾナンス量**（カットオフ周辺の強調）※カット量ではない |
| Notch | 帯域幅の調整 |

### ローパス/ハイパス使用時の重要ポイント

- **Frequency**: カットオフ周波数（この周波数以上/以下をカット）
- **Gain**: レゾナンス（カットオフ付近のブースト量）
- フィルター自体がカット処理を行うので、**マイナスGainでカットするのではない**
- Gainを上げると、カットオフ周波数付近が強調される（キャラクターが出る）

### 具体例

**高域をカットしてLofi感を出したい場合：**

| 方法 | 設定 | 結果 |
|------|------|------|
| ❌ 間違い | Bell + Frequency 8kHz + Gain -4dB | 8kHz付近だけカット（狭い範囲） |
| ✅ 正解 | Low Pass 12dB + Frequency 8kHz | 8kHz以上を全てカット（広い範囲） |
| ✅ 正解 | Low Pass 24dB + Frequency 6kHz | より急峻にカット |

**ローパス設定時のGain：**
- Gain +0dB → フラットなカットオフ
- Gain +5dB → カットオフ付近がブーストされ、キャラクターが出る
- マイナスGainにしても「よりカットされる」わけではない

### OSCでEQ Eightを操作する際のパラメータインデックス

Band 4の例（他のバンドも同様のパターン）：

| パラメータ | インデックス | 値の範囲 |
|-----------|-------------|---------|
| 4 Filter On A | 36 | 0/1 |
| 4 Filter Type A | 37 | 0-7（0=Low Pass 12, 1=Low Pass 24, 5=Bell...） |
| 4 Frequency A | 38 | 0.0-1.0（周波数を正規化した値） |
| 4 Gain A | 39 | 0.0-1.0（-15dB〜+15dBを正規化） |
| 4 Resonance A | 40 | 0.0-1.0 |

### Filter Type の値

| 値 | タイプ |
|----|--------|
| 0 | Low Pass 12dB |
| 1 | Low Pass 24dB |
| 2 | High Pass 12dB |
| 3 | High Pass 24dB |
| 4 | Band Pass |
| 5 | Bell |
| 6 | Notch |
| 7 | Low Shelf |
| 8 | High Shelf |

この仕様を理解して、適切なフィルタータイプとパラメータを選択すること。

---

## テスト

```bash
# pytest実行
uv run pytest

# 単体テスト
.venv/Scripts/python.exe -c "from src.synth_generator import *; print(create_melody('C', 'minor', 2))"
```

## 注意事項

- `state.mock_mode = True` の時はAbleton未接続でもツールが動作（テスト用）
- OSCソケットは一度しか起動できない（再接続時は `stop_listener()` が必要）
- `execute_pattern` は `exec()` を使用するためセキュリティに注意

## 関連リンク

- [MCP Specification](https://modelcontextprotocol.io/)
- [AbletonOSC](https://github.com/ideoforms/AbletonOSC)
- [python-osc](https://github.com/attwad/python-osc)