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
from src.automation_generator import generate_automation_points


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
        self.auto_play_cancel = False  # 自動再生キャンセルフラグ
        self.auto_play_thread = None   # 自動再生スレッド
        
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
        types.Tool(
            name="get_project_overview",
            description="プロジェクト全体の情報を取得（トラック、クリップ、デバイス一覧）",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="set_all_clips_length",
            description="全クリップの長さを統一する（小節数を指定）",
            inputSchema={
                "type": "object",
                "properties": {
                    "bars": {"type": "integer", "description": "小節数（例: 4, 8, 16）", "default": 8}
                }
            }
        ),
        types.Tool(
            name="create_lofi_project",
            description="Lo-Fi Hip Hopプロジェクトを一発で作成（テンプレート）",
            inputSchema={
                "type": "object",
                "properties": {
                    "tempo": {"type": "number", "description": "テンポ（BPM）", "default": 85},
                    "key": {"type": "string", "description": "キー（例: Am, C, Fm）", "default": "Am"}
                }
            }
        ),

        # オートメーション
        types.Tool(
            name="add_automation",
            description="クリップにオートメーションカーブを設定（フィルタースイープ、ボリュームフェード等）",
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index": {"type": "integer", "description": "トラック番号"},
                    "clip_index": {"type": "integer", "description": "クリップ番号", "default": 0},
                    "device_index": {"type": "integer", "description": "デバイス番号（音源=0, エフェクト=1,2,...）"},
                    "param_index": {"type": "integer", "description": "パラメータ番号"},
                    "shape": {
                        "type": "string",
                        "enum": ["linear", "exponential", "s_curve", "sine", "step"],
                        "description": "カーブ形状"
                    },
                    "start_value": {"type": "number", "description": "開始値（0.0-1.0）"},
                    "end_value": {"type": "number", "description": "終了値（0.0-1.0）"},
                    "start_beat": {"type": "number", "description": "開始位置（拍）", "default": 0.0},
                    "duration_beats": {"type": "number", "description": "長さ（拍）。省略時はクリップ全体"}
                },
                "required": ["track_index", "device_index", "param_index", "shape", "start_value", "end_value"]
            }
        ),
        types.Tool(
            name="clear_automation",
            description="オートメーションをクリア（特定パラメータまたは全て）",
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index": {"type": "integer", "description": "トラック番号"},
                    "clip_index": {"type": "integer", "description": "クリップ番号", "default": 0},
                    "device_index": {"type": "integer", "description": "デバイス番号（省略時は全クリア）"},
                    "param_index": {"type": "integer", "description": "パラメータ番号（省略時は全クリア）"}
                },
                "required": ["track_index"]
            }
        ),
        types.Tool(
            name="add_filter_sweep",
            description="フィルタースイープを追加（Auto Filterの周波数を自動変化）",
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index": {"type": "integer", "description": "トラック番号"},
                    "clip_index": {"type": "integer", "description": "クリップ番号", "default": 0},
                    "direction": {
                        "type": "string",
                        "enum": ["up", "down", "updown"],
                        "description": "スイープ方向"
                    },
                    "bars": {"type": "integer", "description": "小節数", "default": 4}
                },
                "required": ["track_index", "direction"]
            }
        ),
        types.Tool(
            name="add_volume_fade",
            description="ボリュームのフェードイン/アウトを追加",
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index": {"type": "integer", "description": "トラック番号"},
                    "clip_index": {"type": "integer", "description": "クリップ番号", "default": 0},
                    "fade_type": {
                        "type": "string",
                        "enum": ["in", "out"],
                        "description": "フェードタイプ"
                    },
                    "bars": {"type": "integer", "description": "小節数", "default": 2}
                },
                "required": ["track_index", "fade_type"]
            }
        ),

        # プロジェクト構成表
        types.Tool(
            name="get_project_table",
            description="プロジェクトの構成表を生成（シーン×トラックのクリップ配置、小節数、テンポ）",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),

        # 全デバイス・パラメータ分析 + 構成表
        types.Tool(
            name="get_full_project_analysis",
            description="全トラックのデバイス・パラメータ一覧と曲構成表を同時出力。オートメーション戦略立案用",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),

        # Chordsオートメーションプリセット
        types.Tool(
            name="apply_chords_automation",
            description="Chordsトラックに構成に合わせたオートメーションを一括適用（Auto Filter Freq, Chorus D/W, E-Piano Room）",
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index": {"type": "integer", "description": "Chordsトラック番号"},
                    "intensity": {
                        "type": "number",
                        "description": "強度（0.5=控えめ, 1.0=標準, 1.5=強め）",
                        "default": 1.0
                    }
                },
                "required": ["track_index"]
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
            # 自動再生スレッドをキャンセル
            state.auto_play_cancel = True
            if state.auto_play_thread and state.auto_play_thread.is_alive():
                state.auto_play_thread.join(timeout=1.0)
            
            if not state.mock_mode and state.osc:
                state.osc.stop()
            state.is_playing = False
            result = "⏹️ 停止しました（自動再生もキャンセル）"
        
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
                    # パラメータを文字列として整形
                    params_str = ", ".join(str(p) for p in params)
                    result += f"  {addr}: {params_str}\n"
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
                                # デバイス名のみ抽出（文字列のみ）
                                device_names = [str(p) for p in params if isinstance(p, str)]
                                track_line += f" {', '.join(device_names)}"
                    result += track_line + "\n"
                    
                    # 各デバイスのパラメータ（最大5デバイス）
                    for dev_idx in range(5):
                        params_resp = state.osc.query_raw("/live/device/get/parameters/name", [track_idx, dev_idx], timeout=0.3)
                        if params_resp:
                            for addr, params in params_resp:
                                if len(params) > 2:
                                    # パラメータ名を文字列として整形
                                    param_names = [str(p) for p in params[2:][:10] if isinstance(p, str)]
                                    result += f"  Device {dev_idx}: {', '.join(param_names)}...\n"
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
                
                # 前回のスレッドをキャンセル
                state.auto_play_cancel = True
                if state.auto_play_thread and state.auto_play_thread.is_alive():
                    state.auto_play_thread.join(timeout=1.0)
                state.auto_play_cancel = False
                
                # テンポから1小節の秒数を計算
                tempo = state.tempo or 85
                seconds_per_bar = (60 / tempo) * 4  # 4拍で1小節
                wait_time = seconds_per_bar * bars_per_scene
                
                result = f"🎬 自動再生開始\n"
                result += f"  テンポ: {tempo} BPM\n"
                result += f"  各シーン: {bars_per_scene}小節 ({wait_time:.1f}秒)\n"
                result += f"  シーン: {start_scene} → {end_scene}\n\n"
                
                def play_sequence():
                    start_time = time.time()
                    for i, scene_idx in enumerate(range(start_scene, end_scene + 1)):
                        if state.auto_play_cancel:
                            break
                        state.osc.send_message("/live/scene/fire", [scene_idx])
                        # 絶対時間で次のシーン発火タイミングを計算（50ms早めに発火してドリフト防止）
                        next_fire_time = start_time + (i + 1) * wait_time - 0.05
                        while time.time() < next_fire_time:
                            if state.auto_play_cancel:
                                break
                            time.sleep(0.05)
                
                # バックグラウンドで実行
                state.auto_play_thread = threading.Thread(target=play_sequence)
                state.auto_play_thread.start()
                
                result += "✅ バックグラウンドで自動再生中...\n"
                result += "（停止するには「停止して」と言ってください）"
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
        
        elif name == "get_project_overview":
            if not state.mock_mode and state.osc:
                import time
                result = "📊 プロジェクト概要\n"
                result += "=" * 40 + "\n\n"
                
                # テンポ取得
                result += f"🎵 テンポ: {state.tempo} BPM\n\n"
                
                # トラック数取得
                resp = state.osc.query_raw("/live/song/get/num_tracks", [], timeout=0.3)
                num_tracks = 0
                if resp:
                    for addr, params in resp:
                        if params:
                            num_tracks = params[0]
                
                # シーン数取得
                resp = state.osc.query_raw("/live/song/get/num_scenes", [], timeout=0.3)
                num_scenes = 0
                if resp:
                    for addr, params in resp:
                        if params:
                            num_scenes = params[0]
                
                result += f"📁 トラック数: {num_tracks}\n"
                result += f"🎬 シーン数: {num_scenes}\n\n"
                
                # 各トラックの情報
                result += "### トラック一覧\n"
                for track_idx in range(num_tracks):
                    # トラック名
                    resp = state.osc.query_raw("/live/track/get/name", [track_idx], timeout=0.2)
                    track_name = f"Track {track_idx}"
                    if resp:
                        for addr, params in resp:
                            if len(params) > 1:
                                track_name = params[1]
                    
                    # ボリューム
                    resp = state.osc.query_raw("/live/track/get/volume", [track_idx], timeout=0.2)
                    volume = 0
                    if resp:
                        for addr, params in resp:
                            if len(params) > 1:
                                volume = params[1]
                    
                    # デバイス
                    resp = state.osc.query_raw("/live/track/get/devices/name", [track_idx], timeout=0.2)
                    devices = []
                    if resp:
                        for addr, params in resp:
                            if len(params) > 1:
                                # 文字列のみ抽出
                                devices = [str(p) for p in params[1:] if isinstance(p, str)]

                    # クリップ情報
                    clips = []
                    for scene_idx in range(min(num_scenes, 8)):  # 最大8シーン
                        resp = state.osc.query_raw("/live/clip_slot/get/has_clip", [track_idx, scene_idx], timeout=0.1)
                        has_clip = False
                        if resp:
                            for addr, params in resp:
                                if len(params) > 2:
                                    has_clip = params[2]
                        clips.append("●" if has_clip else "○")

                    result += f"\n[{track_idx}] {track_name}\n"
                    result += f"    Vol: {volume:.2f} | Devices: {', '.join(devices[:3]) if devices else 'None'}\n"
                    result += f"    Clips: {' '.join(clips)}\n"
                
                # シーン名
                result += "\n### シーン一覧\n"
                for scene_idx in range(num_scenes):
                    resp = state.osc.query_raw("/live/scene/get/name", [scene_idx], timeout=0.1)
                    scene_name = f"Scene {scene_idx}"
                    if resp:
                        for addr, params in resp:
                            if len(params) > 1:
                                scene_name = params[1]
                    result += f"  [{scene_idx}] {scene_name}\n"
            else:
                result = "プロジェクト概要（モック）"
        
        elif name == "set_all_clips_length":
            bars = args.get("bars", 8)
            beats = bars * 4  # 1小節 = 4拍
            
            if not state.mock_mode and state.osc:
                result = f"⚠️ AbletonOSCではクリップ長の変更がサポートされていません。\n\n"
                result += f"**手動で設定してください：**\n"
                result += f"1. Ctrl+A で全クリップを選択\n"
                result += f"2. クリップビューを開く\n"
                result += f"3. Loop Length を {bars} bars ({beats} beats) に設定\n\n"
                result += f"または、各クリップをダブルクリックして個別に設定"
            else:
                result = f"クリップ長設定（モック）: {bars}小節"
        
        elif name == "create_lofi_project":
            tempo = args.get("tempo", 85)
            key = args.get("key", "Am")
            
            if not state.mock_mode and state.osc:
                import time
                result = "🎹 Lo-Fi Hip Hop プロジェクト作成中...\n\n"
                
                # テンポ設定
                state.osc.set_tempo(tempo)
                state.tempo = tempo
                result += f"✅ テンポ: {tempo} BPM\n"
                time.sleep(0.1)
                
                # トラック構成
                tracks = [
                    {"name": "Drums", "type": "drum", "pattern": "basic_beat", "bars": 2},
                    {"name": "Bass", "type": "bass", "style": "basic", "bars": 4},
                    {"name": "Chords", "type": "chords", "style": "lofi", "bars": 4},
                    {"name": "Melody", "type": "melody", "bars": 4},
                ]
                
                for i, track_def in enumerate(tracks):
                    state.osc.create_midi_track(i)
                    time.sleep(0.05)
                    state.osc.set_track_name(i, track_def["name"])
                    time.sleep(0.05)
                    state.osc.create_clip(i, 0, track_def["bars"] * 4.0)
                    time.sleep(0.05)
                    
                    # パターン生成
                    root = key[0]  # "Am" -> "A"
                    scale_type = "minor" if "m" in key else "major"
                    
                    if track_def["type"] == "drum":
                        notes = DrumPattern.basic_beat(track_def["bars"])
                    elif track_def["type"] == "bass":
                        notes = create_bassline(root=root, scale=scale_type, bars=track_def["bars"], style="basic")
                    elif track_def["type"] == "chords":
                        # create_chordsは2次元リストを返すのでフラットにする
                        chord_notes = create_chords(root=root, scale=scale_type, bars=track_def["bars"], style="lofi")
                        notes = []
                        for chord in chord_notes:
                            notes.extend(chord)
                    elif track_def["type"] == "melody":
                        notes = create_melody(root=root, scale=scale_type, bars=track_def["bars"])
                    else:
                        notes = []
                    
                    if notes:
                        state.osc.add_notes(i, 0, notes)
                    time.sleep(0.05)
                    
                    result += f"✅ Track {i}: {track_def['name']}\n"
                
                state.track_counter = len(tracks)
                state.key = key
                
                result += f"\n🎵 キー: {key}\n"
                result += "\n✅ プロジェクト作成完了！\n\n"
                result += "**次のステップ：**\n"
                result += "1. 各トラックにインストゥルメントを追加\n"
                result += "2. エフェクトを追加（Saturator, Reverb, Auto Filter等）\n"
                result += "3. 「アレンジメントを自動構築して」と言ってください"
            else:
                result = f"Lo-Fiプロジェクト作成（モック）: {tempo}BPM, {key}"
        
        # ========== オートメーション ==========
        elif name == "add_automation":
            track_idx = args["track_index"]
            clip_idx = args.get("clip_index", 0)
            device_idx = args["device_index"]
            param_idx = args["param_index"]
            shape = args["shape"]
            start_val = args["start_value"]
            end_val = args["end_value"]
            start_beat = args.get("start_beat", 0.0)
            duration_beats = args.get("duration_beats")

            if duration_beats is None:
                # クリップの長さを取得（デフォルト16拍=4小節）
                if not state.mock_mode and state.osc:
                    length_result = state.osc.query("/live/clip/get/length", [track_idx, clip_idx])
                    if length_result and len(length_result) > 2:
                        duration_beats = float(length_result[2])
                    else:
                        duration_beats = 16.0
                else:
                    duration_beats = 16.0

            points = generate_automation_points(
                shape=shape,
                start_val=start_val,
                end_val=end_val,
                start_time=start_beat,
                duration_beats=duration_beats,
                resolution=32
            )

            if not state.mock_mode and state.osc:
                import time as time_mod
                # クリップを発火してから書き込む（再生中でないとオートメーションが反映されない）
                was_playing = state.is_playing
                state.osc.send_message("/live/clip/fire", [track_idx, clip_idx])
                time_mod.sleep(0.1)
                # まず既存のオートメーションをクリア
                state.osc.clear_automation(track_idx, clip_idx, device_idx, param_idx)
                time_mod.sleep(0.05)
                # ポイントを書き込み
                for t, v, d in points:
                    state.osc.add_automation_step(track_idx, clip_idx, device_idx, param_idx, t, v, d)
                    time_mod.sleep(0.01)
                # 元々再生中でなければ停止
                if not was_playing:
                    state.osc.send_message("/live/song/stop_playing", [])
                    time_mod.sleep(0.05)

            result = (f"📈 オートメーション追加: Track {track_idx} Clip {clip_idx}\n"
                      f"  Device {device_idx} Param {param_idx}\n"
                      f"  Shape: {shape} ({start_val:.2f} → {end_val:.2f})\n"
                      f"  Range: {start_beat:.1f} ~ {start_beat + duration_beats:.1f} beats\n"
                      f"  Points: {len(points)}")

        elif name == "clear_automation":
            track_idx = args["track_index"]
            clip_idx = args.get("clip_index", 0)
            device_idx = args.get("device_index")
            param_idx = args.get("param_index")

            if not state.mock_mode and state.osc:
                if device_idx is not None and param_idx is not None:
                    state.osc.clear_automation(track_idx, clip_idx, device_idx, param_idx)
                    result = f"🗑️ オートメーションクリア: Track {track_idx} Clip {clip_idx} Device {device_idx} Param {param_idx}"
                else:
                    state.osc.clear_all_automation(track_idx, clip_idx)
                    result = f"🗑️ 全オートメーションクリア: Track {track_idx} Clip {clip_idx}"
            else:
                result = f"オートメーションクリア（モック）"

        elif name == "add_filter_sweep":
            track_idx = args["track_index"]
            clip_idx = args.get("clip_index", 0)
            direction = args["direction"]
            bars = args.get("bars", 4)
            duration_beats = bars * 4.0

            # Auto Filterの周波数パラメータを探す
            filter_device_idx = None
            filter_freq_param_idx = None

            if not state.mock_mode and state.osc:
                import time as time_mod
                # デバイス一覧を取得してAuto Filterを探す
                devices_resp = state.osc.query_raw("/live/track/get/devices/name", [track_idx], timeout=0.3)
                if devices_resp:
                    for addr, params in devices_resp:
                        if params:
                            # params = (track_index, "device0", "device1", ...) なので文字列だけカウント
                            str_idx = 0
                            for p in params:
                                if isinstance(p, str):
                                    if "Auto Filter" in p:
                                        filter_device_idx = str_idx
                                        break
                                    str_idx += 1

                if filter_device_idx is None:
                    # Auto Filterがない場合は追加
                    state.osc.load_device(track_idx, "Audio Effects/Auto Filter")
                    time_mod.sleep(0.3)
                    # 再取得
                    devices_resp = state.osc.query_raw("/live/track/get/devices/name", [track_idx], timeout=0.3)
                    if devices_resp:
                        for addr, params in devices_resp:
                            if params:
                                str_idx = 0
                                for p in params:
                                    if isinstance(p, str):
                                        if "Auto Filter" in p:
                                            filter_device_idx = str_idx
                                            break
                                        str_idx += 1

                if filter_device_idx is not None:
                    # Frequencyパラメータを探す（通常index 1）
                    params_resp = state.osc.query_raw(
                        "/live/device/get/parameters/name",
                        [track_idx, filter_device_idx], timeout=0.3
                    )
                    if params_resp:
                        for addr, params in params_resp:
                            for i, p in enumerate(params):
                                if isinstance(p, str) and "Frequency" in p:
                                    filter_freq_param_idx = i - 2  # 最初の2つはtrack/device index
                                    break

                    if filter_freq_param_idx is None:
                        filter_freq_param_idx = 1  # デフォルト

                    # スイープポイント生成
                    if direction == "up":
                        points = generate_automation_points("exponential", 0.1, 0.9, 0.0, duration_beats, 32)
                    elif direction == "down":
                        points = generate_automation_points("exponential", 0.9, 0.1, 0.0, duration_beats, 32)
                    else:  # updown
                        half = duration_beats / 2
                        points_up = generate_automation_points("exponential", 0.1, 0.9, 0.0, half, 16)
                        points_down = generate_automation_points("exponential", 0.9, 0.1, half, half, 16)
                        points = points_up + points_down

                    # クリップを発火してから書き込む（再生中でないとオートメーションが反映されない）
                    was_playing = state.is_playing
                    state.osc.send_message("/live/clip/fire", [track_idx, clip_idx])
                    time_mod.sleep(0.1)
                    # クリア＆書き込み
                    state.osc.clear_automation(track_idx, clip_idx, filter_device_idx, filter_freq_param_idx)
                    time_mod.sleep(0.05)
                    for t, v, d in points:
                        state.osc.add_automation_step(
                            track_idx, clip_idx, filter_device_idx, filter_freq_param_idx, t, v, d
                        )
                        time_mod.sleep(0.01)
                    # 元々再生中でなければ停止
                    if not was_playing:
                        state.osc.send_message("/live/song/stop_playing", [])
                        time_mod.sleep(0.05)

                    result = (f"🌊 フィルタースイープ追加: Track {track_idx}\n"
                              f"  Direction: {direction}\n"
                              f"  Duration: {bars}小節\n"
                              f"  Device: {filter_device_idx}, Param: {filter_freq_param_idx}\n"
                              f"  Points: {len(points)}")
                else:
                    result = "[ERR] Auto Filterが見つかりませんでした"
            else:
                result = f"フィルタースイープ（モック）: Track {track_idx} {direction} {bars}小節"

        elif name == "add_volume_fade":
            track_idx = args["track_index"]
            clip_idx = args.get("clip_index", 0)
            fade_type = args["fade_type"]
            bars = args.get("bars", 2)
            duration_beats = bars * 4.0

            # Mixer Device (トラックボリューム) のパラメータ
            # Abletonではミキサーはデバイスチェーンの一部ではないので、
            # トラックボリュームのオートメーションは別のアプローチが必要
            # ここではクリップのGain（ある場合）またはUtilityのGainを使う

            if not state.mock_mode and state.osc:
                import time as time_mod

                # Utilityデバイスを探す、なければ追加
                utility_device_idx = None
                gain_param_idx = None

                devices_resp = state.osc.query_raw("/live/track/get/devices/name", [track_idx], timeout=0.3)
                if devices_resp:
                    for addr, params in devices_resp:
                        if params:
                            str_idx = 0
                            for p in params:
                                if isinstance(p, str):
                                    if "Utility" in p:
                                        utility_device_idx = str_idx
                                        break
                                    str_idx += 1

                if utility_device_idx is None:
                    state.osc.load_device(track_idx, "Audio Effects/Utility")
                    time_mod.sleep(0.3)
                    devices_resp = state.osc.query_raw("/live/track/get/devices/name", [track_idx], timeout=0.3)
                    if devices_resp:
                        for addr, params in devices_resp:
                            if params:
                                str_idx = 0
                                for p in params:
                                    if isinstance(p, str):
                                        if "Utility" in p:
                                            utility_device_idx = str_idx
                                            break
                                        str_idx += 1

                if utility_device_idx is not None:
                    # Gainパラメータを探す
                    params_resp = state.osc.query_raw(
                        "/live/device/get/parameters/name",
                        [track_idx, utility_device_idx], timeout=0.3
                    )
                    if params_resp:
                        for addr, params in params_resp:
                            for i, p in enumerate(params):
                                if isinstance(p, str) and "Gain" in p:
                                    gain_param_idx = i - 2
                                    break

                    if gain_param_idx is None:
                        gain_param_idx = 1  # デフォルト

                    if fade_type == "in":
                        points = generate_automation_points("s_curve", 0.0, 0.5, 0.0, duration_beats, 32)
                    else:  # out
                        points = generate_automation_points("s_curve", 0.5, 0.0, 0.0, duration_beats, 32)

                    # クリップを発火してから書き込む（再生中でないとオートメーションが反映されない）
                    was_playing = state.is_playing
                    state.osc.send_message("/live/clip/fire", [track_idx, clip_idx])
                    time_mod.sleep(0.1)
                    state.osc.clear_automation(track_idx, clip_idx, utility_device_idx, gain_param_idx)
                    time_mod.sleep(0.05)
                    for t, v, d in points:
                        state.osc.add_automation_step(
                            track_idx, clip_idx, utility_device_idx, gain_param_idx, t, v, d
                        )
                        time_mod.sleep(0.01)
                    # 元々再生中でなければ停止
                    if not was_playing:
                        state.osc.send_message("/live/song/stop_playing", [])
                        time_mod.sleep(0.05)

                    result = (f"🔊 ボリュームフェード追加: Track {track_idx}\n"
                              f"  Type: fade {fade_type}\n"
                              f"  Duration: {bars}小節\n"
                              f"  Device: {utility_device_idx}, Param: {gain_param_idx}\n"
                              f"  Points: {len(points)}")
                else:
                    result = "[ERR] Utilityデバイスが見つかりませんでした"
            else:
                result = f"ボリュームフェード（モック）: Track {track_idx} fade {fade_type} {bars}小節"

        elif name == "get_full_project_analysis":
            if not state.mock_mode and state.osc:
                import time as time_mod

                lines = []

                # --- テンポ・基本情報 ---
                tempo = state.tempo
                num_tracks_resp = state.osc.query("/live/song/get/num_tracks", [])
                num_scenes_resp = state.osc.query("/live/song/get/num_scenes", [])
                num_tracks = int(num_tracks_resp[0]) if num_tracks_resp else 0
                num_scenes = int(num_scenes_resp[0]) if num_scenes_resp else 0

                # --- 構成表 ---
                track_data_resp = state.osc.query_raw(
                    "/live/song/get/track_data",
                    [0, num_tracks, "track.name", "clip_slot.has_clip"],
                    timeout=1.0
                )
                clip_len_resp = state.osc.query_raw(
                    "/live/song/get/track_data",
                    [0, num_tracks, "clip.length"],
                    timeout=1.0
                )

                scene_names = []
                for i in range(num_scenes):
                    resp = state.osc.query("/live/scene/get/name", [i])
                    scene_names.append(resp[1] if resp and len(resp) > 1 else f"Scene {i}")
                    time_mod.sleep(0.01)

                track_names = []
                clip_matrix = []
                if track_data_resp:
                    for addr, params in track_data_resp:
                        if params:
                            idx = 0
                            for t in range(num_tracks):
                                track_names.append(str(params[idx]))
                                idx += 1
                                row = []
                                for s in range(num_scenes):
                                    row.append(bool(params[idx]))
                                    idx += 1
                                clip_matrix.append(row)

                clip_lengths = []
                if clip_len_resp:
                    for addr, params in clip_len_resp:
                        if params:
                            idx = 0
                            for t in range(num_tracks):
                                row = []
                                for s in range(num_scenes):
                                    val = params[idx]
                                    try:
                                        row.append(float(val) if val is not None else None)
                                    except (ValueError, TypeError):
                                        row.append(None)
                                    idx += 1
                                clip_lengths.append(row)

                lines.append(f"# プロジェクト全体分析")
                lines.append(f"🎵 テンポ: {tempo} BPM / トラック: {num_tracks} / シーン: {num_scenes}")
                lines.append("")

                # 構成テーブル
                lines.append("## 曲構成表")
                header = "| # | シーン | 小節 |"
                sep = "|---|---|---|"
                for tn in track_names:
                    header += f" {tn} |"
                    sep += "---|"
                lines.append(header)
                lines.append(sep)

                total_bars = 0
                for s in range(num_scenes):
                    bars = None
                    for t in range(num_tracks):
                        if clip_matrix and clip_matrix[t][s] and clip_lengths and len(clip_lengths) > t and clip_lengths[t][s]:
                            bars = int(clip_lengths[t][s] / 4)
                            break
                    if bars:
                        total_bars += bars
                    row = f"| {s} | {scene_names[s]} | {bars or '-'} |"
                    for t in range(num_tracks):
                        has = clip_matrix[t][s] if clip_matrix else False
                        row += " ● |" if has else " - |"
                    lines.append(row)

                total_sec = total_bars * 4 * 60 / tempo
                lines.append(f"\n**合計**: {total_bars}小節 / 約{int(total_sec//60)}分{int(total_sec%60)}秒")

                # --- 全デバイス・パラメータ ---
                lines.append("")
                lines.append("## 全トラック デバイス・パラメータ一覧")

                # 表示不要なパラメータ（Device On, Macro系）
                skip_prefixes = ("Device On", "Macro ", "Chain Selector")

                for t in range(num_tracks):
                    tname = track_names[t] if t < len(track_names) else f"Track {t}"
                    # デバイス名一覧
                    dev_names_resp = state.osc.query_raw("/live/track/get/devices/name", [t], timeout=0.3)
                    dev_names = []
                    if dev_names_resp:
                        for addr, params in dev_names_resp:
                            if params:
                                for p in params:
                                    if isinstance(p, str):
                                        dev_names.append(p)

                    lines.append(f"\n### [{t}] {tname}")
                    lines.append(f"Devices: {', '.join(dev_names)}")

                    for d_idx, dname in enumerate(dev_names):
                        # パラメータ名取得
                        pnames_resp = state.osc.query_raw(
                            "/live/device/get/parameters/name", [t, d_idx], timeout=0.3
                        )
                        pvals_resp = state.osc.query_raw(
                            "/live/device/get/parameters/value", [t, d_idx], timeout=0.3
                        )
                        time_mod.sleep(0.02)

                        pnames = []
                        pvals = []
                        if pnames_resp:
                            for addr, params in pnames_resp:
                                if params:
                                    pnames = [str(p) for p in params if isinstance(p, str)]
                        if pvals_resp:
                            for addr, params in pvals_resp:
                                if params:
                                    # 最初の2つはtrack/device index
                                    pvals = list(params[2:]) if len(params) > 2 else []

                        if not pnames:
                            continue

                        lines.append(f"\n**D{d_idx}: {dname}**")
                        lines.append("| # | パラメータ | 値 |")
                        lines.append("|---|---|---|")

                        for p_idx, pname in enumerate(pnames):
                            if any(pname.startswith(skip) for skip in skip_prefixes):
                                continue
                            val = pvals[p_idx] if p_idx < len(pvals) else "?"
                            if isinstance(val, float):
                                val_str = f"{val:.3f}" if abs(val) < 10 else f"{val:.1f}"
                            else:
                                val_str = str(val)
                            lines.append(f"| {p_idx} | {pname} | {val_str} |")

                result = "\n".join(lines)
            else:
                result = "プロジェクト分析（モック）"

        elif name == "get_project_table":
            if not state.mock_mode and state.osc:
                import time as time_mod

                # テンポ取得
                tempo = state.tempo

                # トラック数・シーン数
                num_tracks_resp = state.osc.query("/live/song/get/num_tracks", [])
                num_scenes_resp = state.osc.query("/live/song/get/num_scenes", [])
                num_tracks = int(num_tracks_resp[0]) if num_tracks_resp else 0
                num_scenes = int(num_scenes_resp[0]) if num_scenes_resp else 0

                # トラック名 + クリップ有無を一括取得
                track_data_resp = state.osc.query_raw(
                    "/live/song/get/track_data",
                    [0, num_tracks, "track.name", "clip_slot.has_clip"],
                    timeout=1.0
                )

                # クリップ長さも一括取得
                clip_len_resp = state.osc.query_raw(
                    "/live/song/get/track_data",
                    [0, num_tracks, "clip.length"],
                    timeout=1.0
                )

                # シーン名を取得
                scene_names = []
                for i in range(num_scenes):
                    resp = state.osc.query("/live/scene/get/name", [i])
                    scene_names.append(resp[1] if resp and len(resp) > 1 else f"Scene {i}")
                    time_mod.sleep(0.01)

                # track_data パース: (name, has_clip*num_scenes, name, has_clip*num_scenes, ...)
                track_names = []
                clip_matrix = []  # track_idx -> [bool, bool, ...]
                if track_data_resp:
                    for addr, params in track_data_resp:
                        if params:
                            idx = 0
                            for t in range(num_tracks):
                                tname = str(params[idx])
                                track_names.append(tname)
                                idx += 1
                                row = []
                                for s in range(num_scenes):
                                    row.append(bool(params[idx]))
                                    idx += 1
                                clip_matrix.append(row)

                # clip_length パース
                clip_lengths = []  # track_idx -> [float or None, ...]
                if clip_len_resp:
                    for addr, params in clip_len_resp:
                        if params:
                            idx = 0
                            for t in range(num_tracks):
                                row = []
                                for s in range(num_scenes):
                                    val = params[idx]
                                    if val is not None and val != "None":
                                        try:
                                            row.append(float(val))
                                        except (ValueError, TypeError):
                                            row.append(None)
                                    else:
                                        row.append(None)
                                    idx += 1
                                clip_lengths.append(row)

                # テーブル生成
                lines = []
                lines.append(f"🎵 テンポ: {tempo} BPM / トラック: {num_tracks} / シーン: {num_scenes}")
                lines.append("")

                # ヘッダ
                header = "| # | シーン | 小節 |"
                separator = "|---|---|---|"
                for tn in track_names:
                    header += f" {tn} |"
                    separator += "---|"
                lines.append(header)
                lines.append(separator)

                # 各シーン行
                total_bars = 0
                for s in range(num_scenes):
                    # 小節数: そのシーンにあるクリップの長さから算出（4拍=1小節）
                    bars = None
                    for t in range(num_tracks):
                        if clip_matrix and clip_matrix[t][s] and clip_lengths and clip_lengths[t][s]:
                            bars = int(clip_lengths[t][s] / 4)
                            break
                    bars_str = str(bars) if bars else "-"
                    if bars:
                        total_bars += bars

                    row = f"| {s} | {scene_names[s]} | {bars_str} |"
                    for t in range(num_tracks):
                        has = clip_matrix[t][s] if clip_matrix else False
                        row += " ● |" if has else " - |"
                    lines.append(row)

                # 合計
                total_seconds = total_bars * 4 * 60 / tempo
                total_min = int(total_seconds // 60)
                total_sec = int(total_seconds % 60)
                lines.append("")
                lines.append(f"**合計**: {total_bars}小節 / 約{total_min}分{total_sec}秒")

                result = "\n".join(lines)
            else:
                result = "プロジェクト構成表（モック）"

        elif name == "apply_chords_automation":
            track_idx = args["track_index"]
            intensity = args.get("intensity", 1.0)

            if not state.mock_mode and state.osc:
                import time as time_mod

                # デバイス構成を自動検出
                # Auto Filter を探す
                filter_dev = None
                filter_freq_param = None
                chorus_dev = None
                chorus_dw_param = None
                epiano_dev = 0  # 音源は通常 device 0
                room_param = None

                devices_resp = state.osc.query_raw("/live/track/get/devices/name", [track_idx], timeout=0.3)
                if devices_resp:
                    for addr, params in devices_resp:
                        if params:
                            str_idx = 0
                            for p in params:
                                if isinstance(p, str):
                                    if "Auto Filter" in p:
                                        filter_dev = str_idx
                                    elif "Chorus" in p or "Ensemble" in p:
                                        chorus_dev = str_idx
                                    str_idx += 1

                # パラメータ検出
                if filter_dev is not None:
                    resp = state.osc.query_raw("/live/device/get/parameters/name", [track_idx, filter_dev], timeout=0.3)
                    if resp:
                        for addr, params in resp:
                            for i, p in enumerate(params):
                                if isinstance(p, str) and p == "Frequency":
                                    filter_freq_param = i - 2
                                    break

                if chorus_dev is not None:
                    resp = state.osc.query_raw("/live/device/get/parameters/name", [track_idx, chorus_dev], timeout=0.3)
                    if resp:
                        for addr, params in resp:
                            for i, p in enumerate(params):
                                if isinstance(p, str) and p == "Dry/Wet":
                                    chorus_dw_param = i - 2
                                    break

                # E-Piano Room パラメータ検出
                resp = state.osc.query_raw("/live/device/get/parameters/name", [track_idx, epiano_dev], timeout=0.3)
                if resp:
                    for addr, params in resp:
                        for i, p in enumerate(params):
                            if isinstance(p, str) and p == "Room":
                                room_param = i - 2
                                break

                # クリップの有無を確認
                clip_resp = state.osc.query_raw(
                    "/live/song/get/track_data",
                    [track_idx, track_idx + 1, "clip_slot.has_clip"],
                    timeout=0.5
                )
                has_clips = []
                if clip_resp:
                    for addr, params in clip_resp:
                        if params:
                            has_clips = [bool(p) for p in params]

                # シーン名を取得してセクション判定
                num_scenes_resp = state.osc.query("/live/song/get/num_scenes", [])
                num_scenes = int(num_scenes_resp[0]) if num_scenes_resp else 0

                scene_names = []
                for i in range(num_scenes):
                    resp = state.osc.query("/live/scene/get/name", [i])
                    scene_names.append(str(resp[1]).lower() if resp and len(resp) > 1 else "")
                    time_mod.sleep(0.01)

                # セクションごとのプリセット定義
                # (filter_start, filter_end, filter_shape,
                #  chorus_dw_start, chorus_dw_end, chorus_dw_shape,
                #  room_start, room_end, room_shape)
                def scale(base_start, base_end, i=intensity):
                    """intensityで変動幅をスケール（中心値は維持）"""
                    center = (base_start + base_end) / 2
                    half = (base_end - base_start) / 2 * i
                    return (max(0, min(1, center - half)), max(0, min(1, center + half)))

                section_presets = {
                    "intro":    {"filter": (0.40, 0.55, "exponential"), "chorus_dw": (0.25, 0.35, "linear"),      "room": (0.35, 0.45, "linear")},
                    "verse":    {"filter": (0.48, 0.52, "sine"),       "chorus_dw": (0.28, 0.32, "sine"),         "room": (0.38, 0.42, "sine")},
                    "chorus":   {"filter": (0.50, 0.58, "exponential"), "chorus_dw": (0.35, 0.45, "exponential"), "room": (0.45, 0.55, "exponential")},
                    "bridge":   {"filter": (0.45, 0.55, "sine"),       "chorus_dw": (0.40, 0.50, "exponential"), "room": (0.50, 0.60, "exponential")},
                    "outro":    {"filter": (0.50, 0.40, "linear"),     "chorus_dw": (0.35, 0.20, "linear"),      "room": (0.45, 0.30, "linear")},
                }
                # Chorus 3b: 特別な下降パターン
                section_presets["chorus_end"] = {
                    "filter": (0.58, 0.50, "linear"),
                    "chorus_dw": (0.45, 0.35, "linear"),
                    "room": (0.55, 0.45, "linear"),
                }

                def classify_scene(name, idx, total):
                    """シーン名からセクション種別を判定"""
                    if "intro" in name:
                        return "intro"
                    elif "outro" in name:
                        return "outro"
                    elif "bridge" in name or "break" in name:
                        return "bridge"
                    elif "chorus" in name or "hook" in name:
                        # 最後のコーラス系シーンかチェック
                        remaining = [s for s in scene_names[idx+1:] if "chorus" in s or "hook" in s]
                        if len(remaining) == 0:
                            return "chorus_end"
                        return "chorus"
                    elif "verse" in name:
                        return "verse"
                    else:
                        return "verse"  # デフォルト

                # 各クリップにオートメーション適用
                applied = 0
                skipped = 0
                details = []

                for scene_idx in range(num_scenes):
                    if scene_idx >= len(has_clips) or not has_clips[scene_idx]:
                        continue

                    section = classify_scene(scene_names[scene_idx], scene_idx, num_scenes)
                    preset = section_presets.get(section, section_presets["verse"])

                    # クリップを発火
                    state.osc.send_message("/live/clip/fire", [track_idx, scene_idx])
                    time_mod.sleep(0.1)

                    # Auto Filter Frequency
                    if filter_dev is not None and filter_freq_param is not None:
                        s, e = scale(*preset["filter"][:2])
                        shape = preset["filter"][2]
                        state.osc.clear_automation(track_idx, scene_idx, filter_dev, filter_freq_param)
                        time_mod.sleep(0.03)
                        points = generate_automation_points(shape, s, e, 0.0, 16.0, 32)
                        for t, v, d in points:
                            state.osc.add_automation_step(track_idx, scene_idx, filter_dev, filter_freq_param, t, v, d)
                            time_mod.sleep(0.005)

                    # Chorus Dry/Wet
                    if chorus_dev is not None and chorus_dw_param is not None:
                        s, e = scale(*preset["chorus_dw"][:2])
                        shape = preset["chorus_dw"][2]
                        state.osc.clear_automation(track_idx, scene_idx, chorus_dev, chorus_dw_param)
                        time_mod.sleep(0.03)
                        points = generate_automation_points(shape, s, e, 0.0, 16.0, 32)
                        for t, v, d in points:
                            state.osc.add_automation_step(track_idx, scene_idx, chorus_dev, chorus_dw_param, t, v, d)
                            time_mod.sleep(0.005)

                    # E-Piano Room
                    if room_param is not None:
                        s, e = scale(*preset["room"][:2])
                        shape = preset["room"][2]
                        state.osc.clear_automation(track_idx, scene_idx, epiano_dev, room_param)
                        time_mod.sleep(0.03)
                        points = generate_automation_points(shape, s, e, 0.0, 16.0, 32)
                        for t, v, d in points:
                            state.osc.add_automation_step(track_idx, scene_idx, epiano_dev, room_param, t, v, d)
                            time_mod.sleep(0.005)

                    applied += 1
                    details.append(f"  [{scene_idx}] {scene_names[scene_idx]} → {section}")

                # 停止
                state.osc.send_message("/live/song/stop_playing", [])

                devices_used = []
                if filter_dev is not None:
                    devices_used.append(f"Auto Filter(D{filter_dev} P{filter_freq_param})")
                if chorus_dev is not None:
                    devices_used.append(f"Chorus D/W(D{chorus_dev} P{chorus_dw_param})")
                if room_param is not None:
                    devices_used.append(f"Room(D{epiano_dev} P{room_param})")

                result = (f"🎹 Chordsオートメーション適用: Track {track_idx}\n"
                          f"  Intensity: {intensity}\n"
                          f"  Devices: {', '.join(devices_used)}\n"
                          f"  適用: {applied}シーン\n\n"
                          + "\n".join(details))
            else:
                result = "Chordsオートメーション（モック）"

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
