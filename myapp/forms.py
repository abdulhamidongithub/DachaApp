from django import forms
from .models import Room, Booking


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ["room", "guest_name", "guest_phone", "date", "total_price", "prepaid_amount", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ["number", "price_per_night"]