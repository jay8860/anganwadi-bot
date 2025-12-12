import logging
import pytz
import os
import asyncio
from datetime import time
import database
import reports
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
from ultralytics import YOLO
import random
import messages

# Load environment variables
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# Silence httpx (telegram polling) logs
logging.getLogger("httpx").setLevel(logging.WARNING)

# Global variable to store the group chat ID
# In a production app, this should be stored in the database
GROUP_CHAT_ID = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("नमस्ते! मैं आंगनवाड़ी बॉट हूँ (v2.0)।\n✅ नई सुविधाएँ सक्रिय हैं।")

# Load model (globally to cache it)
# yolov8n.pt is small (6MB)
model = YOLO('yolov8n.pt')

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global GROUP_CHAT_ID
    user = update.message.from_user
    chat_id = update.effective_chat.id
    
    # Store group ID if this is a group
    if update.effective_chat.type in ['group', 'supergroup']:
        GROUP_CHAT_ID = chat_id
        
    full_name = user.full_name
    
    # --- Person Detection Start ---
    # Download photo
    photo_file = await update.message.photo[-1].get_file()
    file_path = f"temp_{user.id}.jpg"
    await photo_file.download_to_drive(file_path)
    
    # Run Inference
    # Run in thread to avoid blocking event loop
    results = await asyncio.to_thread(model, file_path, verbose=False)
    
    # Count persons (class 0)
    person_count = 0
    for r in results:
        for cls in r.boxes.cls:
            if int(cls) == 0:
                person_count += 1
                
    # Cleanup
    if os.path.exists(file_path):
        os.remove(file_path)
    # --- Person Detection End ---

    # Register/Update user
    database.add_user_if_not_exists(user.id, full_name)
    
    # Log submission
    status, streak = database.log_submission(user.id)
    
    # Reply logic
    if status == 'new_submission':
        msg = f"नमस्ते {full_name}, आपकी फोटो मिल गई है! ✅\nशानदार काम! आपकी स्ट्रीक: {streak} 🔥"
        
        # Warning if people < 5
        if person_count < 5:
            msg += f"\n\n⚠️ *चेतावनी*: फोटो में केवल {person_count} लोग दिखाई दे रहे हैं (कम से कम 5 होने चाहिए)।"
            
        await update.message.reply_text(msg, reply_to_message_id=update.message.id, parse_mode='Markdown')
        
    elif status == 'already_submitted':
        await update.message.reply_text(f"{full_name}, आपने आज की फोटो पहले ही भेज दी है। धन्यवाद! 🙏", reply_to_message_id=update.message.id)

# Scheduled Jobs
async def send_morning_motivation(context: ContextTypes.DEFAULT_TYPE):
    if GROUP_CHAT_ID:
        quote = random.choice(messages.MOTIVATIONAL_QUOTES)
        activity = random.choice(messages.PRESCHOOL_ACTIVITIES)
        
        full_msg = f"{quote}\n\n{activity}"
        
        await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=full_msg, parse_mode='Markdown')

async def send_egg_poll(context: ContextTypes.DEFAULT_TYPE):
    if GROUP_CHAT_ID:
        question = "क्या आज बच्चों को खाने में अंडे दिए गए? 🥚"
        options = ["हाँ", "नहीं", "आंगनवाड़ी में अंडे उपलब्ध नहीं"]
        await context.bot.send_poll(
            chat_id=GROUP_CHAT_ID, 
            question=question, 
            options=options, 
            is_anonymous=False
        )

async def send_stock_poll(context: ContextTypes.DEFAULT_TYPE):
    if GROUP_CHAT_ID:
        question = "📦 स्टॉक चेक: आंगनवाड़ी में आज कौन सा सामान खत्म है? (जो नहीं है उसे चुनें)"
        options = [
            "✅ सब उपलब्ध है (All Good)",
            "🍚 चावल (Rice)",
            "🥘 दाल (Dal)",
            "🛢️ तेल (Oil)",
            "🥚 अंडे (Eggs)",
            "📦 THR (Dry Ration)",
            "🧂 नमक/मसाले"
        ]
        await context.bot.send_poll(
            chat_id=GROUP_CHAT_ID,
            question=question,
            options=options,
            is_anonymous=False,
            allows_multiple_answers=True
        )

async def report_2pm(context: ContextTypes.DEFAULT_TYPE):
    if GROUP_CHAT_ID:
        count = database.get_submitted_today_count()
        msg = f"📊 *दोपहर 2 बजे की रिपोर्ट*\n\nआज अभी तक {count} सदस्यों ने अपनी गतिविधि की फोटो भेजी है।\nकृपया बाकी सदस्य भी जल्दी फोटो भेजें!"
        await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=msg, parse_mode='Markdown')

async def report_6pm(context: ContextTypes.DEFAULT_TYPE):
    if GROUP_CHAT_ID:
        # 1. Stats
        count = database.get_submitted_today_count()
        
        # 2. Performance & Awards
        awards_msg = reports.get_performance_report_text()
        
        full_msg = f"🌇 *शाम 6 बजे की फाइनल रिपोर्ट*\n\nआज कुल {count} सदस्यों ने फोटो भेजी।\n\n{awards_msg}"
        
        await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=full_msg, parse_mode='Markdown')
        
        # 3. Missing Report Excel
        file_path = reports.generate_missing_workers_excel()
        if file_path:
            await context.bot.send_document(
                chat_id=GROUP_CHAT_ID, 
                document=open(file_path, 'rb'),
                caption="📄 उन सदस्यों की सूची जिन्होंने आज फोटो नहीं भेजी।"
            )
            # Cleanup
            try:
                os.remove(file_path)
            except:
                pass
import quiz_data

# ... existing code ...

async def stock_alert_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("उपयोग: /stock [सामान] [स्थिति]\nउदाहरण: /stock चावल खत्म")
        return
        
    item = " ".join(context.args)
    user = update.message.from_user.full_name
    
    alert_msg = f"⚠️ *STOCK ALERT* ⚠️\n\n📢 *{user}* ने रिपोर्ट किया:\n🛑 *{item}*\n\nकृपया व्यवस्थापक (Admin) ध्यान दें!"
    
    # Send to group (and pin it if needed)
    msg = await update.message.reply_text(alert_msg, parse_mode='Markdown')
    try:
        await msg.pin()
    except:
        pass

async def send_vhsnd_reminder(context: ContextTypes.DEFAULT_TYPE):
    if GROUP_CHAT_ID:
        msg = (
            "💉 *कल टीकाकरण दिवस (VHSND) है!* 💉\n\n"
            "✅ क्या आपने आशा (ASHA) दीदी को सूचित कर दिया?\n"
            "✅ क्या वैक्सीन और रिकॉर्ड रजिस्टर तैयार हैं?\n\n"
            "कल सभी लाभार्थियों को समय पर बुलाएं।"
        )
        await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=msg, parse_mode='Markdown')

async def send_weekly_quiz(context: ContextTypes.DEFAULT_TYPE):
    if GROUP_CHAT_ID:
        # Pick one random question
        q_data = random.choice(quiz_data.QUIZ_QUESTIONS)
        
        await context.bot.send_poll(
            chat_id=GROUP_CHAT_ID,
            question=f"🧠 *पोषण मास्टर क्विज़* 🧠\n\n{q_data['question']}",
            options=q_data['options'],
            type='quiz',
            correct_option_id=q_data['correct_option_id'],
            explanation=q_data['explanation'],
            is_anonymous=False
        )

async def manual_quiz_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    q_data = random.choice(quiz_data.QUIZ_QUESTIONS)
    
    await context.bot.send_poll(
        chat_id=chat_id,
        question=f"🧠 *पोषण मास्टर क्विज़* 🧠\n\n{q_data['question']}",
        options=q_data['options'],
        type='quiz',
        correct_option_id=q_data['correct_option_id'],
        explanation=q_data['explanation'],
        is_anonymous=False
    )

async def manual_poll_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    # 1. Egg Poll
    await context.bot.send_poll(
        chat_id=chat_id, 
        question="क्या आज बच्चों को खाने में अंडे दिए गए? 🥚", 
        options=["हाँ", "नहीं", "आंगनवाड़ी में अंडे उपलब्ध नहीं"], 
        is_anonymous=False
    )
    
    # 2. Stock Poll
    await context.bot.send_poll(
        chat_id=chat_id,
        question="📦 स्टॉक चेक: आंगनवाड़ी में आज कौन सा सामान खत्म है? (जो नहीं है उसे चुनें)",
        options=[
            "✅ सब उपलब्ध है (All Good)",
            "🍚 चावल (Rice)",
            "🥘 दाल (Dal)",
            "🛢️ तेल (Oil)",
            "🥚 अंडे (Eggs)",
            "📦 THR (Dry Ration)",
            "🧂 नमक/मसाले"
        ],
        is_anonymous=False,
        allows_multiple_answers=True
    )

async def manual_report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    # 1. Stats
    count = database.get_submitted_today_count()
    
    # 2. Performance & Awards
    awards_msg = reports.get_performance_report_text()
    
    full_msg = f"📊 *मैनुअल रिपोर्ट (अभी तक)*\n\nआज कुल {count} सदस्यों ने फोटो भेजी।\n\n{awards_msg}"
    
    await context.bot.send_message(chat_id=chat_id, text=full_msg, parse_mode='Markdown')
    
    # 3. Missing Report Excel
    file_path = reports.generate_missing_workers_excel()
    if file_path:
        await context.bot.send_document(
            chat_id=chat_id, 
            document=open(file_path, 'rb'),
            caption="📄 उन सदस्यों की सूची जिन्होंने आज फोटो नहीं भेजी।"
        )
        # Cleanup
        try:
            os.remove(file_path)
        except:
            pass

def main():
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env file")
        return

    # Initialize DB
    database.init_db()
    
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("report", manual_report_handler))
    application.add_handler(CommandHandler("stock", stock_alert_handler))
    application.add_handler(CommandHandler("poll", manual_poll_handler))
    application.add_handler(CommandHandler("quiz", manual_quiz_handler))
    # Handles photos
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    # Update group ID on any text message too
    async def update_group_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
        global GROUP_CHAT_ID
        if update.effective_chat.type in ['group', 'supergroup']:
            GROUP_CHAT_ID = update.effective_chat.id
            
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), update_group_id))

    # Job Queue
    job_queue = application.job_queue
    
    # Timezone: IST (Asia/Kolkata)
    tz = pytz.timezone('Asia/Kolkata')
    
    # 8:00 AM IST - Daily Motivation + Activities
    job_queue.run_daily(send_morning_motivation, time(hour=8, minute=0, tzinfo=tz))

    # 12:00 PM IST (Saturday Only) - Quiz
    # days=(5,) means Saturday (Mon=0)
    job_queue.run_daily(send_weekly_quiz, time(hour=12, minute=0, tzinfo=tz), days=(5,))

    # 2:00 PM IST
    job_queue.run_daily(report_2pm, time(hour=14, minute=0, tzinfo=tz)) 
    
    # 3:00 PM IST - Egg Poll
    job_queue.run_daily(send_egg_poll, time(hour=15, minute=0, tzinfo=tz))

    # 3:00 PM IST - Stock Poll
    job_queue.run_daily(send_stock_poll, time(hour=15, minute=0, tzinfo=tz))
    
    # 6:00 PM IST - Final Report
    job_queue.run_daily(report_6pm, time(hour=18, minute=0, tzinfo=tz))

    # 6:00 PM IST (Tuesday Only) - VHSND Reminder
    # days=(1,) means Tuesday
    job_queue.run_daily(send_vhsnd_reminder, time(hour=18, minute=0, tzinfo=tz), days=(1,))
    
    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
