"""Lock logins after too many consecutive failures (values from SystemConfig)."""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core.services import get_config

from .models import LoginAttempt


def attempt_key(user, identifier):
    """Same counter for email and phone of one account; unknown identifiers get their own."""
    if user is not None:
        return f"user:{user.pk}"
    return f"id:{identifier.strip().lower()}"[:255]


def is_locked(key):
    return LoginAttempt.objects.filter(key=key, locked_until__gt=timezone.now()).exists()


@transaction.atomic
def register_failure(key):
    attempt, _ = LoginAttempt.objects.select_for_update().get_or_create(key=key)
    attempt.failures += 1
    if attempt.failures >= get_config("max_failed_logins"):
        attempt.failures = 0
        attempt.locked_until = timezone.now() + timedelta(minutes=get_config("login_lockout_minutes"))
    attempt.save()


def reset(key):
    LoginAttempt.objects.filter(key=key).delete()


def locked_message():
    return (f"Bạn đã nhập sai quá nhiều lần. Vui lòng thử lại sau "
            f"{get_config('login_lockout_minutes')} phút.")
