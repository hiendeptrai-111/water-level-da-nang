from rest_framework_simplejwt import authentication
from rest_framework_simplejwt.exceptions import InvalidToken


def is_revoked(user, payload):
    """True when the token was issued before the user's tokens were revoked."""
    return payload.get("ver") != user.token_version


class JWTAuthentication(authentication.JWTAuthentication):
    """simplejwt authentication + reject tokens issued before a password change/lock."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if is_revoked(user, validated_token.payload):
            raise InvalidToken("Phiên đăng nhập đã hết hiệu lực, vui lòng đăng nhập lại.")
        return user
