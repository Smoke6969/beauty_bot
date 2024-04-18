import asyncio
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz
from django.conf import settings


def get_calendar_service():
    creds = Credentials.from_service_account_file(
        settings.BASE_DIR / 'secrets' / 'google-sheets-api.json',
        scopes=['https://www.googleapis.com/auth/calendar']
    )
    service = build('calendar', 'v3', credentials=creds)
    return service


async def create_calendar_event(calendar_id, appointment):
    loop = asyncio.get_event_loop()
    service = await loop.run_in_executor(None, get_calendar_service)

    start_time = datetime.strptime(f"{appointment.date} {appointment.timeslot.split(' - ')[0]}", '%Y-%m-%d %H:%M')
    end_time = datetime.strptime(f"{appointment.date} {appointment.timeslot.split(' - ')[1]}", '%Y-%m-%d %H:%M')
    timezone = 'Europe/Kiev'
    event = {
        'summary': f"{appointment.service_name} - {appointment.client.phone_number}",
        'location': 'Saloon5',
        'description': f"{appointment.service_name} з {appointment.client.phone_number}",
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': timezone,
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': timezone,
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }

    event = await loop.run_in_executor(None,
                                       lambda: service.events().insert(calendarId=calendar_id, body=event).execute())
    print('Event created: %s' % (event.get('htmlLink')))
