import os
import sys
import time
import subprocess
import requests
from groq import Groq
from duckduckgo_search import DDGS

API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CUSTOM_TASK = os.getenv("CUSTOM_TASK", "Latest developments in AI agents")

client = Groq(api_key=API_KEY)

def search_web(query, max_results=3):
    print(f"🔍 Searching the web for: {query}")
    results_text = ""
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=max_results)]
            for r in results:
                results_text += f"Title: {r.get('title')}\nSnippet: {r.get('body')}\nURL: {r.get('href')}\n\n"
    except Exception as e:
        print(f"Search error: {e}")
        results_text = "Web search failed or returned no results."
    return results_text

def send_notification(prompt_message):
    text = f"🤖 **Research Agent Ready!**\n\n{prompt_message}\n\nPlease reply with 'YES' to approve and commit the HTML file or 'NO' to abort."
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
                    print("✅ Human approved!")
                    return True
                elif user_text in ["NO", "N", "REJECT"]:
                    print("❌ Human rejected.")
                    return False
        except Exception as e:
            print(f"Error checking telegram: {e}")
            
        time.sleep(5)
    
    print("⏰ Timed out waiting for human input.")
    return False

def save_and_push_html(html_content):
    print("✍️ Saving HTML report and pushing to repository...")
    
    filename = "research-report.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"])
    subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"])
    
    subprocess.run(["git", "add", filename])
    subprocess.run(["git", "commit", f"-m", f"🌐 Add AI research HTML report for: {CUSTOM_TASK[:30]}"])
    
    result = subprocess.run(["git", "push"])
    if result.returncode == 0:
        print("Successfully committed and pushed HTML report!")
    else:
        print("Failed to push changes to repository.")

def run_agent():
    print(f"=== STARTING RESEARCH TASK: {CUSTOM_TASK} ===")
    
    # 1. Perform online research
    search_data = search_web(CUSTOM_TASK)
    
    # 2. Prompt LLM to synthesize research into an HTML file
    system_prompt = (
        "You are an expert web researcher and frontend developer. "
        "Based on the user's research task and the provided search results, "
        "generate a clean, beautifully styled standalone HTML file (with embedded CSS). "
        "Wrap your entire HTML code inside a markdown code block starting with ```html and ending with ```. "
        "Also include the token string: REQUIRES_DECISION somewhere in your response."
    )
    
    user_prompt = f"Task: {CUSTOM_TASK}\n\nSearch Results:\n{search_data}"
    
    print("=== LIVE MODEL THINKING & RESEARCH START ===")
    stream = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
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
        send_notification(f"The agent finished researching '{CUSTOM_TASK}' and generated an HTML report. Do you approve?")
        approved = wait_for_user_decision(timeout_minutes=10)
        if not approved:
            print("Action aborted by user.")
            sys.exit(1)
        else:
            # Extract HTML code block from response
            try:
                html_code = full_response.split("```html")[1].split("```")[0].strip()
            except Exception:
                html_code = "<html><body><h1>Research Report</h1><p>Failed to parse markdown block, but task completed.</p></body></html>"
                
            save_and_push_html(html_code)

if __name__ == "__main__":
    run_agent()
