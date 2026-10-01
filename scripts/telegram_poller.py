import os
import sys
import subprocess
import requests
from groq import Groq
from duckduckgo_search import DDGS

API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

client = Groq(api_key=API_KEY)

def get_latest_telegram_message():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    try:
        response = requests.get(url, params={"timeout": 5}).json()
        results = response.get("result", [])
        if not results:
            return None, None
            
        # Get the latest message
        latest = results[-1]
        update_id = latest["update_id"]
        message = latest.get("message", {})
        text = message.get("text", "").strip()
        chat_id = message.get("chat", {}).get("id")
        
        # Acknowledge the update so it doesn't repeat next time
        requests.get(url, params={"offset": update_id + 1})
        
        return text, chat_id
    except Exception as e:
        print(f"Error fetching telegram updates: {e}")
        return None, None

def search_web(query, max_results=4):
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

def send_completion_notification(chat_id, task_name):
    text = f"🤖 **Research Complete!**\n\nTopic: *{task_name}*\n\nYour `index.html` report has been successfully generated and published."
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id or TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})

def save_and_push_html(html_content, task_name):
    filename = "index.html"
    print(f"✍️ Saving HTML report to {filename}...")
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"])
    subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"])
    
    subprocess.run(["git", "add", filename])
    subprocess.run(["git", "commit", "-m", f"🌐 Autonomous agent generated report for: {task_name[:30]}"])
    
    result = subprocess.run(["git", "push"])
    return result.returncode == 0

def main():
    print("Checking Telegram inbox for new tasks...")
    task_prompt, chat_id = get_latest_telegram_message()
    
    if not task_prompt:
        print("📭 No new messages in Telegram. Exiting.")
        return
        
    print(f"📥 Found new task from Telegram: {task_prompt}")
    
    # 1. Perform research
    search_data = search_web(task_prompt)
    
    # 2. Generate HTML via Groq
    system_prompt = (
        "You are an expert web researcher and frontend developer. "
        "Based on the user's research task and the provided search results, "
        "generate a clean, modern, beautifully styled standalone HTML file with embedded responsive CSS. "
        "Wrap your entire HTML code inside a markdown code block starting with ```html and ending with ```."
    )
    
    user_prompt = f"Research Topic: {task_prompt}\n\nSearch Results:\n{search_data}"
    
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

    try:
        html_code = full_response.split("```html")[1].split("```")[0].strip()
    except Exception:
        html_code = f"<html><body><h1>Research Report: {task_prompt}</h1><p>{full_response}</p></body></html>"
        
    success = save_and_push_html(html_code, task_prompt)
    if success:
        send_completion_notification(chat_id, task_prompt)

if __name__ == "__main__":
    main()
