"""
AI Agent Module
自然言語をAbletonコマンドに変換するエージェント
全機能統合版
"""

import anthropic
import json
from typing import Optional
from dataclasses import dataclass, field


# コマンドスキーマ定義
ABLETON_TOOLS = [
    # ===================
    # 基本操作
    # ===================
    {
        "name": "set_tempo",
        "description": "曲のテンポ（BPM）を設定する",
        "input_schema": {
            "type": "object",
            "properties": {
                "bpm": {
                    "type": "number",
                    "description": "テンポ（BPM）。通常60-200の範囲"
                }
            },
            "required": ["bpm"]
        }
    },
    {
        "name": "play",
        "description": "再生を開始する",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "stop",
        "description": "再生を停止する",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    
    # ===================
    # ドラム
    # ===================
    {
        "name": "create_drum_track",
        "description": "ドラムトラックを作成し、パターンを追加する",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "トラック名"
                },
                "pattern_type": {
                    "type": "string",
                    "enum": ["basic_beat", "four_on_floor", "trap", "breakbeat", "dnb", "minimal"],
                    "description": "ドラムパターンのタイプ"
                },
                "bars": {
                    "type": "integer",
                    "description": "パターンの小節数",
                    "default": 2
                }
            },
            "required": ["pattern_type"]
        }
    },
    
    # ===================
    # メロディ/シンセ
    # ===================
    {
        "name": "create_melody",
        "description": "メロディを自動生成してトラックに追加する",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "トラック名", "default": "Melody"},
                "root": {
                    "type": "string",
                    "description": "ルート音（C, D, E, F, G, A, B）",
                    "default": "C"
                },
                "scale": {
                    "type": "string",
                    "enum": ["major", "minor", "dorian", "pentatonic", "blues"],
                    "description": "スケール",
                    "default": "minor"
                },
                "bars": {"type": "integer", "description": "小節数", "default": 4},
                "density": {
                    "type": "number",
                    "description": "音の密度（0.0=スパース、1.0=密集）",
                    "default": 0.5
                },
                "contour": {
                    "type": "string",
                    "enum": ["ascending", "descending", "wave", "random"],
                    "description": "メロディの輪郭",
                    "default": "wave"
                },
                "octave": {"type": "integer", "description": "オクターブ（3-6）", "default": 4}
            },
            "required": []
        }
    },
    {
        "name": "create_bassline",
        "description": "ベースラインを自動生成",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "トラック名", "default": "Bass"},
                "root": {"type": "string", "description": "ルート音", "default": "C"},
                "scale": {
                    "type": "string",
                    "enum": ["major", "minor", "dorian"],
                    "default": "minor"
                },
                "style": {
                    "type": "string",
                    "enum": ["basic", "walking", "syncopated", "octave", "arpeggiated"],
                    "description": "ベースラインのスタイル",
                    "default": "basic"
                },
                "bars": {"type": "integer", "default": 4}
            },
            "required": []
        }
    },
    {
        "name": "create_chords",
        "description": "コード進行を生成",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "default": "Chords"},
                "root": {"type": "string", "default": "C"},
                "scale": {"type": "string", "enum": ["major", "minor"], "default": "minor"},
                "style": {
                    "type": "string",
                    "enum": ["pop", "jazz", "sad", "epic", "dark", "edm", "lofi", "cinematic"],
                    "description": "コード進行のスタイル",
                    "default": "pop"
                },
                "bars": {"type": "integer", "default": 4}
            },
            "required": []
        }
    },
    {
        "name": "create_arpeggio",
        "description": "アルペジオパターンを生成",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "default": "Arp"},
                "root": {"type": "string", "default": "C"},
                "chord": {
                    "type": "string",
                    "enum": ["major", "minor", "maj7", "min7"],
                    "default": "minor"
                },
                "pattern": {
                    "type": "string",
                    "enum": ["up", "down", "updown", "random"],
                    "default": "up"
                },
                "rate": {
                    "type": "string",
                    "enum": ["8th", "16th", "triplet"],
                    "default": "16th"
                },
                "bars": {"type": "integer", "default": 2}
            },
            "required": []
        }
    },
    
    # ===================
    # サンプル検索
    # ===================
    {
        "name": "search_samples",
        "description": "サンプルを検索する。ドラムヒット、ループ、エフェクト音などを見つける",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "検索クエリ（例：'エスニックなパーカッション'、'ダークなシンセ'）"
                },
                "category": {
                    "type": "string",
                    "enum": ["drums", "percussion", "bass", "synth", "vocal", "fx", "ambient", "ethnic", "orchestral"],
                    "description": "カテゴリフィルタ"
                },
                "mood": {
                    "type": "string",
                    "enum": ["dark", "bright", "aggressive", "chill", "epic", "minimal", "vintage", "modern"],
                    "description": "雰囲気フィルタ"
                },
                "bpm": {"type": "number", "description": "BPMフィルタ（±10の範囲で検索）"},
                "limit": {"type": "integer", "description": "結果数", "default": 10}
            },
            "required": ["query"]
        }
    },
    {
        "name": "load_sample",
        "description": "検索で見つけたサンプルをトラックに読み込む",
        "input_schema": {
            "type": "object",
            "properties": {
                "sample_path": {"type": "string", "description": "サンプルのパス"},
                "track_index": {"type": "integer", "description": "トラック番号"},
                "clip_slot": {"type": "integer", "description": "クリップスロット番号", "default": 0}
            },
            "required": ["sample_path"]
        }
    },
    
    # ===================
    # ミキシング
    # ===================
    {
        "name": "analyze_mix",
        "description": "現在のミックスを分析して問題点と改善提案を返す",
        "input_schema": {
            "type": "object",
            "properties": {
                "focus": {
                    "type": "string",
                    "enum": ["all", "levels", "frequency", "dynamics", "stereo"],
                    "description": "分析のフォーカス",
                    "default": "all"
                }
            },
            "required": []
        }
    },
    {
        "name": "fix_mixing_issue",
        "description": "ミキシングの問題を修正する（例：キックとベースの衝突を解消）",
        "input_schema": {
            "type": "object",
            "properties": {
                "issue": {
                    "type": "string",
                    "description": "問題の説明（例：'キックとベースが被ってる'、'全体的にこもってる'）"
                },
                "auto_fix": {
                    "type": "boolean",
                    "description": "自動で修正するか、提案のみか",
                    "default": False
                }
            },
            "required": ["issue"]
        }
    },
    {
        "name": "add_sidechain",
        "description": "サイドチェインコンプレッションを設定",
        "input_schema": {
            "type": "object",
            "properties": {
                "trigger_track": {"type": "integer", "description": "トリガートラック（通常キック）"},
                "target_track": {"type": "integer", "description": "ターゲットトラック（通常ベース）"},
                "amount": {"type": "number", "description": "サイドチェインの強さ（0.0-1.0）", "default": 0.5}
            },
            "required": ["trigger_track", "target_track"]
        }
    },
    {
        "name": "add_effect",
        "description": "トラックにエフェクトを追加",
        "input_schema": {
            "type": "object",
            "properties": {
                "track_index": {"type": "integer", "description": "トラック番号"},
                "effect_type": {
                    "type": "string",
                    "enum": ["reverb", "delay", "chorus", "distortion", "compressor", "eq", "filter", "limiter", "saturator"],
                    "description": "エフェクトタイプ"
                },
                "preset": {
                    "type": "string",
                    "description": "プリセット名（オプション）"
                }
            },
            "required": ["track_index", "effect_type"]
        }
    },
    {
        "name": "set_track_volume",
        "description": "トラックのボリュームを設定",
        "input_schema": {
            "type": "object",
            "properties": {
                "track_index": {"type": "integer"},
                "volume": {"type": "number", "description": "ボリューム（0.0-1.0）"}
            },
            "required": ["track_index", "volume"]
        }
    },
    {
        "name": "set_track_pan",
        "description": "トラックのパンを設定",
        "input_schema": {
            "type": "object",
            "properties": {
                "track_index": {"type": "integer"},
                "pan": {"type": "number", "description": "パン（-1.0=左、0=中央、1.0=右）"}
            },
            "required": ["track_index", "pan"]
        }
    },
    
    # ===================
    # アレンジメント/曲構成
    # ===================
    {
        "name": "generate_arrangement",
        "description": "曲のアレンジメント（構成）を自動生成する。イントロからアウトロまでの完全な曲構成を作成",
        "input_schema": {
            "type": "object",
            "properties": {
                "genre": {
                    "type": "string",
                    "enum": ["edm", "house", "techno", "dnb", "hiphop", "trap", "lofi", "ambient", "pop"],
                    "description": "ジャンル"
                },
                "duration_minutes": {
                    "type": "number",
                    "description": "曲の長さ（分）",
                    "default": 4.0
                },
                "tempo": {"type": "number", "description": "テンポ（BPM）"},
                "key": {"type": "string", "description": "キー（例：Am, C, Fm）"}
            },
            "required": ["genre"]
        }
    },
    {
        "name": "execute_arrangement",
        "description": "生成したアレンジメントをAbletonに配置して実際の曲を作成",
        "input_schema": {
            "type": "object",
            "properties": {
                "create_tracks": {
                    "type": "boolean",
                    "description": "新しいトラックを作成するか",
                    "default": True
                },
                "include_drums": {"type": "boolean", "default": True},
                "include_bass": {"type": "boolean", "default": True},
                "include_melody": {"type": "boolean", "default": True},
                "include_chords": {"type": "boolean", "default": True}
            },
            "required": []
        }
    },
    
    # ===================
    # 雰囲気/ムード
    # ===================
    {
        "name": "modify_mood",
        "description": "曲全体の雰囲気を変更する",
        "input_schema": {
            "type": "object",
            "properties": {
                "mood": {
                    "type": "string",
                    "description": "目標の雰囲気（例：dark、bright、aggressive、chill、epic、minimal）"
                },
                "intensity": {
                    "type": "number",
                    "description": "変更の強度（0.0-1.0）",
                    "default": 0.5
                }
            },
            "required": ["mood"]
        }
    },
    
    # ===================
    # プロジェクト情報
    # ===================
    {
        "name": "get_project_info",
        "description": "現在のプロジェクト情報を取得（トラック、テンポ、アレンジメントなど）",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "list_available_genres",
        "description": "利用可能なジャンルテンプレート一覧を取得",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]


SYSTEM_PROMPT = """あなたはAbleton Liveを操作するプロフェッショナルな音楽制作アシスタントです。

ユーザーの自然言語の指示を理解し、適切なツールを使ってAbleton Liveを操作します。

## 能力

1. **ドラム/リズム**: 様々なジャンルのドラムパターンを生成
2. **メロディ/ベース**: スケールに基づいたメロディ、ベースライン、アルペジオを生成
3. **コード進行**: ジャンルに合ったコード進行を生成
4. **サンプル検索**: ローカルライブラリやFreesoundからサンプルを検索
5. **ミキシング支援**: 周波数の衝突を検出し、EQ/サイドチェインを提案
6. **曲構成生成**: イントロからアウトロまでの完全なアレンジメントを生成

## 音楽的文脈の理解

- 「ダークな雰囲気」→ マイナーキー、低音強調、遅めのテンポ、リバーブ多め
- 「明るい」→ メジャーキー、高音強調、速めのテンポ
- 「激しい」→ 速いテンポ、ディストーション、強いキック
- 「チル」→ ゆったりテンポ、ローファイ風、リバーブ

## ジャンル別ガイド

- **EDM/ハウス**: 4つ打ち、サイドチェインベース、ビルドアップ→ドロップ構成
- **ヒップホップ/トラップ**: ハイハットロール、808ベース、シンコペーション
- **テクノ**: ミニマルなループ、長いビルドアップ
- **Lo-Fi**: 遅いテンポ、サチュレーション、ビニールノイズ
- **アンビエント**: ロングリバーブ、パッド中心、ゆったりした展開

## 作業の進め方

1. 簡単な要求 → 即座にツールを実行
2. 複雑な要求 → 段階的に作業（例：まずドラム → ベース → メロディ）
3. 「曲を作って」系の要求 → generate_arrangement でフル構成を提案

## 現在のプロジェクト状態
{project_state}
"""


@dataclass
class ProjectState:
    """プロジェクトの状態"""
    tempo: float = 120.0
    key: str = "Am"
    tracks: list = field(default_factory=list)
    is_playing: bool = False
    current_arrangement: Optional[dict] = None
    
    def to_dict(self) -> dict:
        return {
            "tempo": self.tempo,
            "key": self.key,
            "tracks": self.tracks,
            "is_playing": self.is_playing,
            "arrangement": self.current_arrangement
        }
    
    def to_string(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class MusicAgent:
    """自然言語でAbletonを操作するエージェント"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.project_state = ProjectState()
        self.conversation_history: list[dict] = []
        
    def process_input(self, user_input: str) -> tuple[list[dict], any]:
        """
        ユーザー入力を処理し、実行すべきコマンドのリストを返す
        
        Returns:
            tuple of (commands, response)
            commands: list of {"tool": "tool_name", "params": {...}, "tool_use_id": "..."}
        """
        # 会話履歴に追加
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })
        
        # システムプロンプトを構築
        system = SYSTEM_PROMPT.format(
            project_state=self.project_state.to_string()
        )
        
        # Claude APIを呼び出し
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system,
            tools=ABLETON_TOOLS,
            messages=self.conversation_history
        )
        
        # レスポンスを解析
        commands = []
        assistant_content = []
        
        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                })
                commands.append({
                    "tool": block.name,
                    "params": block.input,
                    "tool_use_id": block.id
                })
        
        # アシスタントの応答を会話履歴に追加
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_content
        })
        
        return commands, response
    
    def add_tool_result(self, tool_use_id: str, result: str):
        """ツール実行結果を会話履歴に追加"""
        self.conversation_history.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": result
            }]
        })
        
    def update_state(self, **kwargs):
        """プロジェクト状態を更新"""
        for key, value in kwargs.items():
            if hasattr(self.project_state, key):
                setattr(self.project_state, key, value)
                
    def get_text_response(self, response) -> str:
        """レスポンスからテキスト部分を抽出"""
        for block in response.content:
            if block.type == "text":
                return block.text
        return ""
    
    def clear_history(self):
        """会話履歴をクリア"""
        self.conversation_history = []


# テスト
if __name__ == "__main__":
    agent = MusicAgent()
    
    # テスト入力
    test_inputs = [
        "テンポを140にして",
        "トラップ風のドラムパターンを作って",
        "エスニックなパーカッションを探して",
        "4分のEDMトラックを作って",
    ]
    
    for inp in test_inputs:
        print(f"\n🎤 User: {inp}")
        try:
            commands, response = agent.process_input(inp)
            print(f"🤖 Commands: {json.dumps(commands, ensure_ascii=False, indent=2)}")
            print(f"📝 Response: {agent.get_text_response(response)}")
        except Exception as e:
            print(f"❌ Error: {e}")
