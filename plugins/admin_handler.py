from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
import os

# Helper filter to check if the user is an admin
def is_admin(_, __, message: Message):
    return message.from_user and message.from_user.id in Config.ADMIN_IDS

admin_filter = filters.create(is_admin)

# A dictionary to track what the admin is currently doing (e.g., waiting for an API key)
admin_states = {}

@Client.on_message(filters.command("admincmd") & filters.private & admin_filter)
async def admin_panel(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Add Shortener", callback_data="admin_add_shortener"),
            InlineKeyboardButton("➖ Remove Shortener", callback_data="admin_remove_shortener")
        ],
        [
            InlineKeyboardButton("🔥 Update Firebase", callback_data="admin_update_firebase"),
            InlineKeyboardButton("⏱ Edit Bypass Time", callback_data="admin_edit_bypass")
        ],
        [InlineKeyboardButton("❌ Close Panel", callback_data="admin_close")]
    ])
    
    await message.reply_text(
        "🛠 **Admin Control Panel** 🛠\n\n"
        "Welcome, Boss. What would you like to configure today?",
        reply_markup=keyboard
    )

@Client.on_callback_query(filters.regex("^admin_") & admin_filter)
async def admin_callbacks(client: Client, query: CallbackQuery):
    data = query.data
    admin_id = query.from_user.id
    
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
        from core.database import db
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
        from core.database import db
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


@Client.on_message(filters.private & admin_filter & ~filters.command(["admincmd", "start"]))
async def admin_state_machine(client: Client, message: Message):
    admin_id = message.from_user.id
    
    # If the admin isn't in the middle of a setup process, ignore the message
    if admin_id not in admin_states:
        return 

    state = admin_states[admin_id]
    
    # Universal Cancel Command
    if message.text and message.text.lower() == "cancel":
        del admin_states[admin_id]
        await message.reply_text("❌ Action cancelled. Use `/admincmd` to open the panel.")
        return

    action = state["action"]
    from core.database import db

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
