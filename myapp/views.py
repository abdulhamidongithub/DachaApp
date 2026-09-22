from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from .forms import BookingForm, PaymentForm, RoomForm
from .models import Booking, Payment, Room


class BookingListView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = "bookings/booking_list.html"
    context_object_name = "bookings"

    def get_queryset(self):
        qs = Booking.objects.select_related("room").filter(is_cancelled=False)
        date_from = self.request.GET.get("from")
        date_to = self.request.GET.get("to")
        room_id = self.request.GET.get("room")
        search = self.request.GET.get("q")

        if date_from:
            qs = qs.filter(check_out__gt=date_from)
        if date_to:
            qs = qs.filter(check_in__lt=date_to)
        if room_id:
            qs = qs.filter(room_id=room_id)
        if search:
            qs = qs.filter(Q(guest_name__icontains=search) | Q(guest_phone__icontains=search))
        return qs.order_by("check_in", "room__number")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["rooms"] = Room.objects.all()
        ctx["date_from"] = self.request.GET.get("from", "")
        ctx["date_to"] = self.request.GET.get("to", "")

        room_id = self.request.GET.get("room")
        ctx["selected_room"] = int(room_id) if room_id else None
        return ctx


class BookingCreateView(LoginRequiredMixin, CreateView):
    model = Booking
    form_class = BookingForm
    template_name = "bookings/booking_form.html"
    success_url = reverse_lazy("booking-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["rooms"] = Room.objects.all()
        return ctx

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class BookingUpdateView(LoginRequiredMixin, UpdateView):
    model = Booking
    form_class = BookingForm
    template_name = "bookings/booking_form.html"
    success_url = reverse_lazy("booking-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["rooms"] = Room.objects.all()
        ctx["payment_form"] = PaymentForm()
        ctx["payments"] = self.object.payments.all()
        return ctx


class BookingCancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        booking.is_cancelled = True
        booking.save()
        return redirect("booking-list")


class PaymentCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.booking = booking
            payment.recorded_by = request.user
            payment.save()
        return redirect("booking-edit", pk=booking.pk)


class BookingSettleView(LoginRequiredMixin, View):
    """Convenience button: records one payment for exactly the remaining balance."""

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        remaining = booking.balance_due
        if remaining > 0:
            Payment.objects.create(booking=booking, amount=remaining, note="Yakuniy to'lov", recorded_by=request.user)
        return redirect("booking-edit", pk=booking.pk)


class RoomBookedDatesView(LoginRequiredMixin, View):
    def get(self, request, pk):
        exclude_id = request.GET.get("exclude")
        qs = Booking.objects.filter(room_id=pk, is_cancelled=False)
        if exclude_id:
            qs = qs.exclude(pk=exclude_id)
        booked = set()
        for b in qs:
            d = b.check_in
            while d < b.check_out:
                booked.add(d.isoformat())
                d += timedelta(days=1)
        return JsonResponse({"booked": sorted(booked)})


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