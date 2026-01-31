# Ableton Agent v2.0
from .ableton_osc import AbletonOSC, DrumPattern
from .agent import MusicAgent
from .cli import AbletonAgentCLI
from .synth_generator import (
    MelodyGenerator, BasslineGenerator, ChordProgressionGenerator, ArpeggiatorGenerator,
    create_melody, create_bassline, create_chords, create_arpeggio,
    Scale, ChordType, MusicTheory
)
from .sample_search import SampleSearchEngine, SampleDatabase, parse_sample_query
from .mixing_assistant import MixingAnalyzer, AutoMixer, suggest_mix_improvements
from .arrangement_generator import (
    ArrangementGenerator, ArrangementExecutor,
    create_arrangement, describe_arrangement, get_available_genres
)

__all__ = [
    # Core
    "AbletonOSC", "DrumPattern", "MusicAgent", "AbletonAgentCLI",
    # Synth/Melody
    "MelodyGenerator", "BasslineGenerator", "ChordProgressionGenerator", "ArpeggiatorGenerator",
    "create_melody", "create_bassline", "create_chords", "create_arpeggio",
    "Scale", "ChordType", "MusicTheory",
    # Sample
    "SampleSearchEngine", "SampleDatabase", "parse_sample_query",
    # Mixing
    "MixingAnalyzer", "AutoMixer", "suggest_mix_improvements",
    # Arrangement
    "ArrangementGenerator", "ArrangementExecutor",
    "create_arrangement", "describe_arrangement", "get_available_genres",
]
