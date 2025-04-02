from core.constants import (
    EMAIL_MAX_LENGTH,
    FIRST_NAME_MAX_LENGTH,
    LAST_NAME_MAX_LENGTH,
    USERNAME_MAX_LENGTH
)
from core.validators import validate_username
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models


class User(AbstractUser):
    """Модель пользователя проекта."""
    username_validator = UnicodeUsernameValidator()

    email = models.EmailField(
        unique=True,
        max_length=EMAIL_MAX_LENGTH,
        verbose_name='Адрес электронной почты'
    )
    username = models.CharField(
        max_length=USERNAME_MAX_LENGTH,
        unique=True,
        verbose_name='Имя пользователя',
        validators=[username_validator, validate_username],
    )
    first_name = models.CharField(
        max_length=FIRST_NAME_MAX_LENGTH,
        verbose_name='Имя'
    )
    last_name = models.CharField(
        max_length=LAST_NAME_MAX_LENGTH,
        verbose_name='Фамилия'
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        default='avatars/userpic-icon.jpg',
        verbose_name='Аватар'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'


class Follow(models.Model):
    """
    Модель подписки, которая определяет отношение между подписчиком и автором.
    """
    user = models.ForeignKey(
        User,
        verbose_name='Подписчик',
        on_delete=models.CASCADE,
        related_name='followers',
    )
    following = models.ForeignKey(
        User,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='following',
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        ordering = ['user']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'following'],
                name='unique_user_following',
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F('following')),
                name='prevent_self_follow',
            )
        ]

    def __str__(self):
        return f'Пользователь {self.user} подписчик автора - {self.following}'
