"""JWT classes whose lifetimes are read from SystemConfig each time a token is issued."""
from datetime import timedelta

from rest_framework_simplejwt import tokens


class ConfigLifetime:
    """Descriptor: token.lifetime -> timedelta built from a SystemConfig key."""

    def __init__(self, key, unit):
        self.key, self.unit = key, unit

    def __get__(self, obj, owner=None):
        from core.services import get_config
        return timedelta(**{self.unit: get_config(self.key)})


class AccessToken(tokens.AccessToken):
    lifetime = ConfigLifetime("jwt_access_minutes", "minutes")


class RefreshToken(tokens.RefreshToken):
    lifetime = ConfigLifetime("jwt_refresh_days", "days")
    access_token_class = AccessToken


def token_pair(user):
    refresh = RefreshToken.for_user(user)
    refresh["role"] = user.role
    refresh["ver"] = user.token_version  # copied into the access token
    access = refresh.access_token
    return {"refresh": str(refresh), "access": str(access)}
