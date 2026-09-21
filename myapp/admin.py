from django.contrib import admin
from .models import Room, Booking

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("number", "price_per_night")
    list_filter = ("price_per_night",)

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("room", "check_in", "check_out", "notes", "guest_name", "guest_phone", "created_at")
    list_filter = ("room",)
    search_fields = ("date",)

