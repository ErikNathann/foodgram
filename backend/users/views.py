from django.contrib.auth import get_user_model

from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from core.paginations import CustomPagination

from .models import Follow
from .serializers import (
    AvatarSerializer,
    FollowSerializer,
    FollowCreateSerializer,
    UserSerializer
)

User = get_user_model()


class UserViewSet(DjoserUserViewSet):
    """
    ViewSet для работы с пользователями.
    Включает методы для получения и изменения информации о пользователе.
    """
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    pagination_class = CustomPagination
    permission_classes = [permissions.AllowAny]

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def me(self, request):
        """
        Возвращает информацию о текущем пользователе.
        Если пользователь не авторизован, вернет 401.
        """
        return Response(
            self.get_serializer(request.user).data,
            status=status.HTTP_200_OK
        )

    @action(
        detail=False,
        methods=['put'],
        permission_classes=[permissions.IsAuthenticated],
        url_path='me/avatar'
    )
    def upload_avatar(self, request):
        """
        Обрабатывает загрузку нового аватара для пользователя.
        """
        user = request.user
        serializer = AvatarSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @upload_avatar.mapping.delete
    def delete_avatar(self, request):
        """
        Удаляет аватар пользователя.
        """
        user = request.user
        if user.avatar:
            user.avatar.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated],
        url_path='subscribe'
    )
    def subscribe(self, request, id=None):
        """
        Подписка на пользователя.
        """
        following_user = get_object_or_404(User, pk=id)
        data = {
            'user': request.user.id,
            'following': following_user.id
        }
        serializer = FollowCreateSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        follow = serializer.save()
        response_serializer = FollowSerializer(follow.following, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request, id=None):
        """
        Отписка от пользователя.
        """
        following_user = get_object_or_404(User, pk=id)
        deleted, _ = Follow.objects.filter(
            user=request.user,
            following=following_user
        ).delete()
        if deleted == 0:
            return Response(
                {'detail': 'Вы не подписаны на этого пользователя.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        if self.action == 'subscriptions':
            return User.objects.filter(following__user=self.request.user)
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action == 'subscriptions':
            return FollowSerializer
        return super().get_serializer_class()

    @action(
        detail=False,
        methods=['get'],
        url_path='subscriptions',
        permission_classes=[permissions.IsAuthenticated]
    )
    def subscriptions(self, request, *args, **kwargs):
        """
        Получить список подписок текущего пользователя.
        """
        self.action = 'subscriptions'
        return self.list(request, *args, **kwargs)
