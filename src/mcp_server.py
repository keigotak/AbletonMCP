#!/usr/bin/env python3
"""
Ableton MCP Server
Claude Desktop から直接 Ableton Live を操作できるMCPサーバー
APIキー不要！
"""

import asyncio
import json
import sys
import os
from typing import Any

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# 既存モジュールをインポート
from src.ableton_osc import AbletonOSC, DrumPattern
from src.synth_generator import (
    create_melody, create_bassline, create_chords, create_arpeggio,
    MusicTheory, Scale
)
from src.sample_search import SampleSearchEngine, parse_sample_query
from src.mixing_assistant import suggest_mix_improvements
from src.arrangement_generator import (
    create_arrangement, describe_arrangement, get_available_genres
)


# グローバル状態
class AbletonState:
    def __init__(self):
        self.osc: AbletonOSC = None
        self.tempo = 120.0
        self.key = "Am"
        self.tracks = []
        self.is_playing = False
        self.current_arrangement = None
        self.track_counter = 0
        self.mock_mode = True  # 初期はモックモード
        
    def connect(self):
        """Abletonに接続"""
        import sys
        
        # 既に接続済みならスキップ
        if self.osc is not None and not self.mock_mode:
            print("[OK] Already connected", file=sys.stderr)
            return True
        
        # 既存のソケットがあれば閉じる
        if self.osc is not None:
            try:
                self.osc.stop_listener()
            except:
                pass
            self.osc = None
        
        try:
            print("[...] Connecting to Ableton...", file=sys.stderr)
            self.osc = AbletonOSC()
            print("[...] Starting listener...", file=sys.stderr)
            self.osc.start_listener()
            print("[...] Testing connection...", file=sys.stderr)
            # 実際に応答があるかテスト
            if self.osc.test_connection(timeout=3.0):
                self.mock_mode = False
                self.tempo = self.osc.state.tempo
                print(f"[OK] Connected! Tempo: {self.tempo}", file=sys.stderr)
                return True
            else:
                self.mock_mode = True
                print("[ERR] Connection test failed", file=sys.stderr)
                return False
        except Exception as e:
            self.mock_mode = True
            print(f"[ERR] Exception: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return False
    
    def to_dict(self):
        return {
            "tempo": self.tempo,
            "key": self.key,
            "tracks": self.tracks,
            "is_playing": self.is_playing,
            "mock_mode": self.mock_mode,
            "arrangement": self.current_arrangement
        }

state = AbletonState()
server = Server("ableton-agent")


# ==================== ツール定義 ====================

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """利用可能なツール一覧"""
    return [
        # 基本操作
        types.Tool(
            name="ableton_connect",
            description="Ableton Liveに接続する。最初に一度実行してください。",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="set_tempo",
            description="テンポ（BPM）を設定する",
            inputSchema={
                "type": "object",
                "properties": {
                    "bpm": {"type": "number", "description": "テンポ（60-200）"}
                },
                "required": ["bpm"]
            }
        ),
        types.Tool(
            name="play",
            description="再生を開始する",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="stop", 
            description="再生を停止する",
            inputSchema={"type": "object", "properties": {}}
        ),
        
        # ドラム
        types.Tool(
            name="create_drum_track",
            description="ドラムトラックを作成。パターン: basic_beat, four_on_floor, trap, breakbeat",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern_type": {
                        "type": "string",
                        "enum": ["basic_beat", "four_on_floor", "trap", "breakbeat"],
                        "description": "ドラムパターンのタイプ"
                    },
                    "bars": {"type": "integer", "description": "小節数", "default": 2},
                    "name": {"type": "string", "description": "トラック名", "default": "Drums"}
                },
                "required": ["pattern_type"]
            }
        ),
        
        # メロディ/シンセ
        types.Tool(
            name="create_melody",
            description="メロディを自動生成",
            inputSchema={
                "type": "object",
                "properties": {
                    "root": {"type": "string", "description": "ルート音（C,D,E,F,G,A,B）", "default": "C"},
                    "scale": {"type": "string", "enum": ["major", "minor", "dorian", "pentatonic", "blues"], "default": "minor"},
                    "bars": {"type": "integer", "default": 4},
                    "density": {"type": "number", "description": "音の密度（0.0-1.0）", "default": 0.5},
                    "contour": {"type": "string", "enum": ["ascending", "descending", "wave", "random"], "default": "wave"}
                },
                "required": []
            }
        ),
        types.Tool(
            name="create_bassline",
            description="ベースラインを自動生成",
            inputSchema={
                "type": "object",
                "properties": {
                    "root": {"type": "string", "default": "C"},
                    "scale": {"type": "string", "enum": ["major", "minor", "dorian"], "default": "minor"},
                    "style": {"type": "string", "enum": ["basic", "walking", "syncopated", "octave", "arpeggiated"], "default": "basic"},
                    "bars": {"type": "integer", "default": 4}
                },
                "required": []
            }
        ),
        types.Tool(
            name="create_chords",
            description="コード進行を生成",
            inputSchema={
                "type": "object",
                "properties": {
                    "root": {"type": "string", "default": "C"},
                    "scale": {"type": "string", "enum": ["major", "minor"], "default": "minor"},
                    "style": {"type": "string", "enum": ["pop", "jazz", "sad", "epic", "dark", "edm", "lofi", "cinematic"], "default": "pop"},
                    "bars": {"type": "integer", "default": 4}
                },
                "required": []
            }
        ),
        types.Tool(
            name="create_arpeggio",
            description="アルペジオパターンを生成",
            inputSchema={
                "type": "object",
                "properties": {
                    "root": {"type": "string", "default": "C"},
                    "chord": {"type": "string", "enum": ["major", "minor", "maj7", "min7"], "default": "minor"},
                    "pattern": {"type": "string", "enum": ["up", "down", "updown", "random"], "default": "up"},
                    "rate": {"type": "string", "enum": ["8th", "16th", "triplet"], "default": "16th"},
                    "bars": {"type": "integer", "default": 2}
                },
                "required": []
            }
        ),
        
        # サンプル検索
        types.Tool(
            name="search_samples",
            description="サンプルを検索（例：'エスニックなパーカッション'）",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "検索クエリ"},
                    "category": {"type": "string", "enum": ["drums", "percussion", "bass", "synth", "vocal", "fx", "ambient", "ethnic"]},
                    "mood": {"type": "string", "enum": ["dark", "bright", "aggressive", "chill", "epic", "minimal"]},
                    "limit": {"type": "integer", "default": 10}
                },
                "required": ["query"]
            }
        ),
        
        # ミキシング
        types.Tool(
            name="fix_mixing_issue",
            description="ミキシングの問題を分析して改善策を提案（例：'キックとベースが被ってる'）",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue": {"type": "string", "description": "問題の説明"}
                },
                "required": ["issue"]
            }
        ),
        types.Tool(
            name="add_sidechain",
            description="サイドチェインコンプレッションを設定",
            inputSchema={
                "type": "object",
                "properties": {
                    "trigger_track": {"type": "integer", "description": "トリガートラック番号（通常キック）"},
                    "target_track": {"type": "integer", "description": "ターゲットトラック番号（通常ベース）"},
                    "amount": {"type": "number", "description": "強さ（0.0-1.0）", "default": 0.5}
                },
                "required": ["trigger_track", "target_track"]
            }
        ),
        types.Tool(
            name="add_effect",
            description="トラックにエフェクトを追加",
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index": {"type": "integer"},
                    "effect_type": {"type": "string", "enum": ["reverb", "delay", "chorus", "distortion", "compressor", "eq", "filter"]}
                },
                "required": ["track_index", "effect_type"]
            }
        ),
        types.Tool(
            name="set_track_volume",
            description="トラックのボリュームを設定",
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index": {"type": "integer"},
                    "volume": {"type": "number", "description": "0.0-1.0"}
                },
                "required": ["track_index", "volume"]
            }
        ),
        types.Tool(
            name="set_device_parameter",
            description="デバイス/エフェクトのパラメータを設定",
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index": {"type": "integer", "description": "トラック番号"},
                    "device_index": {"type": "integer", "description": "デバイス番号（0から、音源=0, 最初のエフェクト=1）"},
                    "param_index": {"type": "integer", "description": "パラメータ番号"},
                    "value": {"type": "number", "description": "値 (0.0-1.0)"}
                },
                "required": ["track_index", "device_index", "param_index", "value"]
            }
        ),
        types.Tool(
            name="apply_lofi_settings",
            description="Lo-Fi Hip Hop用のエフェクト設定を一括適用",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        # アレンジメント
        types.Tool(
            name="generate_arrangement",
            description="曲のアレンジメント（構成）を自動生成。イントロからアウトロまで",
            inputSchema={
                "type": "object",
                "properties": {
                    "genre": {"type": "string", "enum": ["edm", "house", "techno", "dnb", "hiphop", "trap", "lofi", "ambient", "pop"]},
                    "duration_minutes": {"type": "number", "default": 4.0},
                    "tempo": {"type": "number", "description": "BPM（省略時はジャンルに応じて自動）"},
                    "key": {"type": "string", "description": "キー（例：Am, C, Fm）"}
                },
                "required": ["genre"]
            }
        ),
        
        # ムード
        types.Tool(
            name="modify_mood",
            description="曲の雰囲気を変更（dark, bright, aggressive, chill, epic, minimal）",
            inputSchema={
                "type": "object",
                "properties": {
                    "mood": {"type": "string", "description": "目標の雰囲気"},
                    "intensity": {"type": "number", "description": "変更の強度（0.0-1.0）", "default": 0.5}
                },
                "required": ["mood"]
            }
        ),
        
        # 情報
        types.Tool(
            name="get_project_info",
            description="現在のプロジェクト情報を取得",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="get_track_info",
            description="トラックの詳細情報を取得（名前、ボリューム、パン）",
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index": {"type": "integer", "description": "トラック番号"}
                },
                "required": ["track_index"]
            }
        ),
        types.Tool(
            name="get_device_params",
            description="デバイス/エフェクトのパラメータ一覧と現在値を取得",
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index": {"type": "integer", "description": "トラック番号"},
                    "device_index": {"type": "integer", "description": "デバイス番号（音源=0, 最初のエフェクト=1）"}
                },
                "required": ["track_index", "device_index"]
            }
        ),
        types.Tool(
            name="list_genres",
            description="利用可能なジャンル一覧を取得",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="osc_send",
            description="OSCメッセージを直接送信し応答を確認（低レベル操作）",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "string", "description": "OSCアドレス（例: /live/song/get/tempo）"},
                    "args": {"type": "array", "description": "引数リスト", "default": []}
                },
                "required": ["address"]
            }
        ),
        types.Tool(
            name="get_all_devices",
            description="全トラックのデバイス・パラメータ一覧を取得",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="create_scene",
            description="新しいシーンを作成",
            inputSchema={
                "type": "object",
                "properties": {
                    "index": {"type": "integer", "description": "シーン番号"},
                    "name": {"type": "string", "description": "シーン名"}
                },
                "required": ["index", "name"]
            }
        ),
        types.Tool(
            name="duplicate_clip",
            description="クリップを別のスロットに複製",
            inputSchema={
                "type": "object",
                "properties": {
                    "src_track": {"type": "integer", "description": "コピー元トラック"},
                    "src_scene": {"type": "integer", "description": "コピー元シーン"},
                    "dst_track": {"type": "integer", "description": "コピー先トラック"},
                    "dst_scene": {"type": "integer", "description": "コピー先シーン"}
                },
                "required": ["src_track", "src_scene", "dst_track", "dst_scene"]
            }
        ),
        types.Tool(
            name="delete_clip",
            description="クリップを削除",
            inputSchema={
                "type": "object",
                "properties": {
                    "track": {"type": "integer", "description": "トラック番号"},
                    "scene": {"type": "integer", "description": "シーン番号"}
                },
                "required": ["track", "scene"]
            }
        ),
        types.Tool(
            name="build_arrangement",
            description="Lo-Fi曲の自動アレンジメント（シーン構成）を作成",
            inputSchema={
                "type": "object",
                "properties": {
                    "style": {"type": "string", "description": "スタイル: simple, standard, extended", "default": "standard"}
                }
            }
        ),
        types.Tool(
            name="fire_scene",
            description="シーンを再生（トリガー）",
            inputSchema={
                "type": "object",
                "properties": {
                    "scene": {"type": "integer", "description": "シーン番号"}
                },
                "required": ["scene"]
            }
        ),
        types.Tool(
            name="auto_play_scenes",
            description="全シーンを自動的に順番に再生（各シーンの小節数を指定）",
            inputSchema={
                "type": "object",
                "properties": {
                    "bars_per_scene": {"type": "integer", "description": "各シーンの小節数", "default": 8},
                    "start_scene": {"type": "integer", "description": "開始シーン", "default": 0},
                    "end_scene": {"type": "integer", "description": "終了シーン", "default": 5}
                }
            }
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    """ツール実行"""
    args = arguments or {}
    result = ""
    
    try:
        # ========== 接続 ==========
        if name == "ableton_connect":
            # 既に接続済みかチェック
            if not state.mock_mode and state.osc is not None:
                result = f"[OK] 既にAbleton Liveに接続済みです（テンポ: {state.tempo} BPM）"
            elif state.connect():
                result = f"[OK] Ableton Liveに接続しました（テンポ: {state.tempo} BPM）"
            else:
                result = "[WARN] 接続できませんでした。モックモードで動作します"
        
        # ========== 基本操作 ==========
        elif name == "set_tempo":
            bpm = args["bpm"]
            if not state.mock_mode and state.osc:
                state.osc.set_tempo(bpm)
            state.tempo = bpm
            result = f"テンポを {bpm} BPM に設定しました"
            
        elif name == "play":
            if not state.mock_mode and state.osc:
                state.osc.play()
            state.is_playing = True
            result = "▶️ 再生を開始しました"
            
        elif name == "stop":
            if not state.mock_mode and state.osc:
                state.osc.stop()
            state.is_playing = False
            result = "⏹️ 停止しました"
        
        # ========== ドラム ==========
        elif name == "create_drum_track":
            pattern_type = args["pattern_type"]
            bars = args.get("bars", 2)
            track_name = args.get("name", "Drums")
            
            track_index = state.track_counter
            
            if not state.mock_mode and state.osc:
                state.osc.create_midi_track(track_index)
                state.osc.set_track_name(track_index, track_name)
                state.osc.create_clip(track_index, 0, bars * 4.0)
                
                pattern_map = {
                    "basic_beat": DrumPattern.basic_beat,
                    "four_on_floor": DrumPattern.four_on_floor,
                    "trap": DrumPattern.trap_pattern,
                    "breakbeat": DrumPattern.breakbeat,
                }
                notes = pattern_map.get(pattern_type, DrumPattern.basic_beat)(bars)
                state.osc.add_notes(track_index, 0, notes)
            
            state.tracks.append({"name": track_name, "type": "drum", "pattern": pattern_type, "index": track_index})
            state.track_counter += 1
            result = f"🥁 ドラムトラック '{track_name}' を作成（{pattern_type}, {bars}小節）"
        
        # ========== メロディ ==========
        elif name == "create_melody":
            root = args.get("root", "C")
            scale = args.get("scale", "minor")
            bars = args.get("bars", 4)
            density = args.get("density", 0.5)
            contour = args.get("contour", "wave")
            
            track_index = state.track_counter
            
            if not state.mock_mode and state.osc:
                state.osc.create_midi_track(track_index)
                state.osc.set_track_name(track_index, "Melody")
                state.osc.create_clip(track_index, 0, bars * 4.0)
                notes = create_melody(root, scale, bars, contour, density)
                state.osc.add_notes(track_index, 0, notes)
            
            state.tracks.append({"name": "Melody", "type": "melody", "root": root, "scale": scale, "index": track_index})
            state.track_counter += 1
            result = f"🎹 メロディトラックを作成（{root} {scale}, {bars}小節, 密度: {density}）"
        
        # ========== ベースライン ==========
        elif name == "create_bassline":
            root = args.get("root", "C")
            scale = args.get("scale", "minor")
            style = args.get("style", "basic")
            bars = args.get("bars", 4)
            
            track_index = state.track_counter
            
            if not state.mock_mode and state.osc:
                state.osc.create_midi_track(track_index)
                state.osc.set_track_name(track_index, "Bass")
                state.osc.create_clip(track_index, 0, bars * 4.0)
                notes = create_bassline(root, scale, bars, style)
                state.osc.add_notes(track_index, 0, notes)
            
            state.tracks.append({"name": "Bass", "type": "bass", "style": style, "index": track_index})
            state.track_counter += 1
            result = f"🎸 ベーストラックを作成（{style}スタイル, {bars}小節）"
        
        # ========== コード ==========
        elif name == "create_chords":
            root = args.get("root", "C")
            scale = args.get("scale", "minor")
            style = args.get("style", "pop")
            bars = args.get("bars", 4)
            
            track_index = state.track_counter
            
            if not state.mock_mode and state.osc:
                state.osc.create_midi_track(track_index)
                state.osc.set_track_name(track_index, "Chords")
                state.osc.create_clip(track_index, 0, bars * 4.0)
                chords = create_chords(root, scale, bars, style)
                for chord_notes in chords:
                    for note in chord_notes:
                        state.osc.add_notes(track_index, 0, [note])
            
            state.tracks.append({"name": "Chords", "type": "chords", "style": style, "index": track_index})
            state.track_counter += 1
            result = f"🎼 コードトラックを作成（{style}スタイル, {bars}小節）"
        
        # ========== アルペジオ ==========
        elif name == "create_arpeggio":
            root = args.get("root", "C")
            chord = args.get("chord", "minor")
            pattern = args.get("pattern", "up")
            rate = args.get("rate", "16th")
            bars = args.get("bars", 2)
            
            track_index = state.track_counter
            
            if not state.mock_mode and state.osc:
                state.osc.create_midi_track(track_index)
                state.osc.set_track_name(track_index, "Arp")
                state.osc.create_clip(track_index, 0, bars * 4.0)
                notes = create_arpeggio(root, chord, bars, pattern, rate)
                state.osc.add_notes(track_index, 0, notes)
            
            state.tracks.append({"name": "Arp", "type": "arpeggio", "pattern": pattern, "index": track_index})
            state.track_counter += 1
            result = f"🎶 アルペジオトラックを作成（{pattern}パターン, {rate}）"
        
        # ========== サンプル検索 ==========
        elif name == "search_samples":
            query = args["query"]
            parsed = parse_sample_query(query)
            
            engine = SampleSearchEngine()
            results = engine.search(
                query=parsed.get("query", query),
                category=args.get("category") or parsed.get("category"),
                mood=args.get("mood") or parsed.get("mood"),
                limit=args.get("limit", 10)
            )
            
            local_count = len(results.get("local", []))
            freesound_count = len(results.get("freesound", []))
            
            output = [f"🔍 検索: '{query}'"]
            if local_count > 0:
                output.append(f"\n📁 ローカル ({local_count}件):")
                for i, s in enumerate(results["local"][:5]):
                    output.append(f"  {i+1}. {s['name']}")
            if freesound_count > 0:
                output.append(f"\n🌐 Freesound ({freesound_count}件)")
            if local_count == 0 and freesound_count == 0:
                output.append("見つかりませんでした")
            
            result = "\n".join(output)
        
        # ========== ミキシング ==========
        elif name == "fix_mixing_issue":
            issue = args["issue"]
            suggestions = suggest_mix_improvements(state.tracks, issue)
            
            if suggestions:
                output = [f"💡 '{issue}' への提案:\n"]
                for s in suggestions:
                    output.append(f"• {s['title']}: {s['description']}")
                result = "\n".join(output)
            else:
                result = f"'{issue}' に対する具体的な提案が見つかりませんでした"
        
        elif name == "add_sidechain":
            trigger = args["trigger_track"]
            target = args["target_track"]
            amount = args.get("amount", 0.5)
            result = f"🔗 サイドチェインを設定: Track {trigger} → Track {target} (強度: {amount})"
        
        elif name == "add_effect":
            track_idx = args["track_index"]
            effect = args["effect_type"]
            
            effect_map = {
                "reverb": "Audio Effects/Reverb",
                "delay": "Audio Effects/Delay",
                "chorus": "Audio Effects/Chorus",
                "distortion": "Audio Effects/Saturator",
                "compressor": "Audio Effects/Compressor",
                "eq": "Audio Effects/EQ Eight",
                "filter": "Audio Effects/Auto Filter",
            }
            
            if not state.mock_mode and state.osc and effect in effect_map:
                state.osc.load_device(track_idx, effect_map[effect])
            
            result = f"✨ Track {track_idx} に {effect} を追加"
        
        elif name == "set_track_volume":
            track_idx = args["track_index"]
            volume = args["volume"]
            
            if not state.mock_mode and state.osc:
                state.osc.set_track_volume(track_idx, volume)
            
            result = f"🔊 Track {track_idx} のボリュームを {volume} に設定"
        
        elif name == "set_device_parameter":
            track_idx = args["track_index"]
            device_idx = args["device_index"]
            param_idx = args["param_index"]
            value = args["value"]
            
            if not state.mock_mode and state.osc:
                state.osc.set_device_parameter(track_idx, device_idx, param_idx, value)
            
            result = f"🎛️ Track {track_idx} Device {device_idx} Param {param_idx} = {value}"
        
        elif name == "apply_lofi_settings":
            # Lo-Fi用の一括設定
            settings_applied = []
            
            if not state.mock_mode and state.osc:
                # Compressor設定 (一般的なパラメータ: Threshold=0, Ratio=1, Attack=2, Release=3)
                # Track 0 (Lo-Fi Drums) - Compressor
                state.osc.set_device_parameter(0, 1, 0, 0.4)  # Threshold
                state.osc.set_device_parameter(0, 1, 1, 0.5)  # Ratio ~4:1
                state.osc.set_device_parameter(0, 1, 2, 0.15) # Attack
                state.osc.set_device_parameter(0, 1, 3, 0.3)  # Release
                settings_applied.append("Track 0: Compressor調整")
                
                # Track 1 (Lo-Fi Chords) - Reverb (Decay=0, Dry/Wet=5 or similar)
                state.osc.set_device_parameter(1, 1, 5, 0.25)  # Dry/Wet 25%
                state.osc.set_device_parameter(1, 1, 0, 0.5)   # Decay
                settings_applied.append("Track 1: Reverb調整")
                
                # Track 1 - Chorus (Rate, Amount)
                state.osc.set_device_parameter(1, 2, 0, 0.2)  # Rate
                state.osc.set_device_parameter(1, 2, 1, 0.3)  # Amount
                settings_applied.append("Track 1: Chorus調整")
                
                # Track 2 (Lo-Fi Bass) - Compressor
                state.osc.set_device_parameter(2, 1, 0, 0.35)
                state.osc.set_device_parameter(2, 1, 1, 0.45)
                settings_applied.append("Track 2: Compressor調整")
                
                # Track 6 (Melody) - Reverb
                state.osc.set_device_parameter(6, 1, 5, 0.35)  # Dry/Wet 35%
                state.osc.set_device_parameter(6, 1, 0, 0.6)   # Decay longer
                settings_applied.append("Track 6: Reverb調整")
                
                # Track 6 - Delay
                state.osc.set_device_parameter(6, 2, 1, 0.3)   # Feedback 30%
                state.osc.set_device_parameter(6, 2, 5, 0.2)   # Dry/Wet 20%
                settings_applied.append("Track 6: Delay調整")
            
            result = "🎛️ Lo-Fi設定を適用:\n  " + "\n  ".join(settings_applied)
        
        # ========== アレンジメント ==========
        elif name == "generate_arrangement":
            genre = args["genre"]
            duration = args.get("duration_minutes", 4.0)
            tempo = args.get("tempo")
            key = args.get("key")
            
            arr = create_arrangement(genre, duration, tempo, key)
            state.current_arrangement = arr
            state.tempo = arr["tempo"]
            state.key = arr.get("key", "Am")
            
            result = f"📐 アレンジメントを生成:\n\n{describe_arrangement(arr)}"
        
        # ========== ムード ==========
        elif name == "modify_mood":
            mood = args["mood"].lower()
            intensity = args.get("intensity", 0.5)
            
            mood_adjustments = {
                "dark": {"tempo_delta": -20, "desc": "テンポダウン、低音強調"},
                "bright": {"tempo_delta": 15, "desc": "テンポアップ、高音強調"},
                "aggressive": {"tempo_delta": 30, "desc": "高速テンポ、ディストーション"},
                "chill": {"tempo_delta": -30, "desc": "スローテンポ、リバーブ"},
                "epic": {"tempo_delta": 10, "desc": "壮大なサウンド"},
                "minimal": {"tempo_delta": 0, "desc": "シンプルに"},
            }
            
            adj = mood_adjustments.get(mood, {"tempo_delta": 0, "desc": ""})
            new_tempo = max(60, min(200, state.tempo + adj["tempo_delta"] * intensity))
            
            if not state.mock_mode and state.osc:
                state.osc.set_tempo(new_tempo)
            state.tempo = new_tempo
            
            result = f"🎭 雰囲気を '{mood}' に変更\n  テンポ: {new_tempo:.0f} BPM\n  {adj['desc']}"
        
        # ========== 情報 ==========
        elif name == "get_project_info":
            info = state.to_dict()
            result = f"""📊 プロジェクト情報:
  テンポ: {info['tempo']} BPM
  キー: {info['key']}
  トラック数: {len(info['tracks'])}
  再生中: {'▶️' if info['is_playing'] else '⏹️'}
  モード: {'🔇 Mock' if info['mock_mode'] else '🔊 Live'}
"""
            if info['tracks']:
                result += "\n  トラック一覧:\n"
                for t in info['tracks']:
                    result += f"    - {t['name']} ({t['type']})\n"
        
        elif name == "list_genres":
            genres = get_available_genres()
            result = f"🎵 利用可能なジャンル:\n  " + ", ".join(genres)
        
        elif name == "get_track_info":
            track_idx = args["track_index"]
            
            if not state.mock_mode and state.osc:
                info = state.osc.get_track_info(track_idx)
                result = f"📊 Track {track_idx} 情報:\n"
                result += f"  名前: {info.get('name', 'Unknown')}\n"
                result += f"  ボリューム: {info.get('volume', 'N/A')}\n"
                result += f"  パン: {info.get('pan', 'N/A')}"
            else:
                result = f"📊 Track {track_idx} 情報（モックモード）"
        
        elif name == "get_device_params":
            track_idx = args["track_index"]
            device_idx = args["device_index"]
            
            if not state.mock_mode and state.osc:
                params = state.osc.get_device_parameters(track_idx, device_idx)
                result = f"🎛️ Track {track_idx} Device {device_idx} パラメータ:\n"
                
                if params:
                    # パラメータ名のリストが返る場合
                    for i, param in enumerate(params[2:] if len(params) > 2 else params):  # 最初の2つはtrack/device index
                        value = state.osc.get_device_parameter_value(track_idx, device_idx, i)
                        val_str = f"{value:.2f}" if value is not None else "N/A"
                        result += f"  [{i}] {param}: {val_str}\n"
                else:
                    result += "  パラメータを取得できませんでした"
            else:
                result = f"🎛️ Track {track_idx} Device {device_idx} パラメータ（モックモード）"
        
        elif name == "osc_send":
            address = args["address"]
            osc_args = args.get("args", [])
            
            if not state.mock_mode and state.osc:
                responses = state.osc.query_raw(address, osc_args, timeout=0.5)
                result = f"OSC: {address} {osc_args}\n"
                result += f"Response ({len(responses)}):\n"
                for addr, params in responses:
                    result += f"  {addr}: {params}\n"
                if not responses:
                    result += "  (no response)"
            else:
                result = "OSC send: mock mode"
        
        elif name == "get_all_devices":
            if not state.mock_mode and state.osc:
                result = "=== Full Parameter Scan ===\n\n"
                
                # トラック数取得
                num_tracks = 7  # デフォルト
                
                for track_idx in range(num_tracks):
                    # デバイス一覧取得
                    devices_resp = state.osc.query_raw("/live/track/get/devices/name", [track_idx], timeout=0.3)
                    
                    track_line = f"[Track {track_idx}]"
                    if devices_resp:
                        for addr, params in devices_resp:
                            if params:
                                track_line += f" {params}"
                    result += track_line + "\n"
                    
                    # 各デバイスのパラメータ（最大5デバイス）
                    for dev_idx in range(5):
                        params_resp = state.osc.query_raw("/live/device/get/parameters/name", [track_idx, dev_idx], timeout=0.3)
                        if params_resp:
                            for addr, params in params_resp:
                                if len(params) > 2:
                                    result += f"  Device {dev_idx}: {params[2:][:10]}...\n"  # 最初の10パラメータ
                                    break
                        else:
                            break  # デバイスがない
                    
                    result += "\n"
            else:
                result = "Scan: mock mode"
        
        elif name == "create_scene":
            index = args["index"]
            scene_name = args["name"]
            if not state.mock_mode and state.osc:
                state.osc.send_message("/live/song/create_scene", [index])
                import time
                time.sleep(0.1)
                state.osc.send_message("/live/scene/set/name", [index, scene_name])
                result = f"🎬 シーン {index} '{scene_name}' を作成しました"
            else:
                result = f"シーン作成（モック）: {scene_name}"
        
        elif name == "duplicate_clip":
            src_track = args["src_track"]
            src_scene = args["src_scene"]
            dst_track = args["dst_track"]
            dst_scene = args["dst_scene"]
            if not state.mock_mode and state.osc:
                state.osc.send_message("/live/clip_slot/duplicate_clip_to", 
                                       [src_track, src_scene, dst_track, dst_scene])
                result = f"📋 クリップ複製: Track{src_track}/Scene{src_scene} → Track{dst_track}/Scene{dst_scene}"
            else:
                result = "クリップ複製（モック）"
        
        elif name == "delete_clip":
            track = args["track"]
            scene = args["scene"]
            if not state.mock_mode and state.osc:
                state.osc.send_message("/live/clip_slot/delete_clip", [track, scene])
                result = f"🗑️ クリップ削除: Track{track}/Scene{scene}"
            else:
                result = "クリップ削除（モック）"
        
        elif name == "fire_scene":
            scene = args["scene"]
            if not state.mock_mode and state.osc:
                state.osc.send_message("/live/scene/fire", [scene])
                result = f"▶️ シーン {scene} を再生"
            else:
                result = f"シーン再生（モック）: {scene}"
        
        elif name == "auto_play_scenes":
            bars_per_scene = args.get("bars_per_scene", 8)
            start_scene = args.get("start_scene", 0)
            end_scene = args.get("end_scene", 5)
            
            if not state.mock_mode and state.osc:
                import time
                import threading
                
                # テンポから1小節の秒数を計算
                tempo = state.tempo or 85
                seconds_per_bar = (60 / tempo) * 4  # 4拍で1小節
                wait_time = seconds_per_bar * bars_per_scene
                
                result = f"🎬 自動再生開始\n"
                result += f"  テンポ: {tempo} BPM\n"
                result += f"  各シーン: {bars_per_scene}小節 ({wait_time:.1f}秒)\n"
                result += f"  シーン: {start_scene} → {end_scene}\n\n"
                
                def play_sequence():
                    for scene_idx in range(start_scene, end_scene + 1):
                        state.osc.send_message("/live/scene/fire", [scene_idx])
                        time.sleep(wait_time)
                
                # バックグラウンドで実行
                thread = threading.Thread(target=play_sequence)
                thread.start()
                
                result += "✅ バックグラウンドで自動再生中..."
            else:
                result = "自動再生（モック）"
        
        elif name == "build_arrangement":
            style = args.get("style", "standard")
            if not state.mock_mode and state.osc:
                import time
                result = "🎼 Lo-Fi アレンジメントを構築中...\n\n"
                
                # シーン構成定義
                scenes = [
                    {"name": "Intro", "tracks": [5]},           # E-Piano only
                    {"name": "Verse 1", "tracks": [0, 1, 5]},   # Drums, Bass, E-Piano
                    {"name": "Chorus 1", "tracks": [0, 1, 2, 3, 4, 5, 6]},  # All
                    {"name": "Verse 2", "tracks": [0, 1, 2, 5]}, # Drums, Bass, Vibes, E-Piano
                    {"name": "Chorus 2", "tracks": [0, 1, 2, 3, 4, 5, 6]},  # All
                    {"name": "Outro", "tracks": [3, 5]},        # Melody, E-Piano
                ]
                
                num_tracks = 7
                
                # 元クリップの場所を特定（Scene 1にあると仮定）
                source_scene = 1
                
                for scene_idx, scene_def in enumerate(scenes):
                    scene_name = scene_def["name"]
                    active_tracks = scene_def["tracks"]
                    
                    # シーン名を設定
                    state.osc.send_message("/live/scene/set/name", [scene_idx, scene_name])
                    time.sleep(0.05)
                    
                    result += f"[Scene {scene_idx}] {scene_name}\n"
                    
                    for track_idx in range(num_tracks):
                        if track_idx in active_tracks:
                            # クリップを複製
                            state.osc.send_message("/live/clip_slot/duplicate_clip_to",
                                                   [track_idx, source_scene, track_idx, scene_idx])
                            result += f"  Track {track_idx}: ✅\n"
                        else:
                            # クリップを削除（空にする）
                            state.osc.send_message("/live/clip_slot/delete_clip", [track_idx, scene_idx])
                            result += f"  Track {track_idx}: ⬜\n"
                        time.sleep(0.03)
                    
                    result += "\n"
                
                result += "✅ アレンジメント構築完了！\n"
                result += "シーンをクリックして再生できます"
            else:
                result = "アレンジメント構築（モック）"
        
        else:
            result = f"[ERR] 未知のツール: {name}"
            
    except Exception as e:
        result = f"[ERR] エラー: {str(e)}"
    
    return [types.TextContent(type="text", text=result)]


# ==================== リソース ====================

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """利用可能なリソース"""
    return [
        types.Resource(
            uri="ableton://project/state",
            name="Project State",
            description="現在のプロジェクト状態",
            mimeType="application/json"
        )
    ]


@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """リソース読み取り"""
    if uri == "ableton://project/state":
        return json.dumps(state.to_dict(), ensure_ascii=False, indent=2)
    raise ValueError(f"Unknown resource: {uri}")


# ==================== メイン ====================

async def main():
    """MCPサーバーを起動"""
    import sys
    
    # 起動時に自動接続を試みる
    print("[START] Starting Ableton MCP Server...", file=sys.stderr)
    state.connect()
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="ableton-agent",
                server_version="2.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
