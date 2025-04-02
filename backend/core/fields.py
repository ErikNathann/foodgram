import base64

from django.core.files.base import ContentFile
from rest_framework import serializers

BASE62 = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'


class Base64ImageField(serializers.ImageField):
    """Поле для обработки изображений в формате base64."""

    def to_internal_value(self, data):
        """Декодирование изображения из base64 и сохранение в формате файла."""
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'temp.{ext}')
        return super().to_internal_value(data)


class Base62Field:
    """Утилита для кодирования и декодирования в Base62."""
    @staticmethod
    def to_base62(num):
        """Конвертирует число в строку в формате Base62."""
        if num == 0:
            return BASE62[0]
        base62 = []
        while num:
            base62.append(BASE62[num % 62])
            num //= 62
        return ''.join(reversed(base62))

    @staticmethod
    def from_base62(short_code):
        """Конвертирует строку в формате Base62 обратно в число."""
        num = 0
        for char in short_code:
            num = num * 62 + BASE62.index(char)
        return num
