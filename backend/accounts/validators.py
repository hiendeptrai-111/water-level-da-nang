import re

from django.core.exceptions import ValidationError


class LetterAndDigitValidator:
    """Password must contain at least one letter and one digit."""

    def validate(self, password, user=None):
        if not re.search(r"[^\W\d_]", password) or not re.search(r"\d", password):
            raise ValidationError("Mật khẩu phải có cả chữ và số.", code="password_letter_digit")

    def get_help_text(self):
        return "Mật khẩu phải có cả chữ và số."
