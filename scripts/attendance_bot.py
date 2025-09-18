import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Please set TELEGRAM_BOT_TOKEN in your .env file.")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("attendance_bot")

STATE_FILE = os.path.join(os.path.dirname(__file__), "data/attendance_state.json")

##############################
# State Persistence Utilities #
##############################

def _now() -> datetime:
    return datetime.now()  # Assumes server local time; adjust if timezone needed.


def load_state() -> Dict[str, Any]:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load state file: {e}")
        return {}


def save_state(state: Dict[str, Any]):
    temp_file = STATE_FILE + ".tmp"
    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
        os.replace(temp_file, STATE_FILE)
    except Exception as e:
        logger.error(f"Failed to save state: {e}")


def get_user_state(state: Dict[str, Any], user_id: int) -> Dict[str, Any]:
    uid = str(user_id)
    today = _now().date().isoformat()
    if uid not in state:
        state[uid] = {
            "date": today,
            "first_mark_time": None,
            "second_mark_time": None,
            "last_reminder_type": None,  # 'first' | 'second'
            "last_reminder_time": None,
        }
    else:
        # Auto-reset if date changed
        if state[uid].get("date") != today:
            state[uid] = {
                "date": today,
                "first_mark_time": None,
                "second_mark_time": None,
                "last_reminder_type": None,
                "last_reminder_time": None,
            }
    return state[uid]


###########################
# Formatting / UI Helpers #
###########################

def status_text(u_state: Dict[str, Any]) -> str:
    first = u_state.get("first_mark_time")
    second = u_state.get("second_mark_time")
    lines = [f"Date: {u_state.get('date')}"]
    lines.append(f"First attendance: {'✅ ' + first if first else '❌ Pending'}")
    if first:
        lines.append(f"Second attendance: {'✅ ' + second if second else '❌ Pending'}")
    else:
        lines.append("Second attendance: ⏳ Waiting for first (min 1 hour gap)")
    return "\n".join(lines)


def first_mark_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Mark First Attendance ✅", callback_data="mark_first")]])


def second_mark_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Mark Second Attendance ✅", callback_data="mark_second")]])


########################
# Command Handlers      #
########################

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.application.bot_data.setdefault('attendance_state', load_state())
    u_state = get_user_state(state, update.effective_user.id)
    save_state(state)
    await update.message.reply_text(
        "👋 Attendance Reminder Bot Activated!\n\n"
        "I'll remind you every 30 minutes to mark attendance (except Sundays) until you mark both times.\n"
        "Rules:\n"
        "1. Two marks per day.\n"
        "2. At least 1 hour gap between first and second.\n"
        "3. Sunday: no reminders.\n\n"
        "Use /status anytime to see progress.",
        reply_markup=first_mark_keyboard() if not u_state.get('first_mark_time') else (None if u_state.get('second_mark_time') else second_mark_keyboard())
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.application.bot_data.setdefault('attendance_state', load_state())
    u_state = get_user_state(state, update.effective_user.id)
    save_state(state)
    await update.message.reply_text(status_text(u_state))


########################
# Callback Handlers     #
########################

async def mark_first(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    state = context.application.bot_data.setdefault('attendance_state', load_state())
    u_state = get_user_state(state, query.from_user.id)
    if u_state.get('first_mark_time'):
        await query.edit_message_text("First attendance already recorded. ✅\n\n" + status_text(u_state))
        return
    now = _now()
    u_state['first_mark_time'] = now.isoformat(timespec='seconds')
    u_state['last_reminder_type'] = None
    u_state['last_reminder_time'] = None
    save_state(state)
    await query.edit_message_text(
        "First attendance marked! ✅\nYou'll be reminded for the second after 1 hour.\n\n" + status_text(u_state)
    )


async def mark_second(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    state = context.application.bot_data.setdefault('attendance_state', load_state())
    u_state = get_user_state(state, query.from_user.id)
    first_ts = u_state.get('first_mark_time')
    if not first_ts:
        await query.answer("Mark first attendance first.", show_alert=True)
        return
    if u_state.get('second_mark_time'):
        await query.edit_message_text("Second attendance already recorded. ✅\n\n" + status_text(u_state))
        return
    first_time = datetime.fromisoformat(first_ts)
    if _now() - first_time < timedelta(hours=1):
        remaining = timedelta(hours=1) - (_now() - first_time)
        minutes = int(remaining.total_seconds() // 60)
        await query.answer(f"Too early. Wait ~{minutes} more min.", show_alert=True)
        return
    u_state['second_mark_time'] = _now().isoformat(timespec='seconds')
    save_state(state)
    await query.edit_message_text(
        "Second attendance marked! ✅ Day complete. 🎉\n\n" + status_text(u_state)
    )


########################
# Reminder Job          #
########################

async def reminder_job(context: ContextTypes.DEFAULT_TYPE):
    state = context.application.bot_data.setdefault('attendance_state', load_state())
    changed = False
    now = _now()
    weekday = now.weekday()  # Monday=0 ... Sunday=6
    if weekday == 6:
        # Sunday: do nothing
        return
    for uid, u_state in list(state.items()):
        # Auto-reset per user if date changed
        if u_state.get('date') != now.date().isoformat():
            state[uid] = {
                "date": now.date().isoformat(),
                "first_mark_time": None,
                "second_mark_time": None,
                "last_reminder_type": None,
                "last_reminder_time": None,
            }
            u_state = state[uid]
            changed = True

        # Determine what reminder to send
        first = u_state.get('first_mark_time')
        second = u_state.get('second_mark_time')
        if not first:
            # Send reminder for first attendance
            await _send_reminder(context, int(uid), 'first')
            u_state['last_reminder_type'] = 'first'
            u_state['last_reminder_time'] = now.isoformat(timespec='seconds')
            changed = True
        elif not second:
            first_time = datetime.fromisoformat(first)
            if now - first_time >= timedelta(hours=1):
                await _send_reminder(context, int(uid), 'second')
                u_state['last_reminder_type'] = 'second'
                u_state['last_reminder_time'] = now.isoformat(timespec='seconds')
                changed = True
        # else: both done; nothing
    if changed:
        save_state(state)


async def _send_reminder(context: ContextTypes.DEFAULT_TYPE, user_id: int, which: str):
    keyboard = first_mark_keyboard() if which == 'first' else second_mark_keyboard()
    text = (
        "⏰ Reminder: Please mark your FIRST attendance." if which == 'first'
        else "⏰ Reminder: Please mark your SECOND attendance."
    )
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.warning(f"Failed to send reminder to {user_id}: {e}")


########################
# Main Entrypoint       #
########################

def main():
    application = Application.builder().token(BOT_TITLE := BOT_TOKEN).build()  # BOT_TITLE ignored result, just binding

    # Preload state into bot_data
    application.bot_data['attendance_state'] = load_state()

    # Command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('status', status))

    # Callback query handlers
    application.add_handler(CallbackQueryHandler(mark_first, pattern='^mark_first$'))
    application.add_handler(CallbackQueryHandler(mark_second, pattern='^mark_second$'))

    # Schedule repeating reminder every 30 minutes (1800 seconds)
    application.job_queue.run_repeating(reminder_job, interval=1800, first=5)

    logger.info("Attendance bot running. Press Ctrl-C to stop.")
    application.run_polling()


if __name__ == '__main__':
    main()
