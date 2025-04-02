from recipes.models import Recipe
from rest_framework import serializers


class RecipeShortSerializer(serializers.ModelSerializer):
    """
    Короткий сериализатор для отображения рецептов в подписках.
    """
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
