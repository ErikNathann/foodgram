import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from djoser.serializers import UserSerializer
from rest_framework import serializers
from users.models import Follow

from .models import Ingredient, Recipe, RecipeIngredient, Tag

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    """Поле для обработки изображений в формате base64."""

    def to_internal_value(self, data):
        """Декодирование изображения из base64 и сохранение в формате файла."""
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'temp.{ext}')
        return super().to_internal_value(data)


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


class IngredientAmountSerializer(serializers.Serializer):
    """Сериализатор для ингредиентов с указанием их количества."""
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all()
    )
    amount = serializers.IntegerField(min_value=1)


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для работы с рецептами (чтение/запись)."""
    ingredients = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        many=True
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'text', 'image',
                  'ingredients', 'tags', 'cooking_time')

    def create(self, validated_data):
        """Создание рецепта с привязкой ингредиентов и тегов."""
        ingredients = validated_data.pop('ingredients', [])
        tags = validated_data.pop('tags', [])
        recipe = Recipe.objects.create(**validated_data)
        recipe.ingredients.set(ingredients)
        recipe.tags.set(tags)
        return recipe

    def update(self, instance, validated_data):
        """Обновление рецепта с изменением ингредиентов и тегов."""
        ingredients = validated_data.pop(
            'ingredients',
            instance.ingredients.all()
        )
        tags = validated_data.pop('tags', instance.tags.all())
        instance.ingredients.set(ingredients)
        instance.tags.set(tags)
        return super().update(instance, validated_data)


class FollowSerializer(UserSerializer):
    """Сериализатор подписок на пользователей."""
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.ReadOnlyField(source='recipes.count')

    class Meta(UserSerializer.Meta):
        fields = ('following', 'user')


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для детального отображения рецепта."""
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()
    ingredients = serializers.SerializerMethodField()
    tags = TagSerializer(many=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )

    def get_author(self, obj):
        """Получение информации об авторе рецепта."""
        user = self.context['request'].user
        is_subscribed = (
            user.is_authenticated
            and Follow.objects.filter(user=user, following=obj.author).exists()
        )
        return {
            'id': obj.author.id,
            'username': obj.author.username,
            'first_name': obj.author.first_name,
            'last_name': obj.author.last_name,
            'email': obj.author.email,
            'is_subscribed': is_subscribed,
            'avatar': obj.author.avatar.url if obj.author.avatar else None
        }

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

    def get_is_in_shopping_cart(self, obj):
        """Проверка, добавлен ли рецепт в список покупок пользователя."""
        user = self.context['request'].user
        return (
            user.is_authenticated
            and obj.in_shopping_cart.filter(user=user).exists()
        )

    def get_is_favorited(self, obj):
        """Проверка, добавлен ли рецепт в избранное пользователя."""
        user = self.context['request'].user
        return (
            user.is_authenticated
            and obj.favorited_by.filter(user=user).exists()
        )


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


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для избранных рецептов."""
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для списка покупок."""
    class Meta:
        model = Recipe
        fields = ['id', 'name', 'image', 'cooking_time']
