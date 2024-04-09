from django.core.management.base import BaseCommand
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from django.conf import settings
from booking_bot.models import Service, Specialist
from asgiref.sync import sync_to_async


class Appointment:
    def __init__(self):
        self.service_id = None
        self.specialist_id = None
        self.specialist_name = None
        self.service_name = None

    def __str__(self):
        return f"{self.service_name} - {self.specialist_name}"


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
        elif data == "services":
            await self.list_services(update, context, chat_id)
        elif data == "specialists":
            await self.list_specialists(update, context, chat_id)
        elif data.startswith("selected_service_") or data.startswith("service_"):
            if data.startswith("service_"):
                service_id = data.split('_')[1]
                service = await sync_to_async(Service.objects.get)(id=service_id)
                appointment.service_id = service_id
                appointment.service_name = service.name
            await self.show_main_options_with_selection(update, context, chat_id, appointment)
        elif data.startswith("selected_specialist_") or data.startswith("specialist_"):
            if data.startswith("specialist_"):
                specialist_id = data.split('_')[1]
                specialist = await sync_to_async(Specialist.objects.get)(id=specialist_id)
                appointment.specialist_id = specialist_id
                appointment.specialist_name = specialist.name
            await self.show_main_options_with_selection(update, context, chat_id, appointment)

        print(f"APPOINTMENT: {context.user_data['appointment']}")

    async def show_main_options_with_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, appointment: Appointment):
        service_text = "Послуги" if not appointment.service_name else f"Послуга: {appointment.service_name}"
        specialist_text = "Спеціалісти" if not appointment.specialist_name else f"Спеціаліст: {appointment.specialist_name}"

        buttons = [
            [InlineKeyboardButton("Дата та час", callback_data="date_time")],
            [InlineKeyboardButton(service_text, callback_data="services")],
            [InlineKeyboardButton(specialist_text, callback_data="specialists")]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await context.bot.send_message(chat_id=chat_id, text="Оберіть опцію:", reply_markup=reply_markup)

    async def show_main_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
        buttons = [
            [InlineKeyboardButton("Дата та час", callback_data="date_time")],
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
