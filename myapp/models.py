from datetime import timedelta

from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db.models import Q


class Room(models.Model):
    number = models.CharField(
        max_length=20,
        unique=True,
        help_text="Xona raqami yoki nomi, masalan: '101'",
    )
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"Room {self.number}"

    def is_available(self, check_in, check_out, exclude_booking_id=None):
        qs = self.bookings.filter(is_cancelled=False).filter(
            Q(check_in__lt=check_out) & Q(check_out__gt=check_in)
        )
        if exclude_booking_id:
            qs = qs.exclude(pk=exclude_booking_id)
        return not qs.exists()


class Booking(models.Model):
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, related_name="bookings")
    guest_name = models.CharField(max_length=50)
    guest_phone = models.CharField(max_length=20)

    check_in = models.DateField(help_text="Kirish sanasi")
    check_out = models.DateField(help_text="Chiqish sanasi (shu kunning tuni band qilinmaydi)")

    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    is_cancelled = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="bookings_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-check_in"]

    def __str__(self):
        return f"{self.room} | {self.guest_name} | {self.check_in} -> {self.check_out}"

    @property
    def nights(self):
        return (self.check_out - self.check_in).days

    @property
    def net_total(self):
        """Total price after discount — this is what the guest actually owes."""
        return self.total_price - self.discount_amount

    @property
    def amount_paid(self):
        return sum((p.amount for p in self.payments.all()), start=0) or 0

    @property
    def balance_due(self):
        return self.net_total - self.amount_paid

    @property
    def is_paid_in_full(self):
        return self.balance_due <= 0

    def clean(self):
        if self.check_out <= self.check_in:
            raise ValidationError("Chiqish sanasi kirish sanasidan keyin bo'lishi kerak.")
        if self.discount_amount > self.total_price:
            raise ValidationError("Chegirma umumiy summadan katta bo'la olmaydi.")
        if self.room_id and not self.is_cancelled:
            if not self.room.is_available(self.check_in, self.check_out, exclude_booking_id=self.pk):
                raise ValidationError(f"{self.room} {self.check_in} - {self.check_out} oralig'ida band.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Payment(models.Model):
    """One payment received against a booking — prepayment, an extra payment, or final settlement."""

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.CharField(
        max_length=100, blank=True,
        help_text="Masalan: 'Oldindan to'lov', 'Qo'shimcha xizmat', 'Yakuniy to'lov'",
    )
    paid_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="payments_recorded"
    )

    class Meta:
        ordering = ["paid_at"]

    def __str__(self):
        return f"{self.amount} — {self.booking}"

    def clean(self):
        if self.amount <= 0:
            raise ValidationError("To'lov summasi musbat bo'lishi kerak.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)