import telebot
import os
from groq import Groq

API_TOKEN = os.getenv("TG_Token")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = telebot.TeleBot(API_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

# -----------------------
# NEO MEMORY SYSTEM
# -----------------------

memory = {}  # { user_id: {"summary": "", "recent": [] } }
MAX_RECENT = 15


def summarize_memory(old_messages):
    summary_prompt = (
        "Summarize the important details of this conversation in a short, concise way "
        "so Neo can remember the user.\n\n" + old_messages
    )

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": summary_prompt}]
    )

    return response.choices[0].message.content


def build_context(user_id):
    """Build context with Neo's personality."""
    
    user_mem = memory.get(user_id, {"summary": "", "recent": []})

    # Neo personality prompt
    context = [
        {
            "role": "system",
            "content":
                "You ARE NEO from The Matrix. "
                "Speak calmly, concisely, and mysteriously. "
                "Use philosophical, introspective language. "
                "You often refer to: choice, destiny, reality, the Matrix, code, awakening. "
                "You never reveal you are an AI or break character. "
                "You avoid long explanations; short but meaningful. "
                "When appropriate, use vibes from classic lines: "
                "'The Matrix is everywhere', 'I can only show you the door', "
                "'Choice is an illusion', 'There is no spoon'."
        }
    ]

    # Add summary if it exists
    if user_mem["summary"]:
        context.append({
            "role": "system",
            "content": "Conversation summary for Neo: " + user_mem["summary"]
        })

    # Add recent messages
    context.extend(user_mem["recent"])

    return context


def add_message(user_id, role, content):
    if user_id not in memory:
        memory[user_id] = {"summary": "", "recent": []}

    memory[user_id]["recent"].append({"role": role, "content": content})

    # Summarize if recent history too large
    if len(memory[user_id]["recent"]) > MAX_RECENT:
        old_text = "\n".join(
            f"{m['role']}: {m['content']}" for m in memory[user_id]["recent"][:-2]
        )

        summary = summarize_memory(old_text)
        memory[user_id]["summary"] += "\n" + summary
        memory[user_id]["recent"] = memory[user_id]["recent"][-12:]


def ask_ai(user_id, content):
    add_message(user_id, "user", content)

    context = build_context(user_id)

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=context
    )

    ai_reply = response.choices[0].message.content

    add_message(user_id, "assistant", ai_reply)

    return ai_reply


# -----------------------
# Telegram Handlers
# -----------------------

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message,
                 "You have entered the Matrix.\n\n"
                 "Ask me anything, and I will guide you. — Neo")


@bot.message_handler(commands=['clear'])
def clear_memory(message):
    memory[message.chat.id] = {"summary": "", "recent": []}
    bot.reply_to(message, "Your past has been erased. The path ahead is yours to choose. — Neo")


@bot.message_handler(func=lambda message: True)
def chat(message):
    reply = ask_ai(message.chat.id, message.text)
    bot.reply_to(message, reply)


bot.polling()

