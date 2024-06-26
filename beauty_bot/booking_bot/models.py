from django.db import models


class Client(models.Model):
    telegram_id = models.CharField(max_length=255, unique=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.name or self.username or 'Unknown'}"


class Service(models.Model):
    name = models.CharField(max_length=100)
    duration = models.DurationField()
    price = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"{self.name}"


class Specialist(models.Model):
    name = models.CharField(max_length=100)
    services = models.ManyToManyField(Service, related_name='specialists')
    email = models.CharField(max_length=100, default='test@gmail.com')
    calendar_id = models.CharField(max_length=100, default='test@gmail.com')

    def __str__(self):
        return f"{self.name}"


class Appointment(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='appointments')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='appointments')
    specialist = models.ForeignKey(Specialist, on_delete=models.CASCADE, related_name='appointments')
    date_time = models.DateTimeField()

    def __str__(self):
        return f"{self.service} - {self.client} - {self.date_time}"
