from django.contrib.auth import get_user_model
from rest_framework import serializers
from djoser.serializers import UserSerializer as DjoserUserSerializer

from core.fields import Base64ImageField
from core.serializers import RecipeShortSerializer

User = get_user_model()


class UserSerializer(DjoserUserSerializer):
    """
    Сериализатор пользователя с полями для подписки и аватара.
    """
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'is_subscribed',
            'avatar'
        )

    def get_is_subscribed(self, obj):
        """
        Проверяет, подписан ли текущий пользователь на obj.
        """
        user = self.context.get('request').user
        return (
            user.is_authenticated
            and user.followers.filter(following=obj).exists()
        )


class FollowSerializer(UserSerializer):
    """
    Сериализатор подписки на пользователя с его рецептами.
    """
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.ReadOnlyField(source='recipes.count')

    class Meta(UserSerializer.Meta):
        fields = tuple(UserSerializer.Meta.fields) + (
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


class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для работы с аватаром пользователя."""
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)

    def validate_avatar(self, value):
        if not value:
            raise serializers.ValidationError("Поле 'avatar' обязательно.")
        return value
