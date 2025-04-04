from collections import Counter

from django.contrib.auth import get_user_model
from rest_framework import serializers

from core.fields import Base64ImageField
from users.serializers import UserSerializer

from .models import (
    Ingredient, Recipe, RecipeIngredient, Tag, Favorite, ShoppingCart
)

User = get_user_model()


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Tag."""
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Ingredient."""
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientAmountSerializer(serializers.ModelSerializer):
    """
    Сериализатор для ингредиентов с указанием их количества.

    Используется для создания рецептов.
    """
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all()
    )
    amount = serializers.IntegerField(min_value=1)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отображения ингредиентов в рецептах.
    """

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для детального отображения рецепта."""

    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    author = UserSerializer()
    ingredients = RecipeIngredientSerializer(
        many=True, source='recipe_ingredients'
    )
    tags = TagSerializer(many=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )

    def _check_user_relation(self, obj, related_name):
        """Универсальная проверка наличия рецепта в списках пользователя."""
        user = self.context['request'].user
        return (
            user.is_authenticated
            and getattr(obj, related_name).filter(user=user).exists()
        )

    def get_is_favorited(self, obj):
        """Проверка, добавлен ли рецепт в избранное пользователя."""
        return self._check_user_relation(obj, 'favorite_by_users')

    def get_is_in_shopping_cart(self, obj):
        """Проверка, добавлен ли рецепт в список покупок пользователя."""
        return self._check_user_relation(obj, 'shoppingcart_by_users')


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и редактирования рецептов."""
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True, required=True
    )
    ingredients = IngredientAmountSerializer(many=True, required=True)
    image = Base64ImageField(use_url=True, required=True)
    cooking_time = serializers.IntegerField(min_value=1)

    class Meta:
        model = Recipe
        fields = '__all__'
        extra_kwargs = {'author': {'required': False}}

    def validate_image(self, image):
        """Проверка, что изображение добавлено."""
        if not image:
            raise serializers.ValidationError('Добавьте фотографию рецепта.')
        return image

    def _find_double(self, ids):
        """Проверка на дублирующиеся значения."""
        counter = Counter(ids)
        duplicates = [item for item, count in counter.items() if count > 1]
        if duplicates:
            raise serializers.ValidationError(f'Есть дубли: {duplicates}.')
        return ids

    def validate_tags(self, tags):
        """Проверка на дубли тегов."""
        return self._find_double(tags)

    def validate_ingredients(self, ingredients_amounts):
        """Проверка на дубли ингредиентов."""
        self._find_double(
            [
                ingredient_amont['id']
                for ingredient_amont in ingredients_amounts
            ]
        )
        return ingredients_amounts

    def validate(self, recipe):
        """Проверка на заполненность ингредиентов и тегов."""
        if not recipe.get('ingredients'):
            raise serializers.ValidationError('Добавьте хотя бы 1 ингредиент.')
        if not recipe.get('tags'):
            raise serializers.ValidationError('Добавьте хотя бы 1 тег.')
        return recipe

    def add_ingredients_to_recipe(self, recipe, ingredients):
        """Сохранение ингредиентов в рецепте."""
        RecipeIngredient.objects.bulk_create(
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient['id'],
                amount=ingredient['amount']
            ) for ingredient in ingredients
        )

    def create(self, validated_data):
        """Создание нового рецепта."""
        validated_data['author'] = self.context['request'].user
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = super().create(validated_data)
        recipe.tags.set(tags)
        self.add_ingredients_to_recipe(recipe, ingredients)
        return recipe

    def update(self, instance, validated_data):
        """Обновление существующего рецепта."""
        instance.tags.clear()
        instance.tags.set(validated_data.pop('tags'))
        instance.ingredients.clear()
        self.add_ingredients_to_recipe(
            instance, validated_data.pop('ingredients')
        )
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        """Возвращение рецепта в виде детального представления."""
        return RecipeReadSerializer(instance, context=self.context).data


class RecipeShortSerializer(serializers.ModelSerializer):
    """
    Сериализатор для объединения FavoriteSerializer и ShoppingCartSerializer.
    """
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FavoriteCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления рецепта в избранное."""
    class Meta:
        model = Favorite
        fields = ('user', 'recipe')

    def validate(self, data):
        """Проверяет, не добавлен ли рецепт уже в избранное."""
        user = data['user']
        recipe = data['recipe']
        if Favorite.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError('Рецепт уже в избранном.')
        return data

    def to_representation(self, instance):
        """Возвращаем нужный формат для рецепта в избранном."""
        return RecipeShortSerializer(
            instance.recipe, context=self.context
        ).data


class ShoppingCartCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления рецепта в корзину."""
    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')

    def validate(self, data):
        """Проверяет, не добавлен ли рецепт уже в корзину."""
        user = data['user']
        recipe = data['recipe']
        if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError('Рецепт уже в корзине.')
        return data

    def to_representation(self, instance):
        """Возвращаем нужный формат для рецепта в корзине."""
        return RecipeShortSerializer(
            instance.recipe,
            context=self.context
        ).data
