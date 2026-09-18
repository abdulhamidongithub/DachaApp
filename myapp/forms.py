class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ["room", "guest_name", "guest_phone", "date", "total_price", "prepaid_amount", "notes"]
        labels = {
            "room": "Xona",
            "guest_name": "Mehmon ismi",
            "guest_phone": "Telefon raqami",
            "date": "Sana",
            "total_price": "Umumiy summa",
            "prepaid_amount": "Oldindan to'lov",
            "notes": "Izoh",
        }
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ["number", "price_per_night"]
        labels = {
            "number": "Xona raqami",
            "price_per_night": "Kunlik narx",
        }