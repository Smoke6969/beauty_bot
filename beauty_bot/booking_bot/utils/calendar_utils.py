from calendar import monthrange
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
from booking_bot.utils.google_sheets import get_available_dates


async def show_date_picker(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, year: int = None,
                           month: int = None):
    now = datetime.now()
    if year is None or month is None:
        year = now.year
        month = now.month

    last_day = monthrange(year, month)[1]
    month_names = ["Січень", "Лютий", "Березень", "Квітень", "Травень", "Червень", "Липень", "Серпень", "Вересень",
                   "Жовтень", "Листопад", "Грудень"]
    month_name = month_names[month - 1]
    days_of_week = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]

    available_dates = get_available_dates()
    available_dates = [datetime.strptime(date, '%d/%m/%Y') for date in available_dates]
    available_dates = [date for date in available_dates if
                       date.year == year and date.month == month and date >= now.replace(hour=0, minute=0, second=0,
                                                                                         microsecond=0)]

    days_buttons = []
    for day in range(1, last_day + 1):
        date = datetime(year, month, day)
        if date in available_dates:
            button = InlineKeyboardButton(str(day), callback_data=f"date_{year}_{month}_{day}")
        else:
            button = InlineKeyboardButton(" ", callback_data="ignore")
        days_buttons.append(button)

    keyboard = [[InlineKeyboardButton(month_name + " " + str(year), callback_data="ignore")]]
    keyboard.append([InlineKeyboardButton(day, callback_data="ignore") for day in days_of_week])
    keyboard += [days_buttons[i:i + 7] for i in range(0, len(days_buttons), 7)]

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    keyboard.append([
        InlineKeyboardButton("<", callback_data=f"change_month_{prev_year}_{prev_month}"),
        InlineKeyboardButton(">", callback_data=f"change_month_{next_year}_{next_month}")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(text="Оберіть дату:", reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=chat_id, text="Оберіть дату:", reply_markup=reply_markup)
