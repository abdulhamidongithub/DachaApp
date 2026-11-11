import re
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

from .models import Room, Booking, Payment, Expense

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

    def __init__(self, *args, resort=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["room"].queryset = Room.objects.filter(resort=resort) if resort else Room.objects.none()
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

    def __init__(self, *args, resort=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.resort = resort

    def clean_number(self):
        number = self.cleaned_data["number"]
        qs = Room.objects.filter(resort=self.resort, number=number)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Bunday raqamli xona allaqachon mavjud.")
        return number


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

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["date", "type", "amount", "note"]
        labels = {"date": "Sana", "type": "Turi", "amount": "Summa", "note": "Izoh"}
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "note": forms.TextInput(attrs={"placeholder": "Masalan: bozordan sabzavot"}),
        }

REQUIRED = {"required": "Bu maydonni to'ldiring."}


class RegisterForm(forms.Form):
    resort_name = forms.CharField(label="Kurort nomi", max_length=100, error_messages=REQUIRED)
    email = forms.EmailField(label="Email", error_messages={**REQUIRED, "invalid": "Email noto'g'ri kiritilgan."})
    password = forms.CharField(
        label="Parol", min_length=8, widget=forms.PasswordInput,
        error_messages={**REQUIRED, "min_length": "Parol kamida 8 ta belgidan iborat bo'lishi kerak."},
    )
    password2 = forms.CharField(label="Parolni takrorlang", widget=forms.PasswordInput, error_messages=REQUIRED)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        existing = User.objects.filter(username__iexact=email).first()
        # Only an unverified leftover from an earlier sign-up attempt may register again
        if existing and (existing.is_active or not hasattr(existing, "email_otp")):
            raise ValidationError("Bu email bilan hisob allaqachon mavjud.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Parollar bir xil emas.")
        return cleaned


class OTPForm(forms.Form):
    code = forms.CharField(
        label="Tasdiqlash kodi", min_length=6, max_length=6,
        widget=forms.TextInput(attrs={
            "inputmode": "numeric", "autocomplete": "one-time-code", "maxlength": "6", "placeholder": "123456",
        }),
        error_messages={"required": "Kodni kiriting.", "min_length": "Kod 6 ta raqamdan iborat.",
                        "max_length": "Kod 6 ta raqamdan iborat."},
    )

    def clean_code(self):
        code = self.cleaned_data["code"].strip()
        if not code.isdigit():
            raise ValidationError("Kod faqat raqamlardan iborat bo'lishi kerak.")
        return code