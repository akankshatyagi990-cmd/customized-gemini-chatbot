# Customized Gemini Chatbot

A beginner-friendly customized AI chatbot built with Python, LangChain, and Google Gemini.

## Features

- Uses Google Gemini through LangChain
- Reads API key securely from `.env`
- Remembers the user's name
- Saves conversation history locally
- Loads previous chats
- Supports clearing chat history
- Supports changing the saved user name
- Handles temporary Gemini API errors
- Keeps private files out of GitHub

## Project Structure

```text
customized-gemini-chatbot/
│
├── chatbot.py
├── requirements.txt
├── README.md
├── .gitignore
├── .env
├── user_profile.json
├── chat_history.json
└── venv/