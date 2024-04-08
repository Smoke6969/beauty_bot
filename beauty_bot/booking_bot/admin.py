from django.contrib import admin
from .models import Client, Service, Specialist, Appointment

# Register your models here.
admin.site.register(Client)
admin.site.register(Service)
admin.site.register(Specialist)
admin.site.register(Appointment)
