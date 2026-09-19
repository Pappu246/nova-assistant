# NOVA

NOVA is a Windows-focused personal desktop assistant built as a modular Python project. It combines voice input, speech output, wake-word detection, persistent memory, reminders, browser automation, screen monitoring, desktop controls, and a local web dashboard.

The project is designed to run on the user's own machine and keep the assistant's operating logic close to the desktop it controls. Cloud services are used where configured, while Ollama provides a local language-model fallback.

## Project Status

| Area | Current state |
| --- | --- |
| Voice input | Implemented with Whisper |
| Voice output | Implemented with Microsoft Edge-TTS |
| Wake word | Implemented with openWakeWord |
| Voice identification | Implemented with SpeechBrain ECAPA |
| Continuous listening | Implemented |
| Desktop controls | Implemented |
| Browser automation | Implemented |
| Memory and notes | Implemented with SQLite |
| Reminders | Implemented |
| Screen watcher | Implemented |
| Desktop HUD | Implemented |
| Web dashboard | Implemented; active development continues |

## What NOVA Can Do

NOVA is built around actions rather than a single chat loop. Depending on the command, it can:

- answer normal questions through the configured language model
- open Windows applications, folders and supported websites
- search files and open screenshot folders
- take screenshots
- control system volume and media playback
- lock the workstation or schedule shutdown/restart commands
- type text and copy content to the clipboard
- search Google and use the browser automation layer
- play or search YouTube and Spotify
- create, list and clear reminders
- remember facts, recall them later, and manage notes
- observe the screen at intervals through the screen watcher
- expose assistant state, chat, tasks and voice controls through a local FastAPI dashboard

## Architecture

```text
                         +----------------------+
                         |       User           |
                         |  Voice / Text / UI   |
                         +----------+-----------+
                                    |
                     +--------------+--------------+
                     |                             |
                     v                             v
              +-------------+                +-------------+
              | Microphone  |                | Web Browser |
              +------+------+                +------+------+
                     |                              |
                     v                              v
              +-------------+                +-------------+
              | Voice ID    |                | FastAPI     |
              | SpeechBrain |                | server.py   |
              +------+------+                +------+------+
                     |                              |
                     v                              |
              +-------------+                       |
              |   Whisper   |                       |
              | Speech-to-  |                       |
              |    Text     |                       |
              +------+------+                       |
                     |                              |
                     +--------------+---------------+
                                    |
                                    v
                         +----------------------+
                         |       brain.py       |
                         | Prompt + LLM routing |
                         +----------+-----------+
                                    |
                    +---------------+----------------+
                    |                                |
                    v                                v
          +--------------------+          +----------------------+
          | Groq / configured  |          | Ollama local model  |
          | cloud model        |          | fallback             |
          +---------+----------+          +----------+-----------+
                    |                                |
                    +----------------+---------------+
                                     |
                                     v
                           +--------------------+
                           |     Tool Router    |
                           |      tools.py      |
                           +---------+----------+
                                     |
           +------------+-------------+-------------+-------------+
           |            |             |             |             |
           v            v             v             v             v
       Windows       Browser       Memory        Reminders      Screen
       control       agent         SQLite         module        watcher
           |            |             |             |             |
           +------------+-------------+-------------+-------------+
                                     |
                                     v
                           +--------------------+
                           | Response / State   |
                           +---------+----------+
                                     |
                         +-----------+-----------+
                         |                       |
                         v                       v
                +----------------+        +-------------+
                | Edge-TTS /     |        | Web / HUD   |
                | speaker output |        | dashboard   |
                +----------------+        +-------------+
```

## Runtime Workflow

```text
Voice path

Microphone
    |
    v
Voice activity detected
    |
    v
Voice ID check
    |
    +---- voice does not match ----> Ignore input
    |
    v
Whisper transcription
    |
    v
brain.ask_nova()
    |
    v
Tool needed?
   / \
 yes  no
  |    |
  v    v
tools.py   Direct response
  |
  v
Execute action
  |
  +-------------------+
                      |
                      v
              Final response text
                      |
                      v
                Edge-TTS output
                      |
                      v
                   Speaker

Web dashboard path

Browser
   |
   v
FastAPI server
   |
   +--> Chat request ------> brain.ask_nova()
   |
   +--> Voice control -----> main / suno / bolo
   |
   +--> Tasks -------------> server state
   |
   +--> Live status --------> WebSocket /ws
   |
   v
Dashboard updates
```

## Core Modules

| File | Responsibility |
| --- | --- |
| `main.py` | Main application entry point and voice, continuous and text modes |
| `brain.py` | Language-model calls, response parsing and tool selection |
| `tools.py` | Windows, browser, media, file, clipboard, memory and reminder actions |
| `suno.py` | Microphone capture, Whisper transcription and stop-command listening |
| `bolo.py` | Speech output, Edge-TTS playback and interruption handling |
| `wake.py` | `Hey Jarvis` wake-word detection |
| `voice_id.py` | Voice registration and speaker verification |
| `browser_agent.py` | Browser automation integration |
| `browser_prompt.py` | Browser-task prompting support |
| `memory.py` | Persistent facts and notes backed by SQLite |
| `reminders.py` | Reminder storage, scheduling and watcher |
| `screen_watcher.py` | Periodic screen analysis |
| `hud.py` | Floating desktop HUD and assistant state display |
| `server.py` | Local FastAPI dashboard and WebSocket state endpoint |
| `web/` | Dashboard HTML, JavaScript and CSS |
| `.github/workflows/python-check.yml` | Python syntax validation in GitHub Actions |

## Tool Layer

The tool registry in `tools.py` currently covers the following areas:

**Desktop**
- application and folder opening
- screenshot capture
- file search
- clipboard copy
- text typing
- workstation lock
- shutdown and restart commands

**Media**
- YouTube search/play
- Spotify search/play
- volume up/down/mute
- play/pause
- next and previous track

**Browser**
- Google/web search
- browser task automation
- browser closing

**Productivity**
- reminders
- memory
- notes

## Language Model Routing

`brain.py` first attempts the configured Groq model and falls back to Ollama when the cloud path is unavailable.

Current model configuration in the code:

```python
GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_FALLBACK = "openai/gpt-oss-20b"
OLLAMA_MODEL = "llama3.2"
```

This means NOVA is not strictly offline by default. A local Ollama path exists, but the normal first-choice model route depends on the environment configuration.

## Voice Pipeline

The current voice stack is split into separate modules:

```text
Microphone
   |
   v
sounddevice
   |
   v
Audio calibration + voice activity detection
   |
   v
Whisper
   |
   v
Transcribed text
   |
   v
NOVA reasoning and actions
   |
   v
Edge-TTS
   |
   v
Speaker
```

The configured TTS voice is:

```python
EDGE_VOICE = "hi-IN-MadhurNeural"
```

The wake-word module listens for:

```text
Hey Jarvis
```

The voice identification module can register a reference voice and compare incoming audio against it using SpeechBrain ECAPA embeddings.

## Web Dashboard

The repository contains a local web interface under `web/`, served by `server.py`.

The dashboard currently includes interfaces for:

- chat
- voice activation
- apps and tools
- files
- automation
- devices
- tasks
- memory
- notes
- settings

The server also exposes local endpoints for chat, speech, voice activation, tasks, history and live WebSocket status.

Run the dashboard with:

```bash
python server.py
```

Then open:

```text
http://127.0.0.1:8000
```

## Requirements

The project is intended primarily for Windows.

Recommended baseline:

- Windows 10 or Windows 11
- Python 3.10 or newer
- Working microphone
- Speakers or headphones
- Sufficient RAM for Whisper inference
- Internet access for cloud model calls, Edge-TTS and browser-related features when those services are enabled

The repository's `requirements.txt` currently contains:

```text
ollama
openai-whisper
sounddevice
numpy
scipy
pyttsx3
```

Some modules also use additional packages conditionally at runtime, such as browser automation, audio playback, screen capture, voice identification and dashboard dependencies. Install those components as required by the feature you enable.

## Installation

Clone the repository:

```bash
git clone https://github.com/Pappu246/nova-assistant.git
cd nova-assistant
```

Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install the repository requirements:

```bash
pip install -r requirements.txt
```

For local model fallback, install Ollama and pull the configured model:

```bash
ollama pull llama3.2
```

Set the required environment variables for the services you plan to use:

```powershell
setx GROQ_API_KEY "your_key"
```

Restart the terminal after using `setx`.

## Running NOVA

Voice mode:

```bash
python main.py
```

Continuous mode:

```bash
python main.py --continuous
```

Text-only mode:

```bash
python main.py --text
```

Voice registration:

```bash
python voice_id.py
```

Web dashboard:

```bash
python server.py
```

## Example Commands

```text
time kya hai
chrome kholo
screenshot lo
volume badhao
youtube pe Kesariya bajao
google pe weather Delhi search karo
5 minute baad yaad dilana chai peena
mera naam Pappu hai
mera naam kya hai
mere notes dikhao
browser mein Google kholo
```

## Configuration

### Language model

Update the constants in `brain.py`:

```python
GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_FALLBACK = "openai/gpt-oss-20b"
OLLAMA_MODEL = "llama3.2"
```

### Text-to-speech

Update the voice in `bolo.py`:

```python
EDGE_VOICE = "hi-IN-MadhurNeural"
EDGE_RATE = "+5%"
EDGE_PITCH = "+0Hz"
```

### Microphone

Update the configured device index in `suno.py` when a different recording device is required:

```python
MIC_DEVICE = 1
```

### Wake word

Wake-word sensitivity is configured in `wake.py`:

```python
THRESHOLD = 0.30
```

### Voice profile

Run:

```bash
python voice_id.py
```

The registration flow stores the reference voice locally as `boss_voice.pkl`.

## Automation and Safety Notes

NOVA can perform real desktop actions. Commands such as opening applications, typing text, locking Windows and scheduling shutdown affect the host machine directly.

Review commands before using them in unattended or continuous mode. The shutdown tool uses a delayed Windows command and supports cancellation through the corresponding command path.

The project should be treated as a personal desktop automation project rather than a sandboxed application.

## Development

The repository includes a GitHub Actions workflow at:

```text
.github/workflows/python-check.yml
```

It currently runs Python syntax checks for:

```text
main.py
brain.py
tools.py
```

Local syntax validation can be run with:

```bash
python -m py_compile main.py brain.py tools.py
```

## Roadmap

The current codebase already contains the major building blocks for a desktop assistant. Planned work can focus on reliability, packaging and integration:

```text
Current
  |
  +--> Dashboard reliability
  |
  +--> More robust browser automation
  |
  +--> Better screen-based control
  |
  +--> Email and messaging integrations
  |
  +--> Device / companion support
  |
  +--> Mobile interface
  |
  +--> Installer and background service
```

## Project Structure

```text
nova-assistant/
|
+-- .github/
|   +-- workflows/
|       +-- python-check.yml
|
+-- web/
|   +-- index.html
|   +-- app.js
|   +-- style.css
|
+-- main.py
+-- brain.py
+-- tools.py
+-- suno.py
+-- bolo.py
+-- wake.py
+-- voice_id.py
+-- browser_agent.py
+-- browser_prompt.py
+-- screen_watcher.py
+-- memory.py
+-- reminders.py
+-- hud.py
+-- server.py
+-- shutdown.py
+-- nova_startup.bat
+-- nova_stop.bat
+-- nova_silent.vbs
+-- requirements.txt
+-- README.md
```

## License

MIT

## Author

Built and maintained by [Pappu246](https://github.com/Pappu246).

Repository:

https://github.com/Pappu246/nova-assistant
