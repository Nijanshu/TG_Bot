# 🤖 NeoBot [(@Newtory_bot)]( https://t.me/Newtory_bot)

NeoBot is an **AI-powered Telegram chatbot** inspired by characters from *The Matrix* universe.  
It provides immersive, personality-driven conversations using **Groq LLMs**, supports **text, voice, and inline interactions**, and works entirely **without a database**, managing context in-memory.

---

## 🚀 Features

### 🧠 Character-Based AI Personalities
Users can interact with NeoBot in different modes:
- **Neo** – calm, mysterious, philosophical
- **Morpheus** – wise mentor, guiding tone
- **Trinity** – sharp, direct, and pragmatic  

Users can switch personalities anytime using commands or inline buttons.

---

### 💬 Text Chat Support
- Handles private chats and group mentions
- Maintains short-term conversational memory (in-memory)
- Automatically summarizes older context to stay within token limits

---

### 🎙️ Voice Message Support
- Accepts voice and audio messages
- Transcribes speech using **Groq Whisper**
- Responds intelligently to spoken queries

---

### ⚡ Inline Mode
- Works inside **any Telegram chat**
- Triggered using: @Newtory_bot ....Your query.....

- Returns AI-generated responses directly into the chat
- Ideal for quick answers without opening the bot

---

### 🧩 Inline Personality Switching
- Users can change modes via inline buttons
- Each mode affects tone, style, and behavior of responses

---

### 📝 Message Logging (No Database)
- All user interactions can be logged to:
- Admin chat / group
- Console or file
- Supports logging for:
- Normal messages
- Inline queries
- Voice interactions

---

### 🔒 Secure Configuration
- Uses environment variables for sensitive data:
- Telegram Bot Token
- Groq API Key
- No credentials are hardcoded

---

## 🛠️ Tech Stack

- **Python**
- **PyTelegramBotAPI (TeleBot)**
- **Groq LLM API**
- **Whisper (Groq ASR)**
- **Telegram Bot API**

---

## 📦 Architecture Overview

- **Polling-based bot** using `infinity_polling()`
- In-memory session management per user
- Modular design:
- Message handlers
- Inline handlers
- Voice handlers
- Personality system
- No external database required

---

## ▶️ How It Works

1. User sends a message (text, voice, or inline)
2. Bot detects interaction type
3. Personality system selects appropriate system prompt
4. Groq LLM generates a response
5. Response is sent back to the user
6. Context is stored temporarily in memory

---

## 📌 Commands

| Command | Description |
|------|-----------|
| `/start` | Start the bot and choose a personality |
| `/neo` | Switch to Neo mode |
| `/morpheus` | Switch to Morpheus mode |
| `/trinity` | Switch to Trinity mode |
| `/clear` | Clear conversation memory |

---

## 🧪 Example Inline Usage

```text
@Newtory_bot what is free will?

