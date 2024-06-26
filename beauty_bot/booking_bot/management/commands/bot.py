from django.core.management.base import BaseCommand
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, \
    ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters, \
    CallbackContext
from django.conf import settings
from booking_bot.models import Service, Specialist, Client, Appointment
from asgiref.sync import sync_to_async
from datetime import datetime
from booking_bot.utils.calendar_utils import show_date_picker
from booking_bot.utils.common import SessionAppointment, SessionClient
from booking_bot.utils.db_utils import save_appointment
from booking_bot.utils.google_sheets import get_available_timeslots, get_cached_data, set_booked_slots
from booking_bot.utils.google_calendar import create_calendar_event
from babel.dates import format_date
from django.utils import timezone
import logging

logger = logging.getLogger('tg_bot')


class Command(BaseCommand):

    async def request_contact(self, update: Update, context: CallbackContext) -> None:
        keyboard = [
            [KeyboardButton("Поділитися контактом", request_contact=True)],
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            "Будь ласка, поділіться вашим контактом для продовження:",
            reply_markup=reply_markup
        )

    async def contact_handler(self, update: Update, context: CallbackContext) -> None:
        contact = update.message.contact
        user = update.message.from_user

        client, created = await sync_to_async(Client.objects.update_or_create)(
            telegram_id=str(user.id),
            defaults={
                'name': f"{user.first_name} {user.last_name if user.last_name else ''}".strip(),
                'phone_number': contact.phone_number,
                'username': user.username
            }
        )

        session_client = SessionClient(
            telegram_id=str(user.id),
            name=f"{user.first_name} {user.last_name if user.last_name else ''}".strip(),
            phone_number=contact.phone_number,
            username=user.username
        )
        context.user_data['appointment'].client = session_client

        await self.prompt_for_service(update, context, session_client.name)

        await update.message.reply_text(
            "Ваш контакт було успішно отримано!",
            reply_markup=ReplyKeyboardRemove()
        )

    async def start(self, update: Update, context: CallbackContext) -> None:
        user = update.message.from_user
        telegram_id = str(user.id)

        try:
            client = await sync_to_async(Client.objects.get)(telegram_id=telegram_id)
            session_client = SessionClient(
                telegram_id=client.telegram_id,
                name=client.name,
                phone_number=client.phone_number,
                username=client.username
            )
            context.user_data['appointment'] = SessionAppointment()
            context.user_data['appointment'].client = session_client
            await self.prompt_for_service(update, context, session_client.name)
        except Client.DoesNotExist:
            context.user_data['appointment'] = SessionAppointment()
            await self.request_contact(update, context)

    async def prompt_for_service(self, update: Update, context: CallbackContext, client_name: str) -> None:
        await update.message.reply_text(
            f"Дякуємо, {client_name}. Будь ласка, оберіть послугу:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Послуги для чоловіків", callback_data="gender_men")],
                [InlineKeyboardButton("Послуги для жінок", callback_data="gender_women")]
            ])
        )

    async def callback_query_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        data = query.data

        chat_id = query.message.chat_id

        if 'appointment' not in context.user_data:
            context.user_data['appointment'] = SessionAppointment()

        appointment = context.user_data['appointment']

        if data.startswith("gender_"):
            context.user_data['gender'] = "men" if data == "gender_men" else "women"
            await self.show_main_options(update, context, chat_id)

        elif data == "dates":
            await show_date_picker(update, context, chat_id, appointment=appointment)
        elif data.startswith("change_month_"):
            parts = data.split('_')
            new_year = parts[2]
            new_month = parts[3]
            await show_date_picker(update, context, chat_id, int(new_year), int(new_month), appointment=appointment)
        elif data.startswith("date_"):
            parts = data.split('_')
            if len(parts) == 4:
                _, year, month, day = parts
                selected_date = datetime(int(year), int(month), int(day))
                appointment.date = selected_date.strftime('%Y-%m-%d')

                available_timeslots = get_available_timeslots(appointment, appointment.date)
                timeslot_buttons = [[InlineKeyboardButton(timeslot, callback_data=f"timeslot_{timeslot}")] for timeslot
                                    in available_timeslots]
                timeslot_markup = InlineKeyboardMarkup(timeslot_buttons)

                if update.callback_query:
                    await update.callback_query.edit_message_text(text="Оберіть час:", reply_markup=timeslot_markup)
                else:
                    await context.bot.send_message(chat_id=chat_id, text="Оберіть час:", reply_markup=timeslot_markup)
        elif data.startswith("timeslot_"):
            timeslot = data.split('_')[1]
            appointment.timeslot = timeslot
            await self.show_main_options_with_selection(update, context, chat_id, appointment)

        elif data == "services":
            await self.list_services(update, context, chat_id, appointment)
        elif data.startswith("selected_service_") or data.startswith("service_"):
            if data.startswith("service_"):
                service_id = data.split('_')[1]
                service = await sync_to_async(Service.objects.get)(id=service_id)
                appointment.service_id = service_id
                appointment.service_name = service.name
            await self.show_main_options_with_selection(update, context, chat_id, appointment)

        elif data == "specialists":
            await self.list_specialists(update, context, chat_id, appointment)
        elif data.startswith("selected_specialist_") or data.startswith("specialist_"):
            if data.startswith("specialist_"):
                specialist_id = data.split('_')[1]
                specialist = await sync_to_async(Specialist.objects.get)(id=specialist_id)
                appointment.specialist_id = specialist_id
                appointment.specialist_name = specialist.name
            await self.show_main_options_with_selection(update, context, chat_id, appointment)

        elif data.startswith("confirm_appointment"):
            logger.info(f"APPOINTMENT CONFIRMED: {context.user_data['appointment']}")
            await query.edit_message_text(text="Дякую, ваш запис підтверджено!")
            await query.answer()

            set_booked_slots(appointment)

            specialist = await sync_to_async(Specialist.objects.get)(name=appointment.specialist_name)
            calendar_id = specialist.calendar_id
            await create_calendar_event(calendar_id, appointment)

            await save_appointment(appointment)

    async def show_main_options_with_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int,
                                               appointment: SessionAppointment):
        if appointment.date and appointment.timeslot:
            formatted_date = datetime.strptime(appointment.date, '%Y-%m-%d')
            locale_date = format_date(formatted_date, "d MMMM", locale='uk_UA')
            date_text = f"Коли: {locale_date} [{appointment.timeslot}]"
        else:
            date_text = "Дата та час"

        service_text = f"Послуга: {appointment.service_name}" if appointment.service_name else "Послуги"
        specialist_text = f"Спеціаліст: {appointment.specialist_name}" if appointment.specialist_name else "Спеціалісти"

        buttons = [
            [InlineKeyboardButton(date_text, callback_data="dates")],
            [InlineKeyboardButton(service_text, callback_data="services")],
            [InlineKeyboardButton(specialist_text, callback_data="specialists")]
        ]

        message_text = "Оберіть опцію:"

        if appointment.date and appointment.service_name and appointment.specialist_name:
            summary_text = f"\n\nДата: {locale_date}\nЧас: {appointment.timeslot}\nПослуга: {appointment.service_name}\nСпеціаліст: {appointment.specialist_name}"
            message_text += summary_text

            confirm_button = [InlineKeyboardButton("Підтвердити запис", callback_data="confirm_appointment")]
            keyboard = [confirm_button]
            reply_markup = InlineKeyboardMarkup(keyboard)

            if update.callback_query:
                await update.callback_query.edit_message_text(text=message_text, reply_markup=None)
                await update.callback_query.answer()
                await context.bot.send_message(chat_id=chat_id, text="Натисніть кнопку нижче для підтвердження",
                                               reply_markup=reply_markup)
            else:
                await context.bot.send_message(chat_id=chat_id, text=message_text, reply_markup=reply_markup)

        else:
            reply_markup = InlineKeyboardMarkup(buttons)
            if update.callback_query:
                await update.callback_query.edit_message_text(text=message_text, reply_markup=reply_markup)
                await update.callback_query.answer()
            else:
                await context.bot.send_message(chat_id=chat_id, text=message_text, reply_markup=reply_markup)

    async def show_main_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
        buttons = [
            [InlineKeyboardButton("Дата та час", callback_data="dates")],
            [InlineKeyboardButton("Послуги", callback_data="services")],
            [InlineKeyboardButton("Спеціалісти", callback_data="specialists")]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await context.bot.send_message(chat_id=chat_id, text="Оберіть опцію:", reply_markup=reply_markup)

    async def services_men(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        context.user_data['appointment'] = SessionAppointment()
        context.user_data['appointment'].gender = "men"
        await self.show_main_options(update, context, update.message.chat_id)

    async def services_women(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        context.user_data['appointment'] = SessionAppointment()
        context.user_data['appointment'].gender = "women"
        await self.show_main_options(update, context, update.message.chat_id)

    async def list_services(self, update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int = None,
                            appointment: SessionAppointment = None) -> None:
        if appointment.date and appointment.timeslot:
            formatted_date = datetime.strptime(appointment.date, '%Y-%m-%d').strftime('%d/%m/%Y')
            selected_timeslot = appointment.timeslot
            data = get_cached_data()

            available_specialists = []
            for specialist, dates in data.items():
                if formatted_date in dates and dates[formatted_date].get(selected_timeslot, False):
                    available_specialists.append(specialist)

            services_query = Service.objects.filter(specialists__name__in=available_specialists).distinct()
            services = await sync_to_async(list)(services_query)

        else:
            services = await sync_to_async(list)(Service.objects.all())
            logger.info("No date/timeslot selected - Showing all services.")

        keyboard = [[InlineKeyboardButton(service.name, callback_data=f"service_{service.id}")] for service in services]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = 'Оберіть послугу:'

        if chat_id is None:
            await update.message.reply_text(text, reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

    async def list_specialists(self, update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int = None,
                               appointment: SessionAppointment = None) -> None:
        if appointment.service_id and not appointment.date:
            service = await sync_to_async(Service.objects.get)(id=appointment.service_id)
            specialists = await sync_to_async(list)(service.specialists.all())

        elif appointment.date and not appointment.service_id and appointment.timeslot:
            formatted_date = datetime.strptime(appointment.date, '%Y-%m-%d').strftime('%d/%m/%Y')
            selected_timeslot = appointment.timeslot
            available_specialists = []
            data = get_cached_data()

            for specialist, dates in data.items():
                if formatted_date in dates and dates[formatted_date].get(selected_timeslot, False):
                    try:
                        specialist_obj = await sync_to_async(Specialist.objects.get)(name=specialist)
                        available_specialists.append(specialist_obj)
                    except Specialist.DoesNotExist:
                        continue
            specialists = available_specialists

        elif appointment.date and appointment.service_id and appointment.timeslot:
            service = await sync_to_async(Service.objects.get)(id=appointment.service_id)
            formatted_date = datetime.strptime(appointment.date, '%Y-%m-%d').strftime('%d/%m/%Y')
            selected_timeslot = appointment.timeslot
            available_specialists = []
            data = get_cached_data()

            for specialist in await sync_to_async(list)(service.specialists.all()):
                if specialist.name in data and formatted_date in data[specialist.name] and data[specialist.name][
                    formatted_date].get(selected_timeslot, False):
                    available_specialists.append(specialist)
            specialists = available_specialists

        else:
            specialists = await sync_to_async(list)(Specialist.objects.all())
            logger.info("No specific filters applied - Showing all specialists.")

        keyboard = [[InlineKeyboardButton(s.name, callback_data=f"specialist_{s.id}")] for s in specialists]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = 'Оберіть спеціаліста:'

        if chat_id is None:
            await update.message.reply_text(text, reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

    async def list_user_appointments(self, update: Update, context: CallbackContext) -> None:
        user_id = update.effective_user.id

        appointments = await sync_to_async(list)(Appointment.objects.filter(
            client__telegram_id=user_id,
            date_time__gte=timezone.now()
        ))

        if appointments:
            for appointment in appointments:
                appointment_text = await sync_to_async(str)(appointment)
                await context.bot.send_message(chat_id=update.effective_chat.id, text=appointment_text)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="No appointments found.")

    def handle(self, *args, **kwargs) -> None:
        application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        application.add_handler(CommandHandler('start', self.start))
        application.add_handler(CallbackQueryHandler(self.callback_query_handler))
        application.add_handler(CommandHandler("appointments", self.list_user_appointments))
        application.add_handler(MessageHandler(filters.CONTACT, self.contact_handler))

        application.run_polling()
