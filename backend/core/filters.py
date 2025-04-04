import django_filters
from recipes.models import Ingredient
from django_filters import rest_framework as filters
from recipes.models import Recipe, Tag


class IngredientFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        field_name='name', lookup_expr='istartswith'
    )

    class Meta:
        model = Ingredient
        fields = ['name']


class RecipeFilter(filters.FilterSet):
    """Фильтрация рецептов по автору, тегам, избранному и списку покупок."""

    tags = filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        field_name='tags__slug',
        to_field_name='slug'
    )
    is_in_shopping_cart = filters.BooleanFilter(
        field_name='shoppingcart_by_users__user', method='filter_shopping_cart'
    )
    is_favorited = filters.BooleanFilter(
        field_name='favorite_by_users__user', method='filter_favorite'
    )

    class Meta:
        model = Recipe
        fields = ['author', 'tags', 'is_in_shopping_cart', 'is_favorited']

    def filter_shopping_cart(self, queryset, name, value):
        """Фильтрация по наличию в корзине."""
        if self.request.user.is_authenticated and value:
            return queryset.filter(
                shoppingcart_by_users__user=self.request.user
            )
        return queryset

    def filter_favorite(self, queryset, name, value):
        """Фильтрация по избранному."""
        if self.request.user.is_authenticated:
            if value:
                return queryset.filter(
                    favorite_by_users__user=self.request.user
                )
        return queryset
