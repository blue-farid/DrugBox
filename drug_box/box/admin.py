from django.contrib import admin
from .models import User, DosageSchedule, EventLog

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('name', 'rfid_code', 'fingerprint_id')
    search_fields = ('name', 'rfid_code', 'fingerprint_id')
    list_filter = ('name',)

@admin.register(DosageSchedule)
class DosageScheduleAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'dosage')
    list_filter = ('date', 'user')
    search_fields = ('user__name', 'date')
    date_hierarchy = 'date'

@admin.register(EventLog)
class EventLogAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'user', 'status', 'event_time')
    list_filter = ('event_type', 'status', 'event_time')
    search_fields = ('event_type', 'user__name', 'message')
    date_hierarchy = 'event_time'
    readonly_fields = ('event_time',)
