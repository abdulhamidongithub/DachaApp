import re
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from .models import Room, Booking, Payment

PHONE_LOCAL_RE = re.compile(r'^\d{9}$')


class BookingForm(forms.ModelForm):
    phone_local = forms.CharField(
        label="Telefon raqami",
        widget=forms.TextInput(attrs={
            "placeholder": "90 6690097",
            "inputmode": "numeric",
            "maxlength": "9",
        }),
    )

    class Meta:
        model = Booking
        fields = ["room", "guest_name", "check_in", "check_out", "total_price", "discount_amount", "notes"]
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.guest_phone:
            digits = re.sub(r'\D', '', self.instance.guest_phone)
            self.fields['phone_local'].initial = digits[-9:]

    def clean_phone_local(self):
        digits_only = re.sub(r'\D', '', self.cleaned_data['phone_local'])
        if not PHONE_LOCAL_RE.match(digits_only):
            raise ValidationError("Telefon raqami 9 ta raqamdan iborat bo'lishi kerak, masalan: 90 6690097")
        return digits_only

    def clean_check_in(self):
        check_in = self.cleaned_data["check_in"]
        if self.instance.pk is None and check_in < timezone.localdate():
            raise ValidationError("Kirish sanasi bugungi kundan oldin bo'la olmaydi.")
        return check_in

    def save(self, commit=True):
        instance = super().save(commit=False)
        local = self.cleaned_data['phone_local']
        instance.guest_phone = f"+998 {local[:2]} {local[2:]}"
        if commit:
            instance.save()
        return instance


class NewBookingForm(BookingForm):
    """Same as BookingForm, plus an optional prepayment — only used when creating a booking."""

    prepayment_amount = forms.DecimalField(
        label="Oldindan to'lov (ixtiyoriy)",
        required=False, min_value=0, max_digits=10, decimal_places=2,
        widget=forms.NumberInput(attrs={"placeholder": "0"}),
    )

    def clean(self):
        cleaned = super().clean()
        prepayment = cleaned.get('prepayment_amount')
        total_price = cleaned.get('total_price')
        discount = cleaned.get('discount_amount') or 0
        if prepayment and total_price is not None:
            net_total = total_price - discount
            if prepayment > net_total:
                raise ValidationError("Oldindan to'lov umumiy summadan (chegirmadan keyin) katta bo'la olmaydi.")
        return cleaned


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


class UzbekAuthenticationForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Login yoki parolda xatolik.",
        "inactive": "Bu hisob faol emas.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = "Login"
        self.fields['username'].error_messages = {"required": "Login kiritilishi kerak."}
        self.fields['password'].label = "Parol"
        self.fields['password'].error_messages = {"required": "Parol kiritilishi kerak."}