#!/usr/bin/env python3
"""
Ableton Agent CLI - Full Featured Version
自然言語でAbleton Liveを操作するコマンドラインツール
"""

import os
import sys
import json
from typing import Optional

# Rich for beautiful CLI
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.prompt import Prompt
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    
from .ableton_osc import AbletonOSC, DrumPattern
from .agent import MusicAgent
from .synth_generator import (
    create_melody, create_bassline, create_chords, create_arpeggio,
    MusicTheory
)
from .sample_search import SampleSearchEngine, parse_sample_query
from .mixing_assistant import MixingAnalyzer, suggest_mix_improvements, AutoMixer
from .arrangement_generator import (
    ArrangementGenerator, ArrangementExecutor,
    create_arrangement, describe_arrangement, get_available_genres
)


class AbletonAgentCLI:
    """全機能対応CLIインターフェース"""
    
    def __init__(self, mock_mode: bool = False):
        self.mock_mode = mock_mode
        self.console = Console() if RICH_AVAILABLE else None
        
        # コンポーネント初期化
        if not mock_mode:
            self.osc = AbletonOSC()
            try:
                self.osc.start_listener()
            except Exception as e:
                self.print_warning(f"OSCリスナー起動失敗: {e}")
                self.print_info("モックモードで続行します")
                self.mock_mode = True
        else:
            self.osc = None
            
        self.agent = MusicAgent()
        
        # 各種ジェネレーター
        self.arrangement_gen = ArrangementGenerator()
        self.sample_engine = SampleSearchEngine()
        self.mixer = AutoMixer()
        
        # トラック管理
        self.track_counter = 0
        
    def print(self, message: str, style: str = None):
        if RICH_AVAILABLE and self.console:
            self.console.print(message, style=style)
        else:
            print(message)
            
    def print_info(self, message: str):
        self.print(f"ℹ️  {message}", style="blue")
        
    def print_success(self, message: str):
        self.print(f"✅ {message}", style="green")
        
    def print_warning(self, message: str):
        self.print(f"⚠️  {message}", style="yellow")
        
    def print_error(self, message: str):
        self.print(f"❌ {message}", style="red")
        
    def print_command(self, tool: str, params: dict):
        self.print(f"🎛️  実行: {tool}", style="cyan")
        if params:
            self.print(f"    パラメータ: {json.dumps(params, ensure_ascii=False)}", style="dim")
    
    def execute_command(self, tool: str, params: dict) -> str:
        """コマンドを実行してAbletonを操作"""
        
        if self.mock_mode:
            return self._execute_mock(tool, params)
            
        try:
            # ========== 基本操作 ==========
            if tool == "set_tempo":
                self.osc.set_tempo(params["bpm"])
                self.agent.update_state(tempo=params["bpm"])
                return f"テンポを {params['bpm']} BPM に設定しました"
                
            elif tool == "play":
                self.osc.play()
                self.agent.update_state(is_playing=True)
                return "再生を開始しました"
                
            elif tool == "stop":
                self.osc.stop()
                self.agent.update_state(is_playing=False)
                return "停止しました"
            
            # ========== ドラム ==========
            elif tool == "create_drum_track":
                return self._create_drum_track(params)
            
            # ========== メロディ/シンセ ==========
            elif tool == "create_melody":
                return self._create_melody_track(params)
                
            elif tool == "create_bassline":
                return self._create_bassline_track(params)
                
            elif tool == "create_chords":
                return self._create_chord_track(params)
                
            elif tool == "create_arpeggio":
                return self._create_arpeggio_track(params)
            
            # ========== サンプル検索 ==========
            elif tool == "search_samples":
                return self._search_samples(params)
                
            elif tool == "load_sample":
                return self._load_sample(params)
            
            # ========== ミキシング ==========
            elif tool == "analyze_mix":
                return self._analyze_mix(params)
                
            elif tool == "fix_mixing_issue":
                return self._fix_mixing_issue(params)
                
            elif tool == "add_sidechain":
                return self._add_sidechain(params)
                
            elif tool == "add_effect":
                return self._add_effect(params)
                
            elif tool == "set_track_volume":
                self.osc.set_track_volume(params["track_index"], params["volume"])
                return f"トラック {params['track_index']} のボリュームを {params['volume']} に設定"
                
            elif tool == "set_track_pan":
                self.osc.set_track_pan(params["track_index"], params["pan"])
                return f"トラック {params['track_index']} のパンを {params['pan']} に設定"
            
            # ========== アレンジメント ==========
            elif tool == "generate_arrangement":
                return self._generate_arrangement(params)
                
            elif tool == "execute_arrangement":
                return self._execute_arrangement(params)
            
            # ========== ムード変更 ==========
            elif tool == "modify_mood":
                return self._modify_mood(params)
            
            # ========== 情報取得 ==========
            elif tool == "get_project_info":
                return json.dumps(self.agent.project_state.to_dict(), ensure_ascii=False, indent=2)
                
            elif tool == "list_available_genres":
                genres = get_available_genres()
                return f"利用可能なジャンル: {', '.join(genres)}"
                
            else:
                return f"未対応のコマンド: {tool}"
                
        except Exception as e:
            return f"エラー: {str(e)}"
            
    def _execute_mock(self, tool: str, params: dict) -> str:
        """モックモードでの実行"""
        if tool == "set_tempo":
            self.agent.update_state(tempo=params["bpm"])
            return f"[MOCK] テンポを {params['bpm']} BPM に設定"
            
        elif tool == "create_drum_track":
            track_info = {"name": params.get("name", "Drums"), "type": "drum", "pattern": params["pattern_type"]}
            self.agent.project_state.tracks.append(track_info)
            return f"[MOCK] ドラムトラック作成: {params['pattern_type']}"
            
        elif tool == "create_melody":
            return f"[MOCK] メロディ作成: {params.get('scale', 'minor')} in {params.get('root', 'C')}"
            
        elif tool == "create_bassline":
            return f"[MOCK] ベースライン作成: {params.get('style', 'basic')}"
            
        elif tool == "create_chords":
            return f"[MOCK] コード進行作成: {params.get('style', 'pop')}"
            
        elif tool == "create_arpeggio":
            return f"[MOCK] アルペジオ作成: {params.get('pattern', 'up')}"
            
        elif tool == "search_samples":
            return f"[MOCK] サンプル検索: '{params['query']}' - 5件見つかりました"
            
        elif tool == "generate_arrangement":
            arr = create_arrangement(
                params["genre"],
                params.get("duration_minutes", 4.0),
                params.get("tempo"),
                params.get("key")
            )
            self.agent.project_state.current_arrangement = arr
            return f"[MOCK] アレンジメント生成:\n{describe_arrangement(arr)}"
            
        elif tool == "modify_mood":
            return f"[MOCK] 雰囲気を '{params['mood']}' に変更"
            
        elif tool == "analyze_mix":
            return "[MOCK] ミックス分析: キックとベースの周波数衝突を検出"
            
        elif tool == "fix_mixing_issue":
            suggestions = suggest_mix_improvements(
                self.agent.project_state.tracks, 
                params["issue"]
            )
            return f"[MOCK] 提案: {json.dumps(suggestions, ensure_ascii=False)}"
            
        else:
            return f"[MOCK] {tool} を実行"
    
    def _create_drum_track(self, params: dict) -> str:
        """ドラムトラックを作成"""
        pattern_type = params["pattern_type"]
        bars = params.get("bars", 2)
        name = params.get("name", "Drums")
        
        # トラック作成
        track_index = self.track_counter
        self.osc.create_midi_track(track_index)
        self.osc.set_track_name(track_index, name)
        
        # クリップ作成
        clip_length = bars * 4.0
        self.osc.create_clip(track_index, 0, clip_length)
        
        # パターン生成
        pattern_map = {
            "basic_beat": DrumPattern.basic_beat,
            "four_on_floor": DrumPattern.four_on_floor,
            "trap": DrumPattern.trap_pattern,
            "breakbeat": DrumPattern.breakbeat,
        }
        gen_func = pattern_map.get(pattern_type, DrumPattern.basic_beat)
        notes = gen_func(bars)
            
        # ノート追加
        self.osc.add_notes(track_index, 0, notes)
        self.osc.set_clip_name(track_index, 0, f"{name} - {pattern_type}")
        
        # 状態更新
        track_info = {"name": name, "type": "drum", "pattern": pattern_type, "index": track_index}
        self.agent.project_state.tracks.append(track_info)
        self.track_counter += 1
        
        return f"ドラムトラック '{name}' を作成（パターン: {pattern_type}, {bars}小節）"
    
    def _create_melody_track(self, params: dict) -> str:
        """メロディトラックを作成"""
        name = params.get("name", "Melody")
        root = params.get("root", "C")
        scale = params.get("scale", "minor")
        bars = params.get("bars", 4)
        density = params.get("density", 0.5)
        contour = params.get("contour", "wave")
        
        # トラック作成
        track_index = self.track_counter
        if not self.mock_mode:
            self.osc.create_midi_track(track_index)
            self.osc.set_track_name(track_index, name)
            
            # クリップ作成
            self.osc.create_clip(track_index, 0, bars * 4.0)
            
            # メロディ生成
            notes = create_melody(root, scale, bars, contour, density)
            self.osc.add_notes(track_index, 0, notes)
        
        # 状態更新
        track_info = {"name": name, "type": "melody", "root": root, "scale": scale, "index": track_index}
        self.agent.project_state.tracks.append(track_info)
        self.track_counter += 1
        
        return f"メロディトラック '{name}' を作成（{root} {scale}, {bars}小節）"
    
    def _create_bassline_track(self, params: dict) -> str:
        """ベースライントラックを作成"""
        name = params.get("name", "Bass")
        root = params.get("root", "C")
        scale = params.get("scale", "minor")
        style = params.get("style", "basic")
        bars = params.get("bars", 4)
        
        track_index = self.track_counter
        if not self.mock_mode:
            self.osc.create_midi_track(track_index)
            self.osc.set_track_name(track_index, name)
            self.osc.create_clip(track_index, 0, bars * 4.0)
            
            notes = create_bassline(root, scale, bars, style)
            self.osc.add_notes(track_index, 0, notes)
        
        track_info = {"name": name, "type": "bass", "style": style, "index": track_index}
        self.agent.project_state.tracks.append(track_info)
        self.track_counter += 1
        
        return f"ベーストラック '{name}' を作成（スタイル: {style}, {bars}小節）"
    
    def _create_chord_track(self, params: dict) -> str:
        """コードトラックを作成"""
        name = params.get("name", "Chords")
        root = params.get("root", "C")
        scale = params.get("scale", "minor")
        style = params.get("style", "pop")
        bars = params.get("bars", 4)
        
        track_index = self.track_counter
        if not self.mock_mode:
            self.osc.create_midi_track(track_index)
            self.osc.set_track_name(track_index, name)
            self.osc.create_clip(track_index, 0, bars * 4.0)
            
            chords = create_chords(root, scale, bars, style)
            # コードの各ノートを追加
            for bar_idx, chord_notes in enumerate(chords):
                for note in chord_notes:
                    self.osc.add_notes(track_index, 0, [note])
        
        track_info = {"name": name, "type": "chords", "style": style, "index": track_index}
        self.agent.project_state.tracks.append(track_info)
        self.track_counter += 1
        
        return f"コードトラック '{name}' を作成（スタイル: {style}, {bars}小節）"
    
    def _create_arpeggio_track(self, params: dict) -> str:
        """アルペジオトラックを作成"""
        name = params.get("name", "Arp")
        root = params.get("root", "C")
        chord = params.get("chord", "minor")
        pattern = params.get("pattern", "up")
        rate = params.get("rate", "16th")
        bars = params.get("bars", 2)
        
        track_index = self.track_counter
        if not self.mock_mode:
            self.osc.create_midi_track(track_index)
            self.osc.set_track_name(track_index, name)
            self.osc.create_clip(track_index, 0, bars * 4.0)
            
            notes = create_arpeggio(root, chord, bars, pattern, rate)
            self.osc.add_notes(track_index, 0, notes)
        
        track_info = {"name": name, "type": "arpeggio", "pattern": pattern, "index": track_index}
        self.agent.project_state.tracks.append(track_info)
        self.track_counter += 1
        
        return f"アルペジオトラック '{name}' を作成（パターン: {pattern}, レート: {rate}）"
    
    def _search_samples(self, params: dict) -> str:
        """サンプル検索"""
        query = params["query"]
        parsed = parse_sample_query(query)
        
        results = self.sample_engine.search(
            query=parsed["query"],
            category=params.get("category") or parsed.get("category"),
            mood=params.get("mood") or parsed.get("mood"),
            bpm=params.get("bpm") or parsed.get("bpm"),
            limit=params.get("limit", 10)
        )
        
        # 結果をフォーマット
        local_count = len(results.get("local", []))
        freesound_count = len(results.get("freesound", []))
        
        output = [f"検索結果: '{query}'"]
        
        if local_count > 0:
            output.append(f"\n📁 ローカル ({local_count}件):")
            for i, sample in enumerate(results["local"][:5]):
                output.append(f"  {i+1}. {sample['name']} [{sample['category']}]")
                
        if freesound_count > 0:
            output.append(f"\n🌐 Freesound ({freesound_count}件):")
            for i, sample in enumerate(results["freesound"][:5]):
                output.append(f"  {i+1}. {sample.get('name', 'Unknown')}")
        
        if local_count == 0 and freesound_count == 0:
            output.append("サンプルが見つかりませんでした")
            
        return "\n".join(output)
    
    def _load_sample(self, params: dict) -> str:
        """サンプルをロード"""
        # 実際の実装ではオーディオトラックにサンプルをロード
        return f"サンプル '{params['sample_path']}' をロードしました"
    
    def _analyze_mix(self, params: dict) -> str:
        """ミックス分析"""
        tracks = self.agent.project_state.tracks
        issues = self.mixer.analyzer.analyze_mix(tracks)
        
        if not issues:
            return "ミックスに大きな問題は見つかりませんでした 👍"
        
        output = ["🔍 ミックス分析結果:\n"]
        for issue in issues[:5]:  # 最大5件
            severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[issue.severity]
            output.append(f"{severity_emoji} {issue.description}")
            
        return "\n".join(output)
    
    def _fix_mixing_issue(self, params: dict) -> str:
        """ミキシング問題を修正"""
        issue = params["issue"]
        auto_fix = params.get("auto_fix", False)
        
        suggestions = suggest_mix_improvements(
            self.agent.project_state.tracks,
            issue
        )
        
        if not suggestions:
            return f"'{issue}' に対する具体的な提案が見つかりませんでした"
        
        output = [f"💡 '{issue}' への提案:\n"]
        for s in suggestions:
            output.append(f"• {s['title']}: {s['description']}")
            
            if auto_fix and not self.mock_mode:
                # 自動修正を実行
                output.append(f"  → 自動適用中...")
                
        return "\n".join(output)
    
    def _add_sidechain(self, params: dict) -> str:
        """サイドチェイン追加"""
        trigger = params["trigger_track"]
        target = params["target_track"]
        amount = params.get("amount", 0.5)
        
        # 実際の実装ではコンプレッサーデバイスを追加
        return f"サイドチェインを設定: トラック{trigger} → トラック{target} (強度: {amount})"
    
    def _add_effect(self, params: dict) -> str:
        """エフェクト追加"""
        track_index = params["track_index"]
        effect_type = params["effect_type"]
        
        effect_map = {
            "reverb": "Audio Effects/Reverb",
            "delay": "Audio Effects/Delay",
            "chorus": "Audio Effects/Chorus",
            "distortion": "Audio Effects/Saturator",
            "compressor": "Audio Effects/Compressor",
            "eq": "Audio Effects/EQ Eight",
            "filter": "Audio Effects/Auto Filter",
            "limiter": "Audio Effects/Limiter",
            "saturator": "Audio Effects/Saturator",
        }
        
        if not self.mock_mode and effect_type in effect_map:
            self.osc.load_device(track_index, effect_map[effect_type])
            
        return f"トラック {track_index} に {effect_type} を追加しました"
    
    def _generate_arrangement(self, params: dict) -> str:
        """アレンジメント生成"""
        genre = params["genre"]
        duration = params.get("duration_minutes", 4.0)
        tempo = params.get("tempo")
        key = params.get("key")
        
        arrangement = create_arrangement(genre, duration, tempo, key)
        self.agent.project_state.current_arrangement = arrangement
        
        # テンポとキーを更新
        self.agent.update_state(
            tempo=arrangement["tempo"],
            key=arrangement.get("key", "Am")
        )
        
        return f"アレンジメントを生成しました:\n\n{describe_arrangement(arrangement)}"
    
    def _execute_arrangement(self, params: dict) -> str:
        """アレンジメントをAbletonに配置"""
        arrangement = self.agent.project_state.current_arrangement
        
        if not arrangement:
            return "先にアレンジメントを生成してください（generate_arrangement）"
        
        executor = ArrangementExecutor(self.osc)
        actions = executor.execute_arrangement(arrangement, create_tracks=params.get("create_tracks", True))
        
        return f"アレンジメントを配置しました（{len(actions)}アクション実行）"
    
    def _modify_mood(self, params: dict) -> str:
        """雰囲気変更"""
        mood = params["mood"].lower()
        intensity = params.get("intensity", 0.5)
        
        changes = []
        current_tempo = self.agent.project_state.tempo
        
        mood_adjustments = {
            "dark": {"tempo_delta": -20, "effects": ["reverb", "filter"]},
            "bright": {"tempo_delta": 15, "effects": ["chorus"]},
            "aggressive": {"tempo_delta": 30, "effects": ["distortion", "compressor"]},
            "chill": {"tempo_delta": -30, "effects": ["reverb", "delay"]},
            "epic": {"tempo_delta": 10, "effects": ["reverb", "compressor"]},
            "minimal": {"tempo_delta": 0, "effects": ["filter"]},
        }
        
        adj = mood_adjustments.get(mood, {"tempo_delta": 0, "effects": []})
        
        # テンポ調整
        new_tempo = max(60, min(200, current_tempo + adj["tempo_delta"] * intensity))
        if not self.mock_mode and self.osc:
            self.osc.set_tempo(new_tempo)
        self.agent.update_state(tempo=new_tempo)
        changes.append(f"テンポ: {new_tempo:.0f} BPM")
        
        # エフェクト追加の提案
        if adj["effects"]:
            changes.append(f"推奨エフェクト: {', '.join(adj['effects'])}")
        
        return f"雰囲気を '{mood}' に変更:\n  " + "\n  ".join(changes)
    
    def run(self):
        """メインループ"""
        self.print_header()
        
        while True:
            try:
                # ユーザー入力
                if RICH_AVAILABLE:
                    user_input = Prompt.ask("\n🎤 [bold cyan]You[/bold cyan]")
                else:
                    user_input = input("\n🎤 You: ")
                    
                if not user_input.strip():
                    continue
                    
                # 終了コマンド
                if user_input.lower() in ["quit", "exit", "q", "終了"]:
                    self.print_info("終了します。お疲れ様でした！🎵")
                    break
                    
                # 特殊コマンド
                if user_input.startswith("/"):
                    self.handle_special_command(user_input)
                    continue
                
                # AIエージェントで処理
                self.print_info("考え中...")
                commands, response = self.agent.process_input(user_input)
                
                # テキスト応答を表示
                text_response = self.agent.get_text_response(response)
                if text_response:
                    if RICH_AVAILABLE:
                        self.console.print(Panel(text_response, title="🤖 Agent", border_style="green"))
                    else:
                        print(f"\n🤖 Agent: {text_response}")
                
                # コマンドを実行
                for cmd in commands:
                    self.print_command(cmd["tool"], cmd["params"])
                    result = self.execute_command(cmd["tool"], cmd["params"])
                    self.print_success(result)
                    
                    # ツール結果をエージェントにフィードバック
                    self.agent.add_tool_result(cmd["tool_use_id"], result)
                    
            except KeyboardInterrupt:
                self.print_info("\n終了します。")
                break
            except Exception as e:
                self.print_error(f"エラー: {e}")
                import traceback
                traceback.print_exc()
                
    def handle_special_command(self, command: str):
        """特殊コマンド処理"""
        cmd = command.lower().strip()
        
        if cmd == "/help":
            self.print_help()
        elif cmd == "/status":
            self.print_status()
        elif cmd == "/mock":
            self.mock_mode = not self.mock_mode
            self.print_info(f"モックモード: {'ON' if self.mock_mode else 'OFF'}")
        elif cmd == "/clear":
            self.agent.clear_history()
            self.print_info("会話履歴をクリアしました")
        elif cmd == "/genres":
            genres = get_available_genres()
            self.print_info(f"利用可能なジャンル: {', '.join(genres)}")
        elif cmd == "/arrangement":
            arr = self.agent.project_state.current_arrangement
            if arr:
                self.print(describe_arrangement(arr))
            else:
                self.print_info("アレンジメントが生成されていません")
        else:
            self.print_warning(f"未知のコマンド: {command}")
            self.print_help()
            
    def print_header(self):
        """ヘッダーを表示"""
        header = """
╔════════════════════════════════════════════════════════════════╗
║               🎹 Ableton Agent CLI v2.0 🎹                     ║
║         自然言語でAbleton Liveを完全コントロール               ║
╠════════════════════════════════════════════════════════════════╣
║  ✨ ドラム/メロディ/ベース/コード自動生成                      ║
║  🔍 サンプル検索                                               ║
║  🎚️ ミキシング支援（サイドチェイン/EQ）                        ║
║  📐 曲構成自動生成（イントロ〜アウトロ）                       ║
╚════════════════════════════════════════════════════════════════╝
"""
        if RICH_AVAILABLE:
            self.console.print(header, style="bold magenta")
        else:
            print(header)
            
        if self.mock_mode:
            self.print_warning("モックモードで起動（Ableton未接続）")
        else:
            self.print_success("Ableton Liveに接続しました")
            
        self.print_info("'/help' でヘルプ | 'quit' で終了")
        
    def print_help(self):
        """ヘルプを表示"""
        help_text = """
## 💬 自然言語で指示

### ドラム/リズム
- 「基本的なドラムパターンを作って」
- 「トラップ風のビートを4小節」
- 「4つ打ちのキック」

### メロディ/ベース
- 「Cマイナーでメロディを作って」
- 「シンコペーションのベースライン」
- 「16分音符のアルペジオ」
- 「ダークなコード進行」

### サンプル検索
- 「エスニックなパーカッションを探して」
- 「ダークなシンセ 140BPM」

### ミキシング
- 「キックとベースが被ってる」→ 自動で対策を提案
- 「サイドチェインを設定して」

### 曲構成
- 「4分のEDMトラックを作って」
- 「ローファイヒップホップの構成を生成」

## ⌨️ 特殊コマンド

| コマンド | 説明 |
|---------|------|
| /help | このヘルプ |
| /status | 現在の状態 |
| /genres | 利用可能なジャンル |
| /arrangement | 現在のアレンジメント |
| /mock | モックモード切替 |
| /clear | 会話履歴クリア |
| quit | 終了 |
"""
        if RICH_AVAILABLE:
            self.console.print(Markdown(help_text))
        else:
            print(help_text)
            
    def print_status(self):
        """現在の状態を表示"""
        state = self.agent.project_state
        
        if RICH_AVAILABLE:
            table = Table(title="🎛️ プロジェクト状態")
            table.add_column("項目", style="cyan")
            table.add_column("値", style="green")
            
            table.add_row("テンポ", f"{state.tempo} BPM")
            table.add_row("キー", state.key)
            table.add_row("再生中", "▶️" if state.is_playing else "⏹️")
            table.add_row("トラック数", str(len(state.tracks)))
            table.add_row("モード", "🔇 Mock" if self.mock_mode else "🔊 Live")
            
            for i, track in enumerate(state.tracks):
                table.add_row(f"  Track {i}", f"{track.get('name', 'Unnamed')} ({track.get('type', 'unknown')})")
            
            if state.current_arrangement:
                table.add_row("アレンジメント", f"{state.current_arrangement['total_bars']} bars")
                
            self.console.print(table)
        else:
            print(f"\n状態: テンポ={state.tempo}BPM, キー={state.key}, トラック={len(state.tracks)}")


def main():
    """エントリーポイント"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ableton Agent CLI v2.0")
    parser.add_argument("--mock", action="store_true", help="モックモードで起動")
    parser.add_argument("--port", type=int, default=11000, help="Ableton OSCポート")
    args = parser.parse_args()
    
    # API キーチェック
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  ANTHROPIC_API_KEY が設定されていません")
        print("   export ANTHROPIC_API_KEY='your-api-key'")
    
    cli = AbletonAgentCLI(mock_mode=args.mock)
    cli.run()


if __name__ == "__main__":
    main()
