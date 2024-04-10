from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from django.conf import settings


def get_sheet_service():
    creds = Credentials.from_service_account_file(
        settings.BASE_DIR / 'secrets' / 'google-sheets-api.json',
        scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
    )
    service = build('sheets', 'v4', credentials=creds)
    return service


def get_available_dates(sheet_service):
    range_name = 'Марія!A2:A'
    result = sheet_service.spreadsheets().values().get(
        spreadsheetId=settings.GOOGLE_SHEET_ID,
        range=range_name
    ).execute()
    dates = result.get('values', [])
    dates = [item[0] for item in dates if item]
    return dates
