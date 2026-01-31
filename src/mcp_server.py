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
            name="list_genres",
            description="利用可能なジャンル一覧を取得",
            inputSchema={"type": "object", "properties": {}}
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
