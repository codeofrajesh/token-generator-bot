import time
import uuid
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config

from config import Config
from core.state import active_verifications
from core.security import generate_secure_token, verify_time_gap, is_expired
from core.shortener_api import get_short_link
from core.firebase_db import save_token_to_firebase

# Main /start command handler
@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    args = message.command
    
    # --- 1. Main Menu (No deep-link arguments) ---
    if len(args) == 1:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Join Channel", url=Config.JOIN_CHANNEL_URL)], 
            [
                InlineKeyboardButton("How to use", callback_data="help_usage"),
                InlineKeyboardButton("Generate Key", callback_data="demo_generate")
            ]
        ])
        start_text = (
            "✨ **Welcome to the Secure Token Generator!** ✨\n\n"
            "I am your automated bridge for secure, token-based authentication.\n\n"
            "**What I do:**\n"
            "🔹 Generate cryptographic access tokens.\n"
            "🔹 Protect links with anti-bypass timers.\n"
            "🔹 Sync real-time with your app database.\n\n"
            "👇 */help to know more*"
        )
        
        await message.reply_text(
            start_text,
            reply_markup=keyboard
        )
        return

    payload = args[1]

    # --- 2. App Workflow Initiation (/start app_User123) ---
    if payload.startswith("app_"):
        app_user_id = payload
        verify_id = f"verify_{uuid.uuid4().hex}"
        
        # Save state locally while they navigate the shortener
        active_verifications[verify_id] = {
            "telegram_user_id": message.from_user.id,
            "start_time": time.time(),
            "flow_type": "app",
            "app_user_id": app_user_id
        }
        
        # Generate the return link and shorten it
        bot_username = (await client.get_me()).username
        long_url = f"https://t.me/{bot_username}?start={verify_id}"
        short_url = get_short_link(long_url)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Verify to Continue", url=short_url)]
        ])
        await message.reply_text(
            "Please click the button below, complete the verification, and you will be redirected back here with your token.",
            reply_markup=keyboard
        )
        return

    # --- 3. Verification Return (/start verify_abc123) ---
    if payload.startswith("verify_"):
        verify_id = payload
        
        # Check if a valid session exists
        if verify_id not in active_verifications:
            await message.reply_text("Invalid or expired verification session. Please generate a new link.")
            return
            
        session_data = active_verifications[verify_id]
        
        # Security Check: Expiry (10 mins)
        if is_expired(session_data["start_time"], max_validity_minutes=10):
            del active_verifications[verify_id]
            await message.reply_text("This verification link has expired (10-minute limit). Please request a new one.")
            return
            
        # Security Check: Anti-Bypass Time Gap
        if not verify_time_gap(session_data["start_time"], Config.MIN_BYPASS_TIME):
            del active_verifications[verify_id]
            await message.reply_text("Bypass detected! You completed the link suspiciously fast. Verification failed.")
            return
            
        # Checks passed! Generate the 16-digit cryptographic Token
        token = generate_secure_token(16)
        
        # Route the success logic based on the flow_type
        if session_data["flow_type"] == "app":
            # Save to Firebase
            success = save_token_to_firebase(session_data["app_user_id"], token)
            if success:
                app_success_text = (
                    "🎉 **VERIFICATION SUCCESSFUL** 🎉\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "Your secure session has been verified, and your one-time access token is ready.\n\n"
                    "🔑 **Your Access Token:**\n"
                    f"👉 `{token}` 👈\n"
                    "*(Tap the token above to copy it instantly)*\n\n"
                    "⏱ **Status:** Active & Synced\n"
                    "🛡 **Security:** One-Time Use Only\n\n"
                    "📱 *You may now return to the app, paste this token, and click Verify!*"
                )
                await message.reply_text(app_success_text)
            else:
                await message.reply_text("⚠️ **Verification passed**, but we failed to sync with the database. Please try again.")

        elif session_data["flow_type"] == "demo":
            # Send to Telegram Log Channel
            log_text = (
                f"🆕 **Demo Token Generated**\n"
                f"👤 User: {message.from_user.mention} (`{message.from_user.id}`)\n"
                f"🔑 Token: `{token}`\n"
                f"⏱ Valid for: 10 minutes"
            )
            try:
                await client.send_message(Config.LOG_CHANNEL_ID, log_text)
                
                demo_success_text = (
                    "🧪 **DEMO VERIFICATION SUCCESSFUL** 🧪\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "You have successfully completed the demo workflow!\n\n"
                    "🔑 **Demo Token:**\n"
                    f"👉 `{token}` 👈\n"
                    "*(Tap to copy)*\n\n"
                    "📡 **Status:** Logged to Admin Channel\n"
                    "⚠️ **Note:** *This is a test token and is NOT synced to the app database.*\n\n"
                    "Thank you for testing the system!"
                )
                await message.reply_text(demo_success_text)
            except Exception as e:
                await message.reply_text(f"Verification passed! Token: `{token}`\n*(Failed to log to channel. Ensure the bot is an admin there).*")
                
        # Cleanup the temporary session state
        del active_verifications[verify_id]


# --- 4. Callback Query Handler for the Inline Menu Buttons ---
@Client.on_callback_query(filters.regex("^(help_usage|demo_generate)$"))
async def callback_handler(client: Client, query: CallbackQuery):
    data = query.data
    
    if data == "help_usage":
        # Shows a pop-up alert inside Telegram
        await query.answer(
            "Click 'Generate Key' to test the demo verification flow. For app users, the process starts automatically inside the app!", 
            show_alert=True
        )
        
    elif data == "demo_generate":
        await query.answer("Generating your secure link, please wait...", show_alert=False) 
        
        verify_id = f"verify_{uuid.uuid4().hex}"
        active_verifications[verify_id] = {
            "telegram_user_id": query.from_user.id,
            "start_time": time.time(),
            "flow_type": "demo"
        }
        
        bot_username = (await client.get_me()).username
        long_url = f"https://t.me/{bot_username}?start={verify_id}"
        
        short_url = get_short_link(long_url)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Verify (Demo)", url=short_url)],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu_return")]
        ])
        await query.message.edit_text(
            "**Demo Mode Initiated**\n\n"
            "⚠️ **IMPORTANT:** When you click the link below, if it opens inside Telegram, tap the **three dots (⋮)** in the top right corner and select **'Open in browser'** (like Chrome). Otherwise, it might get stuck at the end!\n\n"
            "Click below to pass through the shortener. Once verified, return here for your token.",
            reply_markup=keyboard
        )
        
@Client.on_callback_query(filters.regex("^main_menu_return$"))
async def return_to_main_menu(client: Client, callback_query):
    # This recreates the main menu from your start_handler
    from config import Config
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Join Channel", url=Config.JOIN_CHANNEL_URL)], 
        [
            InlineKeyboardButton("How to use", callback_data="help_usage"),
            InlineKeyboardButton("Generate Key", callback_data="demo_generate")
        ]
    ])
    
    await callback_query.message.edit_text(
        "Welcome back to the Token Generator Bot!\n\nPlease select an option below:",
        reply_markup=keyboard
    )        