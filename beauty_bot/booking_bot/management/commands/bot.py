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


class Command(BaseCommand):

    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        keyboard = [
            [InlineKeyboardButton("Послуги для чоловіків", callback_data="gender_men")],
            [InlineKeyboardButton("послуги для жінок", callback_data="gender_women")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Оберіть стать:', reply_markup=reply_markup)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        elif data.startswith("service_"):
            service_id = data.split('_')[1]
            service = await sync_to_async(Service.objects.get)(id=service_id)
            appointment.service_id = service_id
            keyboard = [
                [InlineKeyboardButton(f"Послуга: {service.name}", callback_data=f"selected_service_{service.id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Ви обрали послугу:", reply_markup=reply_markup)

        elif data.startswith("specialist_"):
            specialist_id = data.split('_')[1]
            specialist = await sync_to_async(Specialist.objects.get)(id=specialist_id)
            appointment.specialist_id = specialist_id
            keyboard = [[InlineKeyboardButton(f"Спеціаліст: {specialist.name}",
                                              callback_data=f"selected_specialist_{specialist.id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Ви обрали спеціаліста:", reply_markup=reply_markup)

    async def show_main_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
        keyboard = [
            [InlineKeyboardButton("Оберіть дату та час", callback_data="date_time")],
            [InlineKeyboardButton("Оберіть послуги", callback_data="services")],
            [InlineKeyboardButton("Оберіть спеціаліста", callback_data="specialists")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=chat_id, text="Please select an option:", reply_markup=reply_markup)

    async def services_men(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        context.user_data['gender'] = "men"
        await self.show_main_options(update, context, update.message.chat_id)

    async def services_women(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        context.user_data['gender'] = "women"
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
