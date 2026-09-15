from django.urls import path
from django.contrib import admin
from django.contrib.auth import views as auth_views

from myapp import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", views.BookingListView.as_view(), name="booking-list"),
    path("bookings/add/", views.BookingCreateView.as_view(), name="booking-add"),
    path("bookings/<int:pk>/edit/", views.BookingUpdateView.as_view(), name="booking-edit"),
    path("bookings/<int:pk>/cancel/", views.BookingCancelView.as_view(), name="booking-cancel"),
    path("bookings/<int:pk>/mark-paid/", views.BookingMarkPaidView.as_view(), name="booking-mark-paid"),
    path("rooms/<int:pk>/booked-dates/", views.RoomBookedDatesView.as_view(), name="room-booked-dates"),

    path("rooms/", views.RoomListView.as_view(), name="room-list"),
    path("rooms/add/", views.RoomCreateView.as_view(), name="room-add"),
    path("rooms/<int:pk>/edit/", views.RoomUpdateView.as_view(), name="room-edit"),
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]