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
