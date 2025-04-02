from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import redirect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets, views
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from core.fields import Base62Field
from core.filters import IngredientFilter, RecipeFilter
from core.paginations import CustomPagination
from core.permissions import IsAuthorOrReadOnly
from core.utils import FileFactory

from .models import Ingredient, Recipe, ShoppingCart, Tag, Favorite
from .serializers import (
    RecipeShortSerializer,
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

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset

    def perform_create(self, serializer):
        """Сохраняет рецепт, связывая его с текущим пользователем."""
        serializer.save(author=self.request.user)

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

    def _handle_favorite_or_cart(self, model, serializer_class, request, pk):
        """Метод для добавления и удаления рецептов из избранного/корзины."""
        recipe = self.get_object()
        user = request.user

        if request.method == 'POST':
            if model.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'detail': 'Рецепт уже добавлен'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = serializer_class(
                data={'user': user.id, 'recipe': recipe.id},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(
                RecipeShortSerializer(recipe).data,
                status=status.HTTP_201_CREATED
            )

        elif request.method == 'DELETE':
            obj = model.objects.filter(user=user, recipe=recipe).first()
            if not obj:
                return Response(
                    {'detail': 'Рецепт не найден'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            obj.delete()
            return Response(
                {'detail': 'Рецепт удалён'},
                status=status.HTTP_204_NO_CONTENT
            )

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        """Добавить или удалить рецепт из корзины."""
        return self._handle_favorite_or_cart(
            ShoppingCart,
            ShoppingCartCreateSerializer,
            request,
            pk
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
        ingredients = shopping_cart_items.values(
            'recipe__recipe_ingredients__ingredient__name'
        ).annotate(total_amount=Sum(
            'recipe__recipe_ingredients__amount'
        )).order_by(
            'recipe__recipe_ingredients__ingredient__name'
        )
        file_format = request.query_params.get('format', 'csv').lower()
        file_creator = FileFactory(ingredients, file_format)
        file_data = file_creator.create_file()
        if file_format == 'csv':
            response = HttpResponse(file_data, content_type='text/csv')
            response[
                'Content-Disposition'
            ] = 'attachment; filename="shopping_cart.csv"'
        elif file_format == 'txt':
            response = HttpResponse(file_data, content_type='text/plain')
            response[
                'Content-Disposition'
            ] = 'attachment; filename="shopping_cart.txt"'
        elif file_format == 'pdf':
            response = HttpResponse(file_data, content_type='application/pdf')
            response[
                'Content-Disposition'
            ] = 'attachment; filename="shopping_cart.pdf"'
        else:
            return Response(
                {'detail': 'Unsupported file format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return response

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        """Добавить или удалить рецепт из избранного."""
        return self._handle_favorite_or_cart(
            Favorite,
            FavoriteCreateSerializer,
            request,
            pk
        )


class RecipeRedirectView(views.APIView):
    """Перенаправление на полный рецепт по короткому коду."""

    def get(self, request, short_code):
        try:
            recipe_id = Base62Field.from_base62(short_code)
        except ValueError:
            return Response(
                {'detail': 'Неверный короткий код.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        recipe = get_object_or_404(Recipe, id=recipe_id)
        return redirect(f'/recipes/{recipe.id}/')
