from datetime import timedelta

from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db.models import Q


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

    def is_available(self, date, nights, exclude_booking_id=None):
        """True if this room has no active booking overlapping the given range."""
        check_out = date + timedelta(days=nights)
        qs = self.bookings.filter(is_cancelled=False)
        if exclude_booking_id:
            qs = qs.exclude(pk=exclude_booking_id)
        for booking in qs:
            if booking.date < check_out and booking.check_out > date:
                return False
        return True


class Booking(models.Model):
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True)
    guest_name = models.CharField(max_length=50)
    guest_phone = models.CharField(max_length=15)

    date = models.DateField(help_text="The day the room is booked for / check-in day.")
    nights = models.PositiveSmallIntegerField(
        default=1,
        help_text="1 = same-day, no overnight stay. Bump up only if the guest is actually staying over.",
    )

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
        return f"{self.room} | {self.guest_name} | {self.date} ({self.nights}n)"

    @property
    def check_out(self):
        """The day the room frees up again. Same as `date` + nights."""
        return self.date + timedelta(days=self.nights)

    def clean(self):
        if self.nights < 1:
            raise ValidationError("Nights must be at least 1.")

        if self.prepaid_amount > self.total_price:
            raise ValidationError("Prepaid amount can't be more than the total price.")

        if self.room_id and not self.is_cancelled:
            if not self.room.is_available(self.date, self.nights, exclude_booking_id=self.pk):
                raise ValidationError(
                    f"{self.room} is already booked for part or all of "
                    f"{self.date} to {self.check_out}."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def balance_due(self):
        if self.paid_in_full:
            return 0
        return self.total_price - self.prepaid_amount