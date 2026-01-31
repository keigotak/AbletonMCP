🌐 **English** | [日本語](README.ja.md)

# 🎹 Ableton MCP

An AI agent that gives you full control over Ableton Live using natural language.

## 🚀 Two Modes

### 1️⃣ MCP Mode (Recommended) - No API Key Required!
Use directly from Claude Desktop. Control Ableton just by chatting - no API key needed.

### 2️⃣ CLI Mode - Standalone
Operate from terminal using your Anthropic API key.

> ⚠️ **Note**: CLI mode is experimental and has not been fully tested.

---

## 🌟 MCP Mode Setup (No API Key Required)

### 1. Installation

```bash
cd ableton-mcp
pip install -e .
```

### 2. Configure Claude Desktop

Edit the Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ableton-mcp": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/path/to/ableton-mcp"
    }
  }
}
```

⚠️ Replace `cwd` with the actual path to your ableton-mcp folder.

📖 **Windows users**: See [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md) for detailed instructions.

### 3. Install AbletonOSC

**Option A: Max for Live Device (Simple)**
1. Download [AbletonOSC](https://github.com/ideoforms/AbletonOSC/releases)
2. Drag `AbletonOSC.amxd` onto a track in Ableton Live

**Option B: Remote Script (Recommended)**
1. Download from https://github.com/ideoforms/AbletonOSC
2. Place in Remote Scripts folder:
   - **Windows**: `C:\Users\<YourName>\Documents\Ableton\User Library\Remote Scripts\AbletonOSC`
   - **macOS**: `~/Music/Ableton/User Library/Remote Scripts/AbletonOSC`
3. Folder structure: `AbletonOSC\__init__.py` should be directly inside
4. In Ableton Live → Preferences → Link/Tempo/MIDI → Control Surface → Select **AbletonOSC**

### 4. Restart Claude Desktop

After restarting, you can control Ableton directly through chat!

```
You: Create a 4-minute EDM track

Claude: [using generate_arrangement tool]
Generated arrangement...

You: Add trap-style drums

Claude: [using create_drum_track tool]
Created drum track 'Drums'...
```

---

## ✨ Features

### 🥁 Drum/Rhythm Generation
- Basic beats, four-on-floor, trap, breakbeat, D&B
- Custom pattern creation

### 🎹 Melody/Synth Generation
- **Melody**: Scale-based auto-generation (adjustable density and contour)
- **Basslines**: basic, walking, syncopated, octave, arpeggiated
- **Chord progressions**: pop, jazz, sad, epic, dark, edm, lofi, cinematic
- **Arpeggios**: up, down, updown, random (8th/16th/triplet)

### 🔍 Sample Search
- Local library search (Ableton Core Library, Splice, etc.)
- Freesound API support
- Natural language queries

### 🎚️ Mixing Assistance
- Frequency collision detection (kick vs bass, etc.)
- Automatic sidechain compression setup
- EQ suggestions
- Level/dynamics analysis

### 📐 Song Structure Generation
- Genre templates: EDM, House, Techno, D&B, HipHop, Trap, Lo-Fi, Ambient, Pop
- Complete structure: Intro → Buildup → Drop → Breakdown → Outro
- Automatic automation generation

---

## 💻 CLI Mode Usage

### Launch

```bash
# Ableton connection mode
python src/cli.py

# Mock mode (test without Ableton)
python src/cli.py --mock
```

### Example Session

```
╔════════════════════════════════════════════════════════════════╗
║               🎹 Ableton Agent CLI v2.0 🎹                     ║
╚════════════════════════════════════════════════════════════════╝

🎤 You: Create a 4-minute EDM track

🤖 Agent: I'll generate an EDM track arrangement.

🎛️  Executing: generate_arrangement
    Parameters: {"genre": "edm", "duration_minutes": 4.0}
✅ Generated arrangement:

🎵 Untitled Edm
   Tempo: 128 BPM | Key: Am
   Total: 72 bars

📋 Structure:
   [  0] intro        |  8 bars | Energy: ███░░░░░░░
   [  8] buildup      |  8 bars | Energy: █████░░░░░
   [ 16] drop         | 16 bars | Energy: ██████████
   [ 32] breakdown    |  8 bars | Energy: ████░░░░░░
   [ 40] buildup      |  8 bars | Energy: ███████░░░
   [ 48] drop         | 16 bars | Energy: ██████████
   [ 64] outro        |  8 bars | Energy: ███░░░░░░░

🎤 You: Create trap-style drums

🤖 Agent: I'll create a trap-style drum pattern.
🎛️  Executing: create_drum_track
    Parameters: {"pattern_type": "trap", "bars": 2, "name": "Trap Drums"}
✅ Created drum track 'Trap Drums' (pattern: trap, 2 bars)
```

---

## ⌨️ Commands

### Special Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/status` | Show project status |
| `/genres` | List available genres |
| `/arrangement` | Show current arrangement |
| `/mock` | Toggle mock mode |
| `/clear` | Clear conversation history |
| `quit` | Exit |

### Natural Language Examples

#### Drums
- "Create a basic drum pattern"
- "Make a 4-bar trap beat"
- "Four on the floor kick"
- "Create a breakbeat"

#### Melody/Bass
- "Create a melody in C minor"
- "Bright pentatonic melody"
- "Syncopated bassline"
- "Add an octave bass"
- "16th note arpeggio"

#### Chords
- "Create a dark chord progression"
- "Jazzy chords"
- "Cinematic chord progression"

#### Samples
- "Search for ethnic percussion"
- "Dark synth 140BPM"
- "Find kick samples"

#### Mixing
- "Analyze the mix"
- "Kick and bass are clashing"
- "It sounds muddy"
- "Set up sidechain"
- "Add reverb"

#### Song Structure
- "Create a 4-minute EDM track"
- "Generate a lo-fi hip hop structure"
- "Make a techno arrangement"

#### Mood
- "Make it darker"
- "Brighten it up"
- "Make it more intense"
- "Chill vibe"

---

## 📁 Project Structure

```
ableton-mcp/
├── .gitignore
├── LICENSE
├── README.md                           # English
├── README.ja.md                        # Japanese
├── INSTALL_WINDOWS.md                  # Windows setup guide
├── pyproject.toml
├── setup.bat                           # Windows setup script
├── claude_desktop_config.example.json  # Example config
└── src/
    ├── __init__.py
    ├── mcp_server.py            # MCP server (for Claude Desktop)
    ├── cli.py                   # CLI interface
    ├── agent.py                 # AI agent (Claude API)
    ├── ableton_osc.py           # Ableton OSC communication
    ├── synth_generator.py       # Melody/bass/chord/arpeggio generation
    ├── sample_search.py         # Sample search engine
    ├── mixing_assistant.py      # Mixing analysis & assistance
    └── arrangement_generator.py # Song structure generation
```

---

## 🔧 Extending

### Adding New Tools

1. Add tool definition to `ABLETON_TOOLS` in `src/agent.py`:

```python
{
    "name": "your_tool_name",
    "description": "Tool description",
    "input_schema": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "Description"}
        },
        "required": ["param1"]
    }
}
```

2. Add execution logic to `execute_command` in `src/cli.py`:

```python
elif tool == "your_tool_name":
    return self._your_implementation(params)
```

### Adding Genre Templates

Add to `GenreTemplates.TEMPLATES` in `src/arrangement_generator.py`:

```python
"your_genre": {
    "sections": [
        ("intro", 8, 0.3, ["pad"]),
        ("verse", 16, 0.6, ["drums", "bass"]),
        # ...
    ],
    "tempo_range": (100, 120),
    "default_key": "Am",
}
```

---

## 🎛️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Input (Natural Language)                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Claude API (Tool Use)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │  Drums   │ │ Melody   │ │ Samples  │ │ Mixing   │ ...       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Command Executor                            │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │
│  │ SynthGenerator │  │ SampleSearch   │  │ MixingAssist   │    │
│  └────────────────┘  └────────────────┘  └────────────────┘    │
│  ┌────────────────┐  ┌────────────────┐                        │
│  │ ArrangementGen │  │ DrumPattern    │                        │
│  └────────────────┘  └────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OSC Communication                             │
│                      (python-osc)                                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Ableton Live                                │
│                     (via AbletonOSC)                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## ❓ Troubleshooting

### Startup Order (Important!)
1. **Start Ableton Live first**
2. Confirm AbletonOSC shows "Started AbletonOSC on address ('0.0.0.0', 11000)" in log
3. **Then start Claude Desktop**

### OSC Connection Error
- Check that AbletonOSC is loaded
- Verify port 11000 is available
- Check firewall settings

**Windows - Check ports:**
```powershell
netstat -ano | findstr "11000 11001"
```

**Windows - Check Ableton log:**
```powershell
Get-Content "$env:USERPROFILE\AppData\Roaming\Ableton\Live *\Preferences\Log.txt" -Tail 50 | Select-String "OSC"
```

### Claude Desktop Issues
- **After editing files**: Restart Claude Desktop completely (exit from system tray)
- **Connection problems**: Restart Claude Desktop

### API Error (CLI Mode)
- Verify `ANTHROPIC_API_KEY` is correctly set
- Check API usage limits

### Samples Not Found
- Check sample folder paths
- Specify custom paths when initializing `SampleSearchEngine`

---

## 📄 License

MIT

## 🔗 References

- [AbletonOSC](https://github.com/ideoforms/AbletonOSC)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [python-osc](https://python-osc.readthedocs.io/)
- [Freesound API](https://freesound.org/docs/api/)
