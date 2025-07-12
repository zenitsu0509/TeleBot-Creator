import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
load_dotenv()
# --- 1. CONFIGURATION & INITIALIZATION ---

# Load credentials from environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

if not TELEGRAM_BOT_TOKEN or not PINECONE_API_KEY:
    raise ValueError("Please set TELEGRAM_BOT_TOKEN and PINECONE_API_KEY environment variables.")

# Pinecone and Model Configuration
INDEX_NAME = "medicine-index"
MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'
SCORE_THRESHOLD = 0.5 # Confidence threshold for returning a result

# --- Initialize services ONCE at startup for efficiency ---
print("Initializing services... This may take a moment.")

# Initialize logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)
# Check if index exists before connecting
if INDEX_NAME not in pc.list_indexes().names():
    raise ValueError(f"Pinecone index '{INDEX_NAME}' does not exist. Please run the data ingestion script first.")
index = pc.Index(INDEX_NAME)

# Load the sentence transformer model
model = SentenceTransformer(MODEL_NAME)

print("Services initialized successfully. Bot is ready.")
# --- END OF INITIALIZATION ---


# --- 2. TELEGRAM BOT HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Hello, {user_name}!\n\n"
        "I am your personal medicine information assistant. "
        "Just send me the name of a medicine, and I'll find its details for you.\n\n"
        "For example, try sending 'Paracetamol' or 'Aspirin'."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a help message when the /help command is issued."""
    await update.message.reply_text(
        "Simply type the name of the medicine you want to know about. "
        "I will search my database and return information on its uses, side effects, and more."
    )

async def find_medicine(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """The core function: finds medicine info based on user's message."""
    user_query = update.message.text
    chat_id = update.effective_chat.id
    logger.info(f"Received query from chat_id {chat_id}: '{user_query}'")

    # Let the user know the bot is working
    await context.bot.send_message(chat_id, f"🔍 Searching for '{user_query}'...")

    try:
        # 1. Create an embedding for the user's query
        query_embedding = model.encode(user_query).tolist()

        # 2. Query Pinecone
        query_results = index.query(
            vector=query_embedding,
            top_k=1,  # We only want the single best match
            include_metadata=True
        )

        # 3. Process and send the result
        if query_results['matches'] and query_results['matches'][0]['score'] > SCORE_THRESHOLD:
            best_match = query_results['matches'][0]
            score = best_match['score']
            metadata = best_match['metadata']
            
            # This is the full text block we created in the previous script
            rag_text = metadata.get('text_for_rag', 'Details not found.')
            
            response_message = (
                f"✅ Found a match for '{metadata.get('name', user_query)}' with confidence score: {score:.2f}\n\n"
                "--------------------\n"
                f"{rag_text}"
            )
            await context.bot.send_message(chat_id, response_message)
        else:
            await context.bot.send_message(
                chat_id,
                f"Sorry, I could not find any reliable information for '{user_query}'. "
                "Please check the spelling or try a different name."
            )

    except Exception as e:
        logger.error(f"An error occurred while processing query '{user_query}': {e}", exc_info=True)
        await context.bot.send_message(
            chat_id,
            "An internal error occurred. Please try again later."
        )


# --- 3. MAIN FUNCTION TO RUN THE BOT ---

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Register the message handler for non-command text messages
    # The `~filters.COMMAND` part ensures that commands like /start are ignored by this handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, find_medicine))

    # Start the Bot
    print("Starting bot polling...")
    application.run_polling()


if __name__ == '__main__':
    main()