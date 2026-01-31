"""
Song Arrangement Generator Module
曲構成・アレンジメントの自動生成
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import json


class SectionType(Enum):
    """セクションタイプ"""
    INTRO = "intro"
    VERSE = "verse"
    PRECHORUS = "prechorus"
    CHORUS = "chorus"
    DROP = "drop"
    BREAKDOWN = "breakdown"
    BUILDUP = "buildup"
    BRIDGE = "bridge"
    OUTRO = "outro"


@dataclass
class SectionConfig:
    """セクション設定"""
    section_type: SectionType
    bars: int
    energy: float  # 0.0 - 1.0
    elements: list[str]  # 使用する要素（kick, bass, lead, etc.）
    automation: list[dict] = field(default_factory=list)  # オートメーション
    

@dataclass
class Arrangement:
    """アレンジメント"""
    title: str
    tempo: float
    key: str
    total_bars: int
    sections: list[SectionConfig]
    
    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "tempo": self.tempo,
            "key": self.key,
            "total_bars": self.total_bars,
            "sections": [
                {
                    "type": s.section_type.value,
                    "bars": s.bars,
                    "energy": s.energy,
                    "elements": s.elements,
                    "automation": s.automation,
                }
                for s in self.sections
            ]
        }


class GenreTemplates:
    """ジャンル別のアレンジメントテンプレート"""
    
    TEMPLATES = {
        "edm": {
            "sections": [
                ("intro", 8, 0.3, ["pad", "fx"]),
                ("buildup", 8, 0.5, ["kick", "hihat", "lead", "riser"]),
                ("drop", 16, 1.0, ["kick", "bass", "lead", "hihat", "clap"]),
                ("breakdown", 8, 0.4, ["pad", "lead", "fx"]),
                ("buildup", 8, 0.7, ["kick", "hihat", "lead", "riser"]),
                ("drop", 16, 1.0, ["kick", "bass", "lead", "hihat", "clap"]),
                ("outro", 8, 0.3, ["pad", "fx"]),
            ],
            "tempo_range": (125, 132),
            "default_key": "Am",
        },
        "house": {
            "sections": [
                ("intro", 16, 0.3, ["kick", "hihat"]),
                ("verse", 16, 0.6, ["kick", "bass", "hihat", "clap"]),
                ("breakdown", 8, 0.4, ["pad", "vocal"]),
                ("buildup", 8, 0.7, ["kick", "hihat", "riser"]),
                ("chorus", 16, 0.9, ["kick", "bass", "hihat", "clap", "lead"]),
                ("verse", 16, 0.6, ["kick", "bass", "hihat", "clap"]),
                ("chorus", 16, 0.9, ["kick", "bass", "hihat", "clap", "lead"]),
                ("outro", 16, 0.3, ["kick", "hihat"]),
            ],
            "tempo_range": (120, 128),
            "default_key": "Gm",
        },
        "techno": {
            "sections": [
                ("intro", 16, 0.4, ["kick"]),
                ("verse", 16, 0.6, ["kick", "hihat", "bass"]),
                ("buildup", 8, 0.7, ["kick", "hihat", "synth", "riser"]),
                ("drop", 32, 0.9, ["kick", "bass", "hihat", "synth", "perc"]),
                ("breakdown", 16, 0.5, ["pad", "fx"]),
                ("buildup", 8, 0.7, ["kick", "hihat", "riser"]),
                ("drop", 32, 1.0, ["kick", "bass", "hihat", "synth", "perc"]),
                ("outro", 16, 0.3, ["kick"]),
            ],
            "tempo_range": (130, 145),
            "default_key": "Dm",
        },
        "dnb": {
            "sections": [
                ("intro", 8, 0.3, ["pad", "fx"]),
                ("verse", 16, 0.6, ["drums", "bass", "synth"]),
                ("drop", 16, 1.0, ["drums", "bass", "synth", "lead"]),
                ("breakdown", 8, 0.4, ["pad", "vocal"]),
                ("drop", 16, 1.0, ["drums", "bass", "synth", "lead"]),
                ("outro", 8, 0.3, ["drums"]),
            ],
            "tempo_range": (170, 180),
            "default_key": "Fm",
        },
        "hiphop": {
            "sections": [
                ("intro", 4, 0.3, ["pad", "fx"]),
                ("verse", 16, 0.6, ["drums", "bass", "keys"]),
                ("chorus", 8, 0.8, ["drums", "bass", "lead", "vocal"]),
                ("verse", 16, 0.6, ["drums", "bass", "keys"]),
                ("chorus", 8, 0.8, ["drums", "bass", "lead", "vocal"]),
                ("bridge", 8, 0.5, ["pad", "bass"]),
                ("chorus", 8, 0.9, ["drums", "bass", "lead", "vocal"]),
                ("outro", 4, 0.3, ["pad"]),
            ],
            "tempo_range": (85, 100),
            "default_key": "Cm",
        },
        "trap": {
            "sections": [
                ("intro", 4, 0.3, ["pad", "fx"]),
                ("verse", 16, 0.6, ["drums", "808", "hihat"]),
                ("prechorus", 8, 0.7, ["drums", "808", "hihat", "lead"]),
                ("drop", 16, 1.0, ["drums", "808", "hihat", "lead", "fx"]),
                ("verse", 16, 0.6, ["drums", "808", "hihat"]),
                ("drop", 16, 1.0, ["drums", "808", "hihat", "lead", "fx"]),
                ("outro", 8, 0.3, ["pad", "808"]),
            ],
            "tempo_range": (130, 150),
            "default_key": "Cm",
        },
        "lofi": {
            "sections": [
                ("intro", 4, 0.3, ["pad", "vinyl"]),
                ("verse", 16, 0.5, ["drums", "bass", "keys", "vinyl"]),
                ("chorus", 8, 0.6, ["drums", "bass", "keys", "lead", "vinyl"]),
                ("verse", 16, 0.5, ["drums", "bass", "keys", "vinyl"]),
                ("chorus", 8, 0.6, ["drums", "bass", "keys", "lead", "vinyl"]),
                ("outro", 8, 0.3, ["pad", "vinyl"]),
            ],
            "tempo_range": (70, 90),
            "default_key": "Dm",
        },
        "ambient": {
            "sections": [
                ("intro", 16, 0.2, ["pad"]),
                ("verse", 32, 0.4, ["pad", "texture", "melody"]),
                ("chorus", 16, 0.5, ["pad", "texture", "melody", "bass"]),
                ("breakdown", 16, 0.3, ["pad", "texture"]),
                ("chorus", 16, 0.6, ["pad", "texture", "melody", "bass"]),
                ("outro", 16, 0.2, ["pad"]),
            ],
            "tempo_range": (60, 90),
            "default_key": "Am",
        },
        "pop": {
            "sections": [
                ("intro", 8, 0.4, ["keys", "pad"]),
                ("verse", 16, 0.5, ["drums", "bass", "keys"]),
                ("prechorus", 8, 0.6, ["drums", "bass", "keys", "strings"]),
                ("chorus", 16, 0.9, ["drums", "bass", "keys", "lead", "strings"]),
                ("verse", 16, 0.5, ["drums", "bass", "keys"]),
                ("prechorus", 8, 0.6, ["drums", "bass", "keys", "strings"]),
                ("chorus", 16, 0.9, ["drums", "bass", "keys", "lead", "strings"]),
                ("bridge", 8, 0.5, ["keys", "strings"]),
                ("chorus", 16, 1.0, ["drums", "bass", "keys", "lead", "strings"]),
                ("outro", 8, 0.4, ["keys", "pad"]),
            ],
            "tempo_range": (100, 130),
            "default_key": "C",
        },
    }
    
    @classmethod
    def get_template(cls, genre: str) -> Optional[dict]:
        return cls.TEMPLATES.get(genre.lower())
    
    @classmethod
    def list_genres(cls) -> list[str]:
        return list(cls.TEMPLATES.keys())


class ArrangementGenerator:
    """アレンジメント生成"""
    
    def __init__(self):
        self.current_arrangement: Optional[Arrangement] = None
        
    def generate_from_template(
        self,
        genre: str,
        duration_minutes: float = 4.0,
        tempo: Optional[float] = None,
        key: Optional[str] = None,
        variation: float = 0.0  # 0.0 = テンプレート通り, 1.0 = 大きく変化
    ) -> Arrangement:
        """テンプレートからアレンジメントを生成"""
        
        template = GenreTemplates.get_template(genre)
        if not template:
            template = GenreTemplates.get_template("edm")  # デフォルト
        
        # テンポ決定
        if tempo is None:
            tempo_range = template["tempo_range"]
            tempo = (tempo_range[0] + tempo_range[1]) / 2
        
        # キー決定
        if key is None:
            key = template["default_key"]
        
        # 目標小節数を計算
        target_bars = int((duration_minutes * 60 * tempo) / 4 / 4)  # 4/4拍子想定
        
        # セクションを生成
        sections = []
        total_bars = 0
        template_sections = template["sections"]
        template_total = sum(s[1] for s in template_sections)
        scale_factor = target_bars / template_total
        
        for section_data in template_sections:
            section_type, bars, energy, elements = section_data
            
            # バー数をスケール
            scaled_bars = max(4, round(bars * scale_factor / 4) * 4)  # 4小節単位
            
            # オートメーション生成
            automation = self._generate_automation(SectionType(section_type), scaled_bars, energy)
            
            sections.append(SectionConfig(
                section_type=SectionType(section_type),
                bars=scaled_bars,
                energy=energy,
                elements=elements.copy(),
                automation=automation
            ))
            total_bars += scaled_bars
        
        self.current_arrangement = Arrangement(
            title=f"Untitled {genre.title()}",
            tempo=tempo,
            key=key,
            total_bars=total_bars,
            sections=sections
        )
        
        return self.current_arrangement
    
    def _generate_automation(
        self,
        section_type: SectionType,
        bars: int,
        energy: float
    ) -> list[dict]:
        """セクション用のオートメーションを生成"""
        automation = []
        
        if section_type == SectionType.BUILDUP:
            # フィルターを徐々に開く
            automation.append({
                "parameter": "filter_cutoff",
                "start_value": 0.2,
                "end_value": 1.0,
                "start_bar": 0,
                "end_bar": bars
            })
            # リバーブを減らす
            automation.append({
                "parameter": "reverb_dry_wet",
                "start_value": 0.6,
                "end_value": 0.2,
                "start_bar": 0,
                "end_bar": bars
            })
            
        elif section_type == SectionType.BREAKDOWN:
            # フィルターを閉じる
            automation.append({
                "parameter": "filter_cutoff",
                "start_value": 1.0,
                "end_value": 0.3,
                "start_bar": 0,
                "end_bar": bars // 2
            })
            # リバーブを増やす
            automation.append({
                "parameter": "reverb_dry_wet",
                "start_value": 0.2,
                "end_value": 0.7,
                "start_bar": 0,
                "end_bar": bars
            })
            
        elif section_type in [SectionType.DROP, SectionType.CHORUS]:
            # エネルギーを維持
            automation.append({
                "parameter": "master_volume",
                "start_value": energy,
                "end_value": energy,
                "start_bar": 0,
                "end_bar": bars
            })
        
        return automation
    
    def generate_custom(
        self,
        sections_spec: list[dict],
        tempo: float = 128,
        key: str = "Am"
    ) -> Arrangement:
        """カスタムセクション指定でアレンジメントを生成"""
        
        sections = []
        total_bars = 0
        
        for spec in sections_spec:
            section_type = SectionType(spec.get("type", "verse"))
            bars = spec.get("bars", 8)
            energy = spec.get("energy", 0.5)
            elements = spec.get("elements", ["drums", "bass"])
            
            automation = self._generate_automation(section_type, bars, energy)
            
            sections.append(SectionConfig(
                section_type=section_type,
                bars=bars,
                energy=energy,
                elements=elements,
                automation=automation
            ))
            total_bars += bars
        
        self.current_arrangement = Arrangement(
            title="Custom Track",
            tempo=tempo,
            key=key,
            total_bars=total_bars,
            sections=sections
        )
        
        return self.current_arrangement


class ArrangementExecutor:
    """アレンジメントをAbletonに実行"""
    
    def __init__(self, osc_client=None, melody_gen=None, drum_gen=None):
        self.osc = osc_client
        self.melody_gen = melody_gen
        self.drum_gen = drum_gen
        self.element_tracks: dict[str, int] = {}
        
    def execute_arrangement(
        self,
        arrangement: Arrangement,
        create_tracks: bool = True
    ) -> list[dict]:
        """アレンジメントをAbletonに配置"""
        actions = []
        
        # 1. テンポ設定
        actions.append({
            "action": "set_tempo",
            "tempo": arrangement.tempo
        })
        
        # 2. 必要なトラックを作成
        if create_tracks:
            unique_elements = set()
            for section in arrangement.sections:
                unique_elements.update(section.elements)
            
            track_idx = 0
            for element in sorted(unique_elements):
                actions.append({
                    "action": "create_track",
                    "index": track_idx,
                    "name": element.title(),
                    "type": self._get_track_type(element)
                })
                self.element_tracks[element] = track_idx
                track_idx += 1
        
        # 3. セクションごとにクリップを配置
        current_bar = 0
        for section in arrangement.sections:
            section_actions = self._create_section_clips(
                section,
                current_bar,
                arrangement.key
            )
            actions.extend(section_actions)
            current_bar += section.bars
        
        # 4. オートメーションを設定
        current_bar = 0
        for section in arrangement.sections:
            for auto in section.automation:
                actions.append({
                    "action": "automation",
                    "parameter": auto["parameter"],
                    "start_bar": current_bar + auto["start_bar"],
                    "end_bar": current_bar + auto["end_bar"],
                    "start_value": auto["start_value"],
                    "end_value": auto["end_value"]
                })
            current_bar += section.bars
        
        return actions
    
    def _get_track_type(self, element: str) -> str:
        """エレメントからトラックタイプを決定"""
        midi_elements = {"drums", "bass", "lead", "pad", "keys", "synth", "arp", "melody"}
        if element.lower() in midi_elements:
            return "midi"
        return "audio"
    
    def _create_section_clips(
        self,
        section: SectionConfig,
        start_bar: int,
        key: str
    ) -> list[dict]:
        """セクションのクリップを作成"""
        actions = []
        
        for element in section.elements:
            track_idx = self.element_tracks.get(element, 0)
            
            # エレメントに応じたパターンを生成
            if element in ["kick", "drums"]:
                pattern = self._get_drum_pattern(section.section_type, section.energy)
            elif element == "bass":
                pattern = self._get_bass_pattern(section.section_type, key)
            elif element in ["lead", "synth", "melody"]:
                pattern = self._get_melody_pattern(section.section_type, key)
            elif element == "pad":
                pattern = self._get_pad_pattern(key)
            elif element == "hihat":
                pattern = self._get_hihat_pattern(section.energy)
            else:
                pattern = None
            
            if pattern:
                actions.append({
                    "action": "create_clip",
                    "track": track_idx,
                    "slot": start_bar // 4,  # シーン番号
                    "start_bar": start_bar,
                    "length_bars": section.bars,
                    "pattern": pattern,
                    "name": f"{section.section_type.value} - {element}"
                })
        
        return actions
    
    def _get_drum_pattern(self, section_type: SectionType, energy: float) -> str:
        """セクションに応じたドラムパターンタイプ"""
        if section_type == SectionType.DROP:
            return "four_on_floor" if energy > 0.8 else "basic_beat"
        elif section_type == SectionType.BUILDUP:
            return "buildup_fill"
        elif section_type == SectionType.BREAKDOWN:
            return "minimal"
        else:
            return "basic_beat"
    
    def _get_bass_pattern(self, section_type: SectionType, key: str) -> str:
        if section_type in [SectionType.DROP, SectionType.CHORUS]:
            return "octave"
        elif section_type == SectionType.BREAKDOWN:
            return "sustained"
        else:
            return "basic"
    
    def _get_melody_pattern(self, section_type: SectionType, key: str) -> str:
        if section_type in [SectionType.DROP, SectionType.CHORUS]:
            return "energetic"
        else:
            return "subtle"
    
    def _get_pad_pattern(self, key: str) -> str:
        return "sustained_chord"
    
    def _get_hihat_pattern(self, energy: float) -> str:
        if energy > 0.8:
            return "16th"
        elif energy > 0.5:
            return "8th"
        else:
            return "4th"


# ヘルパー関数
def create_arrangement(
    genre: str,
    duration_minutes: float = 4.0,
    tempo: Optional[float] = None,
    key: Optional[str] = None
) -> dict:
    """アレンジメントを作成して辞書で返す"""
    generator = ArrangementGenerator()
    arrangement = generator.generate_from_template(
        genre=genre,
        duration_minutes=duration_minutes,
        tempo=tempo,
        key=key
    )
    return arrangement.to_dict()


def get_available_genres() -> list[str]:
    """利用可能なジャンル一覧"""
    return GenreTemplates.list_genres()


def describe_arrangement(arrangement: dict) -> str:
    """アレンジメントを人間が読める形式で説明"""
    lines = [
        f"🎵 {arrangement['title']}",
        f"   Tempo: {arrangement['tempo']} BPM | Key: {arrangement['key']}",
        f"   Total: {arrangement['total_bars']} bars",
        "",
        "📋 Structure:",
    ]
    
    bar_position = 0
    for section in arrangement["sections"]:
        energy_bar = "█" * int(section["energy"] * 10) + "░" * (10 - int(section["energy"] * 10))
        lines.append(
            f"   [{bar_position:3d}] {section['type']:12s} | "
            f"{section['bars']:2d} bars | Energy: {energy_bar}"
        )
        bar_position += section["bars"]
    
    return "\n".join(lines)


if __name__ == "__main__":
    # テスト
    print("Available genres:", get_available_genres())
    print()
    
    # EDMトラックを生成
    arrangement = create_arrangement("edm", duration_minutes=4.0, tempo=128)
    print(describe_arrangement(arrangement))
    print()
    
    # Trap トラック
    arrangement = create_arrangement("trap", duration_minutes=3.0, tempo=140)
    print(describe_arrangement(arrangement))
