import telebot
import os
from groq import Groq

# Telegram token
API_TOKEN = os.getenv('TG_Token')
print("Token from Railway:", os.getenv("TG_Token"),API_TOKEN)
if not API_TOKEN:
    raise ValueError("Telegram token not set!")

# Groq API Key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("Groq API key not set!")

bot = telebot.TeleBot(API_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

def ask_ai(prompt):
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content



@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Hey! I'm an AI bot created by Neo @Nijw3. Ask me anything!")


@bot.message_handler(func=lambda message: True)
def chat_with_ai(message):
    user_text = message.text
    ai_reply = ask_ai(user_text)
    bot.reply_to(message, ai_reply)


bot.polling()

