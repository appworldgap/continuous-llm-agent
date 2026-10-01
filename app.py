import os
from flask import Flask, request
import requests

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = "appworldgap"
REPO_NAME = "continuous-llm-agent"
WORKFLOW_FILE = "live-llm.yml"

@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    try:
        update = request.get_json()
        print(f"📥 Received raw update: {update}")
        
        # Safely extract message text (handles standard messages or channel posts)
        message = update.get("message") or update.get("edited_message")
        if not message:
            return "OK", 200
            
        text = message.get("text", "").strip()
        chat = message.get("chat", {})
        chat_id = chat.get("id")
        
        if text and chat_id:
            print(f"💬 Extracted text: '{text}' for chat_id: {chat_id}")
            
            # Trigger GitHub Actions workflow
            url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{WORKFLOW_FILE}/dispatches"
            headers = {
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
            payload = {
                "ref": "main",
                "inputs": {
                    "task_prompt": text
                }
            }
            res = requests.post(url, json=payload, headers=headers)
            
            if res.status_code == 204:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={"chat_id": chat_id, "text": f"🚀 Instant agent triggered for: *{text}*!", "parse_mode": "Markdown"}
                )
            else:
                print(f"❌ Failed to trigger GitHub: {res.status_code} - {res.text}")
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={"chat_id": chat_id, "text": f"❌ Failed to trigger GitHub Actions. Check tokens."}
                )
    except Exception as e:
        print(f"⚠️ Error handling webhook: {e}")
        
    return "OK", 200

@app.route("/")
def index():
    return "Telegram-to-GitHub Webhook is alive and running 24/7!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
