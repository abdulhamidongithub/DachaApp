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

    def is_available(self, check_in, check_out, exclude_booking_id=None):
        """True if this room has no active booking overlapping the given range."""
        qs = self.bookings.filter(is_cancelled=False).filter(
            Q(check_in__lt=check_out) & Q(check_out__gt=check_in)
        )
        if exclude_booking_id:
            qs = qs.exclude(pk=exclude_booking_id)
        return not qs.exists()



