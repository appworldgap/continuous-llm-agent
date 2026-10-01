import os
from flask import Flask, request
import requests
from groq import Groq
from duckduckgo_search import DDGS

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    try:
        update = request.get_json(force=True)
        print(f"📥 Received update: {update}")
        
        message = update.get("message") or update.get("edited_message")
        if not message:
            return "OK", 200
            
        text = message.get("text", "").strip()
        chat = message.get("chat", {})
        chat_id = chat.get("id")
        
        if not text or not chat_id:
            return "OK", 200
            
        print(f"💬 Chatbot query: '{text}' for chat_id: {chat_id}")
        
        # 1. Send a quick "Searching..." notice so you know it's working
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": f"🔍 Searching the web for: *{text}*...", "parse_mode": "Markdown"}
        )
        
        # 2. Perform Web Search via DuckDuckGo
        results_text = ""
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(text, max_results=4):
                    title = r.get("title", "")
                    body = r.get("body", "")
                    href = r.get("href", "")
                    results_text += f"Title: {title}\nSnippet: {body}\nURL: {href}\n\n"
        except Exception as e:
            results_text = "Web search failed."

        # 3. Generate Smart Response via Groq
        client = Groq(api_key=GROQ_API_KEY)
        chat_completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a helpful, brilliant AI research assistant on Telegram. Provide a concise, highly informative, well-formatted answer to the user's query based on the search results provided. Include relevant source links if available."
                },
                {
                    "role": "user", 
                    "content": f"User Query: {text}\n\nSearch Results:\n{results_text}"
                }
            ]
        )
        
        answer = chat_completion.choices[0].message.content

        # 4. Text the Answer back to Telegram
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": answer}
        )
        print("✅ Answer sent successfully to Telegram!")

    except Exception as e:
        print(f"⚠️ Error in chatbot webhook: {e}")
        if chat_id:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": f"❌ Sorry, an error occurred while processing your request."}
            )
            
    return "OK", 200

@app.route("/")
def index():
    return "Telegram AI Research Chatbot is live and running 24/7!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
