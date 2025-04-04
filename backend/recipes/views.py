from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponseRedirect
from django.views import View
from django.shortcuts import redirect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from core.fields import Base62Field
from core.filters import IngredientFilter, RecipeFilter
from core.paginations import CustomPagination
from core.permissions import IsAuthorOrReadOnly
from core.utils import FileFactory, FileResponseFactory

from .models import Ingredient, Recipe, ShoppingCart, Tag, Favorite
from .serializers import (
    IngredientSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
    ShoppingCartCreateSerializer,
    TagSerializer,
    FavoriteCreateSerializer,
)

User = get_user_model()


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
    filter_backends = [DjangoFilterBackend]
    filterset_class = IngredientFilter


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
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        """
        Возвращает сериализатор в зависимости от метода действия.
        """
        if self.action in ['create', 'update', 'partial_update']:
            return RecipeWriteSerializer
        return RecipeReadSerializer

    def perform_create(self, serializer):
        """Сохраняет рецепт, связывая его с текущим пользователем."""
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=['get'],
        url_path='get-link',
        permission_classes=[permissions.AllowAny]
    )
    def get_link(self, request, pk=None):
        """Получить короткую ссылку на рецепт."""
        recipe = self.get_object()
        short_code = Base62Field.to_base62(recipe.id)
        short_link = request.build_absolute_uri(f'/r/{short_code}')
        return Response({'short-link': short_link}, status=status.HTTP_200_OK)

    def add_to_favorite_or_cart(self, serializer_class, pk):
        """Метод для добавления рецепта в избранное/корзину."""
        recipe = self.get_object()
        user = self.request.user
        serializer = serializer_class(
            data={'user': user.id, 'recipe': recipe.id},
            context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def remove_from_favorite_or_cart(self, model, pk):
        """Метод для удаления рецепта из избранного/корзины."""
        recipe = self.get_object()
        user = self.request.user
        if model.objects.filter(user=user, recipe=recipe).delete()[0]:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'detail': 'Рецепт не найден в избранном или корзине.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated],
        url_path='shopping_cart'
    )
    def add_to_shopping_cart(self, request, pk=None):
        """Добавить рецепт из корзины."""
        return self.add_to_favorite_or_cart(ShoppingCartCreateSerializer, pk)

    @add_to_shopping_cart.mapping.delete
    def remove_from_shopping_cart(self, request, pk=None):
        """Удалить рецепт из коризны."""
        return self.remove_from_favorite_or_cart(ShoppingCart, pk)

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
                status=status.HTTP_200_OK
            )
        ingredients = shopping_cart_items.values(
            'recipe__recipe_ingredients__ingredient__name'
        ).annotate(total_amount=Sum(
            'recipe__recipe_ingredients__amount'
        )).order_by(
            'recipe__recipe_ingredients__ingredient__name'
        )
        file_format = request.query_params.get('format', 'csv').lower()
        file_creator = FileFactory.create_file(ingredients, file_format)
        return FileResponseFactory.create_response(file_creator, file_format)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated],
        url_path='favorite'
    )
    def add_to_favorite(self, request, pk=None):
        """Добавить рецепт в избранное."""
        return self.add_to_favorite_or_cart(FavoriteCreateSerializer, pk)

    @add_to_favorite.mapping.delete
    def remove_from_favorite(self, request, pk=None):
        """Удалить рецепт из избранного."""
        return self.remove_from_favorite_or_cart(Favorite, pk)


class RecipeRedirectView(View):
    """Перенаправление на полный рецепт по короткому коду."""

    def get(self, short_code):
        try:
            recipe_id = Base62Field.from_base62(short_code)
        except ValueError:
            return Response(
                {'detail': 'Неверный короткий код.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        recipe = get_object_or_404(Recipe, id=recipe_id)
        return HttpResponseRedirect(f'/recipes/{recipe.id}/')
