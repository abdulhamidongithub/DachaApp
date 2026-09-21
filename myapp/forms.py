import re
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Room, Booking, Payment

PHONE_DIGITS_RE = re.compile(r'^\+998\d{9}$')


class BookingForm(forms.ModelForm):
    guest_phone = forms.CharField(
        label="Telefon raqami",
        initial="+998 ",
        widget=forms.TextInput(attrs={"placeholder": "+998 90 6690097"}),
    )

    class Meta:
        model = Booking
        fields = ["room", "guest_name", "guest_phone", "check_in", "check_out", "total_price", "discount_amount", "notes"]
        labels = {
            "room": "Xona",
            "guest_name": "Mehmon ismi",
            "check_in": "Kirish sanasi",
            "check_out": "Chiqish sanasi",
            "total_price": "Umumiy summa",
            "discount_amount": "Chegirma",
            "notes": "Izoh",
        }
        widgets = {
            "room": forms.HiddenInput(),
            "check_in": forms.HiddenInput(),
            "check_out": forms.HiddenInput(),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_guest_phone(self):
        raw = self.cleaned_data["guest_phone"]
        digits_only = raw.replace(" ", "")
        if not PHONE_DIGITS_RE.match(digits_only):
            raise ValidationError(
                "Telefon raqami +998 bilan boshlanib, jami 9 ta raqamdan iborat bo'lishi kerak. "
                "Masalan: +998 90 6690097"
            )
        core = digits_only[4:]  # 9 digits after +998
        return f"+998 {core[:2]} {core[2:]}"  # normalize to a consistent display format

    def clean_check_in(self):
        check_in = self.cleaned_data["check_in"]
        # Only block past dates on NEW bookings — editing an existing (already past) one shouldn't break.
        if self.instance.pk is None and check_in < timezone.localdate():
            raise ValidationError("Kirish sanasi bugungi kundan oldin bo'la olmaydi.")
        return check_in


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["amount", "note"]
        labels = {"amount": "Summa", "note": "Izoh"}
        widgets = {"note": forms.TextInput(attrs={"placeholder": "Masalan: qo'shimcha xizmat"})}


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ["number", "price_per_night"]
        labels = {"number": "Xona raqami", "price_per_night": "Kunlik narx"}