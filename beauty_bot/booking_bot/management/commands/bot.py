from django.core.management.base import BaseCommand
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from django.conf import settings
from booking_bot.models import Service, Specialist
from asgiref.sync import sync_to_async


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

    async def list_services(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        services = await sync_to_async(list)(Service.objects.all())
        keyboard = [
            [InlineKeyboardButton(service.name, callback_data=f"service_{service.id}")] for service in services
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Please choose a service:', reply_markup=reply_markup)

    async def list_specialists(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        specialists = await sync_to_async(list)(Specialist.objects.all())
        keyboard = [
            [InlineKeyboardButton(specialist.name, callback_data=f"specialist_{specialist.id}")] for specialist in
            specialists
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Please choose a specialist:', reply_markup=reply_markup)

    async def callback_query_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        data = query.data

        if data.startswith("gender_"):
            context.user_data['gender'] = "men" if data == "gender_men" else "women"
            await self.show_main_options(update, context, query.message.chat_id)
        elif data.startswith("service_"):
            service_id = data.split('_')[1]
            service = await sync_to_async(Service.objects.get)(id=service_id)
            await query.edit_message_text(text=f"Selected service: {service.name}")
        elif data.startswith("specialist_"):
            specialist_id = data.split('_')[1]
            specialist = await sync_to_async(Specialist.objects.get)(id=specialist_id)
            await query.edit_message_text(text=f"Selected specialist: {specialist.name}")

    async def show_main_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
        keyboard = [
            [InlineKeyboardButton("Date and Time", callback_data="date_time")],
            [InlineKeyboardButton("Services", callback_data="services")],
            [InlineKeyboardButton("Specialists", callback_data="specialists")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        print(context.user_data['gender'])
        await context.bot.send_message(chat_id=chat_id, text="Please select an option:", reply_markup=reply_markup)

    async def services_men(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        context.user_data['gender'] = "men"
        await self.show_main_options(update, context, update.message.chat_id)

    async def services_women(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        context.user_data['gender'] = "women"
        await self.show_main_options(update, context, update.message.chat_id)

    def handle(self, *args, **kwargs) -> None:
        application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

        application.add_handler(CommandHandler('services_man', self.services_men))
        application.add_handler(CommandHandler('services_women', self.services_women))
        application.add_handler(CommandHandler('start', self.start))
        application.add_handler(CallbackQueryHandler(self.callback_query_handler))

        application.run_polling()
