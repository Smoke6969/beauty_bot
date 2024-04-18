class SessionAppointment:
    def __init__(self):
        self.service_id = None
        self.specialist_id = None
        self.specialist_name = None
        self.service_name = None
        self.date = None
        self.timeslot = None
        self.client = None

    def __str__(self):
        return f"{self.service_name} - {self.specialist_name} - {self.date} - {self.timeslot}"


class SessionClient:
    def __init__(self, telegram_id=None, name=None, phone_number=None, username=None):
        self.telegram_id = telegram_id
        self.name = name
        self.phone_number = phone_number
        self.username = username

    def __str__(self):
        return f"{self.telegram_id} - {self.name} - {self.phone_number} - {self.username}"
