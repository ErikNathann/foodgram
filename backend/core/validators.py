from django.core.exceptions import ValidationError

from .constants import DISALLOWED_USERNAMES


def validate_username(value):
    """Запрещает использование 'me' в качестве имени пользователя."""
    if value.lower() in DISALLOWED_USERNAMES:
        raise ValidationError(
            f"Имя пользователя '{value}' запрещено. "
            "Пожалуйста, выберите другое имя."
        )
    return value
