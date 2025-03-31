import base64
import csv
import uuid
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.shortcuts import redirect
from djoser.views import UserViewSet as DjoserUserViewSet
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from core.paginations import CustomPagination
from core.permissions import IsAuthorOrReadOnly
from users.models import Follow
from users.serializers import CustomUserSerializer, FollowSerializer

from .models import Favorite, Ingredient, Recipe, ShoppingCart, Tag
from .serializers import (FavoriteSerializer, IngredientSerializer,
                          RecipeReadSerializer, RecipeWriteSerializer,
                          ShoppingCartSerializer, TagSerializer)

User = get_user_model()
BASE62 = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'


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


class UserViewSet(DjoserUserViewSet):
    """
    ViewSet для работы с пользователями.
    Включает методы для получения и изменения информации о пользователе.
    """
    queryset = User.objects.all().order_by('username')
    serializer_class = CustomUserSerializer
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
        Обрабатывает загрузку аватара пользователя.
        """
        user = request.user
        avatar_data = request.data.get('avatar')
        if not avatar_data:
            return Response(
                {'avatar': ['Это поле обязательно.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        if user.avatar:
            user.avatar.delete()
        fmt, imgstr = avatar_data.split(';base64,')
        ext = fmt.split('/')[-1]
        data = ContentFile(
            base64.b64decode(imgstr),
            name=f"{uuid.uuid4()}.{ext}"
        )
        user.avatar.save(data.name, data, save=True)
        return Response(
            {'avatar': request.build_absolute_uri(user.avatar.url)},
            status=status.HTTP_200_OK
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


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для работы с тегами.
    Предоставляет только доступ на чтение.
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для работы с ингредиентами.
    Предоставляет только доступ на чтение.
    """
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        """Фильтрует ингредиенты по имени."""
        queryset = super().get_queryset()
        name_filter = self.request.query_params.get('name', None)
        if name_filter:
            queryset = queryset.filter(name__istartswith=name_filter)
        return queryset


class RecipeViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с рецептами.
    Предоставляет методы для создания, чтения, обновления и удаления рецептов.
    """
    queryset = Recipe.objects.all()
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsAuthorOrReadOnly
    ]
    pagination_class = CustomPagination

    def get_serializer_class(self):
        """
        Возвращает сериализатор в зависимости от метода действия.
        """
        if self.action in ['create', 'update', 'partial_update']:
            return RecipeWriteSerializer
        return RecipeReadSerializer

    def get_queryset(self):
        """
        Фильтрует рецепты по автору и тегам.
        """
        queryset = super().get_queryset()
        author_id = self.request.query_params.get('author', None)
        if author_id is not None:
            author = get_object_or_404(User, pk=author_id)
            queryset = queryset.filter(author=author)
        tags_slugs = self.request.query_params.getlist('tags')
        if tags_slugs:
            tags = Tag.objects.filter(slug__in=tags_slugs)
            queryset = queryset.filter(tags__in=tags).distinct()
        is_in_shopping_cart = self.request.query_params.get(
            'is_in_shopping_cart'
        )
        if (
            is_in_shopping_cart
            is not None and self.request.user.is_authenticated
        ):
            if is_in_shopping_cart == '1':
                queryset = queryset.filter(
                    shoppingcart_by_users__user=self.request.user
                )
            elif is_in_shopping_cart == '0':
                queryset = queryset.exclude(
                    shoppingcart_by_users__user=self.request.user
                )
        is_favorited = self.request.query_params.get('is_favorited')
        if is_favorited is not None and self.request.user.is_authenticated:
            if is_favorited == '1':
                queryset = queryset.filter(
                    favorite_by_users__user=self.request.user
                )
            elif is_favorited == '0':
                queryset = queryset.exclude(
                    favorite_by_users__user=self.request.user
                )
        return queryset

    def perform_create(self, serializer):
        """Сохраняет рецепт, связывая его с текущим пользователем."""
        serializer.save(author=self.request.user)

    def create(self, request, *args, **kwargs):
        """Создание рецепта и возврат полного JSON-ответа."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recipe = serializer.save()
        read_serializer = RecipeReadSerializer(
            recipe,
            context={'request': request}
        )
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True, methods=['get'],
        url_path='get-link',
        permission_classes=[permissions.AllowAny]
    )
    def get_link(self, request, pk=None):
        """Получить короткую ссылку на рецепт."""
        recipe = self.get_object()
        short_code = Base62Field.to_base62(recipe.id)
        short_link = request.build_absolute_uri(f'/s/{short_code}')
        return Response({'short-link': short_link}, status=status.HTTP_200_OK)

    def redirect_to_recipe(self, request, short_code=None):
        """
        Перенаправление на полный рецепт по короткому коду.
        """
        try:
            recipe_id = Base62Field.from_base62(short_code)
        except ValueError:
            return Response(
                {'detail': 'Неверный короткий код.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        recipe = get_object_or_404(Recipe, id=recipe_id)
        redirect_url = request.build_absolute_uri(f'/recipes/{recipe.id}/')
        return redirect(redirect_url)

    @action(
        detail=True, methods=['post', 'delete'],
        url_path='shopping_cart',
        permission_classes=[permissions.IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        """
        Добавить или удалить рецепт из списка покупок пользователя.
        """
        recipe = self.get_object()
        user = request.user
        if request.method == 'POST':
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'detail': 'Рецепт уже в корзине'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            ShoppingCart.objects.create(user=user, recipe=recipe)
            return Response(
                ShoppingCartSerializer(recipe).data,
                status=status.HTTP_201_CREATED
            )
        elif request.method == 'DELETE':
            cart_item = ShoppingCart.objects.filter(
                user=user,
                recipe=recipe
            ).first()
            if not cart_item:
                return Response(
                    {'detail': 'Рецепта нет в корзине'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            cart_item.delete()
            return Response(
                {'detail': 'Рецепт удален из корзины'},
                status=status.HTTP_204_NO_CONTENT
            )

    @action(
        detail=False,
        methods=['get'],
        url_path='download_shopping_cart',
        permission_classes=[permissions.IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        """Скачать список покупок в формате CSV, TXT или PDF."""
        user = request.user
        shopping_cart_items = ShoppingCart.objects.filter(user=user)
        if not shopping_cart_items:
            return Response(
                {'detail': 'Shopping cart is empty'},
                status=status.HTTP_404_NOT_FOUND
            )
        file_format = request.query_params.get('format', 'csv').lower()
        if file_format == 'csv':
            return self._download_csv(shopping_cart_items)
        elif file_format == 'txt':
            return self._download_txt(shopping_cart_items)
        elif file_format == 'pdf':
            return self._download_pdf(shopping_cart_items)
        else:
            return Response(
                {'detail': 'Unsupported file format'},
                status=status.HTTP_400_BAD_REQUEST
            )

    def _download_csv(self, shopping_cart_items):
        """Создание файла CSV для скачивания списка покупок."""
        response = HttpResponse(content_type='text/csv')
        response[
            'Content-Disposition'
        ] = 'attachment; filename="shopping_cart.csv"'
        writer = csv.writer(response)
        writer.writerow(['Recipe Name', 'Ingredients'])
        for item in shopping_cart_items:
            recipe = item.recipe
            ingredients = ', '.join([
                ingredient.name
                for ingredient
                in recipe.ingredients.all()
            ])
            writer.writerow([recipe.name, ingredients])
        return response

    def _download_txt(self, shopping_cart_items):
        """Создание текстового файла для скачивания списка покупок."""
        response = HttpResponse(content_type='text/plain')
        response[
            'Content-Disposition'
        ] = 'attachment; filename="shopping_cart.txt"'
        content = []
        for item in shopping_cart_items:
            recipe = item.recipe
            ingredients = ', '.join([
                ingredient.name
                for ingredient
                in recipe.ingredients.all()
            ])
            content.append(
                f'Recipe: {recipe.name}\nIngredients: {ingredients}\n\n'
            )

        response.writelines(content)
        return response

    def _download_pdf(self, shopping_cart_items):
        """Создание PDF-файла для скачивания списка покупок."""
        response = HttpResponse(content_type='application/pdf')
        response[
            'Content-Disposition'
        ] = 'attachment; filename="shopping_cart.pdf"'
        buffer = StringIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        p.setFont("Helvetica-Bold", 12)
        p.drawString(100, height - 40, "Shopping Cart")
        y_position = height - 60
        for item in shopping_cart_items:
            recipe = item.recipe
            ingredients = ', '.join([
                ingredient.name
                for ingredient
                in recipe.ingredients.all()
            ])
            p.setFont("Helvetica", 10)
            p.drawString(100, y_position, f'Recipe: {recipe.name}')
            y_position -= 20
            p.drawString(100, y_position, f'Ingredients: {ingredients}')
            y_position -= 40
            if y_position < 60:
                p.showPage()
                y_position = height - 60
        p.showPage()
        p.save()
        response.write(buffer.getvalue())
        buffer.close()
        return response

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='favorite',
        permission_classes=[permissions.IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        """Добавить или удалить рецепт из избранного."""
        recipe = self.get_object()
        user = request.user
        if request.method == 'POST':
            if Favorite.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'detail': 'Рецепт уже в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Favorite.objects.create(user=user, recipe=recipe)
            return Response(
                FavoriteSerializer(recipe, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )

        elif request.method == 'DELETE':
            favorite = Favorite.objects.filter(
                user=user,
                recipe=recipe
            ).first()
            if not favorite:
                return Response(
                    {'detail': 'Рецепта нет в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            favorite.delete()
            return Response(
                {'detail': 'Рецепт удален из избранного'},
                status=status.HTTP_204_NO_CONTENT
            )
