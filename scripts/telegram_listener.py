import os
import time
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = "appworldgap"  # Your GitHub username/org
REPO_NAME = "continuous-llm-agent"  # Your repository name
WORKFLOW_FILE = "live-llm.yml"  # Your workflow filename

def trigger_github_workflow(task_prompt):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{WORKFLOW_FILE}/dispatches"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    payload = {
        "ref": "main",
        "inputs": {
            "task_prompt": task_prompt
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.status_code == 204

def start_listener():
    print("🤖 Telegram Listener is active and waiting for your commands...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    last_update_id = 0

    while True:
        try:
            response = requests.get(url, params={"offset": last_update_id + 1, "timeout": 30}).json()
            for update in response.get("result", []):
                last_update_id = update["update_id"]
                message = update.get("message", {})
                text = message.get("text", "").strip()
                
                if text:
                    print(f"📥 Received message from Telegram: {text}")
                    
                    # If message starts with /research or any text, trigger the agent
                    success = trigger_github_workflow(text)
                    
                    chat_id = message.get("chat", {}).get("id")
                    if success:
                        reply = f"🚀 Triggered GitHub Agent for your task: *{text}*. It's researching and building your HTML now!"
                    else:
                        reply = "❌ Failed to trigger GitHub workflow. Check API tokens."
                        
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                        json={"chat_id": chat_id, "text": reply, "parse_mode": "Markdown"}
                    )
        except Exception as e:
            print(f"Error in listener loop: {e}")
            
        time.sleep(5)

if __name__ == "__main__":
    start_listener()
