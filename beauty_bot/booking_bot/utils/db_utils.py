from asgiref.sync import sync_to_async
from ..models import Client, Appointment
from booking_bot.utils.common import SessionAppointment, SessionClient
import datetime
from django.utils.timezone import make_aware


async def save_appointment(appointment: SessionAppointment):
    client, _ = await sync_to_async(Client.objects.get_or_create)(
        telegram_id=appointment.client.telegram_id,
        defaults={'username': appointment.client.username,
                  'phone_number': appointment.client.phone_number,
                  'name': appointment.client.name}
    )

    start_time_str = appointment.timeslot.split(' - ')[0]
    start_time = datetime.datetime.strptime(start_time_str, '%H:%M').time()

    appointment_date = datetime.datetime.strptime(appointment.date, '%Y-%m-%d').date()

    date_time = datetime.datetime.combine(appointment_date, start_time)

    date_time = make_aware(date_time)

    appointment_model = await sync_to_async(Appointment.objects.create)(
        client=client,
        service_id=appointment.service_id,
        specialist_id=appointment.specialist_id,
        date_time=date_time
    )

    return appointment_model
