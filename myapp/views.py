from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView
from django.http import JsonResponse

from .forms import BookingForm, RoomForm
from .models import Booking, Room

class RoomBookedDatesView(LoginRequiredMixin, View):
    def get(self, request, pk):
        exclude_id = request.GET.get("exclude")
        qs = Booking.objects.filter(room_id=pk, is_cancelled=False)
        if exclude_id:
            qs = qs.exclude(pk=exclude_id)
        dates = qs.values_list("date", flat=True)
        return JsonResponse({"booked": [d.isoformat() for d in dates]})

class BookingListView(LoginRequiredMixin, ListView):
    """Shows today's bookings by default; ?date= and ?q= filter it."""

    model = Booking
    template_name = "bookings/booking_list.html"
    context_object_name = "bookings"

    def get_queryset(self):
        qs = Booking.objects.select_related("room").filter(is_cancelled=False)
        date_str = self.request.GET.get("date")
        search = self.request.GET.get("q")

        qs = qs.filter(date=date_str) if date_str else qs.filter(date=timezone.localdate())
        if search:
            qs = qs.filter(Q(guest_name__icontains=search) | Q(guest_phone__icontains=search))
        return qs.order_by("room__number")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["selected_date"] = self.request.GET.get("date", timezone.localdate().isoformat())
        return ctx


class BookingCreateView(LoginRequiredMixin, CreateView):
    model = Booking
    form_class = BookingForm
    template_name = "bookings/booking_form.html"
    success_url = reverse_lazy("booking-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class BookingUpdateView(LoginRequiredMixin, UpdateView):
    model = Booking
    form_class = BookingForm
    template_name = "bookings/booking_form.html"
    success_url = reverse_lazy("booking-list")


class BookingCancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        booking.is_cancelled = True
        booking.save()
        return redirect("booking-list")


class BookingMarkPaidView(LoginRequiredMixin, View):
    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        booking.paid_in_full = True
        booking.save()
        return redirect("booking-list")


class RoomListView(LoginRequiredMixin, ListView):
    model = Room
    template_name = "rooms/room_list.html"
    context_object_name = "rooms"


class RoomCreateView(LoginRequiredMixin, CreateView):
    model = Room
    form_class = RoomForm
    template_name = "rooms/room_form.html"
    success_url = reverse_lazy("room-list")


class RoomUpdateView(LoginRequiredMixin, UpdateView):
    model = Room
    form_class = RoomForm
    template_name = "rooms/room_form.html"
    success_url = reverse_lazy("room-list")