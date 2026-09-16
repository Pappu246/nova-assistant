# NOVA — Personal AI Assistant (Jarvis-inspired)

100% free stack: local LLM (Ollama) + free weather API. Voice (STT/TTS)
Phase 2 mein add hoga.

## Setup

1. **Ollama install karo:** https://ollama.com se download karo (Windows/Mac/Linux sab support)

2. **Model download karo** (terminal mein):
   ```bash
   ollama pull llama3.1
   ```

3. **Python dependencies install karo:**
   ```bash
   pip install -r requirements.txt
   ```

4. **NOVA chalao:**
   ```bash
   python main.py
   ```

## Abhi kya kaam karta hai (Phase 1)

- Normal text conversation (Hindi/Hinglish/English)
- "Time batao" → abhi ka time
- "Jaipur mein weather kaisa hai" → live weather
- "Chrome khol do" → app open karta hai (tumhare computer pe jo installed ho)

## Roadmap

- [x] Phase 1: Text chatbot + function calling (time, weather, app open)
- [ ] Phase 2: Speech-to-Text (Whisper) add karna
- [ ] Phase 3: Text-to-Speech (pyttsx3 / Coqui) add karna
- [ ] Phase 4: Wake word ("Hey NOVA") add karna
- [ ] Phase 5: Aur tools — calendar, reminders, file search

## Project Structure

```
nova/
├── main.py          # Entry point, chat loop
├── brain.py         # LLM (Ollama) ke saath baat-cheet + tool-call decision
├── tools.py          # Actual functions jo NOVA execute karta hai
├── requirements.txt
└── README.md
```
