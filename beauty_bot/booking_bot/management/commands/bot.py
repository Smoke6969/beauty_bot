# booking_bot/management/commands/bot.py
from django.core.management.base import BaseCommand
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from django.conf import settings
from booking_bot.models import Service, Specialist


class Command(BaseCommand):
    help = 'Run the telegram bot'

    def start(self, update: Update, context: CallbackContext):
        update.message.reply_text('Hello, welcome to our beauty salon booking system. How can I assist you today?')

    def list_services(self, update: Update, context: CallbackContext):
        services = Service.objects.all()
        message = "Available Services:\n\n"
        message += "\n".join([f"{service.name} - {service.duration} - ${service.price}" for service in services])
        update.message.reply_text(message)

    def list_specialists(self, update: Update, context: CallbackContext):
        specialists = Specialist.objects.all()
        message = "Our Specialists:\n\n"
        message += "\n".join([specialist.name for specialist in specialists])
        update.message.reply_text(message)

    def add_handlers(self, dispatcher):
        dispatcher.add_handler(CommandHandler('start', self.start))
        dispatcher.add_handler(CommandHandler('services', self.list_services))
        dispatcher.add_handler(CommandHandler('specialists', self.list_specialists))

    def handle(self, *args, **kwargs):
        updater = Updater(token=settings.TELEGRAM_BOT_TOKEN, use_context=True)
        dispatcher = updater.dispatcher

        self.add_handlers(dispatcher)

        updater.start_polling()
        updater.idle()
