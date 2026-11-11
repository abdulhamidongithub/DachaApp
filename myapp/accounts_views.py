import logging
import secrets

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.utils import timezone
from django.views import View
from django.views.generic import FormView, TemplateView

from .forms import OTPForm, RegisterForm
from .models import EmailOTP, Profile, Resort

User = get_user_model()
logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 5
RESEND_SECONDS = 60


def send_otp(user):
    code = f"{secrets.randbelow(10**6):06d}"
    EmailOTP.objects.update_or_create(
        user=user,
        defaults={"code_hash": make_password(code), "created_at": timezone.now(), "attempts": 0},
    )
    send_mail(
        subject="Kurort Tizimi — tasdiqlash kodi",
        message=(
            f"Tasdiqlash kodingiz: {code}\n\n"
            "Kod 10 daqiqa davomida amal qiladi.\n"
            "Agar siz ro'yxatdan o'tmagan bo'lsangiz, bu xatga e'tibor bermang."
        ),
        from_email=None,
        recipient_list=[user.email],
    )


class LandingView(TemplateView):
    template_name = "landing.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("booking-list")
        return super().dispatch(request, *args, **kwargs)


class RegisterView(FormView):
    template_name = "registration/register.html"
    form_class = RegisterForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("booking-list")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        data = form.cleaned_data
        user = User.objects.filter(username__iexact=data["email"]).first()
        if user:  # unverified leftover: refresh its password and resort name
            user.set_password(data["password"])
            user.save()
            Resort.objects.filter(members__user=user).update(name=data["resort_name"])
        else:
            user = User.objects.create_user(
                username=data["email"], email=data["email"], password=data["password"], is_active=False
            )
            Profile.objects.create(user=user, resort=Resort.objects.create(name=data["resort_name"]))

        try:
            send_otp(user)
        except Exception:
            logger.exception("OTP email failed")
            form.add_error(None, "Email yuborib bo'lmadi. Birozdan so'ng qayta urinib ko'ring.")
            return self.form_invalid(form)

        self.request.session["pending_user_id"] = user.pk
        return redirect("verify-email")


class VerifyEmailView(FormView):
    template_name = "registration/verify.html"
    form_class = OTPForm

    def dispatch(self, request, *args, **kwargs):
        uid = request.session.get("pending_user_id")
        self.pending_user = User.objects.filter(pk=uid, is_active=False).first() if uid else None
        if not self.pending_user:
            return redirect("register")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["email"] = self.pending_user.email
        return ctx

    def form_valid(self, form):
        user = self.pending_user
        otp = getattr(user, "email_otp", None)

        if otp is None or otp.is_expired():
            form.add_error("code", "Kod muddati tugagan. Yangi kod so'rang.")
            return self.form_invalid(form)
        if otp.attempts >= MAX_ATTEMPTS:
            form.add_error("code", "Urinishlar soni tugadi. Yangi kod so'rang.")
            return self.form_invalid(form)

        otp.attempts += 1
        otp.save(update_fields=["attempts"])
        if not check_password(form.cleaned_data["code"], otp.code_hash):
            form.add_error("code", "Kod noto'g'ri.")
            return self.form_invalid(form)

        user.is_active = True
        user.save(update_fields=["is_active"])
        otp.delete()
        self.request.session.pop("pending_user_id", None)
        login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("booking-list")


class ResendCodeView(View):
    def post(self, request):
        uid = request.session.get("pending_user_id")
        user = User.objects.filter(pk=uid, is_active=False).first() if uid else None
        if not user:
            return redirect("register")

        otp = getattr(user, "email_otp", None)
        if otp and (timezone.now() - otp.created_at).total_seconds() < RESEND_SECONDS:
            messages.error(request, "Yangi kodni so'rashdan oldin bir daqiqa kuting.")
        else:
            try:
                send_otp(user)
                messages.success(request, "Yangi kod yuborildi.")
            except Exception:
                logger.exception("OTP resend failed")
                messages.error(request, "Email yuborib bo'lmadi. Birozdan so'ng qayta urinib ko'ring.")
        return redirect("verify-email")