import os
import requests
import mmap
import hashlib
import cloudscraper
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pyrogram import Client, filters
from pyromod import listen

# --- DUMMY SERVER FOR KOYEB HEALTH CHECK ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running!")

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- BOT CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", 12345))
API_HASH = os.environ.get("API_HASH", "your_hash")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_token")

scraper = cloudscraper.create_scraper()
app = Client("test_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ----------------- MODERN HTML UI GENERATOR ----------------- #
def json_to_html(json_url, title, created_by):
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ background: #f4f7fa; font-family: sans-serif; padding-bottom: 80px; }}
        .navbar {{ background: #1e293b; color: white; padding: 15px; position: sticky; top: 0; z-index: 100; }}
        .q-card {{ background: white; border-radius: 12px; padding: 25px; margin: 20px auto; max-width: 800px; border: 1px solid #e2e8f0; }}
        .option {{ border: 2px solid #e2e8f0; padding: 12px; border-radius: 8px; margin-bottom: 10px; cursor: pointer; }}
        .option.selected {{ border-color: #007bff; background: #e7f1ff; }}
        .footer {{ position: fixed; bottom: 0; width: 100%; background: white; padding: 15px; border-top: 1px solid #ddd; display: flex; justify-content: space-around; }}
    </style>
</head>
<body>
    <div class="navbar"><b>{title}</b></div>
    <div id="content"></div>
    <div class="footer">
        <button class="btn btn-secondary" onclick="move(-1)">Back</button>
        <button class="btn btn-primary" onclick="move(1)">Next</button>
    </div>
    <script>
        let questions = []; let curr = 0;
        async function load() {{
            const r = await fetch('{json_url}'); const d = await r.json();
            questions = Array.isArray(d) ? d : (d.data || []); render();
        }}
        function render() {{
            const q = questions[curr];
            document.getElementById('content').innerHTML = `
                <div class="q-card">
                    <h5>Question ${{curr+1}}</h5>
                    <p>${{q.question}}</p>
                    <div class="option">${{q.option_1}}</div>
                    <div class="option">${{q.option_2}}</div>
                    <div class="option">${{q.option_3}}</div>
                    <div class="option">${{q.option_4}}</div>
                </div>`;
        }}
        function move(s) {{ curr += s; if(curr>=0 && curr<questions.length) render(); }}
        load();
    </script>
</body>
</html>"""

# ----------------- BOT LOGIC ----------------- #
@app.on_message(filters.command("test"))
async def test_handler(bot, msg):
    try:
        api_url = (await bot.ask(msg.chat.id, "🔗 **Send API URL:**")).text.strip()
        creator = (await bot.ask(msg.chat.id, "👤 **Send Creator Name:**")).text.strip()
        
        headers = {{"Client-Service": "Appx", "Auth-Key": "appxapi", "source": "website"}}
        res = scraper.post(f"https://{{api_url}}/get/search", headers=headers, json={{"search_term": "TEST SERIES", "user_id": "-1"}}).json()
        courses = res.get("courses_with_folder", [])
        
        if not courses: return await msg.reply("No courses found.")
        
        c_list = "\\n".join([f"{{i+1}}. {{c['course_name']}}" for i, c in enumerate(courses)])
        idx = int((await bot.ask(msg.chat.id, f"📚 **Select Index:**\\n\\n{{c_list}}")).text) - 1
        
        course_id = courses[idx]['id']
        f_url = f"https://{{api_url}}/get/folder_contentsv3?course_id={{course_id}}&parent_id=-1"
        items = scraper.get(f_url, headers=headers).json().get("data", [])

        for item in items:
            if item.get("material_type") == "TEST":
                q_id = item.get("quiz_title_id")
                det = scraper.get(f"https://{{api_url}}/get/test_title_by_id?id={{q_id}}&userid=-1", headers=headers).json().get("data", {{}})
                title, url = det.get("title"), det.get("test_questions_url")
                if title and url:
                    fname = f"{{title.replace(' ', '_')}}.html"
                    with open(fname, "w", encoding="utf-8") as f: f.write(json_to_html(url, title, creator))
                    await bot.send_document(msg.chat.id, fname)
                    os.remove(fname)
        await msg.reply("✅ Done!")
    except Exception as e: await msg.reply(f"❌ Error: {{e}}")

# ----------------- MAIN EXECUTION ----------------- #
if __name__ == "__main__":
    # Start Health Check Server in a separate thread
    threading.Thread(target=run_health_server, daemon=True).start()
    print("Health Check Server started.")
    app.run()