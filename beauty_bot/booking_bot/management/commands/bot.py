from calendar import monthrange

from django.core.management.base import BaseCommand
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from django.conf import settings
from booking_bot.models import Service, Specialist
from asgiref.sync import sync_to_async
from datetime import datetime
from booking_bot.utils.google_sheets import get_available_dates


class Appointment:
    def __init__(self):
        self.service_id = None
        self.specialist_id = None
        self.specialist_name = None
        self.service_name = None
        self.date = None

    def __str__(self):
        return f"{self.service_name} - {self.specialist_name} - {self.date}"


class Command(BaseCommand):

    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        keyboard = [
            [InlineKeyboardButton("Послуги для чоловіків", callback_data="gender_men")],
            [InlineKeyboardButton("послуги для жінок", callback_data="gender_women")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Оберіть стать:', reply_markup=reply_markup)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        context.user_data['appointment'] = Appointment()
        await self.show_menu(update, context)

    async def show_date_picker(self, update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, year: int = None,
                               month: int = None):
        now = datetime.now()
        if year is None or month is None:
            year = now.year
            month = now.month

        last_day = monthrange(year, month)[1]

        available_dates = get_available_dates()
        available_dates = [datetime.strptime(date, '%d/%m/%Y') for date in available_dates]
        available_dates = [date for date in available_dates if date >= now.replace(hour=0, minute=0, second=0,
                                                                                   microsecond=0) and date.year == year and date.month == month]

        month_name = datetime(year, month, 1).strftime('%B')
        days_buttons = []
        for day in range(1, last_day + 1):
            date = datetime(year, month, day)
            if date in available_dates:
                button = InlineKeyboardButton(str(day), callback_data=f"date_{year}_{month}_{day}")
            else:
                button = InlineKeyboardButton(" ", callback_data="ignore")
            days_buttons.append(button)

        keyboard = [days_buttons[i:i + 7] for i in range(0, len(days_buttons), 7)]

        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1

        keyboard.insert(0, [InlineKeyboardButton(month_name, callback_data="ignore")])
        keyboard.append([
            InlineKeyboardButton("<", callback_data=f"change_month_{prev_year}_{prev_month}"),
            InlineKeyboardButton(">", callback_data=f"change_month_{next_year}_{next_month}")
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(text="Оберіть дату:", reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id=chat_id, text="Оберіть дату:", reply_markup=reply_markup)

    async def callback_query_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        data = query.data

        chat_id = query.message.chat_id

        if 'appointment' not in context.user_data:
            context.user_data['appointment'] = Appointment()

        appointment = context.user_data['appointment']

        if data.startswith("gender_"):
            context.user_data['gender'] = "men" if data == "gender_men" else "women"
            await self.show_main_options(update, context, chat_id)

        elif data == "dates":
            await self.show_date_picker(update, context, chat_id)
        elif data.startswith("change_month_"):
            parts = data.split('_')
            new_year = parts[2]
            new_month = parts[3]
            await self.show_date_picker(update, context, chat_id, int(new_year), int(new_month))
        elif data.startswith("date_"):
            parts = data.split('_')
            if len(parts) == 4:
                _, year, month, day = parts
                selected_date = datetime(int(year), int(month), int(day))
                appointment.date = selected_date.strftime('%Y-%m-%d')
                await self.show_main_options_with_selection(update, context, chat_id, appointment)

        elif data == "services":
            await self.list_services(update, context, chat_id)
        elif data.startswith("selected_service_") or data.startswith("service_"):
            if data.startswith("service_"):
                service_id = data.split('_')[1]
                service = await sync_to_async(Service.objects.get)(id=service_id)
                appointment.service_id = service_id
                appointment.service_name = service.name
            await self.show_main_options_with_selection(update, context, chat_id, appointment)

        elif data == "specialists":
            await self.list_specialists(update, context, chat_id)
        elif data.startswith("selected_specialist_") or data.startswith("specialist_"):
            if data.startswith("specialist_"):
                specialist_id = data.split('_')[1]
                specialist = await sync_to_async(Specialist.objects.get)(id=specialist_id)
                appointment.specialist_id = specialist_id
                appointment.specialist_name = specialist.name
            await self.show_main_options_with_selection(update, context, chat_id, appointment)

        print(f"APPOINTMENT: {context.user_data['appointment']}")

    async def show_main_options_with_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int,
                                               appointment: Appointment):
        date_text = f"Дата: {appointment.date}" if appointment.date else "Дата та час"
        service_text = f"Послуга: {appointment.service_name}" if appointment.service_name else "Послуги"
        specialist_text = f"Спеціаліст: {appointment.specialist_name}" if appointment.specialist_name else "Спеціалісти"

        buttons = [
            [InlineKeyboardButton(date_text, callback_data="dates")],
            [InlineKeyboardButton(service_text, callback_data="services")],
            [InlineKeyboardButton(specialist_text, callback_data="specialists")]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)

        if update.callback_query:
            await update.callback_query.edit_message_text(text="Оберіть опцію:", reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id=chat_id, text="Оберіть опцію:", reply_markup=reply_markup)

    async def show_main_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
        buttons = [
            [InlineKeyboardButton("Дата та час", callback_data="dates")],
            [InlineKeyboardButton("Послуги", callback_data="services")],
            [InlineKeyboardButton("Спеціалісти", callback_data="specialists")]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await context.bot.send_message(chat_id=chat_id, text="Оберіть опцію:", reply_markup=reply_markup)

    async def services_men(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        context.user_data['appointment'] = Appointment()
        context.user_data['appointment'].gender = "men"
        await self.show_main_options(update, context, update.message.chat_id)

    async def services_women(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        context.user_data['appointment'] = Appointment()
        context.user_data['appointment'].gender = "women"
        await self.show_main_options(update, context, update.message.chat_id)

    async def list_services(self, update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int = None) -> None:
        services = await sync_to_async(list)(Service.objects.all())
        keyboard = [[InlineKeyboardButton(service.name, callback_data=f"service_{service.id}")] for service in services]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = 'Оберіть послугу:'

        if chat_id is None:
            await update.message.reply_text(text, reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

    async def list_specialists(self, update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int = None) -> None:
        specialists = await sync_to_async(list)(Specialist.objects.all())
        keyboard = [[InlineKeyboardButton(specialist.name, callback_data=f"specialist_{specialist.id}")] for specialist
                    in specialists]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = 'Оберіть спеціаліста:'

        if chat_id is None:
            await update.message.reply_text(text, reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

    def handle(self, *args, **kwargs) -> None:
        application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

        application.add_handler(CommandHandler('services_man', self.services_men))
        application.add_handler(CommandHandler('services_women', self.services_women))
        application.add_handler(CommandHandler('start', self.start))
        application.add_handler(CallbackQueryHandler(self.callback_query_handler))

        application.run_polling()
