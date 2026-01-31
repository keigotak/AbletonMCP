🌐 [English](README.md) | **日本語**

# 🎹 Ableton MCP

自然言語でAbleton Liveを完全コントロールするAIエージェント。

## 🚀 2つのモード

### 1️⃣ MCP版（推奨）- APIキー不要！
Claude Desktopから直接使用。APIキー不要で、チャットするだけでAbletonを操作。

### 2️⃣ CLI版 - スタンドアロン
Anthropic APIキーを使用してターミナルから操作。

> ⚠️ **注意**: CLI版は実験的な機能であり、十分なテストが行われていません。

---

## 🌟 MCP版セットアップ（APIキー不要）

### 1. インストール

```bash
cd ableton-mcp
pip install -e .
```

### 2. Claude Desktop設定

Claude Desktopの設定ファイルを編集：

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ableton-mcp": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/path/to/ableton-mcp"
    }
  }
}
```

⚠️ `cwd` をableton-mcpフォルダの実際のパスに変更してください。

📖 **Windowsユーザー向け**: 詳細な手順は [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md) を参照してください。

### 3. AbletonOSCをインストール

**方法A: Max for Liveデバイス（簡単）**
1. [AbletonOSC](https://github.com/ideoforms/AbletonOSC/releases)をダウンロード
2. `AbletonOSC.amxd` をAbleton Liveのトラックにドラッグ

**方法B: Remote Script（推奨）**
1. https://github.com/ideoforms/AbletonOSC からダウンロード
2. Remote Scriptsフォルダに配置:
   - **Windows**: `C:\Users\<ユーザー名>\Documents\Ableton\User Library\Remote Scripts\AbletonOSC`
   - **macOS**: `~/Music/Ableton/User Library/Remote Scripts/AbletonOSC`
3. フォルダ構成: `AbletonOSC\__init__.py` が直下にある状態
4. Ableton Live → Preferences → Link/Tempo/MIDI → Control Surface → **AbletonOSC** を選択

### 4. Claude Desktopを再起動

再起動後、チャットで直接Abletonを操作できます！

```
You: 4分のEDMトラックを作って

Claude: [generate_arrangement ツールを使用]
アレンジメントを生成しました...

You: トラップ風のドラムを追加して

Claude: [create_drum_track ツールを使用]
ドラムトラック 'Drums' を作成しました...
```

---

## ✨ 機能

### 🥁 ドラム/リズム生成
- 基本ビート、4つ打ち、トラップ、ブレイクビート、D&B
- カスタムパターン作成

### 🎹 メロディ/シンセ生成
- **メロディ**: スケールベースの自動生成（密度、輪郭を調整可能）
- **ベースライン**: basic, walking, syncopated, octave, arpeggiated
- **コード進行**: pop, jazz, sad, epic, dark, edm, lofi, cinematic
- **アルペジオ**: up, down, updown, random（8th/16th/triplet）

### 🔍 サンプル検索
- ローカルライブラリ検索（Ableton Core Library, Splice等）
- Freesound API対応
- 日本語クエリ対応（「エスニックなパーカッション」など）

### 🎚️ ミキシング支援
- 周波数衝突検出（キックとベースなど）
- サイドチェインコンプレッション自動設定
- EQ提案
- レベル/ダイナミクス分析

### 📐 曲構成生成
- ジャンルテンプレート: EDM, House, Techno, D&B, HipHop, Trap, Lo-Fi, Ambient, Pop
- イントロ→ビルドアップ→ドロップ→ブレイクダウン→アウトロの完全構成
- 自動オートメーション生成

---

## 💻 CLI版の使い方

### 起動

```bash
# Ableton接続モード
python src/cli.py

# モックモード（Abletonなしでテスト）
python src/cli.py --mock
```

### 使用例

```
╔════════════════════════════════════════════════════════════════╗
║               🎹 Ableton Agent CLI v2.0 🎹                     ║
╚════════════════════════════════════════════════════════════════╝

🎤 You: 4分のEDMトラックを作って

🤖 Agent: EDMトラックのアレンジメントを生成します。

🎛️  実行: generate_arrangement
    パラメータ: {"genre": "edm", "duration_minutes": 4.0}
✅ アレンジメントを生成しました:

🎵 Untitled Edm
   Tempo: 128 BPM | Key: Am
   Total: 72 bars

📋 Structure:
   [  0] intro        |  8 bars | Energy: ███░░░░░░░
   [  8] buildup      |  8 bars | Energy: █████░░░░░
   [ 16] drop         | 16 bars | Energy: ██████████
   [ 32] breakdown    |  8 bars | Energy: ████░░░░░░
   [ 40] buildup      |  8 bars | Energy: ███████░░░
   [ 48] drop         | 16 bars | Energy: ██████████
   [ 64] outro        |  8 bars | Energy: ███░░░░░░░

🎤 You: トラップ風のドラムを作って

🤖 Agent: トラップ風のドラムパターンを作成します。
🎛️  実行: create_drum_track
    パラメータ: {"pattern_type": "trap", "bars": 2, "name": "Trap Drums"}
✅ ドラムトラック 'Trap Drums' を作成（パターン: trap, 2小節）
```

---

## ⌨️ コマンド一覧

### 特殊コマンド

| コマンド | 説明 |
|---------|------|
| `/help` | ヘルプを表示 |
| `/status` | プロジェクト状態を表示 |
| `/genres` | 利用可能なジャンル一覧 |
| `/arrangement` | 現在のアレンジメントを表示 |
| `/mock` | モックモードの切り替え |
| `/clear` | 会話履歴をクリア |
| `quit` | 終了 |

### 自然言語コマンド例

#### ドラム
- 「基本的なドラムパターンを作って」
- 「トラップ風のビートを4小節」
- 「4つ打ちのキック」
- 「ブレイクビートを作って」

#### メロディ/ベース
- 「Cマイナーでメロディを作って」
- 「ペンタトニックの明るいメロディ」
- 「シンコペーションのベースライン」
- 「オクターブベースを追加」
- 「16分音符のアルペジオ」

#### コード
- 「ダークなコード進行を作って」
- 「ジャズっぽいコード」
- 「シネマティックなコード進行」

#### サンプル
- 「エスニックなパーカッションを探して」
- 「ダークなシンセ 140BPM」
- 「キックサンプルを検索」

#### ミキシング
- 「ミックスを分析して」
- 「キックとベースが被ってる」
- 「全体的にこもってる」
- 「サイドチェインを設定」
- 「リバーブを追加」

#### 曲構成
- 「4分のEDMトラックを作って」
- 「ローファイヒップホップの構成を生成」
- 「テクノの曲構成を作って」

#### 雰囲気
- 「もっとダークな雰囲気にして」
- 「明るくして」
- 「激しい感じにして」
- 「チルな雰囲気に」

---

## 📁 プロジェクト構成

```
ableton-mcp/
├── .gitignore
├── LICENSE
├── README.md                           # 英語版
├── README.ja.md                        # 日本語版
├── INSTALL_WINDOWS.md                  # Windowsセットアップガイド
├── pyproject.toml
├── setup.bat                           # Windowsセットアップスクリプト
├── claude_desktop_config.example.json  # 設定ファイルの例
└── src/
    ├── __init__.py
    ├── mcp_server.py            # MCPサーバー（Claude Desktop用）
    ├── cli.py                   # CLIインターフェース
    ├── agent.py                 # AIエージェント（Claude API）
    ├── ableton_osc.py           # Ableton OSC通信
    ├── synth_generator.py       # メロディ/ベース/コード/アルペジオ生成
    ├── sample_search.py         # サンプル検索エンジン
    ├── mixing_assistant.py      # ミキシング分析・支援
    └── arrangement_generator.py # 曲構成生成
```

---

## 🔧 拡張方法

### 新しいツールを追加

1. `src/agent.py` の `ABLETON_TOOLS` にツール定義を追加:

```python
{
    "name": "your_tool_name",
    "description": "ツールの説明",
    "input_schema": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "説明"}
        },
        "required": ["param1"]
    }
}
```

2. `src/cli.py` の `execute_command` に実行ロジックを追加:

```python
elif tool == "your_tool_name":
    return self._your_implementation(params)
```

### 新しいジャンルテンプレートを追加

`src/arrangement_generator.py` の `GenreTemplates.TEMPLATES` に追加:

```python
"your_genre": {
    "sections": [
        ("intro", 8, 0.3, ["pad"]),
        ("verse", 16, 0.6, ["drums", "bass"]),
        # ...
    ],
    "tempo_range": (100, 120),
    "default_key": "Am",
}
```

---

## 🎛️ アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Input (自然言語)                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Claude API (Tool Use)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │  Drums   │ │ Melody   │ │ Samples  │ │ Mixing   │ ...       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Command Executor                            │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │
│  │ SynthGenerator │  │ SampleSearch   │  │ MixingAssist   │    │
│  └────────────────┘  └────────────────┘  └────────────────┘    │
│  ┌────────────────┐  ┌────────────────┐                        │
│  │ ArrangementGen │  │ DrumPattern    │                        │
│  └────────────────┘  └────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OSC Communication                             │
│                      (python-osc)                                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Ableton Live                                │
│                     (via AbletonOSC)                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## ❓ トラブルシューティング

### 起動順序（重要！）
1. **Ableton Liveを先に起動**
2. AbletonOSCが「Started AbletonOSC on address ('0.0.0.0', 11000)」とログに出るのを確認
3. **その後にClaude Desktopを起動**

### OSC接続エラー
- AbletonOSCがロードされているか確認
- ポート11000が使用可能か確認
- ファイアウォール設定を確認

**Windows - ポート確認:**
```powershell
netstat -ano | findstr "11000 11001"
```

**Windows - Abletonログ確認:**
```powershell
Get-Content "$env:USERPROFILE\AppData\Roaming\Ableton\Live *\Preferences\Log.txt" -Tail 50 | Select-String "OSC"
```

### Claude Desktopの問題
- **ファイル編集後**: Claude Desktopを完全に再起動（タスクトレイから終了）
- **接続がおかしい時**: Claude Desktopを再起動

### APIエラー（CLI版）
- `ANTHROPIC_API_KEY` が正しく設定されているか確認
- API利用制限を確認

### サンプルが見つからない
- サンプルフォルダのパスを確認
- `SampleSearchEngine` の初期化時にカスタムパスを指定

---

## 📄 ライセンス

MIT

## 🔗 参考

- [AbletonOSC](https://github.com/ideoforms/AbletonOSC)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [python-osc](https://python-osc.readthedocs.io/)
- [Freesound API](https://freesound.org/docs/api/)
