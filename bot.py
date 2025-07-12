# Import the necessary classes from the library
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# --- IMPORTANT: GET YOUR BOT TOKEN FROM THE .env FILE ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Please set the TELEGRAM_BOT_TOKEN environment variable in your .env file.")
# ----------------------------------------------------

# Enable logging to see errors and bot activity
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define the function for the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    user = update.effective_user
    await update.message.reply_html(
        f"Hi {user.mention_html()}! 👋\n\n"
        "I am your first Telegram Bot, an Echo Bot.\n"
        "Send me any message, and I will repeat it back to you.\n\n"
        "Try it out!"
    )

# Define the function for the /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a help message when the /help command is issued."""
    await update.message.reply_text(
        "This is a simple echo bot. Just send any text message, and I will echo it back. "
        "You can also use /start to see the welcome message."
    )

# Define the function that will echo messages
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user's message."""
    logger.info(f"Echoing message from {update.effective_user.first_name}: {update.message.text}")
    # This will simply send back the same text message the user sent.
    await update.message.reply_text(update.message.text)

def main() -> None:
    """Start the bot and listen for messages."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Register the message handler to echo all non-command text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Start the Bot. This will run until you press Ctrl-C
    print("Bot is running... Press Ctrl-C to stop.")
    application.run_polling()

# This part ensures that the main() function is called when the script is executed
if __name__ == '__main__':
    main()