from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config

@Client.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message):
    help_text = (
        "**🤖 Token Generator Bot - Help Menu**\n\n"
        "This bot acts as a secure bridge to generate access tokens after passing through a sponsored link.\n\n"
        "**🛠 How it works:**\n"
        "1️⃣ **App Integration:** When redirected from the app, simply follow the provided link. Upon successful completion, a secure 16-character token will be instantly synced to your app session.\n\n"
        "2️⃣ **Demo Mode:** Send `/start` and click 'Generate Key' to test the workflow. The resulting token will be safely stored in the admin log channel.\n\n"
        "**⚠️ Security Rules:**\n"
        "• **Time Limit:** You have exactly **10 minutes** to complete the verification link once generated.\n"
        "• **Anti-Bypass:** If you use a bypass script and return to the bot too quickly, the system will detect it and reject your verification attempt.\n\n"
        "If you encounter any issues, please generate a new link and try again."
    )
    
    # Provide a quick way to restart the bot or go back to the main menu
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu_return")]
    ])

    await message.reply_text(help_text, reply_markup=keyboard)


# Optional: Handle the "Main Menu" button click to show the start menu again
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