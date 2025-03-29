from djoser.serializers import UserSerializer
from rest_framework import serializers
from users.models import Follow, MyUser


class CustomUserSerializer(UserSerializer):
    """
    Сериализатор пользователя с полями для подписки и аватара.
    """
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = MyUser
        fields = ('id', 'username', 'first_name', 'last_name',
                  'email', 'is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        """
        Проверяет, подписан ли текущий пользователь на obj.
        """
        user = self.context.get('request').user
        return (
            user.is_authenticated
            and obj.follower.filter(user=user, following=obj).exists()
        )

    def get_avatar(self, obj):
        """
        Возвращает URL аватара пользователя или None.
        """
        if obj.avatar:
            return obj.avatar.url
        return None


class FollowSerializer(CustomUserSerializer):
    """
    Сериализатор подписки на пользователя с его рецептами.
    """
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.ReadOnlyField(source='recipes.count')

    class Meta(UserSerializer.Meta):
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar', 'recipes', 'recipes_count'
        )

    def get_recipes(self, obj):
        """
        Возвращает рецепты пользователя, ограниченные по количеству.
        """
        request = self.context.get('request')
        recipes_limit = request.query_params.get(
            'recipes_limit'
        ) if request else None
        recipes = obj.recipes.all()
        if recipes_limit and recipes_limit.isdigit():
            recipes = recipes[:int(recipes_limit)]
        return [
            {
                'id': recipe.id,
                'name': recipe.name,
                'image': recipe.image.url if recipe.image else None,
                'cooking_time': recipe.cooking_time,
            }
            for recipe in recipes
        ]

    def get_is_subscribed(self, obj):
        """
        Проверяет, подписан ли текущий пользователь на obj.
        """
        user = self.context.get('request').user
        return (
            user.is_authenticated
            and Follow.objects.filter(user=user, following=obj).exists()
        )

    def get_avatar(self, obj):
        """
        Возвращает URL аватара пользователя или None.
        """
        if obj.avatar:
            return obj.avatar.url
        return None
