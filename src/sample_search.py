"""
Sample Search Module
サンプルライブラリを検索・管理
"""

import os
import json
import hashlib
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class SampleCategory(Enum):
    """サンプルカテゴリ"""
    DRUMS = "drums"
    PERCUSSION = "percussion"
    BASS = "bass"
    SYNTH = "synth"
    VOCAL = "vocal"
    FX = "fx"
    FOLEY = "foley"
    LOOP = "loop"
    ONESHOT = "oneshot"
    AMBIENT = "ambient"
    ETHNIC = "ethnic"
    ORCHESTRAL = "orchestral"


@dataclass
class Sample:
    """サンプル情報"""
    name: str
    path: str
    category: SampleCategory
    tags: list[str]
    bpm: Optional[float] = None
    key: Optional[str] = None
    duration: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "category": self.category.value,
            "tags": self.tags,
            "bpm": self.bpm,
            "key": self.key,
            "duration": self.duration
        }


class SampleDatabase:
    """ローカルサンプルデータベース"""
    
    # キーワードとカテゴリのマッピング
    CATEGORY_KEYWORDS = {
        SampleCategory.DRUMS: ["kick", "snare", "hihat", "hat", "drum", "tom", "cymbal", "clap", "rim"],
        SampleCategory.PERCUSSION: ["perc", "shaker", "tambourine", "conga", "bongo", "tabla", "djembe"],
        SampleCategory.BASS: ["bass", "sub", "808", "reese"],
        SampleCategory.SYNTH: ["synth", "lead", "pad", "pluck", "chord", "stab", "arp"],
        SampleCategory.VOCAL: ["vocal", "vox", "voice", "choir", "acapella"],
        SampleCategory.FX: ["fx", "riser", "impact", "sweep", "noise", "whoosh", "transition"],
        SampleCategory.FOLEY: ["foley", "footstep", "door", "glass", "metal", "wood"],
        SampleCategory.LOOP: ["loop", "break", "groove"],
        SampleCategory.AMBIENT: ["ambient", "atmosphere", "texture", "drone", "pad"],
        SampleCategory.ETHNIC: ["ethnic", "world", "african", "asian", "indian", "latin", "arabic"],
        SampleCategory.ORCHESTRAL: ["orchestra", "strings", "brass", "woodwind", "piano"],
    }
    
    # ムード/雰囲気のキーワード
    MOOD_KEYWORDS = {
        "dark": ["dark", "evil", "sinister", "horror", "scary", "minor", "deep"],
        "bright": ["bright", "happy", "uplifting", "major", "light", "cheerful"],
        "aggressive": ["aggressive", "hard", "distorted", "heavy", "intense"],
        "chill": ["chill", "lofi", "mellow", "soft", "relaxed", "calm"],
        "epic": ["epic", "cinematic", "dramatic", "big", "powerful"],
        "minimal": ["minimal", "clean", "simple", "subtle"],
        "vintage": ["vintage", "retro", "analog", "tape", "vinyl", "old"],
        "modern": ["modern", "digital", "electronic", "futuristic"],
    }
    
    def __init__(self, sample_paths: Optional[list[str]] = None):
        self.samples: list[Sample] = []
        self.sample_paths = sample_paths or self._get_default_paths()
        
    def _get_default_paths(self) -> list[str]:
        """デフォルトのサンプルパス"""
        paths = []
        
        # Ableton Live標準ライブラリ
        ableton_paths = [
            # macOS
            "/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Core Library",
            "/Applications/Ableton Live 11 Suite.app/Contents/App-Resources/Core Library",
            "/Users/Shared/Library/Application Support/Ableton/Live 12 Core Library",
            # Windows
            "C:/ProgramData/Ableton/Live 12 Core Library",
            "C:/ProgramData/Ableton/Live 11 Core Library",
        ]
        
        # Spliceなど
        user_home = os.path.expanduser("~")
        splice_paths = [
            f"{user_home}/Splice/sounds",
            f"{user_home}/Documents/Splice",
        ]
        
        # カスタムサンプルフォルダ
        custom_paths = [
            f"{user_home}/Music/Samples",
            f"{user_home}/Documents/Samples",
        ]
        
        for path in ableton_paths + splice_paths + custom_paths:
            if os.path.exists(path):
                paths.append(path)
                
        return paths
    
    def scan_samples(self, max_samples: int = 10000):
        """サンプルフォルダをスキャン"""
        audio_extensions = {".wav", ".aif", ".aiff", ".mp3", ".flac", ".ogg"}
        count = 0
        
        for base_path in self.sample_paths:
            if not os.path.exists(base_path):
                continue
                
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if count >= max_samples:
                        return
                        
                    ext = os.path.splitext(file)[1].lower()
                    if ext in audio_extensions:
                        full_path = os.path.join(root, file)
                        sample = self._analyze_sample(file, full_path, root)
                        self.samples.append(sample)
                        count += 1
                        
        print(f"Scanned {len(self.samples)} samples")
    
    def _analyze_sample(self, filename: str, path: str, folder: str) -> Sample:
        """サンプルを分析してメタデータを抽出"""
        name = os.path.splitext(filename)[0]
        
        # ファイル名とフォルダ名からキーワードを抽出
        search_text = f"{name} {folder}".lower()
        
        # カテゴリを推測
        category = self._guess_category(search_text)
        
        # タグを抽出
        tags = self._extract_tags(search_text)
        
        # BPM/キーを抽出（ファイル名から）
        bpm = self._extract_bpm(name)
        key = self._extract_key(name)
        
        return Sample(
            name=name,
            path=path,
            category=category,
            tags=tags,
            bpm=bpm,
            key=key
        )
    
    def _guess_category(self, text: str) -> SampleCategory:
        """テキストからカテゴリを推測"""
        text = text.lower()
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return category
                    
        return SampleCategory.ONESHOT
    
    def _extract_tags(self, text: str) -> list[str]:
        """タグを抽出"""
        tags = []
        text = text.lower()
        
        # カテゴリキーワード
        for keywords in self.CATEGORY_KEYWORDS.values():
            for keyword in keywords:
                if keyword in text and keyword not in tags:
                    tags.append(keyword)
        
        # ムードキーワード
        for mood, keywords in self.MOOD_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text and mood not in tags:
                    tags.append(mood)
                    break
                    
        return tags[:10]  # 最大10タグ
    
    def _extract_bpm(self, text: str) -> Optional[float]:
        """BPMを抽出"""
        import re
        # "120bpm", "120 BPM", "120_bpm" などを検出
        match = re.search(r'(\d{2,3})\s*bpm', text.lower())
        if match:
            return float(match.group(1))
        return None
    
    def _extract_key(self, text: str) -> Optional[str]:
        """キーを抽出"""
        import re
        # "Cm", "C#m", "Fmaj" などを検出
        match = re.search(r'\b([A-G][#b]?)\s*(m|min|maj|major|minor)?\b', text)
        if match:
            return match.group(0)
        return None
    
    def search(
        self,
        query: str = "",
        category: Optional[SampleCategory] = None,
        tags: Optional[list[str]] = None,
        bpm_range: Optional[tuple[float, float]] = None,
        key: Optional[str] = None,
        limit: int = 20
    ) -> list[Sample]:
        """サンプルを検索"""
        results = []
        query = query.lower()
        
        for sample in self.samples:
            score = 0
            
            # クエリマッチ
            if query:
                if query in sample.name.lower():
                    score += 10
                if any(query in tag for tag in sample.tags):
                    score += 5
                if score == 0:
                    continue
            
            # カテゴリフィルタ
            if category and sample.category != category:
                continue
            
            # タグフィルタ
            if tags:
                matching_tags = sum(1 for t in tags if t in sample.tags)
                if matching_tags == 0:
                    continue
                score += matching_tags * 2
            
            # BPMフィルタ
            if bpm_range and sample.bpm:
                if not (bpm_range[0] <= sample.bpm <= bpm_range[1]):
                    continue
                score += 3
            
            # キーフィルタ
            if key and sample.key:
                if key.lower() in sample.key.lower():
                    score += 5
            
            results.append((score, sample))
        
        # スコアでソート
        results.sort(key=lambda x: x[0], reverse=True)
        
        return [sample for _, sample in results[:limit]]


class FreesoundAPI:
    """Freesound.org API クライアント"""
    
    BASE_URL = "https://freesound.org/apiv2"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("FREESOUND_API_KEY")
        
    def search(
        self,
        query: str,
        filter_params: Optional[dict] = None,
        page_size: int = 15
    ) -> list[dict]:
        """Freesoundを検索"""
        if not self.api_key:
            return []
            
        import urllib.request
        import urllib.parse
        
        params = {
            "query": query,
            "token": self.api_key,
            "page_size": page_size,
            "fields": "id,name,tags,duration,previews,download"
        }
        
        if filter_params:
            params["filter"] = " ".join(f"{k}:{v}" for k, v in filter_params.items())
        
        url = f"{self.BASE_URL}/search/text/?{urllib.parse.urlencode(params)}"
        
        try:
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read())
                return data.get("results", [])
        except Exception as e:
            print(f"Freesound API error: {e}")
            return []
    
    def download(self, sound_id: int, output_path: str) -> bool:
        """サウンドをダウンロード"""
        if not self.api_key:
            return False
            
        import urllib.request
        
        url = f"{self.BASE_URL}/sounds/{sound_id}/download/?token={self.api_key}"
        
        try:
            urllib.request.urlretrieve(url, output_path)
            return True
        except Exception as e:
            print(f"Download error: {e}")
            return False


class SampleSearchEngine:
    """統合サンプル検索エンジン"""
    
    def __init__(
        self,
        local_paths: Optional[list[str]] = None,
        freesound_key: Optional[str] = None
    ):
        self.local_db = SampleDatabase(local_paths)
        self.freesound = FreesoundAPI(freesound_key)
        self.cache_dir = os.path.expanduser("~/.ableton-agent/sample-cache")
        
    def initialize(self):
        """初期化（サンプルスキャン）"""
        print("Scanning local samples...")
        self.local_db.scan_samples()
        
        # キャッシュディレクトリ作成
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def search(
        self,
        query: str,
        source: str = "all",  # "local", "freesound", "all"
        category: Optional[str] = None,
        mood: Optional[str] = None,
        bpm: Optional[float] = None,
        key: Optional[str] = None,
        limit: int = 20
    ) -> dict:
        """統合検索"""
        results = {
            "local": [],
            "freesound": [],
            "query": query
        }
        
        # カテゴリ変換
        cat_enum = None
        if category:
            try:
                cat_enum = SampleCategory(category.lower())
            except ValueError:
                pass
        
        # タグ構築
        tags = []
        if mood:
            tags.extend(SampleDatabase.MOOD_KEYWORDS.get(mood.lower(), [mood]))
        
        # BPM範囲
        bpm_range = None
        if bpm:
            bpm_range = (bpm - 10, bpm + 10)
        
        # ローカル検索
        if source in ["local", "all"]:
            local_results = self.local_db.search(
                query=query,
                category=cat_enum,
                tags=tags,
                bpm_range=bpm_range,
                key=key,
                limit=limit
            )
            results["local"] = [s.to_dict() for s in local_results]
        
        # Freesound検索
        if source in ["freesound", "all"] and self.freesound.api_key:
            # クエリ構築
            full_query = query
            if mood:
                full_query += f" {mood}"
            if category:
                full_query += f" {category}"
                
            freesound_results = self.freesound.search(
                full_query,
                page_size=limit
            )
            results["freesound"] = freesound_results
        
        return results
    
    def get_sample_path(self, sample: dict) -> str:
        """サンプルのパスを取得（必要ならダウンロード）"""
        if "path" in sample:
            return sample["path"]
            
        # Freesoundサンプルの場合
        if "id" in sample:
            cache_path = os.path.join(
                self.cache_dir,
                f"freesound_{sample['id']}.wav"
            )
            if not os.path.exists(cache_path):
                self.freesound.download(sample["id"], cache_path)
            return cache_path
            
        return ""


# 自然言語クエリパーサー
def parse_sample_query(query: str) -> dict:
    """
    自然言語クエリをパースして検索パラメータに変換
    例: "エスニックなパーカッション 120BPM" -> {"query": "ethnic percussion", "bpm": 120}
    """
    import re
    
    params = {
        "query": "",
        "category": None,
        "mood": None,
        "bpm": None,
        "key": None
    }
    
    # BPM抽出
    bpm_match = re.search(r'(\d{2,3})\s*bpm', query.lower())
    if bpm_match:
        params["bpm"] = float(bpm_match.group(1))
        query = query[:bpm_match.start()] + query[bpm_match.end():]
    
    # キー抽出
    key_match = re.search(r'\b([A-G][#b]?)\s*(m|min|maj|major|minor)?\b', query)
    if key_match:
        params["key"] = key_match.group(0)
        query = query[:key_match.start()] + query[key_match.end():]
    
    # カテゴリマッピング（日本語対応）
    category_map = {
        "ドラム": "drums", "キック": "drums", "スネア": "drums",
        "パーカッション": "percussion", "パーカス": "percussion",
        "ベース": "bass", "サブベース": "bass",
        "シンセ": "synth", "リード": "synth", "パッド": "synth",
        "ボーカル": "vocal", "声": "vocal",
        "エフェクト": "fx", "SE": "fx", "効果音": "fx",
        "アンビエント": "ambient", "環境音": "ambient",
        "エスニック": "ethnic", "民族": "ethnic", "ワールド": "ethnic",
        "オーケストラ": "orchestral", "ストリングス": "orchestral",
    }
    
    for jp, en in category_map.items():
        if jp in query:
            params["category"] = en
            query = query.replace(jp, "")
            break
    
    # ムードマッピング（日本語対応）
    mood_map = {
        "ダーク": "dark", "暗い": "dark", "不気味": "dark",
        "明るい": "bright", "ハッピー": "bright",
        "激しい": "aggressive", "ハード": "aggressive",
        "チル": "chill", "落ち着いた": "chill", "リラックス": "chill",
        "エピック": "epic", "壮大": "epic", "シネマティック": "epic",
        "ミニマル": "minimal", "シンプル": "minimal",
        "ビンテージ": "vintage", "レトロ": "vintage",
    }
    
    for jp, en in mood_map.items():
        if jp in query:
            params["mood"] = en
            query = query.replace(jp, "")
            break
    
    # 残りをクエリとして使用
    params["query"] = query.strip()
    
    return params


if __name__ == "__main__":
    # テスト
    engine = SampleSearchEngine()
    
    # クエリパース
    queries = [
        "エスニックなパーカッション",
        "ダークなシンセ 140bpm",
        "キック サブベース Cm",
    ]
    
    for q in queries:
        print(f"\nQuery: {q}")
        parsed = parse_sample_query(q)
        print(f"Parsed: {parsed}")
