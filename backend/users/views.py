import base64
import uuid

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from core.paginations import CustomPagination

from .models import Follow
from .serializers import AvatarSerializer, FollowSerializer, UserSerializer

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
        detail=False, methods=['get'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def me(self, request, *args, **kwargs):
        """
        Возвращает информацию о текущем пользователе.
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
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'avatar': request.build_absolute_uri(user.avatar.url)},
                status=status.HTTP_200_OK
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    @upload_avatar.mapping.delete
    def delete_avatar(self, request):
        """
        Удаляет аватар пользователя.
        """
        user = request.user
        if user.avatar:
            user.avatar.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'detail': 'Аватар отсутствует.'},
            status=status.HTTP_404_NOT_FOUND
        )

    @action(
        detail=True, methods=['post', 'delete'],
        url_path='subscribe',
        permission_classes=[permissions.IsAuthenticated]
    )
    def manage_subscription(self, request, id=None):
        """
        Подписка/отписка на пользователя.
        """
        user = request.user
        following_user = get_object_or_404(User, pk=id)
        if user == following_user:
            return Response(
                {'detail': 'Невозможно подписаться на самого себя.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if request.method == 'POST':
            if Follow.objects.filter(
                user=user,
                following=following_user
            ).exists():
                return Response(
                    {'detail': 'Вы уже подписаны на этого пользователя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            follow = Follow.objects.create(user=user, following=following_user)
            return Response(
                FollowSerializer(
                    follow.following,
                    context={'request': request}
                ).data,
                status=status.HTTP_201_CREATED
            )
        follow_instance = Follow.objects.filter(
            user=user,
            following=following_user
        ).first()
        if not follow_instance:
            return Response(
                {'detail': 'Вы не подписаны на этого пользователя.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        follow_instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False,
            methods=['get'],
            url_path='subscriptions',
            permission_classes=[permissions.IsAuthenticated]
            )
    def get_subscriptions(self, request):
        """
        Получить список подписок текущего пользователя.
        """
        user = request.user
        subscriptions = User.objects.filter(following__user=user)
        page = self.paginate_queryset(subscriptions)
        serializer = FollowSerializer(
            page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)
