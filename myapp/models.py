from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings


class Room(models.Model):
    number = models.CharField(
        max_length=20,
        unique=True,
        help_text="Xona raqami yoki nomi, masalan: '101' yoki 'Ayvon oldi 1'",
    )
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"Room {self.number}"

    def is_available(self, date, exclude_booking_id=None):
        """True if this room has no active booking on the given date."""
        qs = self.bookings.filter(is_cancelled=False, date=date)
        if exclude_booking_id:
            qs = qs.exclude(pk=exclude_booking_id)
        return not qs.exists()


class Booking(models.Model):
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, related_name="bookings")
    guest_name = models.CharField(max_length=50)
    guest_phone = models.CharField(max_length=15)

    date = models.DateField(help_text="The day the room is booked for.")

    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    prepaid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_in_full = models.BooleanField(
        default=False,
        help_text="Tick this once the remaining balance is collected at check-in/visit.",
    )

    is_cancelled = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="bookings_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.room} | {self.guest_name} | {self.date}"

    def clean(self):
        if self.prepaid_amount > self.total_price:
            raise ValidationError("Prepaid amount can't be more than the total price.")

        if self.room_id and not self.is_cancelled:
            if not self.room.is_available(self.date, exclude_booking_id=self.pk):
                raise ValidationError(f"{self.room} is already booked on {self.date}.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def balance_due(self):
        if self.paid_in_full:
            return 0
        return self.total_price - self.prepaid_amount


