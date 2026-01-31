# 🎹 Ableton Agent - Windows インストールガイド

## 📋 必要なもの

- Windows 10/11
- Python 3.10以上
- Ableton Live 10/11/12
- Claude Desktop

---

## 🚀 ステップ1: Pythonのインストール

### Python公式サイトからダウンロード

1. https://www.python.org/downloads/ にアクセス
2. 「Download Python 3.12.x」をクリック
3. インストーラーを実行

⚠️ **重要**: インストール時に **「Add Python to PATH」にチェック** を入れる！

### 確認
```powershell
# PowerShellまたはコマンドプロンプトで
python --version
# Python 3.12.x と表示されればOK
```

---

## 🚀 ステップ2: Ableton Agentのインストール

### 2-1. プロジェクトをダウンロード

任意のフォルダに `ableton-agent` フォルダを配置。
例: `C:\Users\あなたの名前\ableton-agent`

### 2-2. 依存パッケージをインストール

PowerShellを**管理者として実行**し、以下を実行：

```powershell
# ableton-agentフォルダに移動
cd C:\Users\あなたの名前\ableton-agent

# パッケージをインストール
pip install -e .
```

または個別にインストール：

```powershell
pip install python-osc rich mcp
```

---

## 🚀 ステップ3: AbletonOSCのインストール

### 3-1. ダウンロード

1. https://github.com/ideoforms/AbletonOSC/releases にアクセス
2. 最新版の `AbletonOSC.amxd` をダウンロード

### 3-2. Ableton Liveに追加

1. Ableton Liveを起動
2. 任意のMIDIトラックを作成
3. `AbletonOSC.amxd` をそのトラックにドラッグ&ドロップ
4. デバイスに「Listening on port 11000」と表示されればOK

💡 **ヒント**: プロジェクトテンプレートとして保存しておくと便利

---

## 🚀 ステップ4: Claude Desktopの設定

### 4-1. Claude Desktopをインストール

まだの場合は https://claude.ai/download からダウンロード

### 4-2. 設定ファイルを編集

1. エクスプローラーで以下のパスを開く：
   ```
   %APPDATA%\Claude
   ```
   （エクスプローラーのアドレスバーにそのまま貼り付けてEnter）

2. `claude_desktop_config.json` を作成または編集

3. 以下の内容を貼り付け：

```json
{
  "mcpServers": {
    "ableton-agent": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "C:\\Users\\あなたの名前\\ableton-agent"
    }
  }
}
```

⚠️ **注意点**:
- `あなたの名前` を実際のユーザー名に変更
- パスの `\` は `\\` と2つ重ねる（JSONのエスケープ）
- または `/` を使う: `"cwd": "C:/Users/あなたの名前/ableton-agent"`

### 4-3. Claude Desktopを再起動

完全に終了してから再度起動。

---

## ✅ 動作確認

### Claude Desktopで確認

1. Claude Desktopを開く
2. 新しいチャットを開始
3. 以下を入力：

```
Abletonに接続して
```

成功すると：
```
✅ Ableton Liveに接続しました
```
または
```
⚠️ 接続できませんでした。モックモードで動作します
```

### テストコマンド

```
利用可能なジャンルを教えて
```

```
テンポを140にして
```

```
トラップ風のドラムパターンを作って
```

---

## 🔧 トラブルシューティング

### ❌ 「python が認識されません」

**原因**: PythonがPATHに追加されていない

**解決方法**:
1. Pythonを再インストール（「Add Python to PATH」にチェック）
2. または手動でPATHに追加：
   - 「システム環境変数の編集」を検索して開く
   - 「環境変数」→「Path」→「編集」
   - `C:\Users\あなたの名前\AppData\Local\Programs\Python\Python312` を追加
   - `C:\Users\あなたの名前\AppData\Local\Programs\Python\Python312\Scripts` も追加

### ❌ 「mcp モジュールが見つかりません」

```powershell
pip install mcp
```

### ❌ Claude Desktopでツールが表示されない

1. 設定ファイルのJSONが正しいか確認（カンマや括弧の位置）
2. パスが正しいか確認
3. Claude Desktopを完全に再起動（タスクマネージャーで終了）

### ❌ Abletonに接続できない

1. Ableton Liveが起動しているか確認
2. AbletonOSCデバイスがトラックに追加されているか確認
3. ファイアウォールがポート11000をブロックしていないか確認

**ファイアウォール設定**:
```powershell
# 管理者PowerShellで実行
netsh advfirewall firewall add rule name="AbletonOSC" dir=in action=allow protocol=UDP localport=11000
netsh advfirewall firewall add rule name="AbletonOSC Out" dir=out action=allow protocol=UDP localport=11001
```

---

## 📁 ファイル配置の例

```
C:\Users\YourName\
├── ableton-agent\
│   ├── src\
│   │   ├── mcp_server.py
│   │   ├── ableton_osc.py
│   │   ├── synth_generator.py
│   │   ├── ... (その他のファイル)
│   ├── pyproject.toml
│   └── README.md
```

---

## 🎵 使用例

Claude Desktopで自然に会話するだけ！

```
You: 4分のEDMトラックの構成を作って

Claude: [generate_arrangement を実行]
📐 アレンジメントを生成:
🎵 Untitled Edm
   Tempo: 128 BPM | Key: Am
   ...

You: ドラムトラックを追加して

Claude: [create_drum_track を実行]
🥁 ドラムトラック 'Drums' を作成（four_on_floor, 2小節）

You: ベースも追加、シンコペーション風で

Claude: [create_bassline を実行]
🎸 ベーストラックを作成（syncopatedスタイル, 4小節）

You: キックとベースが被ってる気がする

Claude: [fix_mixing_issue を実行]
💡 提案:
• サイドチェインコンプレッション
• EQによる住み分け

You: サイドチェイン設定して

Claude: [add_sidechain を実行]
🔗 サイドチェインを設定: Track 0 → Track 1
```

---

## 📞 サポート

問題が解決しない場合：
1. エラーメッセージをコピー
2. `python --version` と `pip list` の結果を確認
3. `claude_desktop_config.json` の内容を確認

Happy Music Making! 🎹🎵
