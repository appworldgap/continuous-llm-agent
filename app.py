import os
from flask import Flask, request
import requests
from groq import Groq

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    chat_id = None
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
        
        # 1. Send a quick "Searching..." notice
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": f"🔍 Searching live web via Tavily: *{text}*...", "parse_mode": "Markdown"}
        )
        
        # 2. Perform Web Search via Tavily API
        results_text = ""
        try:
            tavily_resp = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": text,
                    "max_results": 5,
                    "search_depth": "advanced"
                },
                timeout=10
            )
            if tavily_resp.status_code == 200:
                tavily_data = tavily_resp.json()
                sources = tavily_data.get("results", [])
                print(f"🌐 Tavily raw results found: {len(sources)}")
                for r in sources:
                    title = r.get("title", "")
                    content = r.get("content", "")
                    url = r.get("url", "")
                    results_text += f"Title: {title}\nSnippet: {content}\nURL: {url}\n\n"
            else:
                print(f"⚠️ Tavily error status: {tavily_resp.status_code} - {tavily_resp.text}")
                results_text = "Web search returned an error."
        except Exception as e:
            print(f"⚠️ Search error exception: {e}")
            results_text = "Web search failed."

        print(f"📄 Assembled Search Context:\n{results_text[:300]}...")

        # 3. Generate Smart Response via Groq
        client = Groq(api_key=GROQ_API_KEY)
        chat_completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a live web-search assistant. You MUST answer the user's query using the provided Search Results. Include markdown links [Source Title](URL) referencing the search snippets provided. Be concise, informative, and accurate."
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
            json={"chat_id": chat_id, "text": answer, "disable_web_page_preview": True}
        )
        print("✅ Live search answer sent successfully to Telegram!")

    except Exception as e:
        print(f"⚠️ Error in chatbot webhook: {e}")
        if chat_id:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": f"❌ Error processing search: {str(e)}"}
            )
            
    return "OK", 200

@app.route("/")
def index():
    return "Telegram Tavily Search Chatbot is active!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
