# NOVA - Personal AI Assistant

A fully local, voice-controlled personal AI assistant inspired by JARVIS from Iron Man. Runs entirely on your machine with free APIs and local models.

---

## Current Status

| Module | Status |
|--------|--------|
| Voice input (Whisper medium) | Working |
| Voice output (Edge-TTS Madhur) | Working |
| Wake word (Hey Jarvis) | Working |
| Continuous mode | Working |
| Voice ID (only Boss voice) | Working |
| Memory (facts + recall) | Working |
| 26 Tools | Working |
| Browser automation | Working |
| Screen watcher | Working |
| Reminders | Working |
| HUD overlay | Working |
| Web dashboard | Partial |
---

## Architecture

```
Microphone
    |
    v
Voice ID Filter (SpeechBrain)
    |
    v
Whisper Medium (Speech to Text)
    |
    v
Groq LLM (gpt-oss-120b)
    |
    +---- Tool Router ----+
    |                     |
    v                     v
  26 Tools            Text Reply
    |                     |
    +----------+----------+
               |
               v
    Response Formatter
    (Gender + Length fix)
               |
               v
    Edge-TTS Output
    (Madhur voice)
               |
               v
            Speaker
```

---

## Workflow

```
User speaks
    |
    v
[Voice ID check] --not Boss--> Ignore
    |
    v
[Whisper transcribes]
    |
    v
[LLM decides: tool or text?]
    |
    +-- Tool call --> Execute --> Format --> Speak
    |
    +-- Text reply --> Format --> Speak
    |
    v
Loop back to listening
```

---

## Installation

### Requirements

- Python 3.10+
- Windows 10/11
- Microphone
- 8 GB RAM minimum
- 4 GB free disk

### Setup Steps

1. Clone the repository

```
git clone https://github.com/Pappu246/nova-assistant.git
cd nova-assistant
```

2. Install Python dependencies

```
pip install -r requirements.txt
```

3. Install Ollama (local LLM fallback)

Download from https://ollama.com/download

```
ollama pull llama3.2
```

4. Set environment variables

```
setx GROQ_API_KEY "your_key"
setx GEMINI_API_KEY "your_key"
```

5. Register your voice

```
python voice_id.py
```

Speak 3 times when prompted.

6. Start NOVA

```
python main.py --continuous
```

Or wake-word mode:

```
python main.py
```

---

## File Structure

```
nova/
|
+-- main.py              Main loop
+-- suno.py              Speech to text
+-- bolo.py              Text to speech
+-- brain.py             LLM orchestration
+-- tools.py             26 tools
+-- voice_id.py          Voice fingerprint
+-- wake.py              Wake word
+-- screen_watcher.py    Screen analysis
+-- browser_agent.py     Browser automation
+-- browser_prompt.py    Browser prompt
+-- reminders.py         Reminders
+-- memory.py            Persistent memory
+-- hud.py               HUD overlay
+-- server.py            Web dashboard
+-- shutdown.py          Process cleanup
+-- nova_startup.bat     Launcher
+-- nova_stop.bat        Stop script
+-- nova_silent.vbs      Background launcher
+-- requirements.txt     Dependencies
+-- README.md            This file
```

---

## Usage Examples

### Basic Commands

```
Time kya hai
Chrome kholo
Screenshot lo
Volume badhao
```

### Memory

```
Mera naam Pappu hai
Mera naam kya hai
Kya yaad hai
```

### Browser Automation

```
YouTube pe Kesariya gaana bajao
Google pe weather Delhi search karo
```

### Reminders

```
5 minute baad yaad dilana chai peena
Mere reminders dikhao
```

### Control

```
Stop or Ruko    - Stop speaking
Esc key         - Force stop
Bye             - Exit
```

---

## Configuration

### Change TTS Voice

Edit bolo.py:

```
EDGE_VOICE = "hi-IN-MadhurNeural"
```

Available voices:
- hi-IN-MadhurNeural (Hindi male)
- hi-IN-SwaraNeural (Hindi female)
- en-IN-PrabhatNeural (Indian English male)
- en-IN-NeerjaNeural (Indian English female)
- en-US-AndrewMultilingualNeural (US male)
- en-US-AvaMultilingualNeural (US female)

### Change LLM

Edit brain.py:

```
GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_FALLBACK = "openai/gpt-oss-20b"
OLLAMA_MODEL = "llama3.2"
```

### Change Microphone

Edit suno.py:

```
MIC_DEVICE = 1
```

### Change Wake Word Sensitivity

Edit wake.py:

```
THRESHOLD = 0.30
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Speech to Text | OpenAI Whisper (medium) |
| Text to Speech | Microsoft Edge-TTS |
| Wake Word | openWakeWord |
| Voice ID | SpeechBrain ECAPA |
| LLM Cloud | Groq gpt-oss-120b |
| LLM Local | Ollama llama3.2 |
| Browser Agent | browser-use + Gemini |
| Screen Analysis | Gemini Vision |
| Memory | SQLite |
| HUD | Tkinter |
| Web Dashboard | FastAPI |
---

## Roadmap

- [x] Phase 1 - Basic voice loop
- [x] Phase 2 - 20+ tools
- [x] Phase 3 - Browser automation
- [x] Phase 4 - Wake word
- [x] Phase 5 - Memory
- [x] Phase 6 - Auto-start + HUD
- [x] Phase 7 - Voice ID
- [x] Phase 8 - Continuous mode
- [x] Phase 9 - Screen watcher
- [x] Phase 10 - Reminders
- [ ] Phase 11 - Web dashboard fix
- [ ] Phase 12 - WhatsApp / Email
- [ ] Phase 13 - Vision based app control
- [ ] Phase 14 - Mobile companion app
---

## Known Issues

- Bluetooth headset microphone has low accuracy
- Stop voice command may not work during TTS (use Esc key)
- Web dashboard Failed to fetch error (under investigation)
- Whisper medium requires 1.5 GB RAM during inference
---

## Links

- Whisper: https://github.com/openai/whisper
- Edge-TTS: https://github.com/rany2/edge-tts
- openWakeWord: https://github.com/dscripka/openWakeWord
- SpeechBrain: https://speechbrain.github.io
- browser-use: https://github.com/browser-use/browser-use
- Ollama: https://ollama.com
- Groq: https://console.groq.com
- Gemini: https://aistudio.google.com
---

## License

MIT
---

Inspired by JARVIS from Iron Man. Built with free and open source tools.