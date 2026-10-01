import os
import sys
import time
import subprocess
import requests
from groq import Groq

API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
# Grab the dynamic task passed from the workflow input (or fallback to default)
CUSTOM_TASK = os.getenv("CUSTOM_TASK", "Analyze repository structure.")

client = Groq(api_key=API_KEY)

def send_notification(prompt_message):
    text = f"🤖 **LLM Needs Your Input!**\n\n{prompt_message}\n\nPlease reply with 'YES' to approve or 'NO' to abort."
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})

def wait_for_user_decision(timeout_minutes=10):
    print("\n[PAUSED] Waiting for human decision via Telegram...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    start_time = time.time()
    last_update_id = 0

    while (time.time() - start_time) < (timeout_minutes * 60):
        try:
            response = requests.get(url, params={"offset": last_update_id + 1, "timeout": 10}).json()
            for update in response.get("result", []):
                last_update_id = update["update_id"]
                user_text = update.get("message", {}).get("text", "").strip().upper()
                
                if user_text in ["YES", "Y", "APPROVE"]:
                    print("✅ Human approved the decision!")
                    return True
                elif user_text in ["NO", "N", "REJECT"]:
                    print("❌ Human rejected the decision.")
                    return False
        except Exception as e:
            print(f"Error checking telegram: {e}")
            
        time.sleep(5)
    
    print("⏰ Timed out waiting for human input.")
    return False

def commit_and_push_report():
    print("✍️ Creating and committing new report file...")
    
    report_content = f"# Task Execution Report\n\n**Requested Task:** {CUSTOM_TASK}\n\nThis report was generated autonomously by the LLM agent based on your custom prompt.\n"
    with open("repo-analysis.md", "w") as f:
        f.write(report_content)
        
    subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"])
    subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"])
    
    subprocess.run(["git", "add", "repo-analysis.md"])
    subprocess.run(["git", "commit", "-m", f"🤖 Agent execution: {CUSTOM_TASK[:30]}..."])
    
    result = subprocess.run(["git", "push"])
    if result.returncode == 0:
        print("Successfully committed and pushed new file to repository!")
    else:
        print("Failed to push changes to repository.")

def run_agent():
    task_prompt = f"Fulfill this engineering task for the repository: '{CUSTOM_TASK}'. Analyze what needs to be done, and if it requires creating or modifying a report/file, output the token string: REQUIRES_DECISION"
    
    print(f"=== RUNNING TASK: {CUSTOM_TASK} ===")
    print("=== LIVE MODEL THINKING START ===")
    
    stream = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": task_prompt}],
        stream=True,
    )

    full_response = ""
    for chunk in stream:
        content = chunk.choices[0].delta.content or ""
        sys.stdout.write(content)
        sys.stdout.flush()
        full_response += content

    print("\n=== LIVE MODEL THINKING END ===")

    if "REQUIRES_DECISION" in full_response:
        send_notification(f"The agent wants to execute the task: '{CUSTOM_TASK}' and update your repo. Do you approve?")
        approved = wait_for_user_decision(timeout_minutes=10)
        if not approved:
            print("Action aborted by user.")
            sys.exit(1)
        else:
            print("Proceeding with task execution...")
            commit_and_push_report()

if __name__ == "__main__":
    run_agent()
