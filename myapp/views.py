import calendar
from datetime import date, datetime, timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, F, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView, TemplateView
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.db.models.functions import TruncDate, TruncMonth

from .forms import NewBookingForm, BookingForm, PaymentForm, RoomForm, ExpenseForm
from .models import Booking, Payment, Room, Expense

def _parse(value):
    try:
        return parse_date(value) if value else None
    except ValueError:
        return None

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
    form_class = NewBookingForm
    template_name = "bookings/booking_form.html"
    success_url = reverse_lazy("booking-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["rooms"] = Room.objects.all()
        return ctx

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        prepayment = form.cleaned_data.get("prepayment_amount")
        if prepayment:
            Payment.objects.create(
                booking=self.object, amount=prepayment,
                note="Oldindan to'lov", recorded_by=self.request.user,
            )
        return response


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

class ExpenseListView(LoginRequiredMixin, ListView):
    model = Expense
    template_name = "expenses/expense_list.html"
    context_object_name = "expenses"

    def _filters(self):
        g = self.request.GET
        if not g:  # first visit: show the current month
            today = timezone.localdate()
            last_day = calendar.monthrange(today.year, today.month)[1]
            return {
                "from": today.replace(day=1).isoformat(),
                "to": today.replace(day=last_day).isoformat(),
                "type": "", "q": "",
            }
        return {k: g.get(k, "") for k in ("from", "to", "type", "q")}

    def get_queryset(self):
        f = self._filters()
        qs = Expense.objects.select_related("user")
        d_from, d_to = _parse(f["from"]), _parse(f["to"])
        if d_from:
            qs = qs.filter(date__gte=d_from)
        if d_to:
            qs = qs.filter(date__lte=d_to)
        if f["type"]:
            qs = qs.filter(type=f["type"])
        if f["q"]:
            qs = qs.filter(note__icontains=f["q"])
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filters"] = self._filters()
        ctx["types"] = Expense.TYPE_CHOICES
        ctx["total"] = self.object_list.aggregate(t=Sum("amount"))["t"] or 0
        return ctx


class ExpenseCreateView(LoginRequiredMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = "expenses/expense_form.html"
    success_url = reverse_lazy("expense-list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    model = Expense
    form_class = ExpenseForm
    template_name = "expenses/expense_form.html"
    success_url = reverse_lazy("expense-list")


class ExpenseDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        get_object_or_404(Expense, pk=pk).delete()
        return redirect("expense-list")

def _months(start, end):
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield date(y, m, 1)
        m += 1
        if m == 13:
            y, m = y + 1, 1


def _as_date(value):
    return value.date() if isinstance(value, datetime) else value


def build_series(start, end):
    """Earnings (payments received) and expenses per day, or per month for long periods."""
    monthly = (end - start).days > 62
    pay_qs = Payment.objects.filter(paid_at__date__gte=start, paid_at__date__lte=end).order_by()
    exp_qs = Expense.objects.filter(date__gte=start, date__lte=end).order_by()

    if monthly:
        pay_rows = pay_qs.annotate(b=TruncMonth("paid_at")).values("b").annotate(t=Sum("amount"))
        exp_rows = exp_qs.annotate(b=TruncMonth("date")).values("b").annotate(t=Sum("amount"))
        buckets = list(_months(start, end))
        fmt = "%m.%Y"
    else:
        pay_rows = pay_qs.annotate(b=TruncDate("paid_at")).values("b").annotate(t=Sum("amount"))
        exp_rows = exp_qs.values(b=F("date")).annotate(t=Sum("amount"))
        buckets = [start + timedelta(days=i) for i in range((end - start).days + 1)]
        fmt = "%d.%m"

    pay = {_as_date(r["b"]): float(r["t"]) for r in pay_rows}
    exp = {_as_date(r["b"]): float(r["t"]) for r in exp_rows}
    return {
        "labels": [b.strftime(fmt) for b in buckets],
        "earnings": [pay.get(b, 0) for b in buckets],
        "expenses": [exp.get(b, 0) for b in buckets],
        "monthly": monthly,
    }


class ReportView(LoginRequiredMixin, TemplateView):
    template_name = "report.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()
        first = today.replace(day=1)
        end_of_month = today.replace(day=calendar.monthrange(today.year, today.month)[1])

        date_from = _parse(self.request.GET.get("from")) or first
        date_to = _parse(self.request.GET.get("to")) or end_of_month
        if date_from > date_to:
            date_from, date_to = date_to, date_from

        bookings_count = Booking.objects.filter(
            is_cancelled=False, check_in__gte=date_from, check_in__lte=date_to
        ).count()
        earnings = Payment.objects.filter(
            paid_at__date__gte=date_from, paid_at__date__lte=date_to
        ).aggregate(t=Sum("amount"))["t"] or 0
        spent = Expense.objects.filter(
            date__gte=date_from, date__lte=date_to
        ).aggregate(t=Sum("amount"))["t"] or 0

        # Don't draw future days as a fake "drop to zero"
        chart_end = min(date_to, today) if date_from <= today else date_to

        last_month_end = first - timedelta(days=1)
        ctx.update({
            "date_from": date_from,
            "date_to": date_to,
            "bookings_count": bookings_count,
            "earnings": earnings,
            "spent": spent,
            "net": earnings - spent,
            "chart_data": build_series(date_from, chart_end),
            "presets": [
                {"label": "Bu oy", "start": first, "end": end_of_month},
                {"label": "O'tgan oy", "start": last_month_end.replace(day=1), "end": last_month_end},
                {"label": "Oxirgi 30 kun", "start": today - timedelta(days=29), "end": today},
                {"label": "Bu yil", "start": today.replace(month=1, day=1), "end": today},
            ],
        })
        return ctx

class BookingAddChargeView(LoginRequiredMixin, View):
    """Adds a new charge to the booking's total (e.g. an extra service), optionally paid immediately."""

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        try:
            amount = int(request.POST.get("charge_amount", 0))
        except ValueError:
            amount = 0
        note = request.POST.get("charge_note", "").strip()
        paid_now = request.POST.get("paid_now") == "on"

        if amount > 0:
            booking.total_price += amount
            booking.save()
            if paid_now:
                Payment.objects.create(
                    booking=booking, amount=amount,
                    note=note or "Qo'shimcha xizmat", recorded_by=request.user,
                )
        return redirect("booking-edit", pk=booking.pk)

class RoomDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        get_object_or_404(Room, pk=pk).delete()
        return redirect("room-list")

