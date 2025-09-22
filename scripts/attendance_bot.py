import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
import pytz

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
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

# IST Timezone
IST = pytz.timezone('Asia/Kolkata')

##############################
# State Persistence Utilities #
##############################

def _now() -> datetime:
    return datetime.now(IST)  # Use IST timezone

def _format_time(dt_str: str) -> str:
    """Format datetime string to IST time display"""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = IST.localize(dt)
        else:
            dt = dt.astimezone(IST)
        return dt.strftime('%I:%M %p IST')
    except:
        return dt_str

def _is_work_hours() -> bool:
    """Check if current time is between 9 AM - 8 PM IST"""
    now = _now()
    return 9 <= now.hour < 20


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
            "history": {}  # date -> {"first": time, "second": time}
        }
    else:
        # Ensure history exists
        if "history" not in state[uid]:
            state[uid]["history"] = {}
        
        # Auto-reset if date changed but save to history first
        if state[uid].get("date") != today:
            # Save completed attendance to history
            old_date = state[uid].get("date")
            first_time = state[uid].get("first_mark_time")
            second_time = state[uid].get("second_mark_time")
            
            if old_date and (first_time or second_time):
                state[uid]["history"][old_date] = {
                    "first": first_time,
                    "second": second_time
                }
            
            # Reset for new day
            state[uid].update({
                "date": today,
                "first_mark_time": None,
                "second_mark_time": None,
                "last_reminder_type": None,
                "last_reminder_time": None,
            })
    return state[uid]


###########################
# Formatting / UI Helpers #
###########################

def status_text(u_state: Dict[str, Any]) -> str:
    first = u_state.get("first_mark_time")
    second = u_state.get("second_mark_time")
    lines = [f"Date: {u_state.get('date')}"]
    lines.append(f"First attendance: {'✅ ' + _format_time(first) if first else '❌ Pending'}")
    if first:
        lines.append(f"Second attendance: {'✅ ' + _format_time(second) if second else '❌ Pending'}")
    else:
        lines.append("Second attendance: ⏳ Waiting for first (min 1 hour gap)")
    return "\n".join(lines)


def first_mark_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Mark First Attendance ✅", callback_data="mark_first")]])


def second_mark_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Mark Second Attendance ✅", callback_data="mark_second")]])


def get_weekly_history(u_state: Dict[str, Any]) -> str:
    """Generate weekly attendance history report"""
    history = u_state.get("history", {})
    current_date = u_state.get("date")
    
    if not history and not (u_state.get("first_mark_time") or u_state.get("second_mark_time")):
        return "📊 Weekly Attendance History\n\nNo attendance records found yet. Start marking your attendance!"
    
    # Get last 7 days including today
    today = _now().date()
    week_dates = []
    for i in range(6, -1, -1):  # 6 days ago to today
        date = today - timedelta(days=i)
        week_dates.append(date.isoformat())
    
    lines = ["📊 Weekly Attendance History (Last 7 Days)\n"]
    
    for date_str in week_dates:
        date_obj = datetime.fromisoformat(date_str).date()
        day_name = date_obj.strftime("%A")
        formatted_date = date_obj.strftime("%b %d")
        
        if date_str == current_date:
            # Today's data from current state
            first = u_state.get("first_mark_time")
            second = u_state.get("second_mark_time")
        else:
            # Historical data
            day_data = history.get(date_str, {})
            first = day_data.get("first")
            second = day_data.get("second")
        
        # Format the line
        if day_name == "Sunday":
            lines.append(f"🟡 {formatted_date} ({day_name}) - Holiday")
        elif first and second:
            first_time = _format_time(first) if first else "❌"
            second_time = _format_time(second) if second else "❌"
            lines.append(f"✅ {formatted_date} ({day_name}) - {first_time} | {second_time}")
        elif first:
            first_time = _format_time(first)
            lines.append(f"🟠 {formatted_date} ({day_name}) - {first_time} | ❌ Incomplete")
        else:
            lines.append(f"❌ {formatted_date} ({day_name}) - No attendance")
    
    # Add summary
    total_days = len([d for d in week_dates if datetime.fromisoformat(d).date().strftime("%A") != "Sunday"])
    complete_days = 0
    partial_days = 0
    
    for date_str in week_dates:
        if datetime.fromisoformat(date_str).date().strftime("%A") == "Sunday":
            continue
            
        if date_str == current_date:
            first = u_state.get("first_mark_time")
            second = u_state.get("second_mark_time")
        else:
            day_data = history.get(date_str, {})
            first = day_data.get("first")
            second = day_data.get("second")
        
        if first and second:
            complete_days += 1
        elif first:
            partial_days += 1
    
    lines.append(f"\n📈 Summary:")
    lines.append(f"Complete days: {complete_days}/{total_days}")
    lines.append(f"Partial days: {partial_days}")
    lines.append(f"Attendance rate: {(complete_days/total_days*100):.1f}%" if total_days > 0 else "Attendance rate: 0%")
    
    return "\n".join(lines)


########################
# Command Handlers      #
########################

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.application.bot_data.setdefault('attendance_state', load_state())
    u_state = get_user_state(state, update.effective_user.id)
    save_state(state)
    await update.message.reply_text(
        "👋 Attendance Reminder Bot Activated!\n\n"
        "I'll remind you every 30 minutes to mark attendance (9 AM - 8 PM IST, except Sundays) until you mark both times.\n"
        "Rules:\n"
        "1. Two marks per day.\n"
        "2. At least 1 hour gap between first and second.\n"
        "3. Sunday: no reminders.\n"
        "4. Reminders only between 9 AM - 8 PM IST.\n\n"
        "Use /status anytime to see progress.",
        reply_markup=first_mark_keyboard() if not u_state.get('first_mark_time') else (None if u_state.get('second_mark_time') else second_mark_keyboard())
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.application.bot_data.setdefault('attendance_state', load_state())
    u_state = get_user_state(state, update.effective_user.id)
    save_state(state)
    await update.message.reply_text(status_text(u_state))


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show weekly attendance history"""
    state = context.application.bot_data.setdefault('attendance_state', load_state())
    u_state = get_user_state(state, update.effective_user.id)
    save_state(state)
    history_report = get_weekly_history(u_state)
    await update.message.reply_text(history_report)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any text message by showing status and available commands"""
    state = context.application.bot_data.setdefault('attendance_state', load_state())
    u_state = get_user_state(state, update.effective_user.id)
    save_state(state)
    
    # Show current status
    status_msg = status_text(u_state)
    
    # Add available commands info
    commands_info = (
        "\n\n📋 Available Commands:\n"
        "/start - Initialize bot and see rules\n"
        "/status - Check attendance status\n"
        "/history - View weekly attendance history\n"
        "💬 Send any message to see this info"
    )
    
    # Determine appropriate keyboard
    first_done = u_state.get('first_mark_time')
    second_done = u_state.get('second_mark_time')
    
    if not first_done:
        keyboard = first_mark_keyboard()
    elif not second_done:
        keyboard = second_mark_keyboard()
    else:
        keyboard = None
    
    await update.message.reply_text(
        status_msg + commands_info,
        reply_markup=keyboard
    )


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
    u_state['first_mark_time'] = now.isoformat()
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
    first_time = datetime.fromisoformat(first_ts.replace('Z', '+00:00'))
    if first_time.tzinfo is None:
        first_time = IST.localize(first_time)
    else:
        first_time = first_time.astimezone(IST)
    if _now() - first_time < timedelta(hours=1):
        remaining = timedelta(hours=1) - (_now() - first_time)
        minutes = int(remaining.total_seconds() // 60)
        await query.answer(f"Too early. Wait ~{minutes} more min.", show_alert=True)
        return
    u_state['second_mark_time'] = _now().isoformat()
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
    
    # Check if it's work hours (9 AM - 8 PM IST)
    if not _is_work_hours():
        return
    
    if weekday == 6:
        # Sunday: Send weekly history to all users (once per day)
        for uid, u_state in list(state.items()):
            # Check if we already sent history today
            last_history_date = u_state.get("last_history_date")
            today = now.date().isoformat()
            
            if last_history_date != today:
                # Send weekly history
                history_report = get_weekly_history(u_state)
                await _send_history_report(context, int(uid), history_report)
                u_state["last_history_date"] = today
                changed = True
        
        if changed:
            save_state(state)
        return
        
    # Weekdays: Send attendance reminders
    for uid, u_state in list(state.items()):
        # Auto-reset per user if date changed, but preserve history
        if u_state.get('date') != now.date().isoformat():
            # Save to history before reset
            old_date = u_state.get("date")
            first_time = u_state.get("first_mark_time")
            second_time = u_state.get("second_mark_time")
            
            if old_date and (first_time or second_time):
                if "history" not in u_state:
                    u_state["history"] = {}
                u_state["history"][old_date] = {
                    "first": first_time,
                    "second": second_time
                }
            
            # Reset for new day but keep history
            history_backup = u_state.get("history", {})
            last_history_date = u_state.get("last_history_date")
            u_state.clear()
            u_state.update({
                "date": now.date().isoformat(),
                "first_mark_time": None,
                "second_mark_time": None,
                "last_reminder_type": None,
                "last_reminder_time": None,
                "history": history_backup,
                "last_history_date": last_history_date
            })
            changed = True

        # Determine what reminder to send
        first = u_state.get('first_mark_time')
        second = u_state.get('second_mark_time')
        if not first:
            # Send reminder for first attendance
            await _send_reminder(context, int(uid), 'first')
            u_state['last_reminder_type'] = 'first'
            u_state['last_reminder_time'] = now.isoformat()
            changed = True
        elif not second:
            first_time = datetime.fromisoformat(first.replace('Z', '+00:00'))
            if first_time.tzinfo is None:
                first_time = IST.localize(first_time)
            else:
                first_time = first_time.astimezone(IST)
            if now - first_time >= timedelta(hours=1):
                await _send_reminder(context, int(uid), 'second')
                u_state['last_reminder_type'] = 'second'
                u_state['last_reminder_time'] = now.isoformat()
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


async def _send_history_report(context: ContextTypes.DEFAULT_TYPE, user_id: int, history_report: str):
    """Send weekly history report on Sundays"""
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🎉 Sunday Weekly Report!\n\n{history_report}\n\nEnjoy your day off! 😊"
        )
    except Exception as e:
        logger.warning(f"Failed to send history report to {user_id}: {e}")


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
    application.add_handler(CommandHandler('history', history))
    
    # Text message handler (for any non-command text)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # Callback query handlers
    application.add_handler(CallbackQueryHandler(mark_first, pattern='^mark_first$'))
    application.add_handler(CallbackQueryHandler(mark_second, pattern='^mark_second$'))

    # Schedule repeating reminder every 30 minutes (1800 seconds)
    application.job_queue.run_repeating(reminder_job, interval=1800, first=5)

    logger.info("Attendance bot running. Press Ctrl-C to stop.")
    application.run_polling()


if __name__ == '__main__':
    main()
