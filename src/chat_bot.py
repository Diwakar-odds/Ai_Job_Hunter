"""
chat_bot.py - Two-Way Telegram Conversational Agent for AI Job Hunter.
"""

import os
import yaml
import logging
import sqlite3
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.resolve()

def load_config() -> dict:
    with open(ROOT / 'config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_resume() -> str:
    resume_path = ROOT / 'resume_knowledge.txt'
    if resume_path.exists():
        with open(resume_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "No resume provided."

def get_recent_jobs() -> str:
    """Fetch the latest 10 jobs from the local database for context."""
    db_path = ROOT / 'data' / 'jobs.db'
    if not db_path.exists():
        return "No jobs found in the database yet."
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT title, company, location, match_score, url 
            FROM jobs 
            ORDER BY found_date DESC 
            LIMIT 10
        ''')
        rows = cursor.fetchall()
        if not rows:
            return "No jobs available."
        
        jobs_text = "Recent Jobs Scraped:\n"
        for i, row in enumerate(rows):
            jobs_text += f"{i+1}. {row['title']} at {row['company']} ({row['location']}) - Score: {row['match_score']}% [Link: {row['url']}]\n"
        return jobs_text
    except Exception as e:
        logger.error(f"DB Error: {e}")
        return "Failed to load jobs from database."

# Load configuration
config = load_config()
bot_token = config['telegram']['bot_token']
gemini_api_key = config.get('ai', {}).get('gemini_api_key', '')

if not gemini_api_key or gemini_api_key == "YOUR_GEMINI_API_KEY_HERE":
    logger.error("Please add your gemini_api_key in config.yaml to use the chat bot.")
else:
    genai.configure(api_key=gemini_api_key)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! I am your AI Job Hunter Agent 🤖. "
        "Ask me about any recent jobs I've scraped, or ask me to research companies for you!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process incoming messages through Gemini API."""
    user_message = update.message.text
    chat_id = str(update.message.chat_id)
    
    # Restrict to configured chat_id for security
    allowed_chat_id = str(config['telegram'].get('chat_id', ''))
    if allowed_chat_id and chat_id != allowed_chat_id:
        await update.message.reply_text("Unauthorized user. Ignoring.")
        return

    # Send a typing action
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    resume_text = load_resume()
    recent_jobs = get_recent_jobs()

    # System PROMPT
    system_prompt = f"""
You are the "AI Job Hunter", a personal career agent for a user named Diwakar Chaurasia.
Diwakar's Profile & Resume:
{resume_text}

Latest Jobs in the Database:
{recent_jobs}

You act as a personal recruiter. The user will ask you about job openings, companies, or their profile.
Be concise, friendly, and helpful. If they ask about a company, use your knowledge to tell them about its tech stack and whether it matches Diwakar's skills.
"""

    try:
        # Load the Gemini Model
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        # Combine system prompt with user message
        prompt = f"{system_prompt}\n\nUser: {user_message}\nAI Job Hunter:"
        
        response = model.generate_content(prompt)
        reply_text = response.text
        
        await update.message.reply_text(reply_text)
    except Exception as e:
        logger.error(f"Gemini API Error: {e}")
        await update.message.reply_text(f"Oops! My AI brain hit an error: {e}")

def main() -> None:
    """Start the bot."""
    if bot_token == "YOUR_TELEGRAM_BOT_TOKEN_HERE" or not gemini_api_key:
        print("Required tokens missing in config.yaml. Please configure them.")
        return

    application = Application.builder().token(bot_token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 AI Job Hunter Chat Bot is running... Send it a message on Telegram!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
