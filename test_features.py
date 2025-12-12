
import asyncio
from unittest.mock import AsyncMock, MagicMock
from telegram import Update, User, Chat, Message
from telegram.ext import ContextTypes
import database
import reports
import messages
import main
import os
import shutil

# Mocking Telegram Object Structure
def create_mock_update(user_id=123, full_name="Test User", chat_type="group"):
    update = MagicMock(spec=Update)
    update.effective_chat.id = -100123456789
    update.effective_chat.type = chat_type
    
    user = MagicMock(spec=User)
    user.id = user_id
    user.full_name = full_name
    
    message = MagicMock(spec=Message)
    message.from_user = user
    message.message_id = 999
    
    update.message = message
    return update

def create_mock_context():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot.send_message = AsyncMock()
    context.bot.send_document = AsyncMock()
    return context

async def run_tests():
    print("--- STARTING SANDBOX TESTS ---")
    
    # Setup DB
    if os.path.exists("anganwadi.db"):
        os.remove("anganwadi.db")
    database.init_db()
    
    # 1. Test Motivation
    print("\n[TEST 1] Daily Motivation")
    context = create_mock_context()
    # Set global group ID artificially
    main.GROUP_CHAT_ID = -100123456789
    
    await main.send_morning_motivation(context)
    
    context.bot.send_message.assert_called_once()
    args = context.bot.send_message.call_args[1]
    print(f"✅ Motivation Sent: {args['text'][:50]}...")
    assert args['text'] in messages.MOTIVATIONAL_QUOTES
    
    # 2. Test Manual Report (Empty)
    print("\n[TEST 2] Manual Report (No Data)")
    update = create_mock_update()
    context = create_mock_context()
    
    await main.manual_report_handler(update, context)
    
    # Check message content
    context.bot.send_message.assert_called()
    msg_call = context.bot.send_message.call_args[1]['text']
    print(f"✅ Report Sent: \n{msg_call}")
    assert "0 सदस्यों" in msg_call
    
    # 3. Test YOLO Person Detection
    print("\n[TEST 3] Person Detection")
    # We need a real image for YOLO.
    # I will download a dummy image if one doesn't exist, or skip if offline.
    # For this sandbox, we'll try to use the user uploaded image if available
    # Path: /Users/jayantnahata/.gemini/antigravity/brain/cb82b280-24cb-4552-af11-38e17b9dd3e2/uploaded_image_1765558677835.png
    
    image_path = "/Users/jayantnahata/.gemini/antigravity/brain/cb82b280-24cb-4552-af11-38e17b9dd3e2/uploaded_image_1765558677835.png"
    
    if os.path.exists(image_path):
        print(f"Found image at {image_path}")
        
        # Mocking the photo download part is tricky because it calls get_file().download_to_drive()
        # We will mock the 'download_to_drive' to just copy our local test image to the temp path
        
        async def mock_download(path):
            shutil.copy(image_path, path)
            
        photo_obj = MagicMock()
        photo_obj.get_file = AsyncMock(return_value=MagicMock(download_to_drive=mock_download))
        
        update = create_mock_update(user_id=444, full_name="Photo User")
        update.message.photo = [photo_obj] # List of photos
        update.message.reply_text = AsyncMock()
        
        await main.photo_handler(update, context)
        
        # Verify response
        update.message.reply_text.assert_called()
        reply_args = update.message.reply_text.call_args[0][0]
        print(f"✅ Logic executed. Reply: {reply_args}")
        
        if "केवल" in reply_args and "लोग दिखाई दे रहे हैं" in reply_args:
             print("✅ WARNING TRIGGERED (Less than 5 people detected)")
        else:
             print("✅ Accepted without warning (5+ people detected)")
             
    else:
        print("⚠️ Skipping Image Test (No image found)")

    print("\n--- TESTS COMPLETED ---")

if __name__ == "__main__":
    asyncio.run(run_tests())
