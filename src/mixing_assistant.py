"""
Mixing Assistant Module
ミキシング分析・自動処理
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum
import math


class FrequencyRange(Enum):
    """周波数帯域"""
    SUB_BASS = (20, 60, "Sub Bass")
    BASS = (60, 250, "Bass")
    LOW_MID = (250, 500, "Low Mid")
    MID = (500, 2000, "Mid")
    HIGH_MID = (2000, 4000, "High Mid")
    PRESENCE = (4000, 8000, "Presence")
    BRILLIANCE = (8000, 20000, "Brilliance")
    
    @property
    def low(self) -> int:
        return self.value[0]
    
    @property
    def high(self) -> int:
        return self.value[1]
    
    @property
    def label(self) -> str:
        return self.value[2]


@dataclass
class MixingIssue:
    """ミキシングの問題"""
    issue_type: str
    description: str
    affected_tracks: list[int]
    severity: str  # "low", "medium", "high"
    solution: dict  # 解決策（ツールパラメータ）


@dataclass
class TrackAnalysis:
    """トラック分析結果"""
    track_index: int
    name: str
    peak_db: float
    rms_db: float
    frequency_profile: dict[str, float]  # 帯域ごとのレベル
    dynamic_range: float
    stereo_width: float


class MixingAnalyzer:
    """ミキシング分析"""
    
    # 各楽器タイプの理想的な周波数帯域
    INSTRUMENT_FREQUENCY_TARGETS = {
        "kick": {
            "fundamental": (50, 100),
            "body": (100, 200),
            "click": (2000, 5000),
            "cut": [(200, 500)],  # カットすべき帯域
        },
        "snare": {
            "body": (150, 250),
            "snap": (900, 2500),
            "presence": (5000, 8000),
            "cut": [(400, 800)],
        },
        "bass": {
            "sub": (40, 80),
            "fundamental": (80, 200),
            "harmonics": (800, 2500),
            "cut": [(200, 400)],
        },
        "vocal": {
            "body": (200, 400),
            "presence": (2500, 5000),
            "air": (10000, 16000),
            "cut": [(300, 500)],  # mud
        },
        "synth": {
            "body": (200, 600),
            "presence": (2000, 5000),
        },
        "hihat": {
            "body": (300, 500),
            "presence": (6000, 10000),
        },
    }
    
    def __init__(self):
        self.track_analyses: list[TrackAnalysis] = []
        
    def analyze_mix(self, tracks: list[dict]) -> list[MixingIssue]:
        """ミックス全体を分析して問題を検出"""
        issues = []
        
        # 各トラックを分析
        for track in tracks:
            self._analyze_track(track)
        
        # 周波数衝突を検出
        issues.extend(self._detect_frequency_clashes())
        
        # レベルバランスの問題を検出
        issues.extend(self._detect_level_issues())
        
        # ダイナミクスの問題を検出
        issues.extend(self._detect_dynamics_issues())
        
        # ステレオイメージの問題を検出
        issues.extend(self._detect_stereo_issues())
        
        return issues
    
    def _analyze_track(self, track: dict) -> TrackAnalysis:
        """個別トラックを分析"""
        # 実際の実装ではオーディオ解析が必要
        # ここではモック分析
        analysis = TrackAnalysis(
            track_index=track.get("index", 0),
            name=track.get("name", "Unknown"),
            peak_db=track.get("peak_db", -6.0),
            rms_db=track.get("rms_db", -18.0),
            frequency_profile={
                "sub_bass": 0.0,
                "bass": 0.0,
                "low_mid": 0.0,
                "mid": 0.0,
                "high_mid": 0.0,
                "presence": 0.0,
                "brilliance": 0.0,
            },
            dynamic_range=track.get("dynamic_range", 12.0),
            stereo_width=track.get("stereo_width", 0.5),
        )
        self.track_analyses.append(analysis)
        return analysis
    
    def _detect_frequency_clashes(self) -> list[MixingIssue]:
        """周波数の衝突を検出"""
        issues = []
        
        # キックとベースの衝突（最も一般的）
        kick_tracks = [t for t in self.track_analyses if "kick" in t.name.lower() or "drum" in t.name.lower()]
        bass_tracks = [t for t in self.track_analyses if "bass" in t.name.lower()]
        
        if kick_tracks and bass_tracks:
            issues.append(MixingIssue(
                issue_type="frequency_clash",
                description="キックとベースが低域で衝突している可能性があります",
                affected_tracks=[kick_tracks[0].track_index, bass_tracks[0].track_index],
                severity="medium",
                solution={
                    "action": "sidechain_compression",
                    "trigger_track": kick_tracks[0].track_index,
                    "target_track": bass_tracks[0].track_index,
                    "threshold": -20,
                    "ratio": 4,
                    "attack_ms": 1,
                    "release_ms": 100,
                }
            ))
            
            # EQ処理の提案
            issues.append(MixingIssue(
                issue_type="eq_suggestion",
                description="キックとベースの住み分けのためEQ処理を推奨",
                affected_tracks=[kick_tracks[0].track_index, bass_tracks[0].track_index],
                severity="low",
                solution={
                    "action": "eq",
                    "tracks": [
                        {
                            "track": kick_tracks[0].track_index,
                            "bands": [
                                {"type": "highpass", "freq": 30, "q": 0.7},
                                {"type": "bell", "freq": 60, "gain": 2, "q": 1.5},  # キックの基音
                                {"type": "cut", "freq": 350, "gain": -3, "q": 1.0},  # マッド除去
                            ]
                        },
                        {
                            "track": bass_tracks[0].track_index,
                            "bands": [
                                {"type": "highpass", "freq": 40, "q": 0.7},
                                {"type": "cut", "freq": 60, "gain": -2, "q": 2},  # キックに譲る
                                {"type": "bell", "freq": 120, "gain": 2, "q": 1.2},  # ベースの基音
                            ]
                        }
                    ]
                }
            ))
        
        return issues
    
    def _detect_level_issues(self) -> list[MixingIssue]:
        """レベルバランスの問題を検出"""
        issues = []
        
        for track in self.track_analyses:
            # ピークが高すぎる
            if track.peak_db > -3:
                issues.append(MixingIssue(
                    issue_type="level_too_high",
                    description=f"{track.name} のレベルが高すぎます（{track.peak_db:.1f}dB）",
                    affected_tracks=[track.track_index],
                    severity="high",
                    solution={
                        "action": "set_volume",
                        "track": track.track_index,
                        "adjustment_db": -6  # 6dB下げる
                    }
                ))
            
            # RMSが低すぎる（埋もれている）
            if track.rms_db < -24:
                issues.append(MixingIssue(
                    issue_type="level_too_low",
                    description=f"{track.name} のレベルが低く、ミックスに埋もれている可能性があります",
                    affected_tracks=[track.track_index],
                    severity="low",
                    solution={
                        "action": "set_volume",
                        "track": track.track_index,
                        "adjustment_db": 3
                    }
                ))
        
        return issues
    
    def _detect_dynamics_issues(self) -> list[MixingIssue]:
        """ダイナミクスの問題を検出"""
        issues = []
        
        for track in self.track_analyses:
            # ダイナミックレンジが広すぎる
            if track.dynamic_range > 20:
                issues.append(MixingIssue(
                    issue_type="dynamics_too_wide",
                    description=f"{track.name} のダイナミックレンジが広すぎます。コンプレッサーを推奨",
                    affected_tracks=[track.track_index],
                    severity="medium",
                    solution={
                        "action": "compression",
                        "track": track.track_index,
                        "threshold": -18,
                        "ratio": 3,
                        "attack_ms": 10,
                        "release_ms": 100,
                        "makeup_gain": 3
                    }
                ))
            
            # ダイナミックレンジが狭すぎる（過圧縮）
            elif track.dynamic_range < 4:
                issues.append(MixingIssue(
                    issue_type="over_compressed",
                    description=f"{track.name} が過度に圧縮されています",
                    affected_tracks=[track.track_index],
                    severity="low",
                    solution={
                        "action": "reduce_compression",
                        "track": track.track_index,
                    }
                ))
        
        return issues
    
    def _detect_stereo_issues(self) -> list[MixingIssue]:
        """ステレオイメージの問題を検出"""
        issues = []
        
        # 低音トラックがセンター以外にある
        for track in self.track_analyses:
            if any(x in track.name.lower() for x in ["kick", "bass", "sub"]):
                if track.stereo_width > 0.2:
                    issues.append(MixingIssue(
                        issue_type="bass_not_centered",
                        description=f"{track.name} をセンターに配置することを推奨（低音はモノラル推奨）",
                        affected_tracks=[track.track_index],
                        severity="medium",
                        solution={
                            "action": "set_pan",
                            "track": track.track_index,
                            "pan": 0  # センター
                        }
                    ))
        
        return issues


class MixingPresets:
    """ミキシングプリセット"""
    
    @staticmethod
    def get_genre_preset(genre: str) -> dict:
        """ジャンル別のミキシングプリセット"""
        presets = {
            "edm": {
                "kick": {"high_pass": 30, "boost_60hz": 3, "compression_ratio": 4},
                "bass": {"sidechain": True, "sidechain_amount": 0.7},
                "synth": {"reverb": 0.3, "stereo_width": 0.8},
                "master": {"limiter_ceiling": -0.3, "target_lufs": -8},
            },
            "hiphop": {
                "kick": {"boost_60hz": 4, "boost_2khz": 2},
                "bass": {"sidechain": True, "sidechain_amount": 0.5},
                "vocal": {"compression_ratio": 3, "de_esser": True},
                "master": {"target_lufs": -10},
            },
            "lofi": {
                "drums": {"saturation": 0.3, "low_pass": 8000},
                "bass": {"saturation": 0.2},
                "master": {"tape_saturation": 0.2, "target_lufs": -14},
            },
            "techno": {
                "kick": {"compression_ratio": 6, "boost_100hz": 2},
                "hihat": {"high_pass": 500},
                "master": {"limiter_ceiling": -0.1, "target_lufs": -7},
            },
            "ambient": {
                "synth": {"reverb": 0.7, "delay": 0.4},
                "master": {"target_lufs": -18, "dynamic_range": "wide"},
            },
        }
        return presets.get(genre.lower(), presets["edm"])


class AutoMixer:
    """自動ミキシング"""
    
    def __init__(self, osc_client=None):
        self.osc = osc_client
        self.analyzer = MixingAnalyzer()
    
    def auto_mix(self, tracks: list[dict], genre: str = "edm") -> list[dict]:
        """自動ミキシングを実行"""
        actions = []
        
        # 分析
        issues = self.analyzer.analyze_mix(tracks)
        
        # プリセット取得
        preset = MixingPresets.get_genre_preset(genre)
        
        # 問題を解決
        for issue in issues:
            action = self._resolve_issue(issue)
            if action:
                actions.append(action)
        
        return actions
    
    def _resolve_issue(self, issue: MixingIssue) -> Optional[dict]:
        """問題を解決するアクションを生成"""
        solution = issue.solution
        action_type = solution.get("action")
        
        if action_type == "sidechain_compression":
            return {
                "type": "sidechain",
                "description": issue.description,
                "params": {
                    "trigger": solution["trigger_track"],
                    "target": solution["target_track"],
                    "threshold": solution["threshold"],
                    "ratio": solution["ratio"],
                    "attack": solution["attack_ms"],
                    "release": solution["release_ms"],
                }
            }
        
        elif action_type == "eq":
            return {
                "type": "eq",
                "description": issue.description,
                "params": solution["tracks"]
            }
        
        elif action_type == "set_volume":
            return {
                "type": "volume",
                "description": issue.description,
                "params": {
                    "track": solution["track"],
                    "adjustment_db": solution["adjustment_db"]
                }
            }
        
        elif action_type == "compression":
            return {
                "type": "compression",
                "description": issue.description,
                "params": {
                    "track": solution["track"],
                    "threshold": solution["threshold"],
                    "ratio": solution["ratio"],
                    "attack": solution["attack_ms"],
                    "release": solution["release_ms"],
                }
            }
        
        elif action_type == "set_pan":
            return {
                "type": "pan",
                "description": issue.description,
                "params": {
                    "track": solution["track"],
                    "pan": solution["pan"]
                }
            }
        
        return None


# ヘルパー関数
def suggest_mix_improvements(tracks: list[dict], issue_description: str) -> list[dict]:
    """
    自然言語の問題記述から改善策を提案
    
    例: "キックとベースが被ってる" -> サイドチェイン/EQ提案
    """
    suggestions = []
    issue_lower = issue_description.lower()
    
    # キックとベースの問題
    if any(x in issue_lower for x in ["キック", "ベース", "被", "衝突", "clash", "kick", "bass"]):
        kick_idx = next((t.get("index", 0) for t in tracks if "kick" in t.get("name", "").lower() or "drum" in t.get("name", "").lower()), 0)
        bass_idx = next((t.get("index", 1) for t in tracks if "bass" in t.get("name", "").lower()), 1)
        
        suggestions.append({
            "title": "サイドチェインコンプレッション",
            "description": "キックが鳴るときにベースを自動的にダッキング",
            "action": "sidechain",
            "params": {
                "trigger_track": kick_idx,
                "target_track": bass_idx,
                "amount": 0.5
            }
        })
        
        suggestions.append({
            "title": "EQによる住み分け",
            "description": "キック: 50-80Hz強調、ベース: 80-150Hz強調",
            "action": "eq_carve",
            "params": {
                "tracks": [kick_idx, bass_idx]
            }
        })
    
    # マッド（濁り）の問題
    if any(x in issue_lower for x in ["濁", "マッド", "muddy", "こもり", "篭"]):
        suggestions.append({
            "title": "ローミッドのカット",
            "description": "200-500Hz帯域をカットして濁りを除去",
            "action": "eq",
            "params": {
                "band": "low_mid",
                "gain": -3,
                "freq": 350
            }
        })
    
    # 音が小さい/大きい
    if any(x in issue_lower for x in ["小さい", "聞こえない", "埋もれ", "quiet", "low"]):
        suggestions.append({
            "title": "ボリューム調整",
            "description": "レベルを上げる",
            "action": "volume",
            "params": {"adjustment_db": 3}
        })
        
    if any(x in issue_lower for x in ["大きい", "うるさい", "loud", "clip"]):
        suggestions.append({
            "title": "ボリューム調整",
            "description": "レベルを下げる",
            "action": "volume",
            "params": {"adjustment_db": -6}
        })
    
    # ダイナミクスの問題
    if any(x in issue_lower for x in ["ダイナミクス", "抑揚", "dynamics", "パンチ", "迫力"]):
        suggestions.append({
            "title": "コンプレッション",
            "description": "ダイナミクスをコントロール",
            "action": "compression",
            "params": {
                "threshold": -18,
                "ratio": 4,
                "attack_ms": 10,
                "release_ms": 100
            }
        })
    
    return suggestions


if __name__ == "__main__":
    # テスト
    tracks = [
        {"index": 0, "name": "Kick", "type": "drum"},
        {"index": 1, "name": "Bass", "type": "bass"},
        {"index": 2, "name": "Synth Lead", "type": "synth"},
    ]
    
    # 問題から提案
    issues = [
        "キックとベースが被ってる",
        "全体的に音がこもってる",
        "シンセが聞こえない",
    ]
    
    for issue in issues:
        print(f"\n問題: {issue}")
        suggestions = suggest_mix_improvements(tracks, issue)
        for s in suggestions:
            print(f"  - {s['title']}: {s['description']}")
