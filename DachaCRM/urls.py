from django.urls import path
from django.contrib import admin
from django.contrib.auth import views as auth_views

from myapp import views
from myapp.forms import UzbekAuthenticationForm


urlpatterns = [
    path('admin/', admin.site.urls),
    path("", views.BookingListView.as_view(), name="booking-list"),
    path("bookings/add/", views.BookingCreateView.as_view(), name="booking-add"),
    path("bookings/<int:pk>/edit/", views.BookingUpdateView.as_view(), name="booking-edit"),
    path("bookings/<int:pk>/cancel/", views.BookingCancelView.as_view(), name="booking-cancel"),
    path("bookings/<int:pk>/settle/", views.BookingSettleView.as_view(), name="booking-settle"),
    path("bookings/<int:pk>/add-payment/", views.PaymentCreateView.as_view(), name="booking-add-payment"),
    path("bookings/<int:pk>/add-charge/", views.BookingAddChargeView.as_view(), name="booking-add-charge"),

    path("rooms/", views.RoomListView.as_view(), name="room-list"),
    path("rooms/add/", views.RoomCreateView.as_view(), name="room-add"),
    path("rooms/<int:pk>/edit/", views.RoomUpdateView.as_view(), name="room-edit"),
    path("rooms/<int:pk>/booked-dates/", views.RoomBookedDatesView.as_view(), name="room-booked-dates"),
    path("rooms/<int:pk>/delete/", views.RoomDeleteView.as_view(), name="room-delete"),

    path("expenses/", views.ExpenseListView.as_view(), name="expense-list"),
    path("expenses/add/", views.ExpenseCreateView.as_view(), name="expense-add"),
    path("expenses/<int:pk>/edit/", views.ExpenseUpdateView.as_view(), name="expense-edit"),
    path("expenses/<int:pk>/delete/", views.ExpenseDeleteView.as_view(), name="expense-delete"),
    path("report/", views.ReportView.as_view(), name="report"),

    path("login/", auth_views.LoginView.as_view(template_name="login.html",authentication_form=UzbekAuthenticationForm,), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]

