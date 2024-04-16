from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from django.conf import settings
from datetime import datetime, timedelta
from booking_bot.utils.common import SessionAppointment

# Cache setup
cache = {}
cache_timeout = timedelta(minutes=3)  # Cache expiration in minutes
last_cache_update = datetime.min

TIMESLOT_HEADERS = [
    "8:00 - 9:00", "9:00 - 10:00", "10:00 - 11:00", "11:00 - 12:00",
    "12:00 - 13:00", "13:00 - 14:00", "15:00 - 16:00", "17:00 - 18:00"
]


def get_sheet_service():
    creds = Credentials.from_service_account_file(
        settings.BASE_DIR / 'secrets' / 'google-sheets-api.json',
        scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
    )
    service = build('sheets', 'v4', credentials=creds)
    return service


def refresh_cache(sheet_service):
    global last_cache_update
    print("Refreshing cache...")
    sheet_metadata = sheet_service.spreadsheets().get(spreadsheetId=settings.GOOGLE_SHEET_ID).execute()
    sheets = sheet_metadata.get('sheets', '')
    sheet_names = [sheet['properties']['title'] for sheet in sheets]

    all_data = {}
    for sheet_name in sheet_names:
        range_name = f'{sheet_name}!A2:I'  # Adjust range if necessary
        result = sheet_service.spreadsheets().values().get(
            spreadsheetId=settings.GOOGLE_SHEET_ID,
            range=range_name
        ).execute()
        rows = result.get('values', [])
        sheet_data = {}
        for row in rows:
            date = row[0]
            timeslot_data = row[1:]
            timeslots = {TIMESLOT_HEADERS[i]: (availability.lower() == 'x') if len(availability) > 0 else False for
                         i, availability in enumerate(timeslot_data)}
            if any(timeslots.values()):
                sheet_data[date] = timeslots
        all_data[sheet_name] = sheet_data

    cache.update({'last_update': datetime.now(), 'data': all_data})
    last_cache_update = datetime.now()


def get_cached_data():
    global last_cache_update
    current_time = datetime.now()
    if current_time - last_cache_update > cache_timeout or not cache:
        sheet_service = get_sheet_service()
        refresh_cache(sheet_service)
    return cache['data']


def get_available_dates(appointment: SessionAppointment):
    data = get_cached_data()
    if appointment.specialist_name:
        return data.get(appointment.specialist_name, [])
    else:
        all_dates = set()
        for sheet_dates in data.values():
            all_dates.update(sheet_dates)
        return list(all_dates)


def get_available_timeslots(appointment, selected_date):
    data = get_cached_data()
    available_timeslots = []
    selected_date_dt = datetime.strptime(selected_date, '%Y-%m-%d')

    if appointment.specialist_name:
        specialist_schedule = data.get(appointment.specialist_name, {})
        for date, timeslots in specialist_schedule.items():
            date_dt = datetime.strptime(date, '%d/%m/%Y')
            if date_dt == selected_date_dt:
                available_timeslots.extend([time for time, available in timeslots.items() if available])
    else:
        all_times = set()
        for specialist_schedule in data.values():
            for date, timeslots in specialist_schedule.items():
                date_dt = datetime.strptime(date, '%d/%m/%Y')
                if date_dt == selected_date_dt:
                    all_times.update([time for time, available in timeslots.items() if available])
        available_timeslots = list(all_times)

    available_timeslots.sort(key=lambda x: datetime.strptime(x.split(' - ')[0], '%H:%M'))
    return available_timeslots






