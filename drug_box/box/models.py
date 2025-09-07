from django.db import models

class User(models.Model):
    name = models.CharField(max_length=100, verbose_name='نام')
    rfid_code = models.CharField(max_length=255, unique=True, verbose_name='کد RFID')
    fingerprint_id = models.IntegerField(unique=True, verbose_name='شناسه اثر انگشت')

    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'

    def __str__(self):
        return self.name

class DosageSchedule(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dosage_schedules', verbose_name='کاربر')
    date = models.DateField(verbose_name='تاریخ')
    dosage = models.FloatField(verbose_name='مقدار مصرف')
    used = models.BooleanField(verbose_name="وضعیت مصرف", default=False)

    class Meta:
        verbose_name = 'برنامه مصرف دارو'
        verbose_name_plural = 'برنامه‌های مصرف دارو'
        unique_together = ('user', 'date')

    def __str__(self):
        return f"{self.user} - {self.date}: {self.dosage}"

class EventLog(models.Model):
    event_type = models.CharField(max_length=50, verbose_name='نوع رویداد')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='event_logs', verbose_name='کاربر')
    rfid_code = models.CharField(max_length=255, null=True, blank=True, verbose_name='کد RFID')
    fingerprint_id = models.IntegerField(null=True, blank=True, verbose_name='شناسه اثر انگشت')
    status = models.CharField(max_length=20, verbose_name='وضعیت')
    message = models.TextField(null=True, blank=True, verbose_name='پیام')
    event_time = models.DateTimeField(auto_now_add=True, verbose_name='زمان رویداد')

    class Meta:
        verbose_name = 'گزارش رویداد'
        verbose_name_plural = 'گزارش‌های رویداد'

    def __str__(self):
        return f"[{self.event_time}] {self.event_type} - {self.status}"
