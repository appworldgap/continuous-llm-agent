import os
import sys
import subprocess
import requests
from groq import Groq
from duckduckgo_search import DDGS

API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CUSTOM_TASK = os.getenv("CUSTOM_TASK", "Latest developments in AI agents")

client = Groq(api_key=API_KEY)

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

def send_completion_notification(task_name, filename):
    text = f"🤖 **Autonomous Agent Task Completed!**\n\nTask: *{task_name}*\n\nGenerated and pushed: `{filename}` directly to your repository."
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})

def save_and_push_html(html_content):
    # Create a unique filename based on timestamp or task name slug
    filename = "index.html" # Set to index.html so GitHub Pages can host it instantly!
    print(f"✍️ Saving HTML report to {filename} and pushing to repository...")
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"])
    subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"])
    
    subprocess.run(["git", "add", filename])
    subprocess.run(["git", "commit", "-m", f"🌐 Autonomous agent generated report for: {CUSTOM_TASK[:30]}"])
    
    result = subprocess.run(["git", "push"])
    if result.returncode == 0:
        print("Successfully committed and pushed HTML report!")
        return True
    else:
        print("Failed to push changes to repository.")
        return False

def run_agent():
    print(f"=== STARTING AUTONOMOUS RESEARCH TASK: {CUSTOM_TASK} ===")
    
    # 1. Perform online research
    search_data = search_web(CUSTOM_TASK)
    
    # 2. Prompt LLM to synthesize research into a standalone HTML file
    system_prompt = (
        "You are an expert web researcher and frontend developer. "
        "Based on the user's research task and the provided search results, "
        "generate a clean, modern, beautifully styled standalone HTML file with embedded responsive CSS. "
        "Make it look professional, like a polished publication or dashboard. "
        "Wrap your entire HTML code inside a markdown code block starting with ```html and ending with ```. "
        "Do not include any conversational filler outside the code block."
    )
    
    user_prompt = f"Research Topic: {CUSTOM_TASK}\n\nSearch Results:\n{search_data}"
    
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

    # Extract HTML code block from response
    try:
        html_code = full_response.split("```html")[1].split("```")[0].strip()
    except Exception:
        # Fallback if markdown block is missing
        html_code = f"<html><body><h1>Research Report: {CUSTOM_TASK}</h1><p>{full_response}</p></body></html>"
        
    # Automatically save and push without stopping
    success = save_and_push_html(html_code)
    if success:
        send_completion_notification(CUSTOM_TASK, "index.html")

if __name__ == "__main__":
    run_agent()
