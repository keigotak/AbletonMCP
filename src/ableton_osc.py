"""
Ableton Live OSC Communication Module
AbletonOSCを使ってAbleton Liveと通信する
"""

from pythonosc import osc_message_builder, osc_message
from dataclasses import dataclass
from typing import Optional, Callable
import threading
import socket
import time


@dataclass
class AbletonState:
    """Abletonの現在の状態を保持"""
    tempo: float = 120.0
    is_playing: bool = False
    current_track: int = 0
    track_count: int = 0
    clip_slots: dict = None
    
    def __post_init__(self):
        if self.clip_slots is None:
            self.clip_slots = {}


class AbletonOSC:
    """Ableton LiveとOSC経由で通信するクラス"""
    
    def __init__(
        self,
        ableton_host: str = "127.0.0.1",
        ableton_port: int = 11000,  # AbletonOSCのデフォルト受信ポート
        listen_port: int = 11001,   # Pythonが送受信するポート
    ):
        self.ableton_host = ableton_host
        self.ableton_port = ableton_port
        self.listen_port = listen_port
        self.state = AbletonState()
        self._callbacks: dict[str, list[Callable]] = {}
        self._socket: Optional[socket.socket] = None
        self._listener_thread: Optional[threading.Thread] = None
        self._running = False
        self._capture_all = False
        self._captured_messages = []
        
    def start_listener(self):
        """ソケットを起動して送受信を開始"""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # ポートの再利用を許可
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(("127.0.0.1", self.listen_port))
        self._socket.settimeout(0.1)  # ノンブロッキング風に
        self._running = True
        
        self._listener_thread = threading.Thread(target=self._listen_loop)
        self._listener_thread.daemon = True
        self._listener_thread.start()
        print(f"[OSC] OSC listener started on port {self.listen_port}")
    
    def _listen_loop(self):
        """受信ループ"""
        while self._running:
            try:
                data, addr = self._socket.recvfrom(65536)
                self._handle_message(data)
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    print(f"[WARN] Receive error: {e}")
    
    def _handle_message(self, data: bytes):
        """OSCメッセージをパース"""
        try:
            msg = osc_message.OscMessage(data)
            address = msg.address
            args = list(msg.params)
            
            # デバッグキャプチャ用
            if hasattr(self, '_capture_all') and self._capture_all:
                if hasattr(self, '_captured_messages'):
                    self._captured_messages.append((address, args))
            
            # 待機中のリクエストがあれば応答を保存
            if hasattr(self, '_pending_response') and self._pending_response is not None:
                if address == self._pending_response['address']:
                    self._pending_response['result'] = args
                    self._pending_response['received'] = True
            
            # ハンドラを呼び出す
            if address == "/live/song/get/tempo" and args:
                self._on_tempo(address, *args)
            elif address == "/live/song/get/is_playing" and args:
                self._on_is_playing(address, *args)
            elif address == "/live/song/get/num_tracks" and args:
                self._on_track_count(address, *args)
            else:
                self._on_any_message(address, *args)
        except Exception as e:
            print(f"[WARN] Parse error: {e}")
    
    def send_message(self, address: str, args: list = None):
        """OSCメッセージを送信"""
        if args is None:
            args = []
        msg = osc_message_builder.OscMessageBuilder(address=address)
        for arg in args:
            msg.add_arg(arg)
        built = msg.build()
        self._socket.sendto(built.dgram, (self.ableton_host, self.ableton_port))
    
    def query(self, address: str, args: list = None, timeout: float = 0.5):
        """OSCメッセージを送信して応答を待つ"""
        self._pending_response = {
            'address': address,
            'result': None,
            'received': False
        }
        
        self.send_message(address, args)
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._pending_response['received']:
                result = self._pending_response['result']
                self._pending_response = None
                return result
            time.sleep(0.02)
        
        self._pending_response = None
        return None
    
    def query_raw(self, address: str, args: list = None, timeout: float = 0.5):
        """デバッグ用: 全ての応答をキャプチャ"""
        self._captured_messages = []
        self._capture_all = True
        
        self.send_message(address, args)
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            time.sleep(0.05)
        
        self._capture_all = False
        result = self._captured_messages
        self._captured_messages = []
        return result
    
    def get_track_info(self, track_index: int) -> dict:
        """トラック情報を取得"""
        info = {}
        
        # トラック名
        result = self.query("/live/track/get/name", [track_index])
        if result:
            info['name'] = result[1] if len(result) > 1 else result[0]
        
        # ボリューム
        result = self.query("/live/track/get/volume", [track_index])
        if result:
            info['volume'] = result[1] if len(result) > 1 else result[0]
        
        # パン
        result = self.query("/live/track/get/panning", [track_index])
        if result:
            info['pan'] = result[1] if len(result) > 1 else result[0]
        
        return info
    
    def get_device_parameters(self, track_index: int, device_index: int) -> list:
        """デバイスのパラメータ一覧を取得"""
        result = self.query("/live/device/get/parameters/name", [track_index, device_index])
        return result if result else []
    
    def get_device_parameter_value(self, track_index: int, device_index: int, param_index: int):
        """デバイスパラメータの現在値を取得"""
        result = self.query("/live/device/get/parameter/value", [track_index, device_index, param_index])
        if result and len(result) > 3:
            return result[3]  # [track, device, param, value]
        return None
    
    def test_connection(self, timeout: float = 2.0) -> bool:
        """Abletonとの接続をテスト（応答を待つ）"""
        self._connection_confirmed = False
        
        # テンポ取得を送信
        self.send_message("/live/song/get/tempo")
        
        # 応答を待つ
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._connection_confirmed:
                return True
            time.sleep(0.1)
        
        return False
        
    def stop_listener(self):
        """リスナーを停止"""
        self._running = False
        if self._socket:
            self._socket.close()
            
    # =========================
    # Ableton Live Commands
    # =========================
    
    def play(self):
        """再生開始"""
        self.send_message("/live/song/start_playing", [])
        
    def stop(self):
        """停止"""
        self.send_message("/live/song/stop_playing", [])
        
    def set_tempo(self, bpm: float):
        """テンポを設定"""
        self.send_message("/live/song/set/tempo", [bpm])
        self.state.tempo = bpm
        
    def get_tempo(self):
        """テンポを取得"""
        self.send_message("/live/song/get/tempo", [])
        
    def create_midi_track(self, index: int = -1):
        """MIDIトラックを作成 (-1で末尾に追加)"""
        self.send_message("/live/song/create_midi_track", [index])
        
    def create_audio_track(self, index: int = -1):
        """オーディオトラックを作成"""
        self.send_message("/live/song/create_audio_track", [index])
        
    def set_track_name(self, track_index: int, name: str):
        """トラック名を設定"""
        self.send_message("/live/track/set/name", [track_index, name])
        
    def create_clip(self, track_index: int, clip_index: int, length: float = 4.0):
        """空のMIDIクリップを作成"""
        self.send_message(
            "/live/clip_slot/create_clip",
            [track_index, clip_index, length]
        )
        
    def add_notes(
        self,
        track_index: int,
        clip_index: int,
        notes: list[tuple[int, float, float, int, float]]
    ):
        """
        MIDIノートを追加
        notes: list of (pitch, start_time, duration, velocity, mute)
        """
        # AbletonOSCのノート追加形式に変換
        for note in notes:
            pitch, start, duration, velocity, mute = note
            self.send_message(
                "/live/clip/add/notes",
                [track_index, clip_index, pitch, start, duration, velocity, int(mute)]
            )
            
    def remove_notes(self, track_index: int, clip_index: int):
        """クリップの全ノートを削除"""
        self.send_message(
            "/live/clip/remove/notes",
            [track_index, clip_index, 0, 0, 128, 9999]  # 全範囲
        )
        
    def fire_clip(self, track_index: int, clip_index: int):
        """クリップを再生"""
        self.send_message("/live/clip/fire", [track_index, clip_index])
        
    def stop_clip(self, track_index: int, clip_index: int):
        """クリップを停止"""
        self.send_message("/live/clip/stop", [track_index, clip_index])
        
    def set_clip_name(self, track_index: int, clip_index: int, name: str):
        """クリップ名を設定"""
        self.send_message(
            "/live/clip/set/name",
            [track_index, clip_index, name]
        )
        
    # デバイス/エフェクト関連
    def load_device(self, track_index: int, device_uri: str):
        """デバイス（インストゥルメント/エフェクト）をロード"""
        # device_uri例: "Drums/Drum Rack"
        self.send_message(
            "/live/track/load/device",
            [track_index, device_uri]
        )
        
    def set_device_parameter(
        self,
        track_index: int,
        device_index: int,
        param_index: int,
        value: float
    ):
        """デバイスパラメータを設定 (0.0-1.0)"""
        self.send_message(
            "/live/device/set/parameter/value",
            [track_index, device_index, param_index, value]
        )
    
    def get_track_devices(self, track_index: int):
        """トラックのデバイス一覧を取得"""
        self._devices_response = None
        self.send_message("/live/track/get/devices/name", [track_index])
    
    def get_device_parameters(self, track_index: int, device_index: int):
        """デバイスのパラメータ一覧を取得"""
        self._params_response = None
        self.send_message("/live/device/get/parameters/name", [track_index, device_index])
        
    # ミキサー関連
    def set_track_volume(self, track_index: int, volume: float):
        """トラックボリュームを設定 (0.0-1.0)"""
        self.send_message(
            "/live/track/set/volume",
            [track_index, volume]
        )
        
    def set_track_pan(self, track_index: int, pan: float):
        """パンを設定 (-1.0 to 1.0)"""
        self.send_message(
            "/live/track/set/panning",
            [track_index, pan]
        )
        
    def set_track_mute(self, track_index: int, mute: bool):
        """ミュート設定"""
        self.send_message(
            "/live/track/set/mute",
            [track_index, int(mute)]
        )
        
    # =========================
    # OSC Response Handlers
    # =========================
    
    def _on_tempo(self, address: str, *args):
        if args:
            self.state.tempo = args[0]
            self._connection_confirmed = True
            
    def _on_is_playing(self, address: str, *args):
        if args:
            self.state.is_playing = bool(args[0])
            
    def _on_track_count(self, address: str, *args):
        if args:
            self.state.track_count = args[0]
            
    def _on_clip_info(self, address: str, *args):
        # クリップ情報をパース
        pass
        
    def _on_any_message(self, address: str, *args):
        """デバッグ用: 全メッセージをログ（MCP使用時はstderrに出力）"""
        import sys
        print(f"[MSG] OSC: {address} {args}", file=sys.stderr)


# ドラムパターン用のヘルパー
class DrumPattern:
    """ドラムパターンを生成するヘルパークラス"""
    
    # General MIDI Drum Map
    KICK = 36
    SNARE = 38
    CLOSED_HAT = 42
    OPEN_HAT = 46
    CLAP = 39
    TOM_LOW = 45
    TOM_MID = 47
    TOM_HIGH = 50
    CRASH = 49
    RIDE = 51
    
    @classmethod
    def four_on_floor(cls, bars: int = 1) -> list[tuple]:
        """4つ打ちキックパターン"""
        notes = []
        for bar in range(bars):
            for beat in range(4):
                time = bar * 4.0 + beat
                notes.append((cls.KICK, time, 0.25, 100, False))
        return notes
    
    @classmethod
    def basic_beat(cls, bars: int = 1) -> list[tuple]:
        """基本的な8ビート"""
        notes = []
        for bar in range(bars):
            base = bar * 4.0
            # キック: 1, 3拍目
            notes.append((cls.KICK, base + 0.0, 0.25, 100, False))
            notes.append((cls.KICK, base + 2.0, 0.25, 100, False))
            # スネア: 2, 4拍目
            notes.append((cls.SNARE, base + 1.0, 0.25, 100, False))
            notes.append((cls.SNARE, base + 3.0, 0.25, 100, False))
            # ハイハット: 8分音符
            for i in range(8):
                vel = 100 if i % 2 == 0 else 70
                notes.append((cls.CLOSED_HAT, base + i * 0.5, 0.25, vel, False))
        return notes
    
    @classmethod
    def trap_pattern(cls, bars: int = 1) -> list[tuple]:
        """トラップ風パターン（ハイハットロール）"""
        notes = []
        for bar in range(bars):
            base = bar * 4.0
            # キック: シンコペーション
            notes.append((cls.KICK, base + 0.0, 0.25, 110, False))
            notes.append((cls.KICK, base + 0.75, 0.25, 90, False))
            notes.append((cls.KICK, base + 2.5, 0.25, 100, False))
            # スネア/クラップ
            notes.append((cls.SNARE, base + 1.0, 0.25, 100, False))
            notes.append((cls.CLAP, base + 1.0, 0.25, 90, False))
            notes.append((cls.SNARE, base + 3.0, 0.25, 100, False))
            notes.append((cls.CLAP, base + 3.0, 0.25, 90, False))
            # ハイハット: 32分ロール
            for i in range(32):
                vel = 100 - (i % 4) * 15
                notes.append((cls.CLOSED_HAT, base + i * 0.125, 0.1, vel, False))
        return notes
    
    @classmethod
    def breakbeat(cls, bars: int = 1) -> list[tuple]:
        """ブレイクビート風パターン"""
        notes = []
        for bar in range(bars):
            base = bar * 4.0
            # シンコペーションの効いたキック
            kicks = [0.0, 1.25, 2.0, 2.75, 3.5]
            for k in kicks:
                notes.append((cls.KICK, base + k, 0.25, 100, False))
            # スネア
            snares = [1.0, 2.5, 3.0, 3.75]
            for s in snares:
                notes.append((cls.SNARE, base + s, 0.25, 100, False))
            # オフビートハイハット
            for i in range(8):
                notes.append((cls.CLOSED_HAT, base + i * 0.5 + 0.25, 0.2, 80, False))
        return notes


if __name__ == "__main__":
    # テスト
    osc = AbletonOSC()
    osc.start_listener()
    
    print("Testing connection...")
    osc.get_tempo()
    time.sleep(1)
    print(f"Current tempo: {osc.state.tempo}")
