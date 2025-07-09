# Import the necessary classes from the library
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import os
load_dotenv()
# --- IMPORTANT: PASTE YOUR BOT TOKEN HERE ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# ---------------------------------------------

# Enable logging to see errors
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Define the function for the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message when the command /start is issued."""
    user = update.effective_user
    # The 'await' keyword is used because the send_message function is asynchronous
    await update.message.reply_html(
        f"Hi {user.mention_html()}! I am an echo bot. Send me any message, and I will repeat it back to you.","Send /help fro the help"
    )

# Define the function that will echo messages
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    # This will simply send back the same text message the user sent.
    await update.message.reply_text(update.message.text)
    
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message when the command /help is issued."""
    await update.message.reply_text(
        "This is a simple echo bot. Send me any message, and I will repeat it back to you."
    )
    
def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # on different commands - answer in Telegram
    # Register the /start command handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    

   
    # Register the message handler to echo all text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Start the Bot. This will run forever until you press Ctrl-C
    print("Bot is running... Press Ctrl-C to stop.")
    application.run_polling()

# This part ensures that the main() function is called when the script is executed
if __name__ == '__main__':
    main()
