# tellebot.py
import os
import time
import json
import requests
import telebot
from telebot import types
from io import BytesIO

# ---------- CONFIG / ENV ----------
API_TOKEN = os.getenv("TG_Token")
HF_API_KEY = os.getenv("HF_API_KEY")

HF_CHAT_MODEL = os.getenv("HF_CHAT_MODEL", "HuggingFaceH4/zephyr-7b-beta")
HF_SUMMARY_MODEL = os.getenv("HF_SUMMARY_MODEL", "sshleifer/distilbart-cnn-12-6")
HF_ASR_MODEL = os.getenv("HF_ASR_MODEL", "openai/whisper-large-v2")

if not API_TOKEN:
    raise ValueError("Telegram token not set! Set TG_Token env variable.")
if not HF_API_KEY:
    raise ValueError("Hugging Face API key not set! Set HF_API_KEY env variable.")

HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}

bot = telebot.TeleBot(API_TOKEN)

# ---------- MEMORY ----------
# memory structure:
# memory = {
#   user_id: {
#       "mode": "neo" | "morpheus" | "trinity",
#       "summary": "compressed text",
#       "recent": [ {"role":"user"|"assistant", "content": "..."} ... ]
#   }
# }
memory = {}
MAX_RECENT = 6  # keep last N recent messages

# ---------- PERSONALITY PROMPTS ----------
PERSONALITIES = {
    "neo": {
        "system":
            "You are NEO (from The Matrix). Speak calmly, concisely, and mysteriously. "
            "Use philosophical, introspective language. Refer to choice, destiny, reality, the Matrix, code, awakening. "
            "Avoid long explanations; be short and meaningful. Use iconic vibes like 'The Matrix is everywhere' or 'I can only show you the door.' "
            "Never say you are an AI and never break character."
    },
    "morpheus": {
        "system":
            "You are MORPHEUS from The Matrix. You are confident, mentor-like and inspiring. "
            "Speak with conviction and offer guidance. Use phrases like 'I can show you the truth' and 'Welcome to the real world.' "
            "Be calm, strong, and wise. Never reveal you are an AI or break character."
    },
    "trinity": {
        "system":
            "You are TRINITY from The Matrix. You are pragmatic, loyal, and sharp. "
            "Speak with determination and care. Provide direct answers and occasional encouragement. "
            "Keep character, never reveal you are an AI."
    }
}

# ---------- HELPERS: Hugging Face calls ----------
def hf_text_generation(prompt, model=HF_CHAT_MODEL, max_length=1024):
    """
    HuggingFace call with auto-retry.
    Tries 3 times before giving up.
    """
    url = f"https://api-inference.huggingface.co/models/{model}"
    payload = {"inputs": prompt}

    for attempt in range(3):
        try:
            resp = requests.post(url, headers=HEADERS, json=payload, timeout=120)
            resp.raise_for_status()
            result = resp.json()

            # Common return format
            if isinstance(result, list) and "generated_text" in result[0]:
                return result[0]["generated_text"]

            if isinstance(result, dict) and "generated_text" in result:
                return result["generated_text"]

            if isinstance(result, str):
                return result

            # Fallback
            return json.dumps(result)[:2000]

        except Exception as e:
            # If it's not the last attempt, retry after delay
            if attempt < 2:
                time.sleep(2)  # wait 2 seconds before retry
                continue
            else:
                # Final failure: return Neo-style error message
                return (
                    "The Matrix is resisting... something is blocking the signal. "
                    "Try again."
                )


def hf_summarize(text, model=HF_SUMMARY_MODEL):
    prompt = (
        "Summarize the important details of this conversation in a short paragraph, "
        "preserving only essential facts.\n\n" + text
    )
    return hf_text_generation(prompt, model=model)

def hf_asr_transcribe(audio_bytes, model=HF_ASR_MODEL):
    url = f"https://api-inference.huggingface.co/models/{model}"
    files = {"file": ("voice.ogg", audio_bytes)}

    for attempt in range(3):
        try:
            resp = requests.post(url, headers=HEADERS, files=files, timeout=120)
            resp.raise_for_status()
            result = resp.json()

            if isinstance(result, list) and "text" in result[0]:
                return result[0]["text"]
            if isinstance(result, dict) and "text" in result:
                return result["text"]
            if isinstance(result, str):
                return result

            return json.dumps(result)

        except Exception as e:
            if attempt < 2:
                time.sleep(2)
                continue
            else:
                return (
                    "The signal was distorted. "
                    "The Matrix did not allow me to hear clearly."
                )

# ---------- MEMORY MANAGEMENT ----------
def ensure_user(user_id):
    if user_id not in memory:
        memory[user_id] = {"mode": "neo", "summary": "", "recent": []}

def add_message(user_id, role, content):
    ensure_user(user_id)
    memory[user_id]["recent"].append({"role": role, "content": content})
    # prune & summarize older messages if recent too long
    if len(memory[user_id]["recent"]) > MAX_RECENT:
        # take everything except last 2 messages to summarize
        to_summarize = "\n".join(f"{m['role']}: {m['content']}" for m in memory[user_id]["recent"][:-2])
        try:
            summary = hf_summarize(to_summarize)
            memory[user_id]["summary"] = (memory[user_id]["summary"] + "\n" + summary).strip()
        except Exception as e:
            # if summarization fails, keep minimal fallback
            memory[user_id]["summary"] = (memory[user_id]["summary"] + "\n" + "Older conversation summarized.").strip()
        # keep only last 2 messages
        memory[user_id]["recent"] = memory[user_id]["recent"][-2:]

def build_prompt_for_hf(user_id, user_input):
    """
    Build a single textual prompt combining:
    - system personality instruction
    - conversation summary (if any)
    - recent message exchanges
    - current user input
    We'll format it in a clear instruction style for HF models.
    """
    ensure_user(user_id)
    mode = memory[user_id]["mode"]
    system_text = PERSONALITIES.get(mode, PERSONALITIES["neo"])["system"]

    parts = []
    parts.append("SYSTEM INSTRUCTION:")
    parts.append(system_text)
    if memory[user_id]["summary"]:
        parts.append("\nConversation summary:")
        parts.append(memory[user_id]["summary"])
    if memory[user_id]["recent"]:
        parts.append("\nRecent messages:")
        for m in memory[user_id]["recent"]:
            speaker = "User" if m["role"] == "user" else "Assistant"
            parts.append(f"{speaker}: {m['content']}")
    parts.append("\nUser: " + user_input)
    parts.append("\nAssistant:")  # instruct model to reply as assistant
    prompt = "\n".join(parts)
    return prompt

# ---------- TELEGRAM UI helpers ----------
def make_mode_buttons():
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("Neo", callback_data="mode:neo"),
        types.InlineKeyboardButton("Morpheus", callback_data="mode:morpheus"),
        types.InlineKeyboardButton("Trinity", callback_data="mode:trinity")
    )
    return markup

def send_typing_and_delay(chat_id, seconds=0.5):
    try:
        bot.send_chat_action(chat_id, 'typing')
        time.sleep(seconds)
    except Exception:
        pass

# ---------- COMMAND HANDLERS ----------
@bot.message_handler(commands=['start'])
def cmd_start(msg):
    ensure_user(msg.chat.id)
    bot.reply_to(msg,
                 "You have entered the Matrix.\n"
                 "I am here to guide you. Choose a mode with /mode or use /neo /morpheus /trinity.\n"
                 "Send voice messages or text. Use /clear to erase memory.")
    # show mode buttons
    bot.send_message(msg.chat.id, "Choose your mode:", reply_markup=make_mode_buttons())

@bot.message_handler(commands=['mode'])
def cmd_mode(msg):
    bot.send_message(msg.chat.id, "Select a character mode:", reply_markup=make_mode_buttons())

@bot.message_handler(commands=['neo', 'morpheus', 'trinity'])
def cmd_switch_mode(msg):
    ensure_user(msg.chat.id)
    cmd = msg.text.lstrip("/").split()[0].lower()
    if cmd in PERSONALITIES:
        memory[msg.chat.id]["mode"] = cmd
        bot.reply_to(msg, f"Mode set to {cmd.capitalize()}.")
    else:
        bot.reply_to(msg, "Unknown mode.")
    # show mode buttons for convenience
    bot.send_message(msg.chat.id, "Or tap a mode:", reply_markup=make_mode_buttons())

@bot.message_handler(commands=['clear'])
def cmd_clear(msg):
    memory[msg.chat.id] = {"mode": memory.get(msg.chat.id, {}).get("mode", "neo"), "summary": "", "recent": []}
    bot.reply_to(msg, "Memory cleared. Your slate is clean.")

# ---------- CALLBACK HANDLER for buttons ----------
@bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("mode:"))
def callback_mode(call):
    user_id = call.message.chat.id
    _, mode = call.data.split(":", 1)
    if mode in PERSONALITIES:
        ensure_user(user_id)
        memory[user_id]["mode"] = mode
        bot.answer_callback_query(call.id, f"Mode set to {mode.capitalize()}")
        # edit message or send confirmation
        bot.send_message(user_id, f"Character switched to {mode.capitalize()}.")
    else:
        bot.answer_callback_query(call.id, "Unknown mode.")

# ---------- VOICE HANDLING ----------
@bot.message_handler(content_types=['voice', 'audio'])
def handle_voice(msg):
    user_id = msg.chat.id
    ensure_user(user_id)

    # get file info & download
    file_info = bot.get_file(msg.voice.file_id if hasattr(msg, 'voice') else msg.audio.file_id)
    file_bytes = bot.download_file(file_info.file_path)
    send_typing_and_delay(user_id, 0.4)
    try:
        bot.send_chat_action(user_id, 'record_audio')
    except Exception:
        pass

    # Transcribe via HF ASR
    try:
        transcript = hf_asr_transcribe(file_bytes, model=HF_ASR_MODEL)
    except Exception as e:
        bot.reply_to(msg, "Sorry, I couldn't transcribe your audio.")
        return

    # Show what was transcribed (optional)
    bot.reply_to(msg, f"Transcribed: {transcript}")

    # Continue as normal text message
    process_user_message(user_id, transcript, msg)

# ---------- MAIN MESSAGE PROCESSING ----------
def process_user_message(user_id, text, original_msg=None):
    """
    Shared function to process user text (text or transcribed voice).
    """
    ensure_user(user_id)
    # typing indicator
    send_typing_and_delay(user_id, 0.2)
    bot.send_chat_action(user_id, 'typing')

    # build prompt for HF
    prompt = build_prompt_for_hf(user_id, text)

    # send a small ephemeral '...' message for style, then replace with real reply (can't edit sent message from bot easily in all cases)
    try:
        placeholder = bot.send_message(user_id, "...")
    except Exception:
        placeholder = None

    # call HF
    try:
        ai_text = hf_text_generation(prompt, model=HF_CHAT_MODEL)
    except Exception as e:
        ai_text = "Something in the Matrix is resisting. Try again."
        # cleanup placeholder
        if placeholder:
            try:
                bot.delete_message(user_id, placeholder.message_id)
            except Exception:
                pass
        bot.reply_to(original_msg or user_id, ai_text)
        return

    # remember
    add_message(user_id, "user", text)
    add_message(user_id, "assistant", ai_text)

    # cleanup placeholder and send result
    if placeholder:
        try:
            bot.delete_message(user_id, placeholder.message_id)
        except Exception:
            pass

    # final typing pause for realism
    send_typing_and_delay(user_id, 0.3)

    # send reply in chat
    bot.reply_to(original_msg or user_id, ai_text)

@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_text(msg):
    process_user_message(msg.chat.id, msg.text, msg)

# ---------- START ----------
if __name__ == "__main__":
    print("Starting Matrix bot...")
    bot.infinity_polling()
