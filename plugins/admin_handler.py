from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
import os
import re
from pyrogram.errors import BadRequest
from core.database import db
from core.firebase_db import db as fdb
import asyncio
import io

admin_states = {}

@Client.on_message(filters.command("admincmd") & filters.private)
async def admin_panel(client: Client, message: Message):
    is_coadmin = await db.is_coadmin(message.from_user.id)
    if message.from_user.id not in Config.ADMIN_IDS and not is_coadmin:
        return
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Add Shortener", callback_data="admin_add_shortener"),
            InlineKeyboardButton("➖ Remove Shortener", callback_data="admin_remove_shortener")
        ],
        [
            InlineKeyboardButton("🔥 Update Firebase", callback_data="admin_update_firebase"),
            InlineKeyboardButton("⏱ Edit Bypass Time", callback_data="admin_edit_bypass")
        ],
        [   InlineKeyboardButton("📞 Edit Main URL", callback_data="admin_edit_main"),
            InlineKeyboardButton("📖 Edit How To Use", callback_data="admin_edit_howtouse")
        ],
        [
            InlineKeyboardButton("❌ Close Panel", callback_data="admin_close")
        ]
    ])
    
    await message.reply_text(
        "🛠 **Admin Control Panel** 🛠\n\n"
        "Welcome, Boss. What would you like to configure today?",
        reply_markup=keyboard
    )

@Client.on_callback_query(filters.regex("^admin_"))
async def admin_callbacks(client: Client, query: CallbackQuery):
    try:    
        print(f"🔘 ADMIN BUTTON CLICKED: {query.data} by User {query.from_user.id}")
        data = query.data
        admin_id = query.from_user.id
        is_coadmin = await db.is_coadmin(admin_id)
        if admin_id not in Config.ADMIN_IDS and not is_coadmin:
            return
        
        if data == "admin_close":
            await query.message.delete()
            
        elif data == "admin_add_shortener":
            # We set the admin's state so the bot knows their next message is an API URL
            admin_states[admin_id] = {"action": "waiting_for_shortener_url"}
            await query.message.edit_text(
                "**Add New Shortener**\n\n"
                "Please send me the **API URL** of the shortener (e.g., `https://gplinks.in/api`).\n\n"
                "Type `cancel` to abort."
            )
            
        elif data == "admin_edit_bypass":
            admin_states[admin_id] = {"action": "waiting_for_bypass_time"}
            await query.message.edit_text(
                "**Edit Bypass Time**\n\n"
                "Enter the new minimum bypass time in **seconds** (e.g., `15`).\n\n"
                "Type `cancel` to abort."
            )

        elif data == "admin_remove_shortener":
            # Fetch active shorteners from MongoDB
            shorteners = await db.get_all_shorteners()
            
            if not shorteners:
                await query.answer("No shorteners configured yet!", show_alert=True)
                return


            buttons = []
            for s in shorteners:
                # We pass the MongoDB document _id in the callback data so we know exactly which one to delete
                short_id = str(s['_id'])
                buttons.append([InlineKeyboardButton(f"🗑 {s['name']}", callback_data=f"del_short_{short_id}")])
                
            buttons.append([InlineKeyboardButton("🔙 Cancel", callback_data="admin_close")])
            
            await query.message.edit_text(
                "**Remove a Shortener**\n\n"
                "Tap a shortener below to permanently delete it from the rotation:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            
        elif data.startswith("del_short_"):
            # The admin clicked a specific shortener to delete
            short_id = data.split("del_short_")[1]
            
            await db.remove_shortener(short_id)
            await query.answer("✅ Shortener removed successfully!", show_alert=True)
            await query.message.edit_text("Shortener deleted. Send `/admincmd` to open the panel again.")

        elif data == "admin_update_firebase":
            # Set the state so the bot expects a file next
            admin_states[admin_id] = {"action": "waiting_for_firebase_json"}
            await query.message.edit_text(
                "🔥 **Update Firebase Credentials**\n\n"
                "Step 1: Please send me the new `serviceAccountKey.json` file as a **Document**.\n\n"
                "Type `cancel` to abort."
            )

        elif data == "admin_edit_main":
            admin_states[admin_id] = {"action": "waiting_for_main_url"}
            await query.message.edit_text(
                "🔧 **Edit Main URL**\n\n"
                "Please send me the new **Main URL** (e.g., `https://t.me/telegram`).\n\n"
                "Type `cancel` to abort."
            )

        elif data == "admin_edit_howtouse":
            admin_states[admin_id] = {"action": "waiting_for_how_to_use_url"}
            await query.message.edit_text(
                "📖 **Edit 'How To USE' Link**\n\n"
                "Please send me the URL (Telegram Post, YouTube video, etc.) that explains how to use the bot.\n\n"
                "⚠️ **Must start with `http://` or `https://`**\n\n"
                "Type `cancel` to abort."
            )

    except Exception as e:
        # THE FIX: Force the bot to print the exact error to your Telegram screen
        print(f"🔥 BUTTON CRASH: {str(e)}")
        await query.answer(f"System Error: {str(e)}", show_alert=True)

#State Function
@Client.on_message(filters.private & (filters.text | filters.document) & ~filters.regex("^/"))
async def admin_state_machine(client: Client, message: Message):
    admin_id = message.from_user.id
    is_coadmin = await db.is_coadmin(admin_id)
    if admin_id not in Config.ADMIN_IDS and not is_coadmin:
        return
    if admin_id not in admin_states:
        return 

    state = admin_states[admin_id]
    
    # Universal Cancel Command
    if message.text and message.text.lower() == "cancel":
        del admin_states[admin_id]
        await message.reply_text("❌ Action cancelled. Use `/admincmd` to open the panel.")
        return

    action = state["action"]

    # --- FIREBASE LOGIC ---
    if action == "waiting_for_firebase_json":
        if not message.document or not message.document.file_name.endswith(".json"):
            await message.reply_text("⚠️ Please send a valid `.json` document, or type `cancel`.")
            return
        
        # Safe Replacement: Delete the old key if it exists
        file_path = "serviceAccountKey.json"
        if os.path.exists(file_path):
            os.remove(file_path) 
        
        abs_path = os.path.abspath(file_path)
        await message.download(file_name=abs_path)
        
        # Move to the next state
        admin_states[admin_id]["action"] = "waiting_for_firebase_url"
        await message.reply_text(
            "✅ `serviceAccountKey.json` securely updated!\n\n"
            "Step 2: Now, please send the new **Firebase Realtime Database URL** (e.g., `https://your-app.firebaseio.com/`).\n\n"
            "*(Type `skip` if the URL hasn't changed).*"
        )

    elif action == "waiting_for_firebase_url":
        if message.text and message.text.lower() != "skip":
            new_url = message.text.strip()
            # Save the new URL to MongoDB
            await db.settings.update_one({"_id": "config"}, {"$set": {"firebase_url": new_url}}, upsert=True)
            
            # --- THE MAGIC FIX: Reload Firebase instantly ---
            from core.firebase_db import reload_firebase
            success, error_msg = reload_firebase(new_url)
            
            if success:
                await message.reply_text(
                    f"✅ Firebase URL updated to:\n`{new_url}`\n\n"
                    "🔥 **Firebase re-initialized successfully!** The bot is now using the new database."
                )
            else:
                await message.reply_text(
                    f"⚠️ The URL was saved, but Firebase failed to reload dynamically. You may need to restart. Error: `{error_msg}`"
                )
        else:
            await message.reply_text("✅ Firebase URL skipped.")
            
        # Clear the admin state
        del admin_states[admin_id]
        await message.reply_text("🔥 Firebase setup complete! Use /admincmd to return to the panel.")
        
    # --- BYPASS TIME LOGIC ---
    elif action == "waiting_for_bypass_time":
        if not message.text.isdigit():
            await message.reply_text("⚠️ Please enter a valid number (e.g., `15`).")
            return
            
        new_time = int(message.text)
        await db.set_bypass_time(new_time)
        del admin_states[admin_id]
        await message.reply_text(f"⏱ Bypass time successfully updated to **{new_time} seconds**.")
    elif action == "waiting_for_shortener_url":
        url = message.text.strip()
        if not url.startswith("http"):
            await message.reply_text("⚠️ Please enter a valid URL (starting with http:// or https://).")
            return
            
        admin_states[admin_id]["shortener_url"] = url
        admin_states[admin_id]["action"] = "waiting_for_shortener_key"
        
        await message.reply_text(
            f"✅ **URL Accepted:** `{url}`\n\n"
            "Step 2: Please send the **API Key** for this shortener.\n\n"
            "*(Type `cancel` to abort)*"
        )
        
    elif action == "waiting_for_shortener_key":
        api_key = message.text.strip()
        admin_states[admin_id]["shortener_key"] = api_key
        admin_states[admin_id]["action"] = "waiting_for_shortener_name"
        
        await message.reply_text(
            "✅ **API Key Received.**\n\n"
            "Step 3: What should we call this shortener on the button? (e.g., `Server 1`, `GPLinks`)\n\n"
            "*(Type `cancel` to abort)*"
        )
        
    elif action == "waiting_for_shortener_name":
        name = message.text.strip()
        url = admin_states[admin_id]["shortener_url"]
        api_key = admin_states[admin_id]["shortener_key"]
        
        import requests
        
        # Live validation check to ensure the API actually responds
        wait_msg = await message.reply_text("⏳ Verifying API credentials, please wait...")
        
        try:
            # Standard API format for most shorteners
            test_link = f"{url}?api={api_key}&url=https://google.com"
            response = requests.get(test_link, timeout=5).json()
            
            if response.get("status") == "error":
                await wait_msg.edit_text(f"❌ **API Error:** {response.get('message', 'Invalid URL or Key.')}\nPlease start over and try again.")
                del admin_states[admin_id]
                return
        except Exception as e:
            await wait_msg.edit_text("⚠️ **Warning:** Could not verify the API. It might be down or the URL format is unusual. We will save it anyway, but please test it manually!")
            
        # Checks passed! Save to MongoDB
        await db.add_shortener(name, url, api_key)
        del admin_states[admin_id]
        
        await wait_msg.edit_text(
            f"🎉 **Shortener Successfully Added!**\n\n"
            f"🔘 **Button Name:** {name}\n"
            f"🔗 **API URL:** `{url}`\n\n"
            "It is now live in the database!"
        )
    
    # --- CONTACT URL LOGIC ---
    elif action == "waiting_for_main_url":
        url = message.text.strip()
        if not re.match(r"^(https?://)?(t\.me|telegram\.me)/.+", url):
            await message.reply_text("⚠️ Invalid format! Please enter a valid Telegram link (e.g., `https://t.me/YourGroup`).")
            return
        match = re.search(r"(?:t\.me|telegram\.me)/(?!joinchat/|\+)([\w_]+)(?:/)?$", url)
        if match:
            username = match.group(1)
            try:
                await client.get_chat(username)
            except Exception as e:
                await message.reply_text(
                    f"❌ **Verification Failed!**\n"
                    f"The username `@{username}` does not exist on Telegram, or the link is invalid.\n"
                    f"*(System error: {str(e)})*"
                )
                return

        await db.set_main_url(url)
        del admin_states[admin_id]
        await message.reply_text(f"✅ Main URL successfully updated to:\n`{url}`\n\nUse `/admincmd` to return to the panel.")

    elif action == "waiting_for_how_to_use_url":
        if not message.text:
            await message.reply_text("⚠️ Please send a valid link text, not a file or photo.")
            return
            
        url = message.text.strip()
        
        # LOGICAL ERROR CHECK: Prevent bot crash by enforcing HTTP
        if not re.match(r"^(https?://)", url):
            await message.reply_text(
                "❌ **Invalid Link!**\n"
                "The link MUST start with `http://` or `https://` or the bot's inline buttons will crash for users.\n\n"
                "Please try again."
            )
            return
            
        await db.set_how_to_use_url(url)
        del admin_states[admin_id]
        await message.reply_text(f"✅ 'How to USE' link successfully updated to:\n`{url}`\n\nUsers will now be directed here from the main menu.")    

# --- STATS COMMAND ---
@Client.on_message(filters.command("stats") & filters.private)
async def stats_command(client: Client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        return
        
    loading = await message.reply_text("🔄 Fetching statistics...")
    
    total_users = await db.get_total_users()
    active_shorteners = await db.get_all_shorteners()
    
    stats_text = (
        "📊 **Bot Statistics**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👥 **Total Users:** `{total_users}`\n"
        f"🔗 **Active Servers:** `{len(active_shorteners)}`\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    await loading.edit_text(stats_text)


# --- BROADCAST COMMAND ---
@Client.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client: Client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        return
        
    # The admin must reply to the message they want to broadcast
    if not message.reply_to_message:
        await message.reply_text(
            "⚠️ **How to use Broadcast:**\n\n"
            "1. Send the photo/text/video you want to broadcast.\n"
            "2. **Reply** to that message with `/broadcast`."
        )
        return

    users = await db.get_all_users()
    if not users:
        await message.reply_text("⚠️ No users found in the database.")
        return

    status_msg = await message.reply_text(f"🚀 **Broadcast Started!**\nSending to {len(users)} users...")
    
    success = 0
    failed = 0
    
    # Loop through all users and copy the message to them
    for user in users:
        try:
            await message.reply_to_message.copy(user["_id"])
            success += 1
            # ⚠️ CRITICAL: Sleep for 0.05s to prevent Telegram from banning your bot for spamming!
            await asyncio.sleep(0.05) 
        except Exception:
            # If it fails, it usually means the user blocked the bot or deleted their account
            failed += 1
            
    await status_msg.edit_text(
        "✅ **Broadcast Completed!**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🎯 **Successfully Sent:** `{success}`\n"
        f"❌ **Failed (Blocked/Deleted):** `{failed}`"
    )        


# --- USER STATS TABLE COMMAND ---
@Client.on_message(filters.command("userstats") & filters.private)
async def userstats_command(client: Client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        return
        
    status = await message.reply_text("🔄 Compiling user database...")
    users = await db.get_all_users()
    
    if not users:
        await status.edit_text("⚠️ No users found in the database yet.")
        return

    # 1. Build the Table Header
    # We lock the widths: ID (10 chars), Name (12 chars), Username (12 chars)
    table = "🆔 ID       | 👤 Name     | 🌐 Username  \n"
    table += "━━━━━━━━━━━|━━━━━━━━━━━━━━|━━━━━━━━━━━━━━\n"
    
    # 2. Populate the Rows
    for u in users:
        uid = str(u["_id"])[:10].ljust(10)
        # We use .get() so older users who only have an ID don't crash the bot
        name = str(u.get("first_name", "Unknown"))[:12].ljust(12)
        uname = str(u.get("username", "None"))[:12].ljust(12)
        
        table += f"{uid} | {name} | {uname}\n"

    # 3. Smart Delivery (Message vs. File)
    # Wrap the table in Telegram's Monospace Markdown
    final_text = f"📊 **Detailed User Database ({len(users)} Users)**\n\n```text\n{table}```"
    
    if len(final_text) > 4000:
        await status.edit_text("📦 Database is too large for a message. Generating file...")
        
        # Create a virtual file in memory
        file_bytes = io.BytesIO(table.encode('utf-8'))
        file_bytes.name = "Bot_User_Database.txt"
        
        await message.reply_document(
            document=file_bytes,
            caption=f"📊 **Complete User Database**\nTotal Users: `{len(users)}`"
        )
        await status.delete()
    else:
        await status.edit_text(final_text)  

# --- CO-ADMIN MANAGEMENT COMMANDS (Main Admins Only) ---
@Client.on_message(filters.command("add") & filters.private)
async def add_coadmin_cmd(client: Client, message: Message):
    # Strict Check: Only the absolute main admins from Config can use this
    if message.from_user.id not in Config.ADMIN_IDS:
        return
        
    if len(message.command) < 2:
        await message.reply_text("⚠️ **Usage:** `/add UserID`\n*(e.g., `/add 123456789`)*")
        return
        
    try:
        target_id = int(message.command[1])
        await db.add_coadmin(target_id)
        await message.reply_text(f"✅ **Success:** User `{target_id}` has been granted Co-Admin access to the panel.")
    except ValueError:
        await message.reply_text("⚠️ User ID must be a valid number.")

# --- CLEAR USED TOKENS COMMAND ---
@Client.on_message(filters.command("delete") & filters.private)
async def delete_used_tokens(client: Client, message: Message):
    admin_id = message.from_user.id
    
    # Check if the user is a main admin or co-admin
    is_coadmin = await db.is_coadmin(admin_id)
    if admin_id not in Config.ADMIN_IDS and not is_coadmin:
        return
        
    status_msg = await message.reply_text("🔄 Scanning Firebase for used tokens...")
    
    try:
        # Connect to the 'tokens' node in Firebase
        ref = fdb.reference('tokens')
        all_tokens = ref.get()
        
        # If the database is completely empty
        if not all_tokens:
            await status_msg.edit_text("⚠️ Database is empty. No tokens found.")
            return

        deleted_count = 0
        updates = {} # We will store all the tokens we want to delete here
        
        # Loop through all tokens
        for firebase_key, token_data in all_tokens.items():
            # Check if it's a valid dictionary and if read == 1
            if isinstance(token_data, dict) and token_data.get("read") == 1:
                # Setting a key's value to None in Firebase permanently deletes it
                updates[firebase_key] = None 
                deleted_count += 1
                
        # Execute the deletion
        if deleted_count > 0:
            # ref.update() performs a batch execution (deletes all of them instantly in one go)
            ref.update(updates)
            await status_msg.edit_text(f"✅ Found **{deleted_count}** used tokens and cleared them from the database.")
        else:
            await status_msg.edit_text("✅ Scanned database. No used tokens (`read = 1`) found right now.")
            
    except Exception as e:
        print(f"🔥 FIREBASE DELETE CRASH: {str(e)}")
        await status_msg.edit_text(f"❌ **Error while clearing tokens:** `{str(e)}`")

@Client.on_message(filters.command("remove") & filters.private)
async def remove_coadmin_cmd(client: Client, message: Message):
    # Strict Check: Only the absolute main admins from Config can use this
    if message.from_user.id not in Config.ADMIN_IDS:
        return
        
    if len(message.command) < 2:
        await message.reply_text("⚠️ **Usage:** `/remove UserID`")
        return
        
    try:
        target_id = int(message.command[1])
        await db.remove_coadmin(target_id)
        await message.reply_text(f"❌ **Success:** User `{target_id}` has been removed from Co-Admins.")
    except ValueError:
        await message.reply_text("⚠️ User ID must be a valid number.")          