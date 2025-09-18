# Create Your First Telegram Bot: A Beginner's Tutorial

This repository provides a complete, step-by-step guide to creating your very first Telegram bot using Python. We'll build a simple "Echo Bot" that replies to every message with the same text. It's the perfect project for beginners to get started with bot development.

## What You'll Build

You will create a simple Telegram bot that:
- Responds to a `/start` command with a welcome message.
- Responds to a `/help` command with a helpful text.
- Echoes back any text message it receives.

---

## New: Attendance Reminder Bot (Optional Second Bot)

You can also run a separate bot that reminds you to mark attendance twice per day with at least a 1 hour gap. It will:

- Send a reminder every 30 minutes (config hard‑coded) until the first attendance is marked.
- After the first mark, wait at least 1 hour, then start reminding for the second attendance (every 30 minutes) until marked.
- Stop for the rest of the day once both marks are complete.
- Automatically reset each new day.
- Skip Sundays (no reminders sent).

### Commands

- `/start` – Registers you and shows instructions + current status.
- `/status` – Shows whether you've marked first / second attendance today.

### How to Mark

Each reminder message contains an inline button:

- "Mark First Attendance ✅"
- "Mark Second Attendance ✅"

Tap the button to record the mark. The second mark enforces a 1 hour wait after the first.

### Run the Attendance Bot

This is a separate file so it doesn't interfere with the original echo bot.

```bash
python attendance_bot.py
```

Make sure your `.env` still contains:

```
TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
```

### State Persistence

Per-user daily status is stored in `attendance_state.json` in the same folder. It is recreated automatically if deleted. Data for each user resets automatically at the start of a new day.

### Assumptions / Notes

- Uses server local time. Adjust code if you need a fixed timezone.
- Reminders start only after you run `/start` at least once (registers you in state).
- No extra dependencies beyond those already in `requirements.txt` (relies on `python-telegram-bot` JobQueue).

---

## Getting Started: A Step-by-Step Guide

Follow these instructions to get your first bot running.

### 1. Prerequisites

- Python 3.8 or higher.
- A Telegram account.
- Git installed on your local machine.

### 2. Clone the Repository

First, clone this repository to your local machine:

```bash
git clone https://github.com/zenitsu0509/TeleBot-Creator.git
cd TeleBot-Creator
```

### 3. Create a Telegram Bot with BotFather

To use the Telegram Bot API, you need to create a bot via **BotFather**, a bot provided by Telegram to help developers create and manage their bots.

**Step 1: Find BotFather**
Open your Telegram app and search for `@BotFather`.

![Search BotFather](data/image/search_botfather.jpg)

**Step 2: Start a chat**
Start a chat with BotFather and send the `/start` command.

![Start BotFather](data/image/start_botfath.jpg)

**Step 3: Create a new bot**
Send the `/newbot` command. BotFather will ask you for a name and a username for your bot.

![Steps to create a bot](data/image/step_to_Create_bot.jpg)

**Step 4: Get your Bot Token**
Once you've chosen a name and username, BotFather will provide you with a **token**. This token is your bot's authentication key. **Keep it safe and do not share it.**

![Get Bot Token](data/image/create_bot_name.jpg)

### 4. Set Up Your Environment

**Step 1: Install Dependencies**
Install the necessary Python package using the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

**Step 2: Create a `.env` file**
Create a file named `.env` in the root of the project directory. This file will store your secret bot token.

```
TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
```

Replace `"YOUR_TELEGRAM_BOT_TOKEN"` with the token you got from BotFather.

### 5. Understand the Code (`bot.py`)

The `bot.py` file contains all the logic for your bot. Here's a quick breakdown:
- **`start()`**: This function is called when a user sends the `/start` command. It replies with a friendly welcome message.
- **`help_command()`**: This function is called for the `/help` command and explains what the bot does.
- **`echo()`**: This function is the core of our bot. It takes any text message the user sends and replies with the exact same text.
- **`main()`**: This function sets up all the command handlers and starts the bot, making it listen for messages.

### 6. Run the Bot

Now you are ready to start your bot!

```bash
python bot.py
```

If everything is configured correctly, you will see the message "Bot is running... Press Ctrl-C to stop." in your terminal. You can now go to your bot on Telegram and start sending it messages!

## Project Structure

```bash
TeleBot-Creator/
├── .env                # Stores your secret bot token (you need to create this)
├── bot.py              # The main Python script for your bot
├── LICENSE
├── README.md           # This file
├── requirements.txt    # Python dependencies
└── data/
    └── image/          # Screenshots for the tutorial
```

## Contributing

Contributions are welcome! If you have ideas for new features or improvements, feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
