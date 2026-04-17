import logging
import time
import uuid
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from pyrogram.types import MessageEntity
from pyrogram.enums import MessageEntityType
from config import Config

from config import Config
from core.state import active_verifications
from core.security import generate_secure_token, verify_time_gap, is_expired
from core.shortener_api import get_short_link
#from core.firebase_db import save_token_to_firebase
from core.firebase_db import claim_pregenerated_token
from core.database import db

# Main /start command handler
@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    args = message.command
    await db.add_user(
        message.from_user.id, 
        message.from_user.first_name, 
        message.from_user.username
    )
    active_shorteners = await db.get_all_shorteners()
    
    # --- 1. Main Menu (No deep-link arguments) ---
    if len(args) == 1:
        main_url = await db.get_main_url()
        how_to_use_url = await db.get_how_to_use_url()
        dev_url = Config.DEVELOPER_URL
        if not how_to_use_url or not how_to_use_url.startswith("http"):
            how_to_use_url = "https://t.me/telegram"
            
        buttons = [
            [InlineKeyboardButton("📖 How to USE", url=how_to_use_url)],
            [
                InlineKeyboardButton("🔑 Generate TOKEN", url="https://t.me/gentokenRJbot?start=app_studyingredients"),
                InlineKeyboardButton("👨‍💻 Developer", url=dev_url)
            ],
            [InlineKeyboardButton("💬 Main group", url=main_url)]
        ]
        
        # 1. Fetch custom config from MongoDB
        welcome_config = await db.settings.find_one({"_id": "welcome_settings"})
        
        if welcome_config and welcome_config.get("text"):
            start_text = welcome_config.get("text")
            image_id = welcome_config.get("image_id")
            saved_entities = welcome_config.get("entities", [])
            
            # DESERIALIZATION: Rebuild the MongoDB dict back into Pyrogram Entity objects
            reply_entities = []
            for e in saved_entities:
                try:
                    reply_entities.append(
                        MessageEntity(
                            type=MessageEntityType[e["type"]],
                            offset=e["offset"],
                            length=e["length"],
                            url=e.get("url"),
                            custom_emoji_id=e.get("custom_emoji_id")
                        )
                    )
                except Exception:
                    continue # Skip safely if something goes wrong
                    
            # Send using NATIVE ENTITIES instead of HTML
            if image_id:
                await message.reply_photo(
                    photo=image_id,
                    caption=start_text,
                    caption_entities=reply_entities,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            else:
                await message.reply_text(
                    text=start_text,
                    entities=reply_entities,
                    disable_web_page_preview=True,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
                
        else:
            # Fallback default text (Only uses HTML if no custom message is saved)
            start_text = (
                "✨ <b>Welcome to the Study Ingredients Token Generator!</b> ✨\n\n"
                "I am your automated bridge for secure, token-based authentication.\n\n"
                "👇 <i>/help to know more</i>"
            )
            await message.reply_text(
                text=start_text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        return

    payload = args[1]

    # --- 2. App Workflow Initiation (/start app_appname) ---
    if payload.startswith("app_"):
        appname = payload.split("app_")[1]
        
        buttons = []
        server_row = []
        # DYNAMICALLY ADD APP SERVER BUTTONS
        for s in active_shorteners:
            # We pass both the shortener ID and the appname in the callback
            server_row.append(InlineKeyboardButton(f" 🔑{s['name']}", callback_data=f"app_gen_{s['_id']}_{appname}"))
            
        if server_row:
            buttons.extend([server_row[i:i+2] for i in range(0, len(server_row), 2)])
        else:
            await message.reply_text("Admin hasn't configured any verification servers yet.")
            return

        await message.reply_text(
            "**Verification Required**\n\n"
            "Please select a verification server below. Once completed, your token will be generated.",
            reply_markup=InlineKeyboardMarkup(buttons)
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


        if session_data["flow_type"] == "app":
            print("🟢 VERIFY: Passed time gap, claiming token...")
            try:
                # Fetch the token instead of generating one
                token, error_msg = claim_pregenerated_token(session_data["telegram_user_id"])
                print(f"🟢 VERIFY: Token claimed -> {token}")
                
                if token:
                    print("🟢 VERIFY: Fetching custom message from MongoDB...")
                    token_config = await db.settings.find_one({"_id": "token_msg_settings"})
                    
                    if token_config and token_config.get("text"):
                        print("🟢 VERIFY: Custom message found, replacing {token}...")
                        base_text = token_config.get("text")
                        app_success_text = base_text.replace("{token}", token)
                        token_image_id = token_config.get("image_id")
                    else:
                        print("🟢 VERIFY: No custom message, using default...")
                        app_success_text = (
                            "🎉 <b>VERIFICATION SUCCESSFUL</b> 🎉\n"
                            "━━━━━━━━━━━━━━━━━━━━━━\n"
                            "Your secure session has been verified, and your one-time access token is ready.\n\n"
                            "🔑 <b>Your Access Token:</b>\n"
                            f"👉 <code>{token}</code> 👈\n"
                            "*(Tap the token above to copy it instantly)*\n\n"
                            "⏱ <b>Status:</b> Active & Assigned\n"
                            "🛡 <b>Security:</b> One-Time Use Only\n\n"
                            "📱 <i>You may now return to the app, paste this token, and click Verify!</i>"
                        )
                        token_image_id = None

                    print("🟢 VERIFY: Attempting to send message to user...")
                    from pyrogram.enums import ParseMode
                    
                    if token_image_id:
                        await message.reply_photo(
                            photo=token_image_id, 
                            caption=app_success_text, 
                            parse_mode=ParseMode.HTML
                        )
                    else:
                        await message.reply_text(
                            text=app_success_text, 
                            parse_mode=ParseMode.HTML
                        )
                    print("✅ VERIFY: Message sent successfully!")
                    
                else:
                    print(f"🔴 VERIFY: No tokens left! Error: {error_msg}")
                    await message.reply_text(
                        f"⚠️ **Verification passed, but our database is empty!**\n\n"
                        f"There are no tokens left to dispense. Please contact the administrator.\n"
                        f"*(System error: {error_msg})*"
                    )
                    
            except Exception as e:
                # IF THE BOT CHOKES, IT WILL SCREAM THE EXACT REASON RIGHT HERE
                print(f"🔥 MASSIVE CRASH IN TOKEN DELIVERY: {str(e)}")
                await message.reply_text(f"❌ **System crashed while delivering token:**\n`{str(e)}`")
        
        # --- COMMENTED CODE FOR FUTURE REFERENCE ---
        # Checks passed! Generate the 16-digit cryptographic Token
        # token = generate_secure_token(16)
        # 
        # # Route the success logic based on the flow_type
        # if session_data["flow_type"] == "app":
        #     # Save to Firebase
        #     success = save_token_to_firebase(
        #         session_data["appname"], 
        #         session_data["telegram_user_id"], 
        #         token
        #     )
        #     if success:
        #         app_success_text = (
        #             "🎉 **VERIFICATION SUCCESSFUL** 🎉\n"
        #             "━━━━━━━━━━━━━━━━━━━━━━\n"
        #             "Your secure STUDY INGREDIENTS session has been verified, and your one-time access token is ready.\n\n"
        #             "🔑 **Your Access Token:**\n"
        #             f"👉 `{token}` 👈\n"
        #             "*(Tap the token above to copy it instantly)*\n\n"
        #             "⏱ **Status:** Active & Synced\n"
        #             "🛡 **Security:** One-Time Use Only\n\n"
        #             "📱 *You may now return to the app, paste this token, and click Verify!*"
        #         )
        #         await message.reply_text(app_success_text)
        #     else:
        #         await message.reply_text("⚠️ **Verification passed**, but we failed to sync with the database. Please try again.")
        
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
                logging.error(f"🔥 LOG CHANNEL CRASH: {str(e)}", exc_info=True)
                await message.reply_text(f"Verification passed! Token: `{token}`\n*(Failed to log to channel. Ensure the bot is an admin there).*")
                
        # Cleanup the temporary session state
        del active_verifications[verify_id]


# --- 4. Callback Query Handler for the Inline Menu Buttons ---
@Client.on_callback_query(filters.regex("^(show_demo_servers|demo_gen_|app_gen_|help_usage|main_menu_return)"))
async def callback_handler(client: Client, query: CallbackQuery):
    data = query.data
    # --- RETURN TO MAIN MENU ---
    if data == "main_menu_return":
        main_url = await db.get_main_url()
        dev_url = Config.DEVELOPER_URL
        
        buttons = [
            [InlineKeyboardButton("📢 TOKEN Channel", url=Config.JOIN_CHANNEL_URL)],
            [
                InlineKeyboardButton("🔑 Generate Key", callback_data="show_demo_servers"),
                InlineKeyboardButton("👨‍💻 Developer", url=dev_url)
            ],
            [InlineKeyboardButton("💬 Main group", url=main_url)]
        ]
        
        start_text = (
            "✨ **Welcome to the Secure Token Generator!** ✨\n\n"
            "I am your automated bridge for secure, token-based authentication.\n\n"
            "**What I do:**\n"
            "🔹 Generate cryptographic access tokens.\n"
            "🔹 Protect links with anti-bypass timers.\n"
            "🔹 Sync real-time with your app database.\n\n"
            "👇 */help to know more*"
        )

        await query.message.edit_text(start_text, reply_markup=InlineKeyboardMarkup(buttons))
        return

    # --- SHOW DEMO SERVERS SUBMENU ---
    elif data == "show_demo_servers":
        active_shorteners = await db.get_all_shorteners()
        
        server_row = []
        for s in active_shorteners:
            server_row.append(InlineKeyboardButton(f"🔑 {s['name']}", callback_data=f"demo_gen_{s['_id']}"))
        
        buttons = []
        if server_row:
            # This creates the 2-column layout you asked for!
            buttons.extend([server_row[i:i+2] for i in range(0, len(server_row), 2)])
        else:
            buttons.append([InlineKeyboardButton("⚠️ No Servers Configured", callback_data="help_usage")])
            
        buttons.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu_return")])
        
        await query.message.edit_text(
            "**Server Selection**\n\n"
            "Please select a server below to generate your token:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
    
    elif data == "help_usage":
        await query.answer("Click any Server to test the demo verification flow!", show_alert=True)
        return
        
    # Handle dynamic link generation
    if data.startswith("demo_gen_") or data.startswith("app_gen_"):
        await query.answer("Generating your secure link, please wait...", show_alert=False) 
        
        # Parse the callback data
        parts = data.split("_")
        flow_type = "demo" if data.startswith("demo_gen_") else "app"
        shortener_id = parts[2]
        
        # Fetch the specific shortener credentials from MongoDB
        shorteners = await db.get_all_shorteners()
        selected_server = next((s for s in shorteners if str(s["_id"]) == shortener_id), None)
        
        if not selected_server:
            await query.message.edit_text("Error: This server is no longer available.")
            return

        verify_id = f"verify_{uuid.uuid4().hex}"
        
        # Save state 
        session_data = {
            "telegram_user_id": query.from_user.id,
            "start_time": time.time(),
            "flow_type": flow_type
        }
        if flow_type == "app":
            session_data["appname"] = parts[3] # Get appname from the callback
            
        active_verifications[verify_id] = session_data
        
        bot_username = (await client.get_me()).username
        long_url = f"https://t.me/{bot_username}?start={verify_id}"
        
        # Call the dynamically selected API
        short_url = get_short_link(selected_server["api_url"], selected_server["api_key"], long_url)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"Go to {selected_server['name']}", url=short_url)],
            [InlineKeyboardButton("🔙 Back to Servers", callback_data="main_menu_return")]
        ])
        
        await query.message.edit_text(
            f"**{selected_server['name']} Link Generated**\n\n"
            "⚠️ **IMPORTANT:** When you click the link below, if it opens inside Telegram, tap the **three dots (⋮)** in the top right corner and select **'Open in browser'**.\n\n"
            "Click below to pass through the shortener.",
            reply_markup=keyboard
        )

   