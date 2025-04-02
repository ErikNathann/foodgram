from core.fields import Base64ImageField
from django.contrib.auth import get_user_model
from rest_framework import serializers
from users.serializers import UserSerializer

from .models import Ingredient, Recipe, RecipeIngredient, Tag

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
    image = serializers.ImageField(use_url=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )


    def get_ingredients(self, obj):
        """Получение списка ингредиентов с количеством."""
        return [
            {
                'id': ri.ingredient.id,
                'name': ri.ingredient.name,
                'measurement_unit': ri.ingredient.measurement_unit,
                'amount': ri.amount
            }
            for ri in obj.recipe_ingredients.all()
        ]

    def check_user_relation(self, obj, related_name):
        """Универсальная проверка наличия рецепта в списках пользователя."""
        user = self.context['request'].user
        return (
            user.is_authenticated
            and getattr(obj, related_name).filter(user=user).exists()
        )

    def get_is_favorited(self, obj):
        """Проверка, добавлен ли рецепт в избранное пользователя."""
        return self.check_user_relation(obj, 'favorite_by_users')

    def get_is_in_shopping_cart(self, obj):
        """Проверка, добавлен ли рецепт в список покупок пользователя."""
        return self.check_user_relation(obj, 'shoppingcart_by_users')


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

    def find_double(self, ids):
        """Проверка на дублирующиеся значения."""
        double = set(
            element.id for element in ids if ids.count(element) >= 2
        )
        if double:
            raise serializers.ValidationError(f'Есть дубли: {double}.')
        return ids

    def validate_tags(self, tags):
        """Проверка на дубли тегов."""
        return self.find_double(tags)

    def validate_ingredients(self, ingredients_amounts):
        """Проверка на дубли ингредиентов."""
        self.find_double(
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

    def save_recipes(self, recipe, ingredients):
        """Сохранение ингредиентов в рецепте."""
        RecipeIngredient.objects.bulk_create(
            RecipeIngredient(
                recipe=recipe,
                ingredient=ing['id'],
                amount=ing['amount']
            ) for ing in ingredients
        )

    def create(self, validated_data):
        """Создание нового рецепта."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['author'] = request.user
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = super().create(validated_data)
        recipe.tags.set(tags)
        self.save_recipes(recipe, ingredients)
        return recipe

    def update(self, instance, validated_data):
        """Обновление существующего рецепта."""
        instance.tags.set(validated_data.pop('tags'))
        instance.ingredients.clear()
        self.save_recipes(instance, validated_data.pop('ingredients'))
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        """Возвращение рецепта в виде детального представления."""
        return RecipeReadSerializer(
            context=self.context).to_representation(instance)


class RecipeShortSerializer(serializers.ModelSerializer):
    """
    Сериализатор для объединения FavoriteSerializer и ShoppingCartSerializer.
    """
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FavoriteSerializer(RecipeShortSerializer):
    """Сериализатор для избранных рецептов."""
    pass


class ShoppingCartSerializer(RecipeShortSerializer):
    """Сериализатор для списка покупок."""
    pass
