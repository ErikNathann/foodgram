from djoser.serializers import UserSerializer
from recipes.models import Recipe
from rest_framework import serializers
from users.models import User


class RecipeShortSerializer(serializers.ModelSerializer):
    """
    Короткий сериализатор для отображения рецептов в подписках.
    """
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class CustomUserSerializer(UserSerializer):
    """
    Сериализатор пользователя с полями для подписки и аватара.
    """
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name',
                  'email', 'is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        """
        Проверяет, подписан ли текущий пользователь на obj.
        """
        user = self.context.get('request').user
        return (
            user.is_authenticated
            and user.followers.filter(following=obj).exists()
        )


class FollowSerializer(CustomUserSerializer):
    """
    Сериализатор подписки на пользователя с его рецептами.
    """
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.ReadOnlyField(source='recipes.count')

    class Meta(CustomUserSerializer.Meta):
        fields = tuple(CustomUserSerializer.Meta.fields) + (
            'recipes',
            'recipes_count'
        )

    def get_recipes(self, obj):
        """
        Возвращает ограниченный список рецептов пользователя.
        """
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit')
        recipes = obj.recipes.all()
        if recipes_limit and recipes_limit.isdigit():
            recipes = recipes[:int(recipes_limit)]
        return RecipeShortSerializer(
            recipes,
            many=True,
            context=self.context
        ).data

    def get_is_subscribed(self, obj):
        """
        Наследует логику проверки подписки.
        """
        return super().get_is_subscribed(obj)
