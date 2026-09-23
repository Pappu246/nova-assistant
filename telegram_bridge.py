"""
NOVA Telegram Bridge - phone se NOVA control karo.
Bot sirf tumhare chat ID se messages accept karta hai.
"""
import os
import asyncio
import threading
import time

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    _TG = True
except Exception as e:
    print("[telegram] import fail: " + str(e)[:80])
    _TG = False

try:
    from brain import ask_nova
    _BRAIN = True
except Exception as e:
    print("[telegram] brain import fail: " + str(e)[:80])
    _BRAIN = False


TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ALLOWED_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Conversation history (in-memory)
_history = []

# App reference for sending messages from other threads
_app = None


def _is_allowed(update):
    """Only Boss can talk to the bot."""
    if not ALLOWED_CHAT_ID:
        return True  # if not configured, allow all (dev mode)
    try:
        return str(update.effective_chat.id) == str(ALLOWED_CHAT_ID)
    except Exception:
        return False


async def _handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming Telegram message."""
    if not _is_allowed(update):
        print("[telegram] blocked chat: " + str(update.effective_chat.id))
        await update.message.reply_text("Ye bot sirf Boss ke liye hai.")
        return

    user_text = (update.message.text or "").strip()
    if not user_text:
        return

    print("[telegram] Boss: " + user_text)
    await update.message.reply_text("Soch raha hoon...")

    # Run brain in executor (blocking)
    try:
        loop = asyncio.get_event_loop()
        reply = await loop.run_in_executor(None, ask_nova, user_text, _history)
    except Exception as e:
        reply = "Error: " + str(e)[:120]

    print("[telegram] NOVA: " + reply[:80])
    await update.message.reply_text(reply)

    # Update history
    _history.append({"role": "user", "content": user_text})
    _history.append({"role": "assistant", "content": reply})
    if len(_history) > 20:
        _history[:] = _history[-20:]


async def _start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    name = "Boss"
    try:
        import identity
        name = identity.get_name()
    except Exception:
        pass
    await update.message.reply_text(
        "Namaste " + name + "! NOVA ready hai.\n\n"
        "Commands bhejo:\n"
        "- time kya hai\n"
        "- chrome kholo\n"
        "- youtube pe X bajao\n"
        "- mera naam Pappu hai\n"
        "- 5 minute baad yaad dilana chai\n\n"
        "Bye = exit NOVA"
    )


async def _status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    try:
        import agent_state
        snap = agent_state.get_state().get_snapshot()
        await update.message.reply_text(
            "Mode: " + str(snap.get("current_mode")) + "\n"
            "Task: " + str(snap.get("current_task")) + "\n"
            "Status: " + str(snap.get("task_status"))
        )
    except Exception as e:
        await update.message.reply_text("Status fail: " + str(e)[:80])


def _run_bot():
    """Run telegram bot (blocking)."""
    global _app
    if not _TG:
        print("[telegram] library not available")
        return
    if not TOKEN:
        print("[telegram] TELEGRAM_BOT_TOKEN missing")
        return

    _app = Application.builder().token(TOKEN).build()
    _app.add_handler(CommandHandler("start", _start_cmd))
    _app.add_handler(CommandHandler("status", _status_cmd))
    _app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_message))

    print("[telegram] Bot polling started")
    _app.run_polling(allowed_updates=Update.ALL_TYPES)


def start_in_background():
    """Start bot in a daemon thread (non-blocking)."""
    t = threading.Thread(target=_run_bot, daemon=True)
    t.start()
    print("[telegram] Bot thread started")
    return t


def send_message(text):
    """Send a message to Boss from anywhere in NOVA."""
    global _app
    if not _app or not ALLOWED_CHAT_ID:
        return False
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            _app.bot.send_message(chat_id=ALLOWED_CHAT_ID, text=text)
        )
        return True
    except Exception as e:
        print("[telegram send] " + str(e)[:60])
        return False


if __name__ == "__main__":
    print("Starting NOVA Telegram Bridge...")
    print("Token: " + (TOKEN[:20] + "..." if TOKEN else "MISSING"))
    print("Chat ID: " + (ALLOWED_CHAT_ID if ALLOWED_CHAT_ID else "MISSING"))
    _run_bot()
