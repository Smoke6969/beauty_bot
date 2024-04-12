from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from django.conf import settings
import datetime
from booking_bot.utils.common import SessionAppointment

# Cache setup
cache = {}
cache_timeout = datetime.timedelta(minutes=3)  # Cache expiration in minutes
last_cache_update = datetime.datetime.min


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
        range_name = f'{sheet_name}!A2:I'
        result = sheet_service.spreadsheets().values().get(
            spreadsheetId=settings.GOOGLE_SHEET_ID,
            range=range_name
        ).execute()
        rows = result.get('values', [])
        filtered_dates = [row[0] for row in rows if any(cell.lower() == 'x' for cell in row[1:])]
        all_data[sheet_name] = filtered_dates

    cache.update({'last_update': datetime.datetime.now(), 'data': all_data})
    last_cache_update = datetime.datetime.now()


def get_cached_data():
    global last_cache_update
    current_time = datetime.datetime.now()
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


