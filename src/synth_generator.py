"""
Synth & Melody Generation Module
メロディ、ベースライン、コード進行を生成
"""

import random
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class Scale(Enum):
    """スケール定義"""
    MAJOR = [0, 2, 4, 5, 7, 9, 11]
    MINOR = [0, 2, 3, 5, 7, 8, 10]
    DORIAN = [0, 2, 3, 5, 7, 9, 10]
    PHRYGIAN = [0, 1, 3, 5, 7, 8, 10]
    LYDIAN = [0, 2, 4, 6, 7, 9, 11]
    MIXOLYDIAN = [0, 2, 4, 5, 7, 9, 10]
    AEOLIAN = [0, 2, 3, 5, 7, 8, 10]  # Natural Minor
    LOCRIAN = [0, 1, 3, 5, 6, 8, 10]
    HARMONIC_MINOR = [0, 2, 3, 5, 7, 8, 11]
    MELODIC_MINOR = [0, 2, 3, 5, 7, 9, 11]
    PENTATONIC_MAJOR = [0, 2, 4, 7, 9]
    PENTATONIC_MINOR = [0, 3, 5, 7, 10]
    BLUES = [0, 3, 5, 6, 7, 10]


class ChordType(Enum):
    """コードタイプ"""
    MAJOR = [0, 4, 7]
    MINOR = [0, 3, 7]
    DIM = [0, 3, 6]
    AUG = [0, 4, 8]
    SUS2 = [0, 2, 7]
    SUS4 = [0, 5, 7]
    MAJ7 = [0, 4, 7, 11]
    MIN7 = [0, 3, 7, 10]
    DOM7 = [0, 4, 7, 10]
    DIM7 = [0, 3, 6, 9]
    MIN9 = [0, 3, 7, 10, 14]
    MAJ9 = [0, 4, 7, 11, 14]


@dataclass
class Note:
    """MIDIノート"""
    pitch: int
    start: float
    duration: float
    velocity: int = 100
    
    def to_tuple(self) -> tuple:
        return (self.pitch, self.start, self.duration, self.velocity, False)


class MusicTheory:
    """音楽理論ヘルパー"""
    
    NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    @classmethod
    def note_to_midi(cls, note_name: str, octave: int = 4) -> int:
        """ノート名からMIDI番号へ変換 (例: 'C4' -> 60)"""
        note_name = note_name.upper().replace('♯', '#').replace('♭', 'b')
        
        # フラット処理
        if 'b' in note_name:
            base = note_name.replace('b', '')
            idx = cls.NOTE_NAMES.index(base) - 1
            if idx < 0:
                idx = 11
        else:
            base = note_name.replace('#', '').replace('B', 'B')
            if '#' in note_name:
                idx = cls.NOTE_NAMES.index(base) + 1
                if idx > 11:
                    idx = 0
            else:
                idx = cls.NOTE_NAMES.index(base)
        
        return idx + (octave + 1) * 12
    
    @classmethod
    def midi_to_note(cls, midi: int) -> str:
        """MIDI番号からノート名へ変換"""
        octave = (midi // 12) - 1
        note = cls.NOTE_NAMES[midi % 12]
        return f"{note}{octave}"
    
    @classmethod
    def get_scale_notes(cls, root: int, scale: Scale, octaves: int = 2) -> list[int]:
        """スケールのノートを取得"""
        notes = []
        for octave in range(octaves):
            for interval in scale.value:
                note = root + interval + (octave * 12)
                if note <= 127:
                    notes.append(note)
        return notes
    
    @classmethod
    def get_chord_notes(cls, root: int, chord_type: ChordType) -> list[int]:
        """コードのノートを取得"""
        return [root + interval for interval in chord_type.value]


class MelodyGenerator:
    """メロディ生成"""
    
    def __init__(self, root: str = "C", scale: Scale = Scale.MINOR, octave: int = 4):
        self.root = MusicTheory.note_to_midi(root, octave)
        self.scale = scale
        self.scale_notes = MusicTheory.get_scale_notes(self.root, scale)
        
    def generate_melody(
        self,
        bars: int = 4,
        density: float = 0.5,  # 0.0 = sparse, 1.0 = dense
        note_length: str = "mixed",  # "short", "long", "mixed"
        contour: str = "wave",  # "ascending", "descending", "wave", "random"
        rhythm_pattern: Optional[list] = None
    ) -> list[Note]:
        """メロディを生成"""
        notes = []
        total_beats = bars * 4
        
        # リズムパターン決定
        if rhythm_pattern:
            positions = rhythm_pattern
        else:
            positions = self._generate_rhythm(total_beats, density)
        
        # メロディライン生成
        melody_line = self._generate_contour(len(positions), contour)
        
        for i, pos in enumerate(positions):
            # スケール内のノートを選択
            scale_idx = melody_line[i] % len(self.scale_notes)
            pitch = self.scale_notes[scale_idx]
            
            # 音価決定
            if note_length == "short":
                duration = random.choice([0.25, 0.5])
            elif note_length == "long":
                duration = random.choice([1.0, 2.0])
            else:
                duration = random.choice([0.25, 0.5, 0.75, 1.0])
            
            # ベロシティ（アクセント）
            velocity = 100 if pos % 1 == 0 else 80
            
            notes.append(Note(pitch, pos, duration, velocity))
            
        return notes
    
    def _generate_rhythm(self, total_beats: float, density: float) -> list[float]:
        """リズムパターンを生成"""
        positions = []
        step = 0.25 if density > 0.7 else 0.5 if density > 0.4 else 1.0
        
        current = 0.0
        while current < total_beats:
            if random.random() < density:
                positions.append(current)
            current += step
            
        return positions if positions else [0.0]
    
    def _generate_contour(self, length: int, contour: str) -> list[int]:
        """メロディの輪郭を生成"""
        if contour == "ascending":
            return list(range(length))
        elif contour == "descending":
            return list(range(length - 1, -1, -1))
        elif contour == "wave":
            result = []
            for i in range(length):
                result.append(int(3 * (1 + 0.5 * (i % 8))))
            return result
        else:  # random
            return [random.randint(0, 7) for _ in range(length)]


class BasslineGenerator:
    """ベースライン生成"""
    
    def __init__(self, root: str = "C", scale: Scale = Scale.MINOR, octave: int = 2):
        self.root = MusicTheory.note_to_midi(root, octave)
        self.scale = scale
        self.scale_notes = MusicTheory.get_scale_notes(self.root, scale, octaves=1)
        
    def generate_bassline(
        self,
        bars: int = 4,
        style: str = "basic",  # "basic", "walking", "syncopated", "octave", "arpeggiated"
        chord_progression: Optional[list] = None
    ) -> list[Note]:
        """ベースラインを生成"""
        
        if style == "basic":
            return self._basic_bass(bars, chord_progression)
        elif style == "walking":
            return self._walking_bass(bars, chord_progression)
        elif style == "syncopated":
            return self._syncopated_bass(bars, chord_progression)
        elif style == "octave":
            return self._octave_bass(bars, chord_progression)
        elif style == "arpeggiated":
            return self._arpeggiated_bass(bars, chord_progression)
        else:
            return self._basic_bass(bars, chord_progression)
    
    def _basic_bass(self, bars: int, chords: Optional[list]) -> list[Note]:
        """基本的なルート音ベース"""
        notes = []
        for bar in range(bars):
            root = self._get_chord_root(bar, chords)
            # 1拍目と3拍目
            notes.append(Note(root, bar * 4, 1.0, 100))
            notes.append(Note(root, bar * 4 + 2, 1.0, 90))
        return notes
    
    def _walking_bass(self, bars: int, chords: Optional[list]) -> list[Note]:
        """ウォーキングベース"""
        notes = []
        for bar in range(bars):
            root = self._get_chord_root(bar, chords)
            # 4分音符でスケールを歩く
            for beat in range(4):
                scale_idx = beat % len(self.scale_notes)
                pitch = root + self.scale.value[scale_idx] if scale_idx < len(self.scale.value) else root
                notes.append(Note(pitch, bar * 4 + beat, 0.9, 100 - beat * 5))
        return notes
    
    def _syncopated_bass(self, bars: int, chords: Optional[list]) -> list[Note]:
        """シンコペーションベース"""
        notes = []
        pattern = [0, 0.75, 1.5, 2, 2.75, 3.5]  # シンコペーションパターン
        for bar in range(bars):
            root = self._get_chord_root(bar, chords)
            for pos in pattern:
                notes.append(Note(root, bar * 4 + pos, 0.25, 100))
        return notes
    
    def _octave_bass(self, bars: int, chords: Optional[list]) -> list[Note]:
        """オクターブベース"""
        notes = []
        for bar in range(bars):
            root = self._get_chord_root(bar, chords)
            # 8分音符でオクターブを行き来
            for i in range(8):
                pitch = root if i % 2 == 0 else root + 12
                notes.append(Note(pitch, bar * 4 + i * 0.5, 0.4, 100))
        return notes
    
    def _arpeggiated_bass(self, bars: int, chords: Optional[list]) -> list[Note]:
        """アルペジオベース"""
        notes = []
        for bar in range(bars):
            root = self._get_chord_root(bar, chords)
            # コードトーンをアルペジオ
            chord_tones = [0, 4, 7, 12]  # Root, 3rd, 5th, Octave
            for i, interval in enumerate(chord_tones):
                notes.append(Note(root + interval, bar * 4 + i, 0.9, 100))
        return notes
    
    def _get_chord_root(self, bar: int, chords: Optional[list]) -> int:
        """小節のルート音を取得"""
        if chords and bar < len(chords):
            return chords[bar]
        return self.root


class ChordProgressionGenerator:
    """コード進行生成"""
    
    # 一般的なコード進行パターン（ローマ数字）
    PROGRESSIONS = {
        "pop": [1, 5, 6, 4],          # I-V-vi-IV
        "jazz": [2, 5, 1, 1],          # ii-V-I
        "sad": [6, 4, 1, 5],           # vi-IV-I-V
        "epic": [1, 4, 5, 5],          # I-IV-V-V
        "dark": [6, 4, 6, 5],          # vi-IV-vi-V
        "edm": [6, 4, 1, 5],           # vi-IV-I-V
        "lofi": [2, 5, 3, 6],          # ii-V-iii-vi
        "cinematic": [1, 3, 4, 4],     # I-iii-IV-IV
    }
    
    def __init__(self, root: str = "C", scale: Scale = Scale.MINOR, octave: int = 3):
        self.root = MusicTheory.note_to_midi(root, octave)
        self.scale = scale
        
    def generate_progression(
        self,
        bars: int = 4,
        style: str = "pop",
        voicing: str = "basic"  # "basic", "spread", "drop2"
    ) -> list[list[Note]]:
        """コード進行を生成"""
        
        # コード進行パターンを取得
        if style in self.PROGRESSIONS:
            pattern = self.PROGRESSIONS[style]
        else:
            pattern = self.PROGRESSIONS["pop"]
        
        chords = []
        for bar in range(bars):
            degree = pattern[bar % len(pattern)]
            chord_root = self._get_scale_degree(degree)
            chord_type = self._get_chord_type_for_degree(degree)
            
            chord_notes = self._voice_chord(chord_root, chord_type, voicing)
            
            # このバーのコードノート
            bar_notes = []
            for pitch in chord_notes:
                bar_notes.append(Note(pitch, bar * 4, 4.0, 80))
            chords.append(bar_notes)
            
        return chords
    
    def _get_scale_degree(self, degree: int) -> int:
        """スケールの度数からルート音を取得"""
        intervals = self.scale.value
        idx = (degree - 1) % len(intervals)
        return self.root + intervals[idx]
    
    def _get_chord_type_for_degree(self, degree: int) -> ChordType:
        """度数に応じたコードタイプを取得"""
        if self.scale in [Scale.MAJOR, Scale.LYDIAN, Scale.MIXOLYDIAN]:
            # メジャースケールのダイアトニックコード
            major_types = {
                1: ChordType.MAJOR, 2: ChordType.MINOR, 3: ChordType.MINOR,
                4: ChordType.MAJOR, 5: ChordType.MAJOR, 6: ChordType.MINOR,
                7: ChordType.DIM
            }
            return major_types.get(degree, ChordType.MAJOR)
        else:
            # マイナースケールのダイアトニックコード
            minor_types = {
                1: ChordType.MINOR, 2: ChordType.DIM, 3: ChordType.MAJOR,
                4: ChordType.MINOR, 5: ChordType.MINOR, 6: ChordType.MAJOR,
                7: ChordType.MAJOR
            }
            return minor_types.get(degree, ChordType.MINOR)
    
    def _voice_chord(self, root: int, chord_type: ChordType, voicing: str) -> list[int]:
        """コードのボイシングを決定"""
        base_notes = MusicTheory.get_chord_notes(root, chord_type)
        
        if voicing == "spread":
            # 広いボイシング
            return [base_notes[0], base_notes[1] + 12, base_notes[2] + 12]
        elif voicing == "drop2":
            # Drop 2ボイシング
            if len(base_notes) >= 4:
                return [base_notes[0], base_notes[2], base_notes[3], base_notes[1] + 12]
            return base_notes
        else:
            return base_notes


class ArpeggiatorGenerator:
    """アルペジオパターン生成"""
    
    PATTERNS = {
        "up": lambda n: list(range(n)),
        "down": lambda n: list(range(n - 1, -1, -1)),
        "updown": lambda n: list(range(n)) + list(range(n - 2, 0, -1)),
        "random": lambda n: random.sample(range(n), n),
        "played": lambda n: list(range(n)),  # 押さえた順
    }
    
    def __init__(self, root: str = "C", chord_type: ChordType = ChordType.MINOR, octave: int = 4):
        self.root = MusicTheory.note_to_midi(root, octave)
        self.chord_type = chord_type
        self.chord_notes = MusicTheory.get_chord_notes(self.root, chord_type)
        
    def generate_arpeggio(
        self,
        bars: int = 2,
        pattern: str = "up",
        rate: str = "16th",  # "8th", "16th", "triplet"
        octave_range: int = 2
    ) -> list[Note]:
        """アルペジオを生成"""
        notes = []
        
        # レートから音価を決定
        note_duration = {"8th": 0.5, "16th": 0.25, "triplet": 0.333}[rate]
        
        # 全オクターブのコードノートを準備
        all_notes = []
        for oct in range(octave_range):
            for note in self.chord_notes:
                all_notes.append(note + oct * 12)
        
        # パターンを取得
        pattern_func = self.PATTERNS.get(pattern, self.PATTERNS["up"])
        indices = pattern_func(len(all_notes))
        
        # ノート生成
        total_beats = bars * 4
        current_time = 0.0
        idx = 0
        
        while current_time < total_beats:
            pitch = all_notes[indices[idx % len(indices)]]
            velocity = 100 if current_time % 1 == 0 else 80
            notes.append(Note(pitch, current_time, note_duration * 0.9, velocity))
            
            current_time += note_duration
            idx += 1
            
        return notes


# ファクトリー関数
def create_melody(
    root: str = "C",
    scale: str = "minor",
    bars: int = 4,
    style: str = "wave",
    density: float = 0.5
) -> list[tuple]:
    """メロディを作成"""
    scale_map = {
        "major": Scale.MAJOR,
        "minor": Scale.MINOR,
        "dorian": Scale.DORIAN,
        "pentatonic": Scale.PENTATONIC_MINOR,
        "blues": Scale.BLUES,
    }
    gen = MelodyGenerator(root, scale_map.get(scale, Scale.MINOR))
    notes = gen.generate_melody(bars=bars, contour=style, density=density)
    return [n.to_tuple() for n in notes]


def create_bassline(
    root: str = "C",
    scale: str = "minor",
    bars: int = 4,
    style: str = "basic"
) -> list[tuple]:
    """ベースラインを作成"""
    scale_map = {
        "major": Scale.MAJOR,
        "minor": Scale.MINOR,
        "dorian": Scale.DORIAN,
    }
    gen = BasslineGenerator(root, scale_map.get(scale, Scale.MINOR))
    notes = gen.generate_bassline(bars=bars, style=style)
    return [n.to_tuple() for n in notes]


def create_chords(
    root: str = "C",
    scale: str = "minor",
    bars: int = 4,
    style: str = "pop"
) -> list[list[tuple]]:
    """コード進行を作成"""
    scale_map = {
        "major": Scale.MAJOR,
        "minor": Scale.MINOR,
    }
    gen = ChordProgressionGenerator(root, scale_map.get(scale, Scale.MINOR))
    chords = gen.generate_progression(bars=bars, style=style)
    return [[n.to_tuple() for n in chord] for chord in chords]


def create_arpeggio(
    root: str = "C",
    chord: str = "minor",
    bars: int = 2,
    pattern: str = "up",
    rate: str = "16th"
) -> list[tuple]:
    """アルペジオを作成"""
    chord_map = {
        "major": ChordType.MAJOR,
        "minor": ChordType.MINOR,
        "maj7": ChordType.MAJ7,
        "min7": ChordType.MIN7,
    }
    gen = ArpeggiatorGenerator(root, chord_map.get(chord, ChordType.MINOR))
    notes = gen.generate_arpeggio(bars=bars, pattern=pattern, rate=rate)
    return [n.to_tuple() for n in notes]


if __name__ == "__main__":
    # テスト
    print("=== Melody ===")
    melody = create_melody("C", "minor", 2)
    for n in melody[:5]:
        print(f"  {MusicTheory.midi_to_note(n[0])} at {n[1]}")
    
    print("\n=== Bassline ===")
    bass = create_bassline("C", "minor", 2, "syncopated")
    for n in bass[:5]:
        print(f"  {MusicTheory.midi_to_note(n[0])} at {n[1]}")
    
    print("\n=== Chords ===")
    chords = create_chords("C", "minor", 4, "dark")
    for i, chord in enumerate(chords):
        notes = [MusicTheory.midi_to_note(n[0]) for n in chord]
        print(f"  Bar {i + 1}: {notes}")
    
    print("\n=== Arpeggio ===")
    arp = create_arpeggio("C", "min7", 1, "updown", "16th")
    for n in arp[:8]:
        print(f"  {MusicTheory.midi_to_note(n[0])} at {n[1]:.2f}")
