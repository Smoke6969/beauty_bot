class SessionAppointment:
    def __init__(self):
        self.service_id = None
        self.specialist_id = None
        self.specialist_name = None
        self.service_name = None
        self.date = None

    def __str__(self):
        return f"{self.service_name} - {self.specialist_name} - {self.date}"